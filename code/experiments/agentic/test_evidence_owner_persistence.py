#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(os.path.dirname(HERE))
if CODE not in sys.path:
    sys.path.insert(0, CODE)

from agentic_communication.episodes import o3_backhaul_outage_sustainment_task  # noqa: E402
from agentic_communication.metrics import communication_metrics  # noqa: E402
from agentic_communication.planner import EvidenceAwareComplyPlannerConsumer  # noqa: E402
from agentic_communication.run import run_agentic_episode, run_reference_comply  # noqa: E402


def main() -> int:
    task = o3_backhaul_outage_sustainment_task(task_hours=3)
    sim = {
        "task_hours": 3,
        "tail_hours": 1,
        "harvest_mode": "uniform",
        "harvest_wh_per_hour": 3.0,
        "outage_hours": 0.0,
        "backhaul_p_good": 1.0,
        "enable_backup": True,
        "execution_feedback": True,
    }
    reference, _, _ = run_reference_comply(seed=0, operational_task=task, simulator_kwargs=sim)
    result, policy, _, _ = run_agentic_episode(
        seed=0,
        operational_task=task,
        planner_consumer=EvidenceAwareComplyPlannerConsumer(),
        simulator_kwargs=sim,
    )
    # Persisting owner evidence itself must preserve service correctness in this
    # always-up case.  The remote acquisition round is no longer a free
    # same-tick RPC, so control-plane command/retry counters may legitimately
    # differ from the legacy direct reference.
    ref_m = communication_metrics(reference)
    got_m = communication_metrics(result)
    assert ref_m["timely_delivery_rate"] == got_m["timely_delivery_rate"]
    assert ref_m["collection_rate"] == got_m["collection_rate"]
    gateway_requests = [
        e
        for e in policy.trace.events
        if e.event_type == "capability_request"
        and str(e.payload.get("capability_id", "")).startswith("communication.gateway.")
    ]
    # Two gateway capabilities are queried at initial acquisition and only after
    # their 1h freshness window expires; they must not be reissued every tick.
    assert 2 <= len(gateway_requests) <= 8, len(gateway_requests)
    summary = policy.trace_summary()
    assert summary["model_requests"] < 40, summary
    assert summary["remote_observation_requests"] == len(gateway_requests)
    assert summary["remote_observation_simulated_wait_s_mean"] == 60.0
    assert summary["max_model_requests_per_tick"] == 1
    gateway_rows = []
    for event in policy.trace.events:
        if event.event_type != "evidence_world_revision":
            continue
        gateway_rows.extend(
            row
            for row in event.payload.get("evidence", [])
            if row.get("owner_location") == "gateway"
        )
    assert gateway_rows
    print(
        "PASS evidence owner persistence: gateway evidence survives center updates, "
        "refreshes on freshness boundary, service outcome preserved across async owner reads"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
