#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(os.path.dirname(HERE))
if CODE not in sys.path:
    sys.path.insert(0, CODE)

from agentic_communication.episodes import benchmark_episode_catalog  # noqa: E402
from agentic_communication.task_compiler import CommunicationTaskCompiler  # noqa: E402
from agentic_communication.trajectory_eval import (  # noqa: E402
    capability_steps,
    gold_replacement_registry,
    trajectory_metrics,
)
from agentic_communication.contracts import RuntimeTraceEvent  # noqa: E402
from agentic_communication.runtime_contracts import CapabilityRequest, EffectSemantics  # noqa: E402


def main() -> int:
    catalog = benchmark_episode_catalog()
    assert list(catalog) == ["O1", "O2", "O3", "O4", "O5", "O6"]
    compiler = CommunicationTaskCompiler()
    for key, template in catalog.items():
        contract = compiler.compile(template.task, 0)
        assert contract.desired_state["operational_task_family"] == template.task.family.value, key
        assert contract.target_resources, key
    req = CapabilityRequest(
        request_id="r1",
        task_contract_id="t",
        task_run_id="run",
        principal="p",
        capability_id="communication.config.set_report_period",
        contract_revision=1,
        action="set_report_period",
        resource="n01",
        resource_type="monitoring_node_config",
        canonical_arguments={"target_s": 300},
        intended_effect=EffectSemantics.EXTERNAL_SIDE_EFFECT,
    )
    events = [RuntimeTraceEvent(seq=1, t_s=0, event_type="capability_request", payload=req.model_dump(mode="json"))]
    steps = capability_steps(events)
    score = trajectory_metrics(steps, steps)
    assert score["tool_exact_match"] is True
    assert score["tool_in_order_normalized"] == 1.0
    assert score["argument_grounding_accuracy"] == 1.0
    assert len(gold_replacement_registry()) == 9
    print("PASS task catalog + trajectory/gold replacement schema")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
