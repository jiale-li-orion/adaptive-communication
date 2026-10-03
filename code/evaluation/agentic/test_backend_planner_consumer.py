#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(CODE)
if CODE not in sys.path:
    sys.path.insert(0, CODE)

from agentic_communication.model_protocol import PROTOCOL_REVISION  # noqa: E402
from agentic_communication.planner import BackendPlannerConsumer, invoke_consumer  # noqa: E402
from agentic_communication.replay import frozen_r1_inputs, load_trace  # noqa: E402


class _FakeBackend:
    name = "fake-openai-compatible"
    model = "fixture-model"

    def __init__(self):
        self.usage = {"prompt_tokens": 100, "completion_tokens": 20, "calls": 0}
        self.last_messages = None

    def complete(self, messages):
        self.last_messages = messages
        self.usage["prompt_tokens"] += 17
        self.usage["completion_tokens"] += 5
        self.usage["calls"] += 1
        return "```json\n" + json.dumps(
            {"stop": True, "invocations": [], "reason_codes": ["fixture"]}
        ) + "\n```"


def main() -> int:
    trace = os.path.join(
        ROOT,
        "results",
        "agentic",
        "o2-risk-escalation-v1",
        "runtime_traces",
        "seed-000-task_conditioned.jsonl",
    )
    record = frozen_r1_inputs(load_trace(trace))[0]
    backend = _FakeBackend()
    consumer = BackendPlannerConsumer(backend)
    result = invoke_consumer(
        assembly=record.assembly,
        consumer=consumer,
        request_id="backend-adapter-smoke",
    )
    assert result.decision is not None and result.decision.stop is True
    assert result.attempt.usage.input_tokens == 17
    assert result.attempt.usage.output_tokens == 5
    assert result.attempt.usage.total_tokens == 22
    assert result.attempt.usage.latency_ms is not None
    assert backend.last_messages and len(backend.last_messages) == 2
    envelope = json.loads(backend.last_messages[1]["content"])
    assert envelope["protocol_revision"] == PROTOCOL_REVISION
    print("PASS backend planner consumer: existing complete(messages) transport -> typed runtime ledger")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
