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
from agentic_communication.planner import EvidenceAwareComplyPlannerConsumer  # noqa: E402
from agentic_communication.run import run_agentic_episode, run_reference_comply  # noqa: E402


def main() -> int:
    task = o3_backhaul_outage_sustainment_task(task_hours=2)
    sim = {
        "task_hours": 2,
        "tail_hours": 1,
        "harvest_mode": "uniform",
        "harvest_wh_per_hour": 3.0,
        "backhaul_p_good": 1.0,
        "outage_hours": 0.0,
        "enable_backup": True,
        "execution_feedback": True,
    }
    ref, _, _ = run_reference_comply(seed=0, operational_task=task, simulator_kwargs=sim)
    cur, policy, _, _ = run_agentic_episode(
        seed=0,
        operational_task=task,
        planner_consumer=EvidenceAwareComplyPlannerConsumer(),
        simulator_kwargs=sim,
    )
    assert physical_signature(ref) == physical_signature(cur), "evidence-use round changed physical policy"
    decisions = [e for e in policy.trace.events if e.event_type == "planner_decision"]
    assert decisions
    assert any(
        any(
            str(x.get("capability_id", "")).startswith("communication.gateway.")
            for x in e.payload.get("invocations", [])
        )
        for e in decisions
    ), "planner never selected gateway evidence capability"
    gateway_results = [
        e for e in policy.trace.events
        if e.event_type == "capability_result"
        and ":communication.gateway." in e.payload.get("request_id", "")
    ]
    assert gateway_results and all(e.payload.get("status") == "succeeded" for e in gateway_results)
    # At least one simulator tick must contain two model requests: pre-evidence
    # context, then revised context after the owner-scoped observation.
    per_t = {}
    for e in policy.trace.events:
        if e.event_type == "model_request":
            per_t[e.t_s] = per_t.get(e.t_s, 0) + 1
    assert max(per_t.values(), default=0) >= 2, per_t
    print("PASS multi-round runtime: Context -> evidence tool -> world revision -> Context -> device policy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
