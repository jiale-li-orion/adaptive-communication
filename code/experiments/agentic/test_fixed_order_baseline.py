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
    FixedOrderEagerPlannerConsumer,
)
from agentic_communication.run import run_agentic_episode  # noqa: E402


def main() -> int:
    task = OperationalTask(
        task_id="fixed-order-baseline-smoke",
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
        "outage_hours": 0.0,
        "backhaul_p_good": 1.0,
        "execution_feedback": True,
    }
    direct, p0, _, _ = run_agentic_episode(
        seed=0,
        operational_task=task,
        planner_consumer=DeterministicComplyPlannerConsumer(),
        simulator_kwargs=sim,
    )
    fixed, p1, _, _ = run_agentic_episode(
        seed=0,
        operational_task=task,
        planner_consumer=FixedOrderEagerPlannerConsumer(),
        simulator_kwargs=sim,
    )
    assert physical_signature(direct) == physical_signature(fixed)
    a, b = p0.trace_summary(), p1.trace_summary()
    assert b["capability_requests"] > a["capability_requests"], (a, b)
    assert b["model_requests"] > a["model_requests"], (a, b)
    gateway_calls = [
        e for e in p1.trace.events
        if e.event_type == "capability_request"
        and str(e.payload.get("capability_id", "")).startswith("communication.gateway.")
    ]
    assert gateway_calls
    print("PASS fixed-order eager baseline: same physics, strictly more irrelevant probing overhead")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
