#!/usr/bin/env python3
"""Smoke-test R0/R1/R2 replay on a short freshly generated trace."""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(os.path.dirname(HERE))
for p in (
    CODE,
    os.path.join(CODE, "substrate", "joint"),
    os.path.join(CODE, "substrate", "instance"),
    os.path.join(CODE, "substrate", "monitoring"),
    os.path.join(CODE, "substrate", "physics"),
    os.path.join(CODE, "substrate", "runtime"),
    os.path.join(CODE, "evaluation", "agentic"),
    os.path.join(CODE, "legacy-communication", "analysis"),
):
    if p not in sys.path:
        sys.path.insert(0, p)

from agentic_communication.contracts import OperationalTask, OperationalTaskFamily, OperationalTaskPhase  # noqa: E402
from agentic_communication.replay import audit_r0, audit_r2, frozen_r1_inputs  # noqa: E402
from agentic_communication.run import run_agentic_episode  # noqa: E402


def main() -> int:
    task = OperationalTask(
        task_id="replay-smoke",
        family=OperationalTaskFamily.RISK_ESCALATION,
        target_node_ids=["n10", "n11"],
        phases=[
            OperationalTaskPhase(start_s=0, required_period_s=3600, level="blue"),
            OperationalTaskPhase(start_s=3600, required_period_s=300, level="yellow"),
        ],
        task_horizon_s=7200,
        authorized_effects=[
            "communication.config.set_sampling_interval",
            "communication.config.set_report_period",
        ],
    )
    result, policy, _, _ = run_agentic_episode(
        seed=0,
        operational_task=task,
        context_mode="task_conditioned",
        simulator_kwargs={
            "task_hours": 2,
            "tail_hours": 1,
            "harvest_mode": "uniform",
            "harvest_wh_per_hour": 3.0,
            "outage_hours": 0.0,
        },
    )
    del result
    r0 = audit_r0(policy.trace.events)
    r2 = audit_r2(policy.trace.events, context_mode="task_conditioned")
    r1 = frozen_r1_inputs(policy.trace.events)
    assert r0["passed"], r0
    assert r2["passed"], r2
    assert r1 and r2["exact_assembly_matches"] == r2["contexts"], r2
    print(
        "PASS replay: "
        f"R0 events={r0['events']}, R1 inputs={len(r1)}, "
        f"R2 exact={r2['exact_assembly_matches']}/{r2['contexts']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
