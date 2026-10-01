#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(os.path.dirname(HERE))
if CODE not in sys.path:
    sys.path.insert(0, CODE)

from agentic_communication.contracts import (  # noqa: E402
    OperationalTask,
    OperationalTaskFamily,
    OperationalTaskPhase,
)
from agentic_communication.metrics import physical_signature  # noqa: E402
from agentic_communication.planner import (  # noqa: E402
    DeterministicComplyPlannerConsumer,
    GoldReplacementPlannerConsumer,
)
from agentic_communication.run import run_agentic_episode, run_reference_comply  # noqa: E402
from agentic_communication.runtime_contracts import (  # noqa: E402
    ModelUsage,
    PlannedCapabilityInvocation,
    PlannerDecision,
)
from agentic_communication.trajectory_eval import GoldReplacementLayer  # noqa: E402


class _WrongPlanner:
    consumer_id = "wrong-planner-fixture"
    provider = "test"
    model = "wrong-fixture"

    def decide(self, request, assembly):
        return (
            PlannerDecision(
                decision_id=f"decision:{request.request_id}",
                request_id=request.request_id,
                stop=False,
                invocations=[
                    PlannedCapabilityInvocation(
                        capability_id="communication.config.set_sampling_interval",
                        resource="n00",
                        canonical_arguments={"target_s": 600},
                    )
                ],
                reason_codes=["intentionally-wrong"],
            ),
            ModelUsage(),
        )


def main() -> int:
    task = OperationalTask(
        task_id="live-gold-smoke",
        family=OperationalTaskFamily.RISK_ESCALATION,
        phases=[
            OperationalTaskPhase(start_s=0, required_period_s=3600, level="blue"),
            OperationalTaskPhase(start_s=3600, required_period_s=300, level="yellow"),
        ],
        task_horizon_s=2 * 3600,
        authorized_effects=[
            "communication.config.set_sampling_interval",
            "communication.config.set_report_period",
        ],
    )
    sim = {
        "task_hours": 2,
        "tail_hours": 1,
        "harvest_mode": "uniform",
        "harvest_wh_per_hour": 3.0,
        "backhaul_p_good": 1.0,
        "outage_hours": 0.0,
        "execution_feedback": True,
    }
    ref, _, _ = run_reference_comply(seed=0, operational_task=task, simulator_kwargs=sim)
    wrong, _, _, _ = run_agentic_episode(
        seed=0,
        operational_task=task,
        planner_consumer=_WrongPlanner(),
        simulator_kwargs=sim,
    )
    assert physical_signature(ref) != physical_signature(wrong), "wrong planner fixture unexpectedly matches gold"

    gold_consumer = DeterministicComplyPlannerConsumer()
    cumulative = GoldReplacementPlannerConsumer(
        _WrongPlanner(),
        gold_consumer,
        [
            GoldReplacementLayer.CAPABILITY_SELECTION,
            GoldReplacementLayer.CAPABILITY_ORDER,
            GoldReplacementLayer.CAPABILITY_ARGUMENTS,
        ],
    )
    fixed, policy, _, _ = run_agentic_episode(
        seed=0,
        operational_task=task,
        planner_consumer=cumulative,
        simulator_kwargs=sim,
    )
    assert physical_signature(ref) == physical_signature(fixed), "cumulative gold replacement did not restore reference physics"
    assert policy.trace_summary()["model_requests"] > 0

    policy_gold = GoldReplacementPlannerConsumer(
        _WrongPlanner(), gold_consumer, [GoldReplacementLayer.POLICY]
    )
    fixed2, _, _, _ = run_agentic_episode(
        seed=0,
        operational_task=task,
        planner_consumer=policy_gold,
        simulator_kwargs=sim,
    )
    assert physical_signature(ref) == physical_signature(fixed2)
    print("PASS live gold replacement: wrong planner -> cumulative layers/policy -> reference physical outcome")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
