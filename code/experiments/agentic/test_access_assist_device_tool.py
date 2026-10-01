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
from agentic_communication.planner import DeterministicComplyPlannerConsumer  # noqa: E402
from agentic_communication.run import run_agentic_episode, run_reference_comply  # noqa: E402
from agentic_communication.runtime_contracts import (  # noqa: E402
    ModelUsage,
    PlannedCapabilityInvocation,
    PlannerDecision,
)


class _OneShotAssist:
    consumer_id = "one-shot-access-assist"
    provider = "test"
    model = "deterministic-fixture"

    def __init__(self):
        self.done = False
        self.base = DeterministicComplyPlannerConsumer()

    def decide(self, request, assembly):
        base, _usage = self.base.decide(request, assembly)
        if self.done:
            return base, ModelUsage()
        self.done = True
        return base.model_copy(
            update={
                "stop": False,
                "invocations": [
                    *base.invocations,
                    PlannedCapabilityInvocation(
                        capability_id="communication.fallback.access_assist",
                        resource="access-path",
                        canonical_arguments={"duration_s": 3600},
                    ),
                ],
                "reason_codes": [*base.reason_codes, "install-one-hour-assist-window"],
            }
        ), ModelUsage()


def main() -> int:
    task = OperationalTask(
        task_id="access-assist-tool-smoke",
        family=OperationalTaskFamily.COMPOUND_LONG_HORIZON,
        phases=[OperationalTaskPhase(start_s=0, required_period_s=3600, level="blue")],
        task_horizon_s=2 * 3600,
        authorized_effects=[
            "communication.config.set_sampling_interval",
            "communication.config.set_report_period",
            "communication.fallback.access_assist",
        ],
        source_refs=["S06", "task-contract-v1.1"],
        scoring_profile_ref="communication-physical-v1",
    )
    base = {
        "task_hours": 2,
        "tail_hours": 1,
        "harvest_mode": "uniform",
        "harvest_wh_per_hour": 3.0,
        "uplink_p_arrive": 1.0,
        "backhaul_p_good": 1.0,
        "outage_hours": 0.0,
        "access_outage_start_h": 0.0,
        "access_outage_hours": 1.0,
        "enable_backup": False,
        "execution_feedback": True,
    }
    ref_sim = dict(base, access_assist_windows=[(0, 3600)])
    agent_sim = dict(base, access_assist_windows=[])
    ref, _, _ = run_reference_comply(seed=0, operational_task=task, simulator_kwargs=ref_sim)
    cur, policy, _, _ = run_agentic_episode(
        seed=0,
        operational_task=task,
        planner_consumer=_OneShotAssist(),
        simulator_kwargs=agent_sim,
    )
    assert physical_signature(ref) == physical_signature(cur), "runtime access-assist window changed physical semantics"
    assert cur["repair"]["access_assist_duration_s"] == 3600
    assert cur["repair"]["access_assist_bypassed"] > 0
    effects = [
        e for e in policy.trace.events
        if e.event_type == "physical_effect"
        and e.payload.get("capability_id") == "communication.fallback.access_assist"
    ]
    assert len(effects) == 1
    assert effects[0].payload.get("duration_s") == 3600
    print("PASS access-assist device tool: typed window -> existing access-assist physics/accounting")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
