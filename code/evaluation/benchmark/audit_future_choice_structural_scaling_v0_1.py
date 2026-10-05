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
from contextlib import contextmanager
from hashlib import sha256
import json
from pathlib import Path
import signal
from statistics import median
from time import perf_counter
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


class _WallTimeout(RuntimeError):
    pass


@contextmanager
def _wall_timeout(seconds: float | None):
    if seconds is None or seconds <= 0:
        yield
        return

    def _handler(_signum, _frame):
        raise _WallTimeout(f"wall-time limit {seconds}s exceeded")

    old = signal.signal(signal.SIGALRM, _handler)
    signal.setitimer(signal.ITIMER_REAL, float(seconds))
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.0)
        signal.signal(signal.SIGALRM, old)


def _timeout_exact(
    bundle,
    predicate: str,
    *,
    at_s: int,
    states,
    query_budget: int,
    max_expansions: int,
    wall_timeout_s: float | None,
) -> dict[str, Any]:
    solver = ExactPredicateSolver(bundle)
    started = perf_counter()
    try:
        with _wall_timeout(wall_timeout_s):
            row = solver.prove(
                predicate,
                at_s=at_s,
                states=deepcopy(states),
                query_budget=query_budget,
                max_expansions=max_expansions,
            )
        row["timed_out"] = False
        return row
    except _WallTimeout:
        return {
            "predicate": predicate,
            "value": None,
            "status": "TIMEOUT",
            "timed_out": True,
            "checked_action_keys": [],
            "action_checks": int(solver.totals["action_checks"]),
            "continuation_calls": int(solver.totals["continuation_calls"]),
            # Search metrics update only after a completed continuation call;
            # this is therefore a lower bound when a timeout interrupts search.
            "expanded": int(solver.totals["expanded"]),
            "expanded_is_lower_bound": True,
            "wall_s": perf_counter() - started,
        }


def _timeout_bound(
    bundle,
    predicate: str,
    *,
    at_s: int,
    states,
    query_budget: int,
    choice_upper_depth: int,
    choice_lower_depth: int,
    wall_timeout_s: float | None,
) -> dict[str, Any]:
    solver = BoundPredicateSolver(
        bundle,
        choice_upper_depth=choice_upper_depth,
        choice_lower_depth=choice_lower_depth,
    )
    started = perf_counter()
    try:
        with _wall_timeout(wall_timeout_s):
            row = solver.prove(
                predicate,
                at_s=at_s,
                states=deepcopy(states),
                query_budget=query_budget,
            )
        row["timed_out"] = False
        return row
    except _WallTimeout:
        return {
            "predicate": predicate,
            "value": None,
            "status": "TIMEOUT",
            "timed_out": True,
            "checked_action_keys": [],
            "action_checks": int(solver.totals["action_checks"]),
            "upper_nodes": int(solver.totals["upper_nodes"]),
            "lower_nodes": int(solver.totals["lower_nodes"]),
            "nodes_are_lower_bounds": True,
            "wall_s": perf_counter() - started,
        }


def _parse_ints(text: str) -> set[int]:
    return {int(x.strip()) for x in text.split(",") if x.strip()}


def _parse_strings(text: str) -> set[str]:
    return {x.strip() for x in text.split(",") if x.strip()}


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    exact_wall = sum(float(r["exact"]["wall_s"]) for r in rows)
    bound_wall = sum(float(r["bound"]["wall_s"]) for r in rows)
    exact_expanded = sum(int(r["exact"].get("expanded", 0)) for r in rows)
    bound_upper = sum(int(r["bound"].get("upper_nodes", 0)) for r in rows)
    bound_lower = sum(int(r["bound"].get("lower_nodes", 0)) for r in rows)
    exact_timeouts = sum(bool(r["exact"].get("timed_out")) for r in rows)
    bound_timeouts = sum(bool(r["bound"].get("timed_out")) for r in rows)
    paired = [
        r for r in rows
        if not r["exact"].get("timed_out") and not r["bound"].get("timed_out")
    ]
    paired_exact_wall = sum(float(r["exact"]["wall_s"]) for r in paired)
    paired_bound_wall = sum(float(r["bound"]["wall_s"]) for r in paired)
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
        for r in paired
        if float(r["exact"]["wall_s"]) > 0
    ]
    return {
        "row_count": len(rows),
        "paired_completed_count": len(paired),
        "exact_timeout_count": exact_timeouts,
        "bound_timeout_count": bound_timeouts,
        "exact_resolved_count": exact_resolved,
        "bound_resolved_count": bound_resolved,
        "bound_unresolved_count": len(rows) - bound_resolved,
        "bound_unknown_without_timeout_count": sum(
            r["bound"].get("status") == "UNRESOLVED" for r in rows
        ),
        "soundness_error_count": sound_errors,
        "exact_wall_s": exact_wall,
        "bound_wall_s": bound_wall,
        "paired_exact_wall_s": paired_exact_wall,
        "paired_bound_wall_s": paired_bound_wall,
        "aggregate_bound_vs_exact_wall_ratio": (
            paired_bound_wall / paired_exact_wall if paired_exact_wall else None
        ),
        "median_per_row_bound_vs_exact_wall_ratio": median(ratios) if ratios else None,
        "exact_expanded": exact_expanded,
        "exact_expanded_includes_timeout_lower_bounds": bool(exact_timeouts),
        "bound_upper_nodes": bound_upper,
        "bound_lower_nodes": bound_lower,
        "bound_nodes_include_timeout_lower_bounds": bool(bound_timeouts),
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
    ap.add_argument("--wall-timeout-s", type=float, default=None)
    ap.add_argument("--checkpoint", type=Path, default=None)
    ap.add_argument("--resume", action="store_true")
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

    # Complete one structural scale before moving to the next so a partial run
    # still yields an interpretable k=4 / k=6 / k=8 progression.
    selected = sorted(
        selected,
        key=lambda r: (int(r["overlap_count"]), str(r["parent_signature"])),
    )

    checkpoint = args.checkpoint or Path(str(args.out) + ".rows.jsonl")
    run_config = {
        "inputs_sha256": sha256(args.inputs.read_bytes()).hexdigest(),
        "parent_splits": sorted(split_filter),
        "overlap_values": sorted(overlap_filter),
        "predicates": list(predicates),
        "query_budget": args.query_budget,
        "choice_upper_depth": args.choice_upper_depth,
        "choice_lower_depth": args.choice_lower_depth,
        "max_expansions": args.max_expansions,
        "wall_timeout_s": args.wall_timeout_s,
        "limit_parents": args.limit_parents,
    }
    run_config_digest = sha256(
        json.dumps(run_config, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    rows = []
    completed_keys: set[tuple[str, int, str]] = set()
    if args.resume and checkpoint.exists():
        for line in checkpoint.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("run_config_digest") != run_config_digest:
                raise ValueError("checkpoint run configuration does not match requested scaling audit")
            key = (
                str(row["parent_signature"]),
                int(row["overlap_count"]),
                str(row["predicate"]),
            )
            if key in completed_keys:
                continue
            completed_keys.add(key)
            rows.append(row)
    elif checkpoint.exists():
        checkpoint.unlink()
    checkpoint.parent.mkdir(parents=True, exist_ok=True)

    for index, source_row in enumerate(selected):
        bundle = source_row["bundle"]
        at_s = min(_attempt_lattice(bundle))
        satellite_budget = int(bundle["public_environment"]["satellite_budget_units"])
        states = _initial(bundle, satellite_budget)
        for predicate in predicates:
            key = (
                str(source_row["parent_signature"]),
                int(source_row["overlap_count"]),
                predicate,
            )
            if key in completed_keys:
                continue
            exact = _timeout_exact(
                bundle,
                predicate,
                at_s=at_s,
                states=states,
                query_budget=args.query_budget,
                max_expansions=args.max_expansions,
                wall_timeout_s=args.wall_timeout_s,
            )
            bound = _timeout_bound(
                bundle,
                predicate,
                at_s=at_s,
                states=states,
                query_budget=args.query_budget,
                choice_upper_depth=args.choice_upper_depth,
                choice_lower_depth=args.choice_lower_depth,
                wall_timeout_s=args.wall_timeout_s,
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
                "run_config_digest": run_config_digest,
            }
            rows.append(row)
            completed_keys.add(key)
            with checkpoint.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                fh.flush()
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
        "wall_timeout_s": args.wall_timeout_s,
        "run_config_digest": run_config_digest,
        "checkpoint_ref": str(checkpoint),
        "checkpoint_sha256": sha256(checkpoint.read_bytes()).hexdigest(),
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
