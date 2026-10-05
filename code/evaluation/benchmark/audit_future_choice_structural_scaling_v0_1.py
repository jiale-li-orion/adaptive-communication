#!/usr/bin/env python3
"""Controlled structural-scaling audit for future-choice predicates.

The input bundles are method-evaluation-only derivatives of frozen Layer-1 hard
parents.  Only the declared workload-density overlap coordinate is scaled.
This audit never changes benchmark membership or labels.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from statistics import median
from typing import Any

from audit_conditional_acquisition_timing_v0_1 import _initial
from exact_reference_oracle_v0_1 import _attempt_lattice
from future_choice_predicate_solver_v0_1 import (
    BoundPredicateSolver,
    ExactPredicateSolver,
    PREDICATES,
)


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUT = ROOT / "results/benchmark/layer2-future-choice-structural-scaling-v0.1.json"


def _parse_ints(text: str) -> set[int]:
    return {int(x.strip()) for x in text.split(",") if x.strip()}


def _parse_strings(text: str) -> set[str]:
    return {x.strip() for x in text.split(",") if x.strip()}


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    exact_wall = sum(float(r["exact"]["wall_s"]) for r in rows)
    bound_wall = sum(float(r["bound"]["wall_s"]) for r in rows)
    exact_expanded = sum(int(r["exact"]["expanded"]) for r in rows)
    bound_upper = sum(int(r["bound"]["upper_nodes"]) for r in rows)
    bound_lower = sum(int(r["bound"]["lower_nodes"]) for r in rows)
    exact_resolved = sum(r["exact"]["value"] is not None for r in rows)
    bound_resolved = sum(r["bound"]["value"] is not None for r in rows)
    sound_errors = sum(
        r["bound"]["value"] is not None
        and r["exact"]["value"] is not None
        and r["bound"]["value"] != r["exact"]["value"]
        for r in rows
    )
    ratios = [
        float(r["bound"]["wall_s"]) / float(r["exact"]["wall_s"])
        for r in rows
        if float(r["exact"]["wall_s"]) > 0
    ]
    return {
        "row_count": len(rows),
        "exact_resolved_count": exact_resolved,
        "bound_resolved_count": bound_resolved,
        "bound_unresolved_count": len(rows) - bound_resolved,
        "soundness_error_count": sound_errors,
        "exact_wall_s": exact_wall,
        "bound_wall_s": bound_wall,
        "aggregate_bound_vs_exact_wall_ratio": bound_wall / exact_wall if exact_wall else None,
        "median_per_row_bound_vs_exact_wall_ratio": median(ratios) if ratios else None,
        "exact_expanded": exact_expanded,
        "bound_upper_nodes": bound_upper,
        "bound_lower_nodes": bound_lower,
        "truth_count": dict(sorted(Counter(str(r["exact"]["value"]) for r in rows).items())),
        "bound_value_count": dict(sorted(Counter(str(r["bound"]["value"]) for r in rows).items())),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inputs", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--parent-splits", default="train,dev")
    ap.add_argument("--overlaps", default="4,6,8")
    ap.add_argument("--predicates", default=",".join(PREDICATES))
    ap.add_argument("--query-budget", type=int, default=1)
    ap.add_argument("--choice-upper-depth", type=int, default=4)
    ap.add_argument("--choice-lower-depth", type=int, default=6)
    ap.add_argument("--max-expansions", type=int, default=200_000)
    ap.add_argument("--limit-parents", type=int, default=None)
    args = ap.parse_args()

    split_filter = _parse_strings(args.parent_splits)
    overlap_filter = _parse_ints(args.overlaps)
    predicates = tuple(x for x in args.predicates.split(",") if x)
    unknown = set(predicates) - set(PREDICATES)
    if unknown:
        raise ValueError(f"unknown predicates: {sorted(unknown)}")

    data = json.loads(args.inputs.read_text(encoding="utf-8"))
    if data.get("benchmark_membership") is not False:
        raise ValueError("structural-scaling input must explicitly be outside benchmark membership")
    selected = [
        r for r in data["rows"]
        if str(r["parent_split"]) in split_filter and int(r["overlap_count"]) in overlap_filter
    ]
    if args.limit_parents is not None:
        parent_ids = []
        for row in selected:
            sig = str(row["parent_signature"])
            if sig not in parent_ids:
                parent_ids.append(sig)
        keep = set(parent_ids[: args.limit_parents])
        selected = [r for r in selected if str(r["parent_signature"]) in keep]

    rows = []
    for index, source_row in enumerate(selected):
        bundle = source_row["bundle"]
        at_s = min(_attempt_lattice(bundle))
        satellite_budget = int(bundle["public_environment"]["satellite_budget_units"])
        states = _initial(bundle, satellite_budget)
        for predicate in predicates:
            exact_solver = ExactPredicateSolver(bundle)
            bound_solver = BoundPredicateSolver(
                bundle,
                choice_upper_depth=args.choice_upper_depth,
                choice_lower_depth=args.choice_lower_depth,
            )
            exact = exact_solver.prove(
                predicate,
                at_s=at_s,
                states=deepcopy(states),
                query_budget=args.query_budget,
                max_expansions=args.max_expansions,
            )
            bound = bound_solver.prove(
                predicate,
                at_s=at_s,
                states=deepcopy(states),
                query_budget=args.query_budget,
            )
            sound = (
                bound["value"] is None
                or exact["value"] is None
                or bound["value"] == exact["value"]
            )
            row = {
                "parent_signature": source_row["parent_signature"],
                "parent_recipe_id": source_row["parent_recipe_id"],
                "parent_split": source_row["parent_split"],
                "overlap_count": int(source_row["overlap_count"]),
                "report_interval_s": int(source_row["report_interval_s"]),
                "resource_headroom": source_row["resource_headroom"],
                "bundle_id": bundle["bundle_id"],
                "predicate": predicate,
                "time_s": at_s,
                "query_budget": args.query_budget,
                "satellite_budget": satellite_budget,
                "exact": exact,
                "bound": bound,
                "bound_sound_against_exact": sound,
            }
            rows.append(row)
        print(
            index + 1,
            source_row["parent_split"],
            str(source_row["parent_signature"])[:12],
            "k=", source_row["overlap_count"],
            flush=True,
        )

    by_overlap = {}
    for overlap in sorted({int(r["overlap_count"]) for r in rows}):
        subset = [r for r in rows if int(r["overlap_count"]) == overlap]
        by_overlap[str(overlap)] = {
            "overall": _summarize(subset),
            "by_predicate": {
                p: _summarize([r for r in subset if r["predicate"] == p])
                for p in predicates
            },
        }
    by_predicate = {
        p: _summarize([r for r in rows if r["predicate"] == p])
        for p in predicates
    }
    overall = _summarize(rows)
    all_sound = overall["soundness_error_count"] == 0
    artifact = {
        "schema_version": "0.1",
        "status": "METHOD_ONLY_STRUCTURAL_SCALING_DIAGNOSTIC",
        "benchmark_membership": False,
        "inputs_ref": str(args.inputs),
        "inputs_sha256": sha256(args.inputs.read_bytes()).hexdigest(),
        "parent_splits": sorted(split_filter),
        "overlap_values": sorted(overlap_filter),
        "predicates": list(predicates),
        "query_budget": args.query_budget,
        "choice_upper_depth": args.choice_upper_depth,
        "choice_lower_depth": args.choice_lower_depth,
        "max_expansions": args.max_expansions,
        "bundle_count": len(selected),
        "predicate_row_count": len(rows),
        "all_bound_answers_sound": all_sound,
        "overall": overall,
        "by_overlap": by_overlap,
        "by_predicate": by_predicate,
        "rows": rows,
        "claim_boundary": [
            "This is method-only CONTROLLED_STRESS and never changes Layer-1 benchmark membership or release identity.",
            "Only workload-density overlap and the same headroom-class satellite budget scale; task/source/service/evidence/recovery semantics remain fixed per parent.",
            "Each row uses fresh exact and structural-proof caches at the initial legal decision boundary, isolating per-boundary structural scaling rather than amortized cross-boundary reuse.",
            "Generic exact answers the same requested predicate with early stop; bound UNKNOWN is preserved rather than converted to a label.",
            "Train/dev hard parents are used for development scaling; repeatedly inspected Layer-1 test parents are excluded by default.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "all_bound_answers_sound": all_sound,
        "bundle_count": len(selected),
        "predicate_row_count": len(rows),
        "overall": overall,
        "by_overlap": by_overlap,
        "out": str(args.out),
    }, ensure_ascii=False, indent=2))
    return 0 if all_sound else 1


if __name__ == "__main__":
    raise SystemExit(main())
