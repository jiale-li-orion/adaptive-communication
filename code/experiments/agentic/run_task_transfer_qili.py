#!/usr/bin/env python3
"""Formal source-derived Operational Task transfer gate using the Qili monitoring record."""
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
from agentic_communication.planner import DeterministicComplyPlannerConsumer  # noqa: E402
from agentic_communication.replay import audit_trace  # noqa: E402
from agentic_communication.run import (  # noqa: E402
    DEFAULT_FULLSIM,
    run_agentic_episode,
    run_reference_comply,
)
from agentic_communication.task_transfer import qili_2016_rainfall_deformation_profile  # noqa: E402
from run_o2_risk_escalation import _source_manifest  # noqa: E402


DEFAULT_OUT = ROOT / "results" / "agentic" / "task-transfer-qili-v1"


def _dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="0,1,2,3,4")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    seeds = [int(x) for x in args.seeds.split(",") if x.strip()]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    hand = o2_risk_escalation_task(task_hours=12)
    source_profile = qili_2016_rainfall_deformation_profile()
    qili = source_profile.to_operational_task(task_hours=12)
    tasks = {
        "hand_authored_o2": hand,
        "qili_source_derived": qili,
    }
    simulator = dict(DEFAULT_FULLSIM)
    contract = {
        "experiment_id": "task-transfer-qili-v1",
        "seeds": seeds,
        "task_schedules": {
            key: task.model_dump(mode="json") for key, task in tasks.items()
        },
        "planner_consumer": "DeterministicComplyPlannerConsumer",
        "context_mode": "task_conditioned",
        "simulator": simulator,
        "simulator_authority": "code/agentic_communication/run.py::DEFAULT_FULLSIM",
        "method_invariant": (
            "same deployment/exogenous communication world/runtime/capabilities/planner/scorer; "
            "only Operational Task authority/schedule changes"
        ),
        "claim_ceiling": (
            "Secondary task-authority transfer only. Supports that a literature-derived monitoring regime can be "
            "compiled and executed through the unchanged Agentic Communication runtime with paired physical "
            "equivalence. Cross-schedule metric differences are task-demand differences, not method gains; the "
            "compressed schedule is not a Qili field warning threshold."
        ),
    }
    _dump(out / "experiment_contract.json", contract)
    source_manifest = _source_manifest(qili, simulator)
    source_manifest["external_task_authority"] = {
        "source_ref": "S14",
        "source_registry": "research/sources.json",
        "url": "https://www.mdpi.com/1424-8220/21/1/14",
        "transform_rule": source_profile.transform_rule,
        "claim_boundary": source_profile.claim_boundary,
    }
    _dump(out / "source_manifest.json", source_manifest)

    rows = []
    replay_rows = []
    with (out / "per_episode_results.jsonl").open("w", encoding="utf-8") as fh:
        for seed in seeds:
            for schedule_id, task in tasks.items():
                reference, _, _ = run_reference_comply(
                    seed=seed,
                    operational_task=task,
                    simulator_kwargs=simulator,
                )
                result, policy, _, _ = run_agentic_episode(
                    seed=seed,
                    operational_task=task,
                    context_mode="task_conditioned",
                    planner_consumer=DeterministicComplyPlannerConsumer(),
                    simulator_kwargs=simulator,
                )
                trace_path = out / "runtime_traces" / f"seed-{seed:03d}-{schedule_id}.jsonl"
                policy.trace.write_jsonl(trace_path)
                replay = audit_trace(trace_path, context_mode="task_conditioned")
                replay_rows.append({"seed": seed, "schedule": schedule_id, **replay})
                row = {
                    "seed": seed,
                    "schedule": schedule_id,
                    "task_id": task.task_id,
                    "source_refs": list(task.source_refs),
                    "phases": [x.model_dump(mode="json") for x in task.phases],
                    "physical_equal_reference": physical_signature(reference) == physical_signature(result),
                    "replay_passed": bool(replay["passed"]),
                    "communication_metrics": result["agentic"]["communication_metrics"],
                    "agent_metrics": result["agentic"]["agent_metrics"],
                    "trace_path": _display_path(trace_path),
                }
                rows.append(row)
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    by_schedule = {}
    for schedule_id in tasks:
        selected = [row for row in rows if row["schedule"] == schedule_id]
        keys = (
            "timely_delivery_rate",
            "collection_rate",
            "delivery_latency_p90_s",
            "backup_bytes",
            "total_consumed_wh",
        )
        by_schedule[schedule_id] = {
            "n": len(selected),
            "physical_equal_reference": all(row["physical_equal_reference"] for row in selected),
            "replay_exact": all(row["replay_passed"] for row in selected),
            "mean": {
                key: statistics.fmean(
                    float(row["communication_metrics"][key]) for row in selected
                    if row["communication_metrics"].get(key) is not None
                )
                for key in keys
            },
        }
    aggregate = {
        "n_seeds": len(seeds),
        "schedules": by_schedule,
        "all_physical_equal_reference": all(row["physical_equal_reference"] for row in rows),
        "all_replay_exact": all(row["replay_passed"] for row in rows),
        "source_schedule_differs_from_hand_authored": (
            [x.model_dump(mode="json") for x in hand.phases]
            != [x.model_dump(mode="json") for x in qili.phases]
        ),
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
            "schedules": list(tasks),
            "runtime": "code/agentic_communication/",
        },
    )
    passed = (
        aggregate["all_physical_equal_reference"]
        and aggregate["all_replay_exact"]
        and aggregate["source_schedule_differs_from_hand_authored"]
        and all(row["expected"] for row in [
            {"expected": "S14" in qili.source_refs},
            {"expected": hand.task_id != qili.task_id},
        ])
    )
    audit = {
        "status": "PASS" if passed else "FAIL",
        **aggregate,
        "same_runtime_and_planner": True,
        "qili_source_ref_present": "S14" in qili.source_refs,
        "trace_files": len(list((out / "runtime_traces").glob("*.jsonl"))),
        "expected_trace_files": len(seeds) * len(tasks),
        "claim_ceiling": contract["claim_ceiling"],
        "result_hashes": {
            str(path.relative_to(out)): _sha(path)
            for path in sorted(out.rglob("*"))
            if path.is_file() and path.name != "audit.json"
        },
    }
    _dump(out / "audit.json", audit)
    print(json.dumps({"audit": audit, "aggregate": aggregate}, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
