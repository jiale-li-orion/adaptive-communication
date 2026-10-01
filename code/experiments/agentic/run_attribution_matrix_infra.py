#!/usr/bin/env python3
"""Formal infrastructure run for the cumulative Agent attribution matrix.

This is deliberately **not** an LLM result.  It injects controlled upstream and
planner corruptions into frozen R1 inputs, then verifies that the canonical
replacement order repairs only the owned layer and cumulatively recovers gold.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
ROOT = CODE.parent
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from agentic_communication.attribution_matrix import evaluate_cumulative_r1_attribution  # noqa: E402
from agentic_communication.planner import DeterministicComplyPlannerConsumer  # noqa: E402
from agentic_communication.replay import frozen_r1_inputs, load_trace  # noqa: E402
from agentic_communication.runtime_contracts import (  # noqa: E402
    MaterializedFragment,
    ModelUsage,
    PlannedCapabilityInvocation,
    PlannerDecision,
    PromptAssembly,
)


DEFAULT_TRACE = (
    ROOT
    / "results"
    / "agentic"
    / "o2-risk-escalation-v1"
    / "runtime_traces"
    / "seed-000-task_conditioned.jsonl"
)
DEFAULT_OUT = ROOT / "results" / "agentic" / "attribution-matrix-infra-v1"


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _corrupt_upstream(gold: PromptAssembly) -> PromptAssembly:
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


class _CorruptingPlanner:
    consumer_id = "controlled-corruption-planner"
    provider = "benchmark"
    model = "controlled-corruption-fixture"

    def __init__(self) -> None:
        self.base = DeterministicComplyPlannerConsumer()

    def decide(self, request, assembly):
        decision, _usage = self.base.decide(request, assembly)
        invocations = list(decision.invocations)
        if invocations:
            # Keep some candidate structure so selection/order/argument repairs
            # remain separately observable.
            damaged = []
            for idx, inv in enumerate(reversed(invocations)):
                if idx == 0:
                    damaged.append(
                        PlannedCapabilityInvocation(
                            capability_id="communication.fallback.gateway_backup",
                            resource="gw0",
                            canonical_arguments={"enabled": True},
                        )
                    )
                else:
                    args = dict(inv.canonical_arguments)
                    if "target_s" in args:
                        args["target_s"] = 600
                    damaged.append(
                        PlannedCapabilityInvocation(
                            capability_id=inv.capability_id,
                            resource="n00",
                            canonical_arguments=args,
                        )
                    )
            invocations = damaged
        else:
            invocations = [
                PlannedCapabilityInvocation(
                    capability_id="communication.fallback.gateway_backup",
                    resource="gw0",
                    canonical_arguments={"enabled": True},
                )
            ]
        return (
            PlannerDecision(
                decision_id=f"decision:{request.request_id}",
                request_id=request.request_id,
                stop=False,
                invocations=invocations,
                reason_codes=["controlled-attribution-corruption"],
            ),
            ModelUsage(),
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace", default=str(DEFAULT_TRACE))
    ap.add_argument("--turns", type=int, default=20)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    trace_path = Path(args.trace)
    out = Path(args.out)
    records = frozen_r1_inputs(load_trace(trace_path))[: args.turns]
    if not records:
        raise RuntimeError("no frozen R1 inputs")
    candidate = _CorruptingPlanner()
    gold = DeterministicComplyPlannerConsumer()

    per_turn = []
    layer_values: dict[int, list[dict]] = defaultdict(list)
    for turn_idx, record in enumerate(records):
        rows = evaluate_cumulative_r1_attribution(
            candidate_assembly=_corrupt_upstream(record.assembly),
            gold_assembly=record.assembly,
            candidate_consumer=candidate,
            gold_consumer=gold,
            request_prefix=f"infra:{turn_idx}",
        )
        serialized = []
        for layer_idx, row in enumerate(rows):
            payload = {
                "layer_index": layer_idx,
                "cumulative_layers": list(row.cumulative_layers),
                "assembly_matches_gold": row.assembly_matches_gold,
                "stop_correct": row.stop_correct,
                "unresolved_argument_slots": list(row.unresolved_argument_slots),
                **row.trajectory,
            }
            serialized.append(payload)
            layer_values[layer_idx].append(payload)
        per_turn.append(
            {
                "seq": record.seq,
                "t_s": record.t_s,
                "task_run_id": record.task_run_id,
                "gold_assembly_hash": record.assembly.assembly_hash,
                "rows": serialized,
            }
        )

    def mean_bool(rows: list[dict], key: str):
        vals = [row[key] for row in rows if row.get(key) is not None]
        return (sum(bool(x) for x in vals) / len(vals)) if vals else None

    def mean_num(rows: list[dict], key: str):
        vals = [float(row[key]) for row in rows if isinstance(row.get(key), (int, float)) and not isinstance(row.get(key), bool)]
        return statistics.fmean(vals) if vals else None

    aggregate_rows = []
    for idx in sorted(layer_values):
        rows = layer_values[idx]
        aggregate_rows.append(
            {
                "layer_index": idx,
                "cumulative_layers": rows[0]["cumulative_layers"],
                "assembly_match_rate": mean_bool(rows, "assembly_matches_gold"),
                "stopping_correctness": mean_bool(rows, "stop_correct"),
                "tool_exact_match_rate": mean_bool(rows, "tool_exact_match"),
                "tool_any_order_precision": mean_num(rows, "tool_any_order_precision"),
                "tool_any_order_recall": mean_num(rows, "tool_any_order_recall"),
                "tool_in_order_normalized": mean_num(rows, "tool_in_order_normalized"),
                "argument_grounding_accuracy": mean_num(rows, "argument_grounding_accuracy"),
                "mean_unresolved_argument_slots": statistics.fmean(
                    len(row["unresolved_argument_slots"]) for row in rows
                ),
            }
        )

    upstream_restored = aggregate_rows[4]["assembly_match_rate"] == 1.0
    final_exact = aggregate_rows[-1]["tool_exact_match_rate"] == 1.0
    final_args = aggregate_rows[-1]["argument_grounding_accuracy"] in (1.0, None)
    planner_does_not_change_assembly = all(
        row["assembly_match_rate"] == 1.0 for row in aggregate_rows[4:]
    )
    passed = upstream_restored and final_exact and final_args and planner_does_not_change_assembly

    contract = {
        "experiment_id": "attribution-matrix-infra-v1",
        "source_trace": str(trace_path.relative_to(ROOT)),
        "turns": len(records),
        "candidate": "controlled upstream corruption + controlled planner corruption",
        "gold_consumer": "DeterministicComplyPlannerConsumer",
        "claim_ceiling": (
            "Infrastructure validation only. This result validates disjoint/cumulative attribution "
            "semantics; it is not an LLM failure rate or method-quality result."
        ),
    }
    _dump(out / "experiment_contract.json", contract)
    with (out / "per_turn_results.jsonl").open("w", encoding="utf-8") as fh:
        for row in per_turn:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    _dump(out / "aggregate.json", {"rows": aggregate_rows})
    audit = {
        "status": "PASS" if passed else "FAIL",
        "upstream_full_replacement_restores_gold_assembly": upstream_restored,
        "planner_posthoc_keeps_gold_assembly": planner_does_not_change_assembly,
        "final_tool_exact_match_rate": aggregate_rows[-1]["tool_exact_match_rate"],
        "final_argument_grounding_accuracy": aggregate_rows[-1]["argument_grounding_accuracy"],
        "source_trace_sha256": _sha(trace_path),
    }
    _dump(out / "audit.json", audit)
    print(json.dumps({"audit": audit, "aggregate": aggregate_rows}, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
