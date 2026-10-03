#!/usr/bin/env python3
"""Formal paired O2 Agent/runtime baseline matrix."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
ROOT = CODE.parent
for p in (
    HERE,
    CODE,
    CODE / "substrate" / "joint",
    CODE / "substrate" / "instance",
    CODE / "substrate" / "monitoring",
    CODE / "substrate" / "physics",
    CODE / "substrate" / "runtime",
    CODE / "evaluation" / "agentic",
    CODE / "legacy-communication" / "analysis",
):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from agentic_communication.episodes import o2_risk_escalation_task  # noqa: E402
from agentic_communication.metrics import physical_signature  # noqa: E402
from agentic_communication.planner import (  # noqa: E402
    DeterministicComplyPlannerConsumer,
    DiagnosisFirstPlannerConsumer,
    EvidenceAwareComplyPlannerConsumer,
    FixedOrderEagerPlannerConsumer,
)
from agentic_communication.replay import audit_trace  # noqa: E402
from agentic_communication.run import DEFAULT_FULLSIM, run_agentic_episode  # noqa: E402
from run_o2_risk_escalation import _source_manifest  # noqa: E402


DEFAULT_OUT = ROOT / "results" / "agentic" / "o2-baseline-matrix-v1"

ARM_SPECS = {
    "deterministic_comply": {
        "factory": DeterministicComplyPlannerConsumer,
        "context_mode": "task_conditioned",
    },
    "evidence_aware": {
        "factory": EvidenceAwareComplyPlannerConsumer,
        "context_mode": "task_conditioned",
    },
    "diagnosis_first": {
        "factory": DiagnosisFirstPlannerConsumer,
        "context_mode": "task_conditioned",
    },
    "fixed_order_eager": {
        "factory": FixedOrderEagerPlannerConsumer,
        "context_mode": "task_conditioned",
    },
    "generic_react": {
        "factory": DeterministicComplyPlannerConsumer,
        "context_mode": "generic_react",
    },
}


def _dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _total_materialized(metrics: dict) -> float:
    return float(metrics.get("mean_materialized_bytes", 0.0) or 0.0) * float(
        metrics.get("context_manifests", metrics.get("contexts", 0)) or 0
    )


def _scalar_overhead(metrics: dict) -> dict:
    return {
        "model_requests": int(metrics.get("model_requests", 0) or 0),
        "capability_requests": int(metrics.get("capability_requests", 0) or 0),
        "percepts": int(metrics.get("percepts", 0) or 0),
        "context_manifests": int(metrics.get("context_manifests", 0) or 0),
        "total_materialized_bytes": _total_materialized(metrics),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="0,1,2,3,4")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    seeds = [int(x) for x in args.seeds.split(",") if x.strip()]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    task = o2_risk_escalation_task()
    simulator = dict(DEFAULT_FULLSIM)
    contract = {
        "experiment_id": "o2-baseline-matrix-v1",
        "seeds": seeds,
        "task_id": task.task_id,
        "arm_specs": {
            arm: {
                "context_mode": spec["context_mode"],
                "planner_consumer": spec["factory"].__name__,
            }
            for arm, spec in ARM_SPECS.items()
        },
        "arms": list(ARM_SPECS),
        "simulator": simulator,
        "simulator_authority": "code/agentic_communication/run.py::DEFAULT_FULLSIM",
        "primary_comparison": (
            "paired runtime overhead under identical physical policy/outcome; "
            "deterministic_comply is the reference arm"
        ),
        "claim_ceiling": (
            "O2 deterministic baseline comparison only. Supports statements about unnecessary "
            "Agent/runtime work under the same paired physical outcome; does not establish LLM "
            "quality or a communication-service gain."
        ),
    }
    _dump(out / "experiment_contract.json", contract)
    _dump(out / "source_manifest.json", _source_manifest(task, simulator))

    rows = []
    replay_rows = []
    with (out / "per_episode_results.jsonl").open("w", encoding="utf-8") as fh:
        for seed in seeds:
            arm_results = {}
            arm_metrics = {}
            for arm, spec in ARM_SPECS.items():
                result, policy, _, _ = run_agentic_episode(
                    seed=seed,
                    operational_task=task,
                    context_mode=spec["context_mode"],
                    planner_consumer=spec["factory"](),
                    simulator_kwargs=simulator,
                )
                arm_results[arm] = result
                arm_metrics[arm] = result["agentic"]["agent_metrics"]
                trace_path = out / "runtime_traces" / f"seed-{seed:03d}-{arm}.jsonl"
                policy.trace.write_jsonl(trace_path)
                replay = audit_trace(trace_path, context_mode=spec["context_mode"])
                replay_rows.append({"seed": seed, "arm": arm, **replay})

            reference_signature = physical_signature(arm_results["deterministic_comply"])
            physical_equal = {
                arm: physical_signature(result) == reference_signature
                for arm, result in arm_results.items()
            }
            reference_overhead = _scalar_overhead(arm_metrics["deterministic_comply"])
            overhead = {arm: _scalar_overhead(m) for arm, m in arm_metrics.items()}
            deltas = {
                arm: {
                    key: float(overhead[arm][key]) - float(reference_overhead[key])
                    for key in reference_overhead
                }
                for arm in ARM_SPECS
                if arm != "deterministic_comply"
            }
            row = {
                "seed": seed,
                "physical_equal_reference": physical_equal,
                "agent_metrics": arm_metrics,
                "runtime_overhead": overhead,
                "paired_delta_vs_deterministic": deltas,
            }
            rows.append(row)
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    delta_arms = [a for a in ARM_SPECS if a != "deterministic_comply"]
    delta_keys = list(_scalar_overhead({}))
    aggregate = {
        "n": len(rows),
        "all_physical_equal_reference": all(
            all(row["physical_equal_reference"].values()) for row in rows
        ),
        "paired_delta_mean": {
            arm: {
                key: statistics.fmean(
                    float(row["paired_delta_vs_deterministic"][arm][key]) for row in rows
                )
                for key in delta_keys
            }
            for arm in delta_arms
        },
        "paired_delta_median": {
            arm: {
                key: statistics.median(
                    float(row["paired_delta_vs_deterministic"][arm][key]) for row in rows
                )
                for key in delta_keys
            }
            for arm in delta_arms
        },
    }
    _dump(out / "aggregate.json", aggregate)
    _dump(out / "replay_audit.json", {"runs": replay_rows})
    _dump(
        out / "run_manifest.json",
        {
            "generated_at": datetime.now(UTC).isoformat(),
            "python": sys.version,
            "cwd": str(ROOT),
            "seeds": seeds,
            "arms": list(ARM_SPECS),
            "runtime": "code/agentic_communication/",
            "baseline_registry": "research/policy/BASELINE-REGISTRY.v1.json",
        },
    )
    all_replay = all(row["passed"] for row in replay_rows)
    diag_positive = all(
        row["paired_delta_vs_deterministic"]["diagnosis_first"]["model_requests"] > 0
        and row["paired_delta_vs_deterministic"]["diagnosis_first"]["capability_requests"] > 0
        for row in rows
    )
    fixed_positive = all(
        row["paired_delta_vs_deterministic"]["fixed_order_eager"]["model_requests"] > 0
        and row["paired_delta_vs_deterministic"]["fixed_order_eager"]["capability_requests"] > 0
        for row in rows
    )
    evidence_no_extra = all(
        row["paired_delta_vs_deterministic"]["evidence_aware"]["capability_requests"] == 0
        for row in rows
    )
    status = (
        "PASS"
        if aggregate["all_physical_equal_reference"]
        and all_replay
        and diag_positive
        and fixed_positive
        and evidence_no_extra
        else "FAIL"
    )
    audit = {
        "status": status,
        "all_physical_equal_reference": aggregate["all_physical_equal_reference"],
        "all_replay_exact": all_replay,
        "diagnosis_first_overhead_positive_each_seed": diag_positive,
        "fixed_order_overhead_positive_each_seed": fixed_positive,
        "evidence_aware_no_irrelevant_probe_each_seed": evidence_no_extra,
        "trace_files": len(list((out / "runtime_traces").glob("*.jsonl"))),
        "expected_trace_files": len(seeds) * len(ARM_SPECS),
        "result_hashes": {
            str(p.relative_to(out)): _sha(p)
            for p in sorted(out.rglob("*"))
            if p.is_file() and p.name != "audit.json"
        },
    }
    _dump(out / "audit.json", audit)
    print(json.dumps({"audit": audit, "aggregate": aggregate}, ensure_ascii=False, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
