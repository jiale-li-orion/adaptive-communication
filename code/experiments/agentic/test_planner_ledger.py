#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(os.path.dirname(HERE))
if CODE not in sys.path:
    sys.path.insert(0, CODE)

from agentic_communication.planner import CallablePlannerConsumer  # noqa: E402
from agentic_communication.replay import load_trace, replay_r1_planner  # noqa: E402


def main() -> int:
    root = os.path.dirname(CODE)
    trace = os.path.join(
        root,
        "results",
        "agentic",
        "o2-risk-escalation-v1",
        "runtime_traces",
        "seed-000-task_conditioned.jsonl",
    )
    assert os.path.isfile(trace), trace

    def consumer(_assembly: dict) -> dict:
        return {
            "stop": True,
            "invocations": [],
            "state_patch": {},
            "reason_codes": ["r1-ledger-smoke"],
            "_usage": {"input_tokens": 10, "output_tokens": 2, "total_tokens": 12},
        }

    runner = CallablePlannerConsumer(
        consumer,
        consumer_id="smoke-consumer",
        provider="test",
        model="deterministic-fixture",
    )
    rows = replay_r1_planner(load_trace(trace), runner)
    assert rows
    assert all(r.decision is not None for r in rows)
    assert all(r.attempt.status.value == "succeeded" for r in rows)
    assert all(r.attempt.usage.total_tokens == 12 for r in rows)
    assert all(r.request.assembly_hash for r in rows)
    print(f"PASS planner ledger: {len(rows)} frozen R1 requests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
