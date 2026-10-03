#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(CODE)
if CODE not in sys.path:
    sys.path.insert(0, CODE)

from agentic_communication.model_protocol import (  # noqa: E402
    PROTOCOL_REVISION,
    assert_no_evaluator_leakage,
    protocol_hash,
    render_planner_protocol,
)
from agentic_communication.planner import CallablePlannerConsumer, invoke_consumer  # noqa: E402
from agentic_communication.replay import frozen_r1_inputs, load_trace  # noqa: E402


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
    payload = render_planner_protocol(record.assembly)
    assert payload["protocol_revision"] == PROTOCOL_REVISION
    assert payload["task_contract"]
    assert payload["resource_inventory"]
    assert isinstance(payload["capabilities"], list)
    assert "properties" in payload["output_schema"]
    assert_no_evaluator_leakage(payload)
    h1 = protocol_hash(record.assembly)
    h2 = protocol_hash(record.assembly)
    assert h1 == h2 and len(h1) == 64

    seen = {}
    def fn(model_input: dict) -> dict:
        seen.update(model_input)
        return {"stop": True, "invocations": [], "reason_codes": ["protocol-smoke"]}

    consumer = CallablePlannerConsumer(
        fn,
        consumer_id="protocol-smoke",
        provider="test",
        model="fixture",
        input_renderer=render_planner_protocol,
    )
    result = invoke_consumer(
        assembly=record.assembly,
        consumer=consumer,
        request_id="protocol-smoke-request",
    )
    assert result.decision is not None and result.decision.stop is True
    assert seen.get("protocol_revision") == PROTOCOL_REVISION
    print("PASS model protocol: stable hash, typed proposal schema, no evaluator-only leakage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
