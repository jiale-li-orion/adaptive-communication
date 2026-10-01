#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(os.path.dirname(HERE))
if CODE not in sys.path:
    sys.path.insert(0, CODE)

from agentic_communication.contracts import OperationalTask, OperationalTaskFamily, OperationalTaskPhase  # noqa: E402
from agentic_communication.metrics import physical_signature  # noqa: E402
from agentic_communication.planner import DeterministicComplyPlannerConsumer  # noqa: E402
from agentic_communication.run import run_agentic_episode, run_reference_comply  # noqa: E402


def main() -> int:
    task = OperationalTask(
        task_id="live-planner-smoke",
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
        "enable_backup": True,
        "execution_feedback": True,
    }
    ref, _, _ = run_reference_comply(seed=0, operational_task=task, simulator_kwargs=sim)
    cur, policy, _, _ = run_agentic_episode(
        seed=0,
        operational_task=task,
        context_mode="task_conditioned",
        planner_consumer=DeterministicComplyPlannerConsumer(),
        simulator_kwargs=sim,
    )
    assert physical_signature(ref) == physical_signature(cur), "live planner boundary changed physics"
    summary = policy.trace_summary()
    assert summary["model_requests"] > 0, summary
    assert summary["model_requests"] == summary["model_attempts"] == summary["model_usage_records"]
    assert summary["planner_decisions"] == summary["model_requests"]
    print("PASS live PlannerConsumer: typed model ledger + physical equivalence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
