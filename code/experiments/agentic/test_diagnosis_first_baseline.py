#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(os.path.dirname(HERE))
if CODE not in sys.path:
    sys.path.insert(0, CODE)

from agentic_communication.episodes import o2_risk_escalation_task  # noqa: E402
from agentic_communication.metrics import physical_signature  # noqa: E402
from agentic_communication.planner import (  # noqa: E402
    DeterministicComplyPlannerConsumer,
    DiagnosisFirstPlannerConsumer,
)
from agentic_communication.run import run_agentic_episode  # noqa: E402


def main() -> int:
    task = o2_risk_escalation_task(task_hours=8)
    sim = {
        "task_hours": 8,
        "tail_hours": 1,
        "harvest_mode": "uniform",
        "harvest_wh_per_hour": 3.0,
        "backhaul_p_good": 1.0,
        # O2's second TaskRun starts at 6h; force its fixed gateway diagnosis
        # into an outage so BLOCKED/UNREACHABLE must trigger another reasoning
        # round without fabricating an EvidenceWorld revision.
        "outage_start_h": 5.0,
        "outage_hours": 2.0,
        "execution_feedback": True,
    }
    direct, p_direct, _, _ = run_agentic_episode(
        seed=0,
        operational_task=task,
        planner_consumer=DeterministicComplyPlannerConsumer(),
        simulator_kwargs=sim,
    )
    diag, p_diag, _, _ = run_agentic_episode(
        seed=0,
        operational_task=task,
        planner_consumer=DiagnosisFirstPlannerConsumer(),
        simulator_kwargs=sim,
    )
    assert physical_signature(direct) == physical_signature(diag)
    a = p_direct.trace_summary()
    b = p_diag.trace_summary()
    assert b["model_requests"] > a["model_requests"], (a, b)
    assert b["capability_requests"] > a["capability_requests"], (a, b)
    gateway_requests = [
        e for e in p_diag.trace.events
        if e.event_type == "capability_request"
        and str(e.payload.get("capability_id", "")).startswith("communication.gateway.")
    ]
    # O2 has two TaskRuns (before/after task revision), so fixed diagnosis occurs twice.
    assert len(gateway_requests) == 4, len(gateway_requests)
    blocked = [
        e for e in p_diag.trace.events
        if e.event_type == "capability_result"
        and e.payload.get("status") == "blocked"
        and ":communication.gateway." in e.payload.get("request_id", "")
    ]
    assert blocked, "outage diagnosis never produced a blocked gateway observation"
    blocked_times = {e.t_s for e in blocked}
    model_requests_by_t = {}
    for e in p_diag.trace.events:
        if e.event_type == "model_request":
            model_requests_by_t[e.t_s] = model_requests_by_t.get(e.t_s, 0) + 1
    assert any(model_requests_by_t.get(t, 0) >= 2 for t in blocked_times), (
        blocked_times,
        model_requests_by_t,
    )
    print("PASS diagnosis-first baseline: same physics, strictly higher evidence/model/tool overhead on O2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
