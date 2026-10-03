#!/usr/bin/env python3
"""No-API gate for the held-out Qili + NASA POWER 2024/w1 coordinate."""
from __future__ import annotations

import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
ROOT = HERE.parents[2]
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from agentic_communication.benchmark_split import WINDOW_START_HOURS  # noqa: E402
from agentic_communication.metrics import physical_signature  # noqa: E402
from agentic_communication.planner import CompiledChecklistPlannerConsumer  # noqa: E402
from agentic_communication.run import DEFAULT_FULLSIM, run_agentic_episode, run_reference_comply  # noqa: E402
from agentic_communication.task_transfer import qili_2016_rainfall_deformation_profile  # noqa: E402


OUT = ROOT / "results" / "agentic" / "heldout-qili-2024-w1" / "gate.json"
SEEDS = tuple(range(5))


def _requested(policy) -> list[dict]:
    assemblies = {}
    for event in policy.trace.events:
        if event.event_type == "prompt_assembly":
            assemblies[str(event.payload.get("assembly_id"))] = event
    rows = []
    for event in policy.trace.events:
        if event.event_type != "model_request":
            continue
        assembly = assemblies[str(event.payload.get("assembly_id"))]
        fragments = {
            str(row.get("kind")): row.get("content")
            for row in assembly.payload.get("fragments", [])
            if isinstance(row, dict)
        }
        candidate = fragments.get("candidate_action_context") or {}
        plans = [row for row in candidate.get("candidate_plans", []) if isinstance(row, dict)]
        ready = [
            row
            for row in plans
            if row.get("feasibility") == "supported"
            and not bool(row.get("unresolved_conditions"))
        ]
        needs = [row for row in (fragments.get("evidence_needs") or []) if isinstance(row, dict)]
        rows.append(
            {
                "t_s": int(event.t_s),
                "ready_plan_ids": [str(row.get("plan_id")) for row in ready],
                "visible_need_ids": [str(row.get("need_id")) for row in needs],
                "evidence_count": len(fragments.get("evidence_slice") or []),
                "has_sufficiency": "decision_sufficiency" in candidate,
            }
        )
    return rows


def main() -> int:
    profile = qili_2016_rainfall_deformation_profile()
    task = profile.to_operational_task(task_hours=12)
    simulator = dict(DEFAULT_FULLSIM)
    simulator.update(
        {
            "harvest_mode": "irradiance",
            "irradiance_year": 2024,
            "irradiance_start_hour": WINDOW_START_HOURS["w1"],
        }
    )

    episodes = []
    failures = []
    for seed in SEEDS:
        reference, _, _ = run_reference_comply(
            seed=seed,
            operational_task=task,
            simulator_kwargs=simulator,
        )
        results = {}
        for mode in ("action_conditioned_compact", "woa_style"):
            result, policy, _, _ = run_agentic_episode(
                seed=seed,
                operational_task=task,
                context_mode=mode,
                planner_consumer=CompiledChecklistPlannerConsumer(),
                planner_replan_mode="decision_state",
                simulator_kwargs=simulator,
            )
            results[mode] = (result, _requested(policy))

        compact_result, compact_rows = results["action_conditioned_compact"]
        woa_result, woa_rows = results["woa_style"]
        physical_compact = physical_signature(compact_result) == physical_signature(reference)
        physical_woa = physical_signature(woa_result) == physical_signature(reference)
        same_times = [row["t_s"] for row in compact_rows] == [row["t_s"] for row in woa_rows]
        all_unique = all(len(row["ready_plan_ids"]) == 1 for row in compact_rows)
        no_needs = all(not row["visible_need_ids"] for row in compact_rows)
        woa_no_needs = all(not row["visible_need_ids"] for row in woa_rows)
        suff_compact = all(row["has_sufficiency"] for row in compact_rows)
        suff_woa = any(row["has_sufficiency"] for row in woa_rows)
        evidence_superset = all(
            right["evidence_count"] >= left["evidence_count"]
            for left, right in zip(compact_rows, woa_rows, strict=True)
        ) if len(compact_rows) == len(woa_rows) else False

        row = {
            "seed": seed,
            "planner_requests": len(compact_rows),
            "physical_equal_reference_compact": physical_compact,
            "physical_equal_reference_woa": physical_woa,
            "same_request_times": same_times,
            "all_requests_unique_ready_plan": all_unique,
            "compact_visible_needs_zero": no_needs,
            "woa_visible_needs_zero": woa_no_needs,
            "compact_all_have_sufficiency": suff_compact,
            "woa_any_sufficiency_leak": suff_woa,
            "woa_evidence_superset": evidence_superset,
            "request_times_s": [r["t_s"] for r in compact_rows],
        }
        episodes.append(row)
        if not all(
            (
                physical_compact,
                physical_woa,
                same_times,
                all_unique,
                no_needs,
                woa_no_needs,
                suff_compact,
                not suff_woa,
                evidence_superset,
            )
        ):
            failures.append(row)

    payload = {
        "experiment": "heldout-qili-2024-w1-gate",
        "status": "PASS" if not failures else "FAIL",
        "heldout_coordinate": {
            "task": "qili_source_derived",
            "task_id": task.task_id,
            "task_source_refs": list(task.source_refs),
            "task_phases": [row.model_dump(mode="json") for row in task.phases],
            "source_split": "test",
            "irradiance_year": 2024,
            "window_id": "w1",
            "irradiance_start_hour": WINDOW_START_HOURS["w1"],
            "simulator_overrides": simulator,
            "claim_boundary": profile.claim_boundary,
        },
        "seeds": list(SEEDS),
        "episodes": episodes,
        "failures": failures,
        "aggregate": {
            "episodes": len(episodes),
            "planner_requests": sum(row["planner_requests"] for row in episodes),
            "physical_compact_exact": sum(row["physical_equal_reference_compact"] for row in episodes),
            "physical_woa_exact": sum(row["physical_equal_reference_woa"] for row in episodes),
            "unique_ready_plan_episodes": sum(row["all_requests_unique_ready_plan"] for row in episodes),
            "zero_visible_need_episodes": sum(row["compact_visible_needs_zero"] for row in episodes),
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

