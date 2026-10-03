#!/usr/bin/env python3
"""Agentic Communication runtime conformance check.

The self-contained runtime must preserve the physical behavior of the existing
mission-comply controller while emitting typed Evidence/Context/Capability trace.
"""
from __future__ import annotations

import json
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

from agentic_communication.contracts import (  # noqa: E402
    OperationalTask,
    OperationalTaskFamily,
    OperationalTaskPhase,
)
from agentic_communication.episodes import o2_localized_risk_escalation_task  # noqa: E402
from agentic_communication.metrics import physical_signature  # noqa: E402
from agentic_communication.run import run_agentic_episode, run_reference_comply  # noqa: E402


def main() -> int:
    task = OperationalTask(
        task_id="runtime-conformance-smoke",
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
    full, full_policy, _, _ = run_agentic_episode(
        seed=0,
        operational_task=task,
        context_mode="full_dump",
        simulator_kwargs=sim,
    )
    assert physical_signature(ref) == physical_signature(cur), "task-conditioned harness changed physics"
    assert physical_signature(ref) == physical_signature(full), "FullDump harness changed physics"
    am = cur["agentic"]["agent_metrics"]
    assert am["runtime_task_contracts"] == 2, am
    assert am["context_manifests"] > 0 and am["capability_requests"] > 0, am
    assert am["contexts"] < 3 * 60, "context refreshed every tick instead of on evidence/task revision"
    registry = json.loads(policy.catalog.registry_path.read_text(encoding="utf-8"))
    assert len(policy.catalog.contracts) == len(registry["capabilities"]), (
        len(policy.catalog.contracts), len(registry["capabilities"])
    )
    assert full_policy.trace.events and policy.trace.events

    # A target-scoped Operational Task must constrain the business denominator and context using
    # the same scope.  This is the first Context-vs-FullDump benchmark sanity check.
    local_task = o2_localized_risk_escalation_task(task_hours=12)
    local_ref, _, _ = run_reference_comply(
        seed=0, operational_task=local_task,
        simulator_kwargs={"harvest_mode": "uniform", "harvest_wh_per_hour": 3.0},
    )
    local_tc, _, _, _ = run_agentic_episode(
        seed=0,
        operational_task=local_task,
        context_mode="task_conditioned",
        simulator_kwargs={"harvest_mode": "uniform", "harvest_wh_per_hour": 3.0},
    )
    local_fd, _, _, _ = run_agentic_episode(
        seed=0,
        operational_task=local_task,
        context_mode="full_dump",
        simulator_kwargs={"harvest_mode": "uniform", "harvest_wh_per_hour": 3.0},
    )
    assert physical_signature(local_ref) == physical_signature(local_tc)
    assert physical_signature(local_ref) == physical_signature(local_fd)
    assert (
        local_tc["agentic"]["agent_metrics"]["mean_selected_evidence"]
        < local_fd["agentic"]["agent_metrics"]["mean_selected_evidence"]
    ), (local_tc["agentic"]["agent_metrics"], local_fd["agentic"]["agent_metrics"])
    assert (
        local_tc["agentic"]["agent_metrics"]["mean_materialized_bytes"]
        < local_fd["agentic"]["agent_metrics"]["mean_materialized_bytes"]
    ), (local_tc["agentic"]["agent_metrics"], local_fd["agentic"]["agent_metrics"])
    print("PASS agentic runtime: self-contained contracts, typed trace, physical equivalence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
