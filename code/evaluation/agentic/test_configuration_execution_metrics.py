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
from agentic_communication.planner import DeterministicComplyPlannerConsumer  # noqa: E402
from agentic_communication.run import run_agentic_episode, run_reference_comply  # noqa: E402


def main() -> int:
    task = o2_risk_escalation_task()
    ref, _, _ = run_reference_comply(seed=0, operational_task=task)
    cur, _, _, _ = run_agentic_episode(
        seed=0,
        operational_task=task,
        planner_consumer=DeterministicComplyPlannerConsumer(),
    )
    assert physical_signature(ref) == physical_signature(cur)
    a = ref["configuration_execution"]
    b = cur["configuration_execution"]
    assert a == b, "typed runtime and legacy reference disagree on evaluator applied-config trajectory"
    assert a["evaluated_alive_node_s"] > 0
    assert a["config_mismatch_node_s"] > 0
    assert 0.0 <= a["config_mismatch_rate"] <= 1.0
    assert 0.0 <= a["install_completion_rate"] <= 1.0
    assert a["install_latency_p50_s"] <= a["install_latency_p90_s"] <= a["install_latency_p95_s"]
    assert 0.0 <= a["revision_install_completion_rate"] <= 1.0
    assert (
        a["revision_install_latency_p50_s"]
        <= a["revision_install_latency_p90_s"]
        <= a["revision_install_latency_p95_s"]
    )
    assert a["revision_install_latency_p50_s"] > 0, a
    cm = cur["agentic"]["communication_metrics"]
    assert cm["config_mismatch_node_s"] == a["config_mismatch_node_s"]
    assert cm["config_install_completion_rate"] == a["install_completion_rate"]
    assert cm["config_revision_install_completion_rate"] == a["revision_install_completion_rate"]
    print("PASS configuration execution metrics: OperationalTask desired vs evaluator-only applied state over time")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
