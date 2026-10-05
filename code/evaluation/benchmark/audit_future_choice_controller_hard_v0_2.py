#!/usr/bin/env python3
"""Scale future-choice controller evaluation to all Layer-1 v0.2 hard signatures."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import time

from audit_conditional_acquisition_timing_v0_1 import _initial, _minimal_policy
from causal_evidence_process_v0_1 import attach_causal_evidence
from conditional_action_frontier_v0_1 import build_action_frontier
from exact_reference_oracle_v0_1 import _attempt_lattice
from future_choice_bound_controller_v0_1 import bound_future_choice_context
from v8_policy_baselines_v0_1 import _normalize_one, _step


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUTS = ROOT / "results/benchmark/layer1-v0.2-hard-signature-bundles.json"
DEFAULT_OUT = ROOT / "results/benchmark/layer2-future-choice-controller-hard-v0.2.json"


def _truth(frontier: dict) -> dict[str, bool]:
    cert = set(frontier["certified_action_keys"])
    q = "ISSUE_QUERY:gateway_state_summary"
    non = [x for x in cert if x != q]
    return {
        "stop": frontier["context"]["query_free_completion"] is True,
        "harmful": frontier["context"]["query_now_legal"] and q not in cert,
        "defer": bool(non),
        "required": q in cert and not non,
    }


def _label_sound(labels: list[str], truth: dict[str, bool]) -> list[str]:
    mapping = {
        "STOP_ACQUISITION_CERTIFIED": "stop",
        "QUERY_HARMFUL_NOW": "harmful",
        "CAN_DEFER_QUERY": "defer",
        "QUERY_REQUIRED_NOW": "required",
    }
    return [label for label, key in mapping.items() if label in labels and not truth[key]]


def _run_case(
    row: dict,
    upper_depth: int,
    choice_upper_depth: int | None,
    lower_depth: int,
    max_expansions: int,
) -> dict:
    bundle = row["bundle"]
    chosen = _minimal_policy(bundle, max_expansions)
    if chosen is None:
        return {
            "signature": row["signature"], "split": row["split"],
            "status": "NO_MINIMAL_POLICY_IN_RECTANGLE", "boundaries": [],
        }
    q, b, solved = chosen
    process = attach_causal_evidence(bundle)
    states = _initial(bundle, b)
    at_s = min(_attempt_lattice(bundle))
    node = solved["policy"]
    boundaries = []
    safe = True

    while node and not node.get("terminal"):
        branches = _normalize_one(bundle, process, at_s, states)
        if len(branches) != 1 or next(iter(branches)) != "same" or node.get("event") == "OBSERVATION":
            break
        states = next(iter(branches.values()))
        exact_t0 = time.perf_counter()
        exact = build_action_frontier(
            bundle, at_s=at_s, states=deepcopy(states), query_budget=q,
            max_expansions=max_expansions,
        )
        exact_wall_s = time.perf_counter() - exact_t0
        bound_t0 = time.perf_counter()
        bounded = bound_future_choice_context(
            bundle, at_s=at_s, states=deepcopy(states), query_budget=q,
            upper_depth=upper_depth,
            choice_upper_depth=choice_upper_depth,
            choice_lower_depth=lower_depth,
        )
        bound_wall_s = time.perf_counter() - bound_t0
        truth = _truth(exact)
        bad = _label_sound(bounded["labels"], truth)
        safe = safe and not bad
        boundaries.append({
            "time_s": at_s,
            "truth": truth,
            "exact_certified_action_keys": exact["certified_action_keys"],
            "labels": bounded["labels"],
            "soundness_errors": bad,
            "bound_cost": bounded["bound_cost"],
            "exact_reference_wall_s": exact_wall_s,
            "bound_controller_wall_s": bound_wall_s,
        })

        if node["action"] == "ISSUE_QUERY":
            break
        stepped = _step(bundle, process, states, at_s, (node["action"], node["arg"]))
        if stepped is None:
            break
        states, at_s = stepped
        node = node["subpolicy"]

    return {
        "signature": row["signature"],
        "recipe_id": bundle["recipe_id"],
        "split": row["split"],
        "minimal_resource_point": [q, b],
        "status": "PASS" if safe else "UNSAFE",
        "boundary_count": len(boundaries),
        "safe_against_exact_reference": safe,
        "boundaries": boundaries,
    }


def _aggregate(rows: list[dict]) -> dict:
    truth = Counter(); labels = Counter(); cost = Counter(); status = Counter()
    boundaries = 0; decisive = 0; unresolved = 0; errors = 0
    exact_wall_s = 0.0; bound_wall_s = 0.0
    for row in rows:
        status[row["status"]] += 1
        for b in row.get("boundaries", []):
            boundaries += 1
            for k, v in b["truth"].items():
                if v: truth[k] += 1
            for label in b["labels"]: labels[label] += 1
            if b["labels"] == ["UNRESOLVED"]: unresolved += 1
            else: decisive += 1
            errors += len(b["soundness_errors"])
            cost["upper_nodes"] += int(b["bound_cost"]["upper_nodes"])
            cost["lower_nodes"] += int(b["bound_cost"]["lower_nodes"])
            exact_wall_s += float(b["exact_reference_wall_s"])
            bound_wall_s += float(b["bound_controller_wall_s"])
    return {
        "signature_count": len(rows),
        "status_count": dict(sorted(status.items())),
        "boundary_count": boundaries,
        "truth_count": dict(sorted(truth.items())),
        "label_count": dict(sorted(labels.items())),
        "decisive_boundary_count": decisive,
        "unresolved_boundary_count": unresolved,
        "decisive_fraction": decisive / boundaries if boundaries else None,
        "soundness_error_count": errors,
        "upper_nodes": int(cost["upper_nodes"]),
        "lower_nodes": int(cost["lower_nodes"]),
        "exact_reference_wall_s": exact_wall_s,
        "bound_controller_wall_s": bound_wall_s,
        "bound_vs_exact_wall_ratio": (bound_wall_s / exact_wall_s) if exact_wall_s else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inputs", type=Path, default=DEFAULT_INPUTS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--upper-depth", type=int, default=0)
    ap.add_argument("--choice-upper-depth", type=int, default=None)
    ap.add_argument("--choice-lower-depth", type=int, default=2)
    ap.add_argument("--max-expansions", type=int, default=200_000)
    ap.add_argument("--split", choices=["all", "train", "dev", "test"], default="all")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    data = json.loads(args.inputs.read_text(encoding="utf-8"))
    selected = [r for r in data["rows"] if args.split == "all" or r["split"] == args.split]
    if args.limit is not None:
        selected = selected[:args.limit]
    rows = []
    for i, row in enumerate(selected):
        result = _run_case(
            row,
            args.upper_depth,
            args.choice_upper_depth,
            args.choice_lower_depth,
            args.max_expansions,
        )
        rows.append(result)
        print(i + 1, row["split"], str(row["signature"])[:12], result["status"], result["boundary_count"], flush=True)

    by_split = defaultdict(list)
    for row in rows:
        by_split[row["split"]].append(row)
    aggregate = _aggregate(rows)
    split_aggregate = {split: _aggregate(part) for split, part in sorted(by_split.items())}
    all_safe = aggregate["soundness_error_count"] == 0 and aggregate["status_count"].get("UNSAFE", 0) == 0
    artifact = {
        "schema_version": "0.2",
        "status": "HARD_SIGNATURE_FUTURE_CHOICE_CONTROLLER_EVAL",
        "inputs_ref": str(args.inputs.relative_to(ROOT)),
        "inputs_sha256": sha256(args.inputs.read_bytes()).hexdigest(),
        "upper_depth": args.upper_depth,
        "choice_upper_depth": args.choice_upper_depth,
        "choice_lower_depth": args.choice_lower_depth,
        "split_filter": args.split,
        "all_labels_safe_against_exact_reference": all_safe,
        "aggregate": aggregate,
        "by_split": split_aggregate,
        "rows": rows,
        "claim_boundary": [
            "One current Layer-1 v0.2 representative bundle is evaluated per hard survivor solver signature.",
            "Exact action frontiers are regenerated at each exact-policy-prefix boundary and are used only as reference.",
            "The controller itself uses no exact fallback: it emits only sound L/U labels or UNRESOLVED.",
            "Train/dev/test are inherited from the structure-aware Layer-1 split with zero signature overlap.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "all_labels_safe_against_exact_reference": all_safe,
        "aggregate": aggregate,
        "by_split": split_aggregate,
        "out": str(args.out),
    }, ensure_ascii=False, indent=2))
    return 0 if all_safe else 1


if __name__ == "__main__":
    raise SystemExit(main())
