#!/usr/bin/env python3
"""Paired O2 baseline: direct deterministic comply vs fixed diagnosis-first."""
from __future__ import annotations

import argparse
from collections import defaultdict
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
    CODE / "v3joint",
    CODE / "instance",
    CODE / "monitoring",
    CODE / "physics",
    CODE / "runtime",
    CODE / "experiments",
    CODE / "analysis",
):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from agentic_communication.episodes import o2_risk_escalation_task  # noqa: E402
from agentic_communication.metrics import physical_signature  # noqa: E402
from agentic_communication.planner import (  # noqa: E402
    DeterministicComplyPlannerConsumer,
    DiagnosisFirstPlannerConsumer,
)
from agentic_communication.replay import audit_trace  # noqa: E402
from agentic_communication.run import DEFAULT_FULLSIM, run_agentic_episode  # noqa: E402
from run_o2_risk_escalation import _source_manifest  # noqa: E402


DEFAULT_OUT = ROOT / "results" / "agentic" / "o2-diagnosis-first-v1"


def _dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _total_materialized_bytes(metrics: dict) -> float:
    return float(metrics.get("mean_materialized_bytes", 0.0) or 0.0) * float(
        metrics.get("context_manifests", metrics.get("contexts", 0)) or 0
    )


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
        "experiment_id": "o2-diagnosis-first-v1",
        "seeds": seeds,
        "task_id": task.task_id,
        "arms": ["deterministic_comply", "diagnosis_first_fixed"],
        "context_mode": "task_conditioned",
        "simulator": simulator,
        "simulator_authority": "code/agentic_communication/run.py::DEFAULT_FULLSIM",
        "claim_ceiling": (
            "Deterministic efficiency baseline only: on O2, a fixed gateway diagnosis phase can "
            "increase Agent/model/tool/context work without changing the paired communication "
            "policy or physical outcome. No LLM-quality or general communication gain is claimed."
        ),
    }
    _dump(out / "experiment_contract.json", contract)
    _dump(out / "source_manifest.json", _source_manifest(task, simulator))

    rows = []
    replay_rows = []
    physical_equal = []
    with (out / "per_episode_results.jsonl").open("w", encoding="utf-8") as fh:
        for seed in seeds:
            direct, p_direct, _, _ = run_agentic_episode(
                seed=seed,
                operational_task=task,
                context_mode="task_conditioned",
                planner_consumer=DeterministicComplyPlannerConsumer(),
                simulator_kwargs=simulator,
            )
            diag, p_diag, _, _ = run_agentic_episode(
                seed=seed,
                operational_task=task,
                context_mode="task_conditioned",
                planner_consumer=DiagnosisFirstPlannerConsumer(),
                simulator_kwargs=simulator,
            )
            equal = physical_signature(direct) == physical_signature(diag)
            physical_equal.append({"seed": seed, "physical_equal": equal})
            metrics = {
                "deterministic_comply": direct["agentic"]["agent_metrics"],
                "diagnosis_first_fixed": diag["agentic"]["agent_metrics"],
            }
            for arm, policy in (("deterministic_comply", p_direct), ("diagnosis_first_fixed", p_diag)):
                trace_path = out / "runtime_traces" / f"seed-{seed:03d}-{arm}.jsonl"
                policy.trace.write_jsonl(trace_path)
                replay = audit_trace(trace_path, context_mode="task_conditioned")
                replay_rows.append({"seed": seed, "arm": arm, **replay})

            a = metrics["deterministic_comply"]
            b = metrics["diagnosis_first_fixed"]
            row = {
                "seed": seed,
                "physical_equal": equal,
                "direct": a,
                "diagnosis_first": b,
                "paired_delta": {
                    "model_requests": b["model_requests"] - a["model_requests"],
                    "capability_requests": b["capability_requests"] - a["capability_requests"],
                    "context_manifests": b["context_manifests"] - a["context_manifests"],
                    "percepts": b["percepts"] - a["percepts"],
                    "total_materialized_bytes": _total_materialized_bytes(b) - _total_materialized_bytes(a),
                },
            }
            rows.append(row)
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    delta_keys = sorted(rows[0]["paired_delta"]) if rows else []
    paired_mean = {
        key: statistics.fmean(float(row["paired_delta"][key]) for row in rows)
        for key in delta_keys
    }
    paired_median = {
        key: statistics.median(float(row["paired_delta"][key]) for row in rows)
        for key in delta_keys
    }
    aggregate = {
        "n": len(rows),
        "paired_delta_mean": paired_mean,
        "paired_delta_median": paired_median,
        "all_physical_equal": all(row["physical_equal"] for row in rows),
    }
    _dump(out / "aggregate.json", aggregate)
    _dump(out / "replay_audit.json", {"runs": replay_rows})
    run_manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "python": sys.version,
        "cwd": str(ROOT),
        "seeds": seeds,
        "arms": contract["arms"],
        "runtime": "code/agentic_communication/",
        "baseline_registry": "research/AGENTIC-BASELINE-REGISTRY.v1.json",
    }
    _dump(out / "run_manifest.json", run_manifest)
    all_replay = all(row["passed"] for row in replay_rows)
    overhead_positive = all(
        row["paired_delta"]["model_requests"] > 0
        and row["paired_delta"]["capability_requests"] > 0
        for row in rows
    )
    audit = {
        "status": "PASS" if aggregate["all_physical_equal"] and all_replay and overhead_positive else "FAIL",
        "all_physical_equal": aggregate["all_physical_equal"],
        "all_replay_exact": all_replay,
        "overhead_positive_each_seed": overhead_positive,
        "trace_files": len(list((out / "runtime_traces").glob("*.jsonl"))),
        "expected_trace_files": len(seeds) * 2,
        "result_hashes": {
            str(p.relative_to(out)): _sha(p)
            for p in sorted(out.rglob("*"))
            if p.is_file() and p.name != "audit.json"
        },
    }
    _dump(out / "audit.json", audit)
    print(json.dumps({"audit": audit, "aggregate": aggregate}, ensure_ascii=False, indent=2))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
