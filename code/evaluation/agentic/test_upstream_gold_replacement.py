#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(CODE)
if CODE not in sys.path:
    sys.path.insert(0, CODE)

from agentic_communication.replay import frozen_r1_inputs, load_trace  # noqa: E402
from agentic_communication.runtime_contracts import MaterializedFragment, PromptAssembly  # noqa: E402
from agentic_communication.trajectory_eval import GoldReplacementLayer  # noqa: E402
from agentic_communication.upstream_gold import (  # noqa: E402
    apply_upstream_gold_replacement,
    upstream_layer_ownership,
)


def _corrupt(gold: PromptAssembly) -> PromptAssembly:
    replacements = {
        "runtime_task_contract": {"corrupted": "task"},
        "evidence_needs": [{"corrupted": "need"}],
        "recent_capability_outcomes": [{"corrupted": "percept"}],
        "resource_inventory": [],
        "investigation_state": {"corrupted": "state"},
        "evidence_slice": [],
        "capability_catalog": [],
    }
    fragments = []
    for fragment in gold.fragments:
        if fragment.kind in replacements:
            fragments.append(
                MaterializedFragment.build(
                    kind=fragment.kind,
                    source_ref=fragment.source_ref,
                    source_revision=fragment.source_revision,
                    trust_class=fragment.trust_class,
                    cache_class=fragment.cache_class,
                    content=replacements[fragment.kind],
                    selection_reason=fragment.selection_reason,
                )
            )
        else:
            fragments.append(fragment)
    return PromptAssembly.build(
        task_contract_id="corrupted-task-contract",
        task_run_id=gold.task_run_id,
        context_manifest_revision=gold.context_manifest_revision + 100,
        fragments=fragments,
        percept_refs=["corrupted-percept"],
    )


def main() -> int:
    trace = os.path.join(
        ROOT,
        "results",
        "agentic",
        "o2-risk-escalation-v1",
        "runtime_traces",
        "seed-000-task_conditioned.jsonl",
    )
    gold = frozen_r1_inputs(load_trace(trace))[0].assembly
    candidate = _corrupt(gold)
    assert candidate.assembly_hash != gold.assembly_hash

    task_only = apply_upstream_gold_replacement(
        candidate, gold, [GoldReplacementLayer.TASK]
    ).assembly
    assert task_only.task_contract_id == gold.task_contract_id
    assert task_only.assembly_hash != gold.assembly_hash

    needs_only = apply_upstream_gold_replacement(
        candidate, gold, [GoldReplacementLayer.EVIDENCE_NEED]
    ).assembly
    assert next(f for f in needs_only.fragments if f.kind == "evidence_needs").content == next(
        f for f in gold.fragments if f.kind == "evidence_needs"
    ).content
    assert next(f for f in needs_only.fragments if f.kind == "runtime_task_contract").content != next(
        f for f in gold.fragments if f.kind == "runtime_task_contract"
    ).content

    all_upstream = apply_upstream_gold_replacement(
        candidate,
        gold,
        [
            GoldReplacementLayer.TASK,
            GoldReplacementLayer.EVIDENCE_NEED,
            GoldReplacementLayer.PERCEPT,
            GoldReplacementLayer.CONTEXT,
        ],
    ).assembly
    assert all_upstream.model_dump(mode="json") == gold.model_dump(mode="json")
    assert all_upstream.assembly_hash == gold.assembly_hash
    ownership = upstream_layer_ownership()
    assert ownership["gold_task"] == ["runtime_task_contract"]
    assert "evidence_slice" in ownership["gold_context"]
    assert "recent_capability_outcomes" in ownership["gold_percept"]
    print("PASS upstream gold replacement: Task/EvidenceNeed/Percept/Context are disjoint and cumulatively restore gold hash")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
