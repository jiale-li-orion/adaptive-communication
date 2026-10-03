#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(os.path.dirname(HERE))
if CODE not in sys.path:
    sys.path.insert(0, CODE)

from agentic_communication.episodes import o3_backhaul_outage_sustainment_task  # noqa: E402
from agentic_communication.metrics import physical_signature  # noqa: E402
from agentic_communication.planner import DeterministicComplyPlannerConsumer  # noqa: E402
from agentic_communication.runtime_contracts import (  # noqa: E402
    ModelUsage,
    PlannedCapabilityInvocation,
)
from agentic_communication.run import run_agentic_episode, run_reference_comply  # noqa: E402


def main() -> int:
    task = o3_backhaul_outage_sustainment_task(task_hours=4)
    ref_sim = {
        "task_hours": 4,
        "tail_hours": 1,
        "harvest_mode": "uniform",
        "harvest_wh_per_hour": 3.0,
        "backhaul_p_good": 1.0,
        "outage_start_h": 1.0,
        "outage_hours": 2.0,
        "enable_backup": True,
        "execution_feedback": True,
    }
    agent_sim = dict(ref_sim, enable_backup=False)

    class _ComplyPlusBackup:
        consumer_id = "comply-plus-gateway-backup"
        provider = "test"
        model = "deterministic-fixture"

        def __init__(self):
            self.base = DeterministicComplyPlannerConsumer()

        def decide(self, request, assembly):
            decision, _usage = self.base.decide(request, assembly)
            decision = decision.model_copy(
                update={
                    "stop": False,
                    "invocations": [
                        *decision.invocations,
                        PlannedCapabilityInvocation(
                            capability_id="communication.fallback.gateway_backup",
                            resource="gw0",
                            canonical_arguments={"enabled": True},
                        ),
                    ],
                    "reason_codes": [*decision.reason_codes, "enable-existing-backup-path"],
                }
            )
            return decision, ModelUsage()

    consumer = _ComplyPlusBackup()
    ref, _, _ = run_reference_comply(seed=0, operational_task=task, simulator_kwargs=ref_sim)
    cur, policy, _, _ = run_agentic_episode(
        seed=0,
        operational_task=task,
        planner_consumer=consumer,
        simulator_kwargs=agent_sim,
    )
    assert physical_signature(ref) == physical_signature(cur), "runtime backup tool did not reproduce static-enabled reference"
    effects = [
        e for e in policy.trace.events
        if e.event_type == "physical_effect"
        and e.payload.get("capability_id") == "communication.fallback.gateway_backup"
    ]
    assert effects, "no gateway-backup physical effect traced"
    assert effects[0].payload.get("enabled") is True
    assert effects[0].payload.get("changed") is True
    assert cur["backup"]["backup_packets"] > 0
    print("PASS gateway backup device tool: typed invocation -> real JointControlPlane effect/cost")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
