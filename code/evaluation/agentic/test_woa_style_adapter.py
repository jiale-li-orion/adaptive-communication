#!/usr/bin/env python3
"""Conformance tests for the strong WirelessOpsAgent-style adaptation."""
from __future__ import annotations

from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from agentic_communication.episodes import benchmark_episode_catalog  # noqa: E402
from agentic_communication.planner import CompiledChecklistPlannerConsumer  # noqa: E402
from agentic_communication.replay import frozen_r1_inputs  # noqa: E402
from agentic_communication.run import run_agentic_episode  # noqa: E402
from agentic_communication.runtime_contracts import (  # noqa: E402
    ModelRequest,
    ModelUsage,
    PlannedCapabilityInvocation,
    PlannerDecision,
)
from woa_style_adapter import (  # noqa: E402
    GOVERNOR_APPLY,
    GOVERNOR_HOLD,
    WirelessOpsStyleAssuranceConsumer,
)


class FixedProposalConsumer:
    consumer_id = "test-fixed-proposal"
    provider = "test"
    model = "fixed-proposal"

    def __init__(self, decision: PlannerDecision) -> None:
        self.decision = decision

    def decide(self, request, assembly):
        return (
            self.decision.model_copy(
                update={
                    "decision_id": f"decision:{request.request_id}",
                    "request_id": request.request_id,
                }
            ),
            ModelUsage(),
        )


def _assembly(episode_name: str, t_s: int):
    episode = benchmark_episode_catalog()[episode_name]
    _, policy, _, _ = run_agentic_episode(
        seed=0,
        operational_task=episode.task,
        context_mode="woa_style",
        planner_consumer=CompiledChecklistPlannerConsumer(),
        planner_replan_mode="decision_state",
        simulator_kwargs=episode.simulator_overrides,
    )
    rows = [row for row in frozen_r1_inputs(policy.trace.events) if int(row.t_s) == t_s]
    assert rows, (episode_name, t_s)
    return rows[0].assembly


def _request(assembly, suffix: str) -> ModelRequest:
    return ModelRequest(
        request_id=f"woa-test:{suffix}",
        task_run_id=assembly.task_run_id,
        assembly_id=assembly.assembly_id,
        assembly_hash=assembly.assembly_hash,
        consumer_id="woa-style-test",
        response_schema="PlannerDecision",
    )


def main() -> int:
    # O5 task revision: repair an invalid/rejected hold proposal to the unique
    # supported install plan.  This is bounded proposal repair, not a second LLM.
    o5 = _assembly("O5", 14400)
    bad_hold = PlannerDecision(
        decision_id="decision:bad-o5",
        request_id="bad-o5",
        stop=True,
        selected_plan_id="hold_current_profile",
        invocations=[],
    )
    o5_consumer = WirelessOpsStyleAssuranceConsumer(FixedProposalConsumer(bad_hold))
    repaired, _ = o5_consumer.decide(_request(o5, "o5"), o5)
    assert repaired.selected_plan_id == "install_required_profile", repaired
    assert repaired.stop is False, repaired
    assert repaired.invocations == [], repaired
    rec = o5_consumer.records[-1]
    assert rec["governor"] == GOVERNOR_APPLY, rec
    assert rec["integrity"]["valid"] is True, rec
    assert any(row["type"] == "repair_to_unique_supported_plan" for row in rec["repairs"]), rec

    # O6 closed hold: proposal selects the right no-op plan but attempts two
    # unrelated gateway reads. Assurance should preserve the supported hold,
    # drop nonblocking reads and repair stop semantics.
    o6 = _assembly("O6", 10860)
    noisy_hold = PlannerDecision(
        decision_id="decision:bad-o6",
        request_id="bad-o6",
        stop=False,
        selected_plan_id="hold_current_profile",
        invocations=[
            PlannedCapabilityInvocation(
                capability_id="communication.gateway.node_report",
                resource="n00",
                canonical_arguments={"node_id": "n00"},
            ),
            PlannedCapabilityInvocation(
                capability_id="communication.gateway.node_report",
                resource="n15",
                canonical_arguments={"node_id": "n15"},
            ),
        ],
    )
    o6_consumer = WirelessOpsStyleAssuranceConsumer(FixedProposalConsumer(noisy_hold))
    repaired, _ = o6_consumer.decide(_request(o6, "o6"), o6)
    assert repaired.selected_plan_id == "hold_current_profile", repaired
    assert repaired.stop is True, repaired
    assert repaired.invocations == [], repaired
    rec = o6_consumer.records[-1]
    assert rec["governor"] == GOVERNOR_HOLD, rec
    assert rec["integrity"]["valid"] is True, rec
    assert any(row["type"] == "drop_nonblocking_observation_calls" for row in rec["repairs"]), rec
    assert any(row["type"] == "repair_stop_semantics" for row in rec["repairs"]), rec

    print(
        "PASS WOA-style adapter: invalid action proposal repaired to APPLY; "
        "noisy supported hold revalidated to HOLD without unrelated queries"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

