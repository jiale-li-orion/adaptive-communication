#!/usr/bin/env python3
"""Held-out hard-signature audit for demand-driven future-choice predicates."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from audit_conditional_acquisition_timing_v0_1 import _initial, _minimal_policy
from causal_evidence_process_v0_1 import attach_causal_evidence
from exact_reference_oracle_v0_1 import _attempt_lattice
from future_choice_predicate_solver_v0_1 import (
    BoundPredicateSolver,
    ExactPredicateSolver,
    PREDICATES,
    ProgressiveBoundPredicateSolver,
)
from v8_policy_baselines_v0_1 import _normalize_one, _step


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUTS = ROOT / "results/benchmark/layer1-v0.2-hard-signature-bundles.json"
REFERENCE = ROOT / "results/benchmark/layer2-future-choice-exact-reference-hard-test-v0.2.json"
DEFAULT_OUT = ROOT / "results/benchmark/layer2-future-choice-predicates-hard-test-v0.2.json"

TRUTH_KEY = {
    "CAN_DEFER_QUERY": "defer",
    "QUERY_HARMFUL_NOW": "harmful",
    "QUERY_REQUIRED_NOW": "required",
    "STOP_ACQUISITION": "stop",
}


def _reference_truth(reference_path: Path = REFERENCE) -> dict[str, list[dict]]:
    data = json.loads(reference_path.read_text(encoding="utf-8"))
    out: dict[str, list[dict]] = {}
    for row in data["rows"]:
        sig = str(row["signature"])
        out[sig] = [
            {"time_s": int(boundary["time_s"]), "truth": dict(boundary["truth"])}
            for boundary in row["boundaries"]
        ]
    return out


def _run_predicate(row: dict, predicate: str, truth_by_boundary: dict,
                   choice_upper_depth: int, choice_lower_depth: int,
                   max_expansions: int, bound_scheduler: str,
                   upper_depths: tuple[int, ...] | None = None,
                   lower_depths: tuple[int, ...] | None = None) -> dict:
    bundle = row["bundle"]
    chosen = _minimal_policy(bundle, max_expansions)
    if chosen is None:
        return {
            "signature": row["signature"],
            "split": row["split"],
            "predicate": predicate,
            "status": "NO_MINIMAL_POLICY_IN_RECTANGLE",
            "boundaries": [],
        }
    q, b, solved = chosen
    process = attach_causal_evidence(bundle)
    exact = ExactPredicateSolver(bundle)
    if bound_scheduler == "progressive":
        if upper_depths is None:
            upper_depths = tuple(range(0, choice_upper_depth + 1))
        if lower_depths is None:
            lower_depths = tuple(range(0, choice_lower_depth + 1))
        bound = ProgressiveBoundPredicateSolver(
            bundle,
            upper_depths=upper_depths,
            lower_depths=lower_depths,
        )
    elif bound_scheduler == "maxdepth":
        bound = BoundPredicateSolver(
            bundle,
            choice_upper_depth=choice_upper_depth,
            choice_lower_depth=choice_lower_depth,
        )
    else:
        raise ValueError(bound_scheduler)
    states = _initial(bundle, b)
    at_s = min(_attempt_lattice(bundle))
    node = solved["policy"]
    rows = []
    safe = True
    exact_reference_match = True
    ref_rows = truth_by_boundary[str(row["signature"])]
    boundary_index = 0

    while node and not node.get("terminal"):
        branches = _normalize_one(bundle, process, at_s, states)
        if len(branches) != 1 or next(iter(branches)) != "same" or node.get("event") == "OBSERVATION":
            break
        states = next(iter(branches.values()))
        if boundary_index >= len(ref_rows):
            raise RuntimeError(f"reference boundary underflow for {row['signature']}")
        ref = ref_rows[boundary_index]
        if int(ref["time_s"]) != int(at_s):
            raise RuntimeError(
                f"reference boundary drift for {row['signature']} index={boundary_index}: "
                f"reference_t={ref['time_s']} current_t={at_s}"
            )
        truth = ref["truth"][TRUTH_KEY[predicate]]
        exact_result = exact.prove(
            predicate,
            at_s=at_s,
            states=deepcopy(states),
            query_budget=q,
            max_expansions=max_expansions,
        )
        bound_result = bound.prove(
            predicate,
            at_s=at_s,
            states=deepcopy(states),
            query_budget=q,
        )
        exact_ok = exact_result["value"] is truth
        exact_reference_match = exact_reference_match and exact_ok
        bound_ok = bound_result["value"] is None or bound_result["value"] is truth
        safe = safe and bound_ok
        rows.append({
            "boundary_index": boundary_index,
            "time_s": at_s,
            "truth": truth,
            "exact": exact_result,
            "bound": bound_result,
            "exact_matches_reference": exact_ok,
            "bound_sound": bound_ok,
        })

        if node["action"] == "ISSUE_QUERY":
            break
        stepped = _step(bundle, process, states, at_s, (node["action"], node["arg"]))
        if stepped is None:
            break
        states, at_s = stepped
        node = node["subpolicy"]
        boundary_index += 1

    return {
        "signature": row["signature"],
        "recipe_id": bundle["recipe_id"],
        "split": row["split"],
        "predicate": predicate,
        "minimal_resource_point": [q, b],
        "status": "PASS" if safe and exact_reference_match else "FAIL",
        "safe_against_exact_reference": safe,
        "exact_matches_frozen_reference": exact_reference_match,
        "boundary_count": len(rows),
        "boundaries": rows,
    }


def _aggregate(rows: list[dict]) -> dict:
    status = Counter(); truth = Counter(); bound_value = Counter()
    boundaries = resolved = errors = exact_errors = 0
    exact_wall = bound_wall = 0.0
    exact_expanded = exact_actions = exact_continuations = 0
    bound_upper = bound_lower = bound_actions = 0
    for row in rows:
        status[row["status"]] += 1
        for b in row.get("boundaries", []):
            boundaries += 1
            truth[str(bool(b["truth"]))] += 1
            bv = b["bound"]["value"]
            bound_value["UNKNOWN" if bv is None else str(bool(bv))] += 1
            resolved += int(bv is not None)
            errors += int(not b["bound_sound"])
            exact_errors += int(not b["exact_matches_reference"])
            exact_wall += float(b["exact"]["wall_s"])
            bound_wall += float(b["bound"]["wall_s"])
            exact_expanded += int(b["exact"]["expanded"])
            exact_actions += int(b["exact"]["action_checks"])
            exact_continuations += int(b["exact"]["continuation_calls"])
            bound_upper += int(b["bound"]["upper_nodes"])
            bound_lower += int(b["bound"]["lower_nodes"])
            bound_actions += int(b["bound"]["action_checks"])
    return {
        "signature_count": len(rows),
        "status_count": dict(sorted(status.items())),
        "boundary_count": boundaries,
        "truth_count": dict(sorted(truth.items())),
        "bound_value_count": dict(sorted(bound_value.items())),
        "resolved_boundary_count": resolved,
        "unresolved_boundary_count": boundaries - resolved,
        "resolved_fraction": resolved / boundaries if boundaries else None,
        "soundness_error_count": errors,
        "exact_reference_mismatch_count": exact_errors,
        "exact_wall_s": exact_wall,
        "bound_wall_s": bound_wall,
        "bound_vs_exact_wall_ratio": bound_wall / exact_wall if exact_wall else None,
        "exact_expanded": exact_expanded,
        "exact_action_checks": exact_actions,
        "exact_continuation_calls": exact_continuations,
        "bound_upper_nodes": bound_upper,
        "bound_lower_nodes": bound_lower,
        "bound_action_checks": bound_actions,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inputs", type=Path, default=DEFAULT_INPUTS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--reference", type=Path, default=REFERENCE)
    ap.add_argument("--split", choices=["train", "dev", "test", "all"], default="test")
    ap.add_argument("--choice-upper-depth", type=int, default=4)
    ap.add_argument("--choice-lower-depth", type=int, default=6)
    ap.add_argument("--bound-scheduler", choices=["maxdepth", "progressive"], default="maxdepth")
    ap.add_argument("--upper-depths", default=None, help="comma-separated progressive U schedule, e.g. 0,4")
    ap.add_argument("--lower-depths", default=None, help="comma-separated progressive L schedule, e.g. 1,6")
    ap.add_argument("--max-expansions", type=int, default=200_000)
    args = ap.parse_args()

    data = json.loads(args.inputs.read_text(encoding="utf-8"))
    truth = _reference_truth(args.reference)
    upper_depths = tuple(int(x) for x in args.upper_depths.split(",")) if args.upper_depths else None
    lower_depths = tuple(int(x) for x in args.lower_depths.split(",")) if args.lower_depths else None
    selected = [r for r in data["rows"] if args.split == "all" or r["split"] == args.split]
    by_predicate = {}
    all_rows = []
    for predicate in PREDICATES:
        rows = []
        for i, row in enumerate(selected):
            result = _run_predicate(
                row,
                predicate,
                truth,
                args.choice_upper_depth,
                args.choice_lower_depth,
                args.max_expansions,
                args.bound_scheduler,
                upper_depths,
                lower_depths,
            )
            rows.append(result); all_rows.append(result)
            print(predicate, i + 1, row["split"], str(row["signature"])[:12], result["status"], result["boundary_count"], flush=True)
        by_predicate[predicate] = _aggregate(rows)

    overall = _aggregate(all_rows)
    safe = overall["soundness_error_count"] == 0 and overall["exact_reference_mismatch_count"] == 0
    artifact = {
        "schema_version": "0.2",
        "status": "DEMAND_DRIVEN_FUTURE_CHOICE_PREDICATE_EVAL",
        "inputs_ref": str(args.inputs.relative_to(ROOT)),
        "inputs_sha256": sha256(args.inputs.read_bytes()).hexdigest(),
        "reference_ref": str(args.reference.relative_to(ROOT)),
        "reference_sha256": sha256(args.reference.read_bytes()).hexdigest(),
        "split_filter": args.split,
        "choice_upper_depth": args.choice_upper_depth,
        "choice_lower_depth": args.choice_lower_depth,
        "bound_scheduler": args.bound_scheduler,
        "upper_depths": list(upper_depths) if upper_depths is not None else None,
        "lower_depths": list(lower_depths) if lower_depths is not None else None,
        "all_bound_answers_sound": overall["soundness_error_count"] == 0,
        "exact_same_predicate_matches_frozen_reference": overall["exact_reference_mismatch_count"] == 0,
        "by_predicate": by_predicate,
        "overall": overall,
        "rows": all_rows,
        "claim_boundary": [
            "Each predicate is evaluated in a separate pass with fresh per-case proof caches, preventing cross-predicate memo warming.",
            "The exact baseline answers the same predicate directly with early stopping; it does not construct the full action frontier.",
            "The bound solver may return UNKNOWN; every non-UNKNOWN answer must agree with the frozen exact action-frontier truth.",
            "Wall time includes continuation search or structural proof work and witness replay, but not loading the frozen reference truth.",
            "Results are held-out Layer-1 v0.2 hard test signatures only and still follow exact-policy-prefix states rather than closed-loop states induced by the compared solvers.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "safe": safe,
        "by_predicate": by_predicate,
        "overall": overall,
        "out": str(args.out),
    }, ensure_ascii=False, indent=2))
    return 0 if safe else 1


if __name__ == "__main__":
    raise SystemExit(main())
