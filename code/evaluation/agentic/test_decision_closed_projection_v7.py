#!/usr/bin/env python3
"""v7 retires inactive-plan unresolved guards without changing control semantics."""
from __future__ import annotations

from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from agentic_communication.benchmark_split import WINDOW_START_HOURS  # noqa: E402
from agentic_communication.metrics import physical_signature  # noqa: E402
from agentic_communication.planner import CompiledChecklistPlannerConsumer  # noqa: E402
from agentic_communication.run import DEFAULT_FULLSIM, run_agentic_episode  # noqa: E402
from agentic_communication.task_transfer import qili_2016_rainfall_deformation_profile  # noqa: E402


def _requested(policy):
    assemblies = {
        str(event.payload.get("assembly_id")): event
        for event in policy.trace.events
        if event.event_type == "prompt_assembly"
    }
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
        rows.append((int(event.t_s), fragments))
    return rows


def _plan(candidate: dict, plan_id: str) -> dict:
    rows = [
        row
        for row in candidate.get("candidate_plans", [])
        if isinstance(row, dict) and row.get("plan_id") == plan_id
    ]
    assert len(rows) == 1, (plan_id, rows)
    return rows[0]


def _semantic_plan(plan: dict) -> dict:
    return {
        key: plan.get(key)
        for key in (
            "plan_id",
            "kind",
            "feasibility",
            "decision_guards",
            "affected_resources",
            "invocations",
            "contradicted_by",
            "reason",
        )
    }


def main() -> int:
    task = qili_2016_rainfall_deformation_profile().to_operational_task(task_hours=12)
    simulator = dict(DEFAULT_FULLSIM)
    simulator.update(
        {
            "harvest_mode": "irradiance",
            "irradiance_year": 2024,
            "irradiance_start_hour": WINDOW_START_HOURS["w1"],
        }
    )
    outputs = {}
    for mode in ("action_conditioned_compact", "action_conditioned_compact_v7"):
        result, policy, _, _ = run_agentic_episode(
            seed=0,
            operational_task=task,
            context_mode=mode,
            planner_consumer=CompiledChecklistPlannerConsumer(),
            planner_replan_mode="decision_state",
            simulator_kwargs=simulator,
        )
        outputs[mode] = (result, _requested(policy))

    old_result, old_rows = outputs["action_conditioned_compact"]
    new_result, new_rows = outputs["action_conditioned_compact_v7"]
    assert physical_signature(old_result) == physical_signature(new_result)
    assert [t for t, _ in old_rows] == [t for t, _ in new_rows]
    assert len(old_rows) == len(new_rows) == 6

    saw_retired_cleanup = False
    for (t_old, old), (t_new, new) in zip(old_rows, new_rows, strict=True):
        assert t_old == t_new
        old_candidate = old["candidate_action_context"]
        new_candidate = new["candidate_action_context"]
        assert old["evidence_needs"] == new["evidence_needs"]
        assert old_candidate["decision_sufficiency"] == new_candidate["decision_sufficiency"]
        assert old_candidate["unresolved_dependencies"] == new_candidate["unresolved_dependencies"]
        assert old_candidate["open_dependency_count"] == new_candidate["open_dependency_count"]
        old_plans = {row["plan_id"]: row for row in old_candidate["candidate_plans"]}
        new_plans = {row["plan_id"]: row for row in new_candidate["candidate_plans"]}
        assert set(old_plans) == set(new_plans)
        for plan_id in old_plans:
            assert _semantic_plan(old_plans[plan_id]) == _semantic_plan(new_plans[plan_id])
            feasibility = old_plans[plan_id].get("feasibility")
            if feasibility in {"rejected", "dominated"}:
                if old_plans[plan_id].get("unresolved_conditions"):
                    saw_retired_cleanup = True
                assert "unresolved_conditions" not in new_plans[plan_id]
            else:
                assert old_plans[plan_id].get("unresolved_conditions") == new_plans[plan_id].get(
                    "unresolved_conditions"
                )

    assert saw_retired_cleanup
    old60 = next(f for t, f in old_rows if t == 60)
    new60 = next(f for t, f in new_rows if t == 60)
    old_hold = _plan(old60["candidate_action_context"], "hold_current_profile")
    new_hold = _plan(new60["candidate_action_context"], "hold_current_profile")
    assert old_hold["feasibility"] == new_hold["feasibility"] == "rejected"
    assert old_hold.get("unresolved_conditions") == [
        "fresh confirmed configuration for n01",
        "fresh confirmed configuration for n16",
    ]
    assert "unresolved_conditions" not in new_hold
    assert new60["candidate_action_context"]["open_dependency_count"] == 2

    print(
        "PASS v7 decision-closed projection: retired-plan unresolved guards removed; "
        "candidate semantics, sufficiency, needs, top-level dependency audit and physics unchanged"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

