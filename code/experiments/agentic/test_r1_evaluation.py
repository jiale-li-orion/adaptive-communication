#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(CODE)
if CODE not in sys.path:
    sys.path.insert(0, CODE)

from agentic_communication.planner import (  # noqa: E402
    CallablePlannerConsumer,
    DeterministicComplyPlannerConsumer,
)
from agentic_communication.r1_evaluation import evaluate_r1_consumers  # noqa: E402
from agentic_communication.replay import load_trace  # noqa: E402


def main() -> int:
    trace = os.path.join(
        ROOT,
        "results",
        "agentic",
        "o2-risk-escalation-v1",
        "runtime_traces",
        "seed-000-task_conditioned.jsonl",
    )
    assert os.path.isfile(trace), trace
    events = load_trace(trace)
    gold = DeterministicComplyPlannerConsumer()

    _, perfect = evaluate_r1_consumers(events, candidate=gold, gold=gold)
    assert perfect["stopping_correctness"] == 1.0, perfect
    assert perfect["tool_exact_match_rate"] == 1.0, perfect
    assert perfect["tool_any_order_precision"] == 1.0, perfect
    assert perfect["tool_any_order_recall"] == 1.0, perfect
    assert perfect["tool_in_order_normalized"] == 1.0, perfect
    assert perfect["argument_grounding_accuracy"] == 1.0, perfect

    def bad(_assembly: dict) -> dict:
        return {
            "stop": False,
            "invocations": [
                {
                    "capability_id": "communication.config.set_sampling_interval",
                    "resource": "n00",
                    "canonical_arguments": {"target_s": 600},
                }
            ],
            "reason_codes": ["intentionally-bad-r1-fixture"],
        }

    wrong = CallablePlannerConsumer(
        bad,
        consumer_id="bad-r1-fixture",
        provider="test",
        model="bad-fixture",
    )
    _, degraded = evaluate_r1_consumers(events, candidate=wrong, gold=gold)
    assert degraded["tool_exact_match_rate"] < 1.0, degraded
    assert degraded["tool_any_order_recall"] < 1.0, degraded
    assert degraded["argument_grounding_accuracy"] < 1.0, degraded
    assert degraded["stopping_correctness"] < 1.0, degraded
    print("PASS R1 evaluation: stop/tool selection/order/arguments are frozen-input diagnostics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
