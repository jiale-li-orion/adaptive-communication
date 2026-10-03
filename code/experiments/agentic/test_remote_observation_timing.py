#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(os.path.dirname(HERE))
if CODE not in sys.path:
    sys.path.insert(0, CODE)

from agentic_communication.episodes import o3_backhaul_outage_sustainment_task  # noqa: E402
from agentic_communication.planner import (  # noqa: E402
    DeterministicComplyPlannerConsumer,
    EvidenceAwareComplyPlannerConsumer,
)
from agentic_communication.run import run_agentic_episode  # noqa: E402
from agentic_communication.runtime_contracts import (  # noqa: E402
    ModelUsage,
    PlannedCapabilityInvocation,
    PlannerDecision,
)


class MixedReadyAndQueryConsumer:
    """Regression fixture: remote evidence must not globally block ready actions."""

    provider = "test"
    model = "mixed-ready-and-query"
    consumer_id = "mixed-ready-and-query"

    def __init__(self) -> None:
        self.base = DeterministicComplyPlannerConsumer()
        self.injected_at_s: int | None = None

    def decide(self, request, assembly):
        ready, usage = self.base.decide(request, assembly)
        if self.injected_at_s is None and ready.invocations:
            query = [
                PlannedCapabilityInvocation(
                    capability_id="communication.gateway.primary_health",
                    resource="gw0",
                    canonical_arguments={},
                ),
                PlannedCapabilityInvocation(
                    capability_id="communication.gateway.receipt_summary",
                    resource="gw0",
                    canonical_arguments={},
                ),
            ]
            # Request ids encode the simulator tick in the third field.
            self.injected_at_s = int(str(request.request_id).split(":")[2])
            return (
                PlannerDecision(
                    decision_id=f"decision:{request.request_id}:mixed",
                    request_id=request.request_id,
                    invocations=[*ready.invocations, *query],
                    reason_codes=["ready_action_plus_nonblocking_remote_query"],
                ),
                ModelUsage(),
            )
        return ready, usage


def run(delay_s: int):
    task = o3_backhaul_outage_sustainment_task(task_hours=1)
    sim = {
        "task_hours": 1,
        "tail_hours": 1,
        "harvest_mode": "uniform",
        "harvest_wh_per_hour": 3.0,
        "backhaul_p_good": 1.0,
        "backhaul_delay_s": delay_s,
        "outage_hours": 0.0,
        "enable_backup": True,
        "execution_feedback": True,
    }
    _, policy, _, _ = run_agentic_episode(
        seed=0,
        operational_task=task,
        planner_consumer=EvidenceAwareComplyPlannerConsumer(),
        simulator_kwargs=sim,
    )
    return policy


def assert_timing(policy, expected_wait_s: int) -> None:
    requests = {
        e.payload["request_id"]: e.t_s
        for e in policy.trace.events
        if e.event_type == "capability_request"
        and str(e.payload.get("capability_id", "")).startswith("communication.gateway.")
    }
    results = [
        e for e in policy.trace.events
        if e.event_type == "capability_result" and e.payload.get("request_id") in requests
    ]
    assert requests and results
    assert all(e.t_s - requests[e.payload["request_id"]] == expected_wait_s for e in results)
    assert all(
        int((e.payload.get("latency") or {}).get("simulated_s", -1)) == expected_wait_s
        for e in results
    )
    summary = policy.trace_summary()
    assert summary["remote_observation_requests"] == len(requests)
    assert summary["remote_observation_results"] == len(results)
    assert summary["remote_observation_simulated_wait_s_mean"] == float(expected_wait_s)
    assert summary["max_model_requests_per_tick"] == 1


def assert_mixed_query_does_not_block_ready_action() -> None:
    task = o3_backhaul_outage_sustainment_task(task_hours=1)
    sim = {
        "task_hours": 1,
        "tail_hours": 1,
        "harvest_mode": "uniform",
        "harvest_wh_per_hour": 3.0,
        "backhaul_p_good": 1.0,
        "backhaul_delay_s": 240,
        "outage_hours": 0.0,
        "enable_backup": True,
        "execution_feedback": True,
    }
    consumer = MixedReadyAndQueryConsumer()
    _, policy, inst, _ = run_agentic_episode(
        seed=0,
        operational_task=task,
        planner_consumer=consumer,
        simulator_kwargs=sim,
    )
    assert consumer.injected_at_s is not None
    t_s = consumer.injected_at_s
    same_tick_requests = [
        e for e in policy.trace.events
        if e.event_type == "capability_request" and int(e.t_s) == t_s
    ]
    gateway_requests = [
        e for e in same_tick_requests
        if str(e.payload.get("capability_id", "")).startswith("communication.gateway.")
    ]
    config_requests = [
        e for e in same_tick_requests
        if str(e.payload.get("capability_id", "")).startswith("communication.config.")
    ]
    assert len(gateway_requests) == 2
    assert config_requests, "ready configuration actions were globally blocked by remote evidence"
    assert any(
        len(row) >= 6 and int(row[0]) == t_s and row[2] == "sent"
        for row in inst.trace_events
    ), "ready configuration command was not physically submitted on the query tick"

    request_times = {e.payload["request_id"]: int(e.t_s) for e in gateway_requests}
    gateway_results = [
        e for e in policy.trace.events
        if e.event_type == "capability_result" and e.payload.get("request_id") in request_times
    ]
    assert len(gateway_results) == 2
    assert all(int(e.t_s) - request_times[e.payload["request_id"]] == 300 for e in gateway_results)


def main() -> int:
    # With zero store-and-forward delay, phase ordering still imposes one 60 s
    # decision barrier.  With 240 s backhaul delay, the response becomes
    # forwardable at t+240 in phase 3 and therefore planner-visible at t+300.
    assert_timing(run(0), 60)
    assert_timing(run(240), 300)
    assert_mixed_query_does_not_block_ready_action()
    print(
        "PASS remote observation timing: backhaul delay + simulator phase ordering determine "
        "the next legal planner turn; unrelated ready actions can progress while evidence is pending"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
