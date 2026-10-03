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
from agentic_communication.run import run_agentic_episode, run_reference_comply  # noqa: E402
from agentic_communication.runtime_contracts import (  # noqa: E402
    ModelUsage,
    PlannedCapabilityInvocation,
)


class _AlwaysAvailableDtS:
    tx_energy_wh = 0.0001
    p_succ = 1.0

    @staticmethod
    def opportunity(_t_s: int, _node_id: str) -> bool:
        return True

    @staticmethod
    def should_send(_t_s: int, _node) -> bool:
        return True


class _ComplyPlusDtS:
    consumer_id = "comply-plus-terminal-dts"
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
                        capability_id="communication.fallback.terminal_dts",
                        resource="terminal-dts-path",
                        canonical_arguments={"enabled": True},
                    ),
                ],
                "reason_codes": [*decision.reason_codes, "enable-existing-terminal-dts"],
            }
        )
        return decision, ModelUsage()


def main() -> int:
    task = o3_backhaul_outage_sustainment_task(task_hours=2)
    base = {
        "task_hours": 2,
        "tail_hours": 1,
        "harvest_mode": "uniform",
        "harvest_wh_per_hour": 3.0,
        "backhaul_p_good": 1.0,
        "outage_hours": 0.0,
        "access_outage_start_h": 0.0,
        "access_outage_hours": 2.0,
        "enable_backup": False,
        "execution_feedback": True,
    }
    ref_sim = dict(base, terminal_dts=_AlwaysAvailableDtS(), terminal_dts_enabled=True)
    agent_sim = dict(base, terminal_dts=_AlwaysAvailableDtS(), terminal_dts_enabled=False)
    ref, _, _ = run_reference_comply(seed=0, operational_task=task, simulator_kwargs=ref_sim)
    cur, policy, _, _ = run_agentic_episode(
        seed=0,
        operational_task=task,
        planner_consumer=_ComplyPlusDtS(),
        simulator_kwargs=agent_sim,
    )
    assert physical_signature(ref) == physical_signature(cur), "runtime DtS gate changed physical semantics"
    assert cur["repair"]["terminal_dts_attempts"] > 0
    effects = [
        e for e in policy.trace.events
        if e.event_type == "physical_effect"
        and e.payload.get("capability_id") == "communication.fallback.terminal_dts"
    ]
    assert effects and effects[0].payload.get("changed") is True
    assert effects[0].payload.get("enabled") is True
    print("PASS terminal-DtS device tool: typed gate -> existing DtS opportunity/energy physics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
