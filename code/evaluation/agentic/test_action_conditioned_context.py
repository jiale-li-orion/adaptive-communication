#!/usr/bin/env python3
"""Action-conditioned context method smoke/conformance test."""
from __future__ import annotations

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
for p in (
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

from agentic_communication.episodes import o2_localized_risk_escalation_task  # noqa: E402
from agentic_communication.metrics import physical_signature  # noqa: E402
from agentic_communication.model_protocol import render_planner_protocol  # noqa: E402
from agentic_communication.planner import ActionConditionedReferencePlannerConsumer  # noqa: E402
from agentic_communication.run import run_agentic_episode, run_reference_comply  # noqa: E402


def main() -> int:
    task = o2_localized_risk_escalation_task()
    ref, _, _ = run_reference_comply(seed=0, operational_task=task)
    task_conditioned, _, _, _ = run_agentic_episode(
        seed=0, operational_task=task, context_mode="task_conditioned"
    )
    action, policy, _, _ = run_agentic_episode(
        seed=0,
        operational_task=task,
        context_mode="action_conditioned",
        planner_consumer=ActionConditionedReferencePlannerConsumer(),
    )
    action_full, _, _, _ = run_agentic_episode(
        seed=0,
        operational_task=task,
        context_mode="action_candidates_full_dump",
        planner_consumer=ActionConditionedReferencePlannerConsumer(),
    )
    assert physical_signature(ref) == physical_signature(action)
    assert physical_signature(ref) == physical_signature(action_full)
    tm = task_conditioned["agentic"]["agent_metrics"]
    am = action["agentic"]["agent_metrics"]
    fm = action_full["agentic"]["agent_metrics"]
    assert am["mean_selected_evidence"] < tm["mean_selected_evidence"], (am, tm)
    assert am["mean_selected_evidence"] < fm["mean_selected_evidence"], (am, fm)
    assert am["mean_materialized_bytes"] < fm["mean_materialized_bytes"], (am, fm)
    payload = render_planner_protocol(policy._latest_assembly)
    candidate = payload.get("candidate_action_context")
    assert candidate, payload.keys()
    assert candidate["action_scope"] == sorted(task.target_node_ids)
    assert set(candidate["evidence_scope"]) <= set(task.target_node_ids)
    plan_ids = {row["plan_id"] for row in candidate["candidate_plans"]}
    assert {"hold_current_profile", "install_required_profile"} <= plan_ids
    print(
        "PASS action-conditioned context: same physics, candidate-driven evidence contraction, "
        "model-facing candidate plans"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
