#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(CODE)
if CODE not in sys.path:
    sys.path.insert(0, CODE)

from agentic_communication.attribution_matrix import evaluate_cumulative_r1_attribution  # noqa: E402
from agentic_communication.planner import (  # noqa: E402
    CallablePlannerConsumer,
    DeterministicComplyPlannerConsumer,
)
from agentic_communication.replay import frozen_r1_inputs, load_trace  # noqa: E402
from agentic_communication.runtime_contracts import MaterializedFragment, PromptAssembly  # noqa: E402


def corrupt(gold: PromptAssembly) -> PromptAssembly:
    replacements = {
        "runtime_task_contract": {"desired_state": {"required_period_s": 600}},
        "evidence_needs": [{"corrupted": "need"}],
        "recent_capability_outcomes": [{"corrupted": "percept"}],
        "resource_inventory": ["n00"],
        "investigation_state": {"targets": ["n00"]},
        "evidence_slice": [],
        "capability_catalog": [],
    }
    fragments = []
    for f in gold.fragments:
        if f.kind in replacements:
            fragments.append(
                MaterializedFragment.build(
                    kind=f.kind,
                    source_ref=f.source_ref,
                    source_revision=f.source_revision,
                    trust_class=f.trust_class,
                    cache_class=f.cache_class,
                    content=replacements[f.kind],
                    selection_reason=f.selection_reason,
                )
            )
        else:
            fragments.append(f)
    return PromptAssembly.build(
        task_contract_id="corrupted-task",
        task_run_id=gold.task_run_id,
        context_manifest_revision=gold.context_manifest_revision + 99,
        fragments=fragments,
        percept_refs=["corrupted-percept"],
    )


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
        "reason_codes": ["bad-attribution-fixture"],
    }


def main() -> int:
    trace = os.path.join(
        ROOT,
        "results",
        "agentic",
        "o2-risk-escalation-v1",
        "runtime_traces",
        "seed-000-task_conditioned.jsonl",
    )
    gold_assembly = frozen_r1_inputs(load_trace(trace))[0].assembly
    candidate_assembly = corrupt(gold_assembly)
    candidate = CallablePlannerConsumer(
        bad,
        consumer_id="bad-attribution-fixture",
        provider="test",
        model="bad-fixture",
    )
    gold = DeterministicComplyPlannerConsumer()
    rows = evaluate_cumulative_r1_attribution(
        candidate_assembly=candidate_assembly,
        gold_assembly=gold_assembly,
        candidate_consumer=candidate,
        gold_consumer=gold,
    )
    assert len(rows) == 8, len(rows)  # base + 4 upstream + 3 planner layers
    assert rows[0].assembly_matches_gold is False
    assert rows[4].assembly_matches_gold is True, rows[4]
    # Planner post-hoc layers must not alter the fully-gold upstream assembly.
    assert all(row.assembly_matches_gold for row in rows[4:])
    assert rows[-1].trajectory["tool_exact_match"] is True, rows[-1]
    assert rows[-1].trajectory["argument_grounding_accuracy"] in (1.0, None)
    # The bad callable ignores its input, so upstream replacement alone must not
    # be misreported as a planner repair.
    assert rows[4].trajectory["tool_exact_match"] is False
    print("PASS attribution matrix: upstream rerun + planner posthoc layers are cumulative and disjoint")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
