#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(os.path.dirname(HERE))
if CODE not in sys.path:
    sys.path.insert(0, CODE)

from agentic_communication.episodes import o3_backhaul_outage_sustainment_task  # noqa: E402
from agentic_communication.metrics import agent_metrics, communication_metrics  # noqa: E402
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
    # Service outcome stays equal in this easy always-up case, while the honest
    # cross-tick evidence round is allowed to change control-plane cost/retry
    # timing.  Physical bit-equality was the old synchronous-RPC assumption.
    assert communication_metrics(ref)["timely_delivery_rate"] == \
        communication_metrics(cur)["timely_delivery_rate"]
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
    req_t = {
        e.payload["request_id"]: e.t_s
        for e in policy.trace.events
        if e.event_type == "capability_request"
        and str(e.payload.get("capability_id", "")).startswith("communication.gateway.")
    }
    remote_results = [
        e for e in policy.trace.events
        if e.event_type == "capability_result" and e.payload.get("request_id") in req_t
    ]
    assert remote_results
    assert all(e.t_s - req_t[e.payload["request_id"]] == 60 for e in remote_results)
    assert all((e.payload.get("latency") or {}).get("simulated_s") == 60 for e in remote_results)
    metrics = agent_metrics(policy)
    assert metrics["remote_observation_pending_events"] == metrics["remote_observation_requests"]
    assert metrics["max_model_requests_per_tick"] == 1, metrics
    assert metrics["remote_observation_unknown_transport_cost_results"] == \
        metrics["remote_observation_results"]
    print(
        "PASS multi-round runtime: remote evidence crosses simulator tick; "
        "Context revision happens on the next legal planner turn"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
