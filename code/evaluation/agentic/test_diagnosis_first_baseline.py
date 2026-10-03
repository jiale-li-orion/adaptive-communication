#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(os.path.dirname(HERE))
if CODE not in sys.path:
    sys.path.insert(0, CODE)

from agentic_communication.episodes import o2_risk_escalation_task  # noqa: E402
from agentic_communication.metrics import communication_metrics, physical_signature  # noqa: E402
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
    # Diagnosis-first is intentionally an eager remote-probe baseline.  Once
    # owner reads respect simulator time, the extra diagnostic round may perturb
    # actuation and therefore must not be required to remain bit-identical.
    assert physical_signature(direct) != physical_signature(diag)
    a = p_direct.trace_summary()
    b = p_diag.trace_summary()
    assert a["remote_observation_requests"] == 0, a
    assert b["remote_observation_requests"] == 4, b
    assert b["remote_observation_simulated_wait_s_total"] == 240.0, b
    assert b["max_model_requests_per_tick"] == 1, b
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
    request_t = {
        e.payload["request_id"]: e.t_s
        for e in p_diag.trace.events
        if e.event_type == "capability_request"
        and str(e.payload.get("capability_id", "")).startswith("communication.gateway.")
    }
    assert all(e.t_s - request_t[e.payload["request_id"]] == 60 for e in blocked)
    # This scenario deliberately places the second diagnosis at a Task revision
    # inside a backhaul outage.  The eager probe consumes decision slack and
    # measurably reduces service, which is the baseline failure we want exposed.
    assert communication_metrics(diag)["timely_delivery_rate"] < \
        communication_metrics(direct)["timely_delivery_rate"]
    print(
        "PASS diagnosis-first baseline: eager remote diagnosis crosses simulator time "
        "and can perturb O2 control/service under outage"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
