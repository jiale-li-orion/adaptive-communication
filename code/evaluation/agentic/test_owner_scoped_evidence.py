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
from agentic_communication.run import run_agentic_episode, run_reference_comply  # noqa: E402


def main() -> int:
    task = o3_backhaul_outage_sustainment_task(task_hours=4)
    sim = {
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
    ref, _, _ = run_reference_comply(seed=0, operational_task=task, simulator_kwargs=sim)
    cur, policy, _, _ = run_agentic_episode(
        seed=0,
        operational_task=task,
        context_mode="task_conditioned",
        simulator_kwargs=sim,
    )
    assert physical_signature(ref) == physical_signature(cur), "owner evidence broker changed physics"
    statuses = []
    gateway_percepts = 0
    gateway_evidence = 0
    for event in policy.trace.events:
        if event.event_type == "capability_result" and event.payload.get("request_id", "").endswith(
            ("communication.gateway.primary_health", "communication.gateway.receipt_summary")
        ):
            statuses.append((event.payload.get("status"), event.payload.get("observation_class")))
        if event.event_type == "percept" and event.payload.get("source_roles") == ["gateway"]:
            gateway_percepts += 1
        if event.event_type == "evidence_world_revision":
            for row in event.payload.get("evidence", []):
                if row.get("owner_location") == "gateway":
                    gateway_evidence += 1
    assert any(s == "succeeded" for s, _ in statuses), statuses
    assert any(c == "unreachable" for _, c in statuses), statuses
    assert gateway_percepts > 0, gateway_percepts
    assert gateway_evidence > 0, gateway_evidence
    print(
        "PASS owner-scoped evidence: gateway success + UNREACHABLE, "
        "typed percept/evidence, physical equivalence"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
