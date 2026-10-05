#!/usr/bin/env python3
"""Explain the actions still requiring exact fallback after the cheap L/U stack."""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

from action_feasibility_bounds_v0_1 import (
    LazyActionFeasibility,
    causal_lower_certificate,
    causal_upper,
    choice_depth_lower_certificate,
    choice_depth_upper,
)
from audit_conditional_acquisition_timing_v0_1 import _initial, _minimal_policy
from causal_evidence_process_v0_1 import attach_causal_evidence
from exact_reference_oracle_v0_1 import _attempt_lattice
from v8_policy_baselines_v0_1 import _legal_actions, _normalize_one, _step


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUTS = ROOT / "results/benchmark/layer1-retry-review-inputs.json"
DEFAULT_OUT = ROOT / "results/benchmark/layer2-unresolved-action-certificate-gaps-v0.1.json"


def _akey(action) -> str:
    return f"{action[0]}:{action[1] if action[1] is not None else '-'}"


def _first_lower_depth(bundle, process, at_s, child, qleft, max_depth: int) -> int | None:
    for depth in range(0, max_depth + 1):
        policy = causal_lower_certificate(
            bundle, process, at_s, deepcopy(child), qleft, depth,
        )
        if policy is not None:
            return depth
    return None


def _first_choice_upper_depth(bundle, process, at_s, child, qleft, max_depth: int) -> int | None:
    for depth in range(0, max_depth + 1):
        if not choice_depth_upper(
            bundle, process, at_s, deepcopy(child), qleft, depth,
        ):
            return depth
    return None


def _first_choice_lower_depth(bundle, process, at_s, child, qleft, max_depth: int) -> int | None:
    for depth in range(0, max_depth + 1):
        policy = choice_depth_lower_certificate(
            bundle, process, at_s, deepcopy(child), qleft, depth,
        )
        if policy is not None:
            return depth
    return None


def _first_upper_depth(bundle, process, at_s, child, qleft, max_depth: int) -> int | None:
    for depth in range(0, max_depth + 1):
        if not causal_upper(bundle, process, at_s, deepcopy(child), qleft, depth):
            return depth
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inputs", type=Path, default=DEFAULT_INPUTS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-expansions", type=int, default=200_000)
    ap.add_argument("--probe-depth", type=int, default=12)
    args = ap.parse_args()

    frozen = json.loads(args.inputs.read_text(encoding="utf-8"))
    rows = []
    counts = Counter()
    lower_depths = Counter()
    choice_lower_depths = Counter()
    upper_depths = Counter()
    choice_upper_depths = Counter()

    for source_row in frozen["rows"]:
        bundle = source_row["bundle"]
        chosen = _minimal_policy(bundle, args.max_expansions)
        if chosen is None:
            continue
        q, b, solved = chosen
        process = attach_causal_evidence(bundle)
        lazy = LazyActionFeasibility(
            bundle,
            mode="witness_domain",
            use_upper=True,
            upper_depth=0,
            causal_lower_depth=2,
        )
        states = _initial(bundle, b)
        at_s = min(_attempt_lattice(bundle))
        node = solved["policy"]

        while node and not node.get("terminal"):
            branches = _normalize_one(bundle, process, at_s, states)
            if len(branches) != 1 or next(iter(branches)) != "same" or node.get("event") == "OBSERVATION":
                break
            states = next(iter(branches.values()))
            for action in _legal_actions(bundle, process, states, at_s):
                result = lazy.classify(
                    at_s=at_s,
                    states=states,
                    query_budget=q,
                    action=action,
                    max_expansions=args.max_expansions,
                )
                if not result["source"].startswith("EXACT_FALLBACK_"):
                    continue
                stepped = _step(bundle, process, states, at_s, action)
                assert stepped is not None
                child, next_t = stepped
                qleft = q - int(action[0] == "ISSUE_QUERY")
                if result["source"] == "EXACT_FALLBACK_SUCCESS":
                    depth = _first_lower_depth(
                        bundle, process, next_t, child, qleft, args.probe_depth,
                    )
                    choice_depth = _first_choice_lower_depth(
                        bundle, process, next_t, child, qleft, min(args.probe_depth, 6),
                    )
                    bucket = f"LOWER_DEPTH_{depth}" if depth is not None else f"NO_LOWER_CERT_THROUGH_D{args.probe_depth}"
                    lower_depths[bucket] += 1
                    choice_bucket = (
                        f"CHOICE_LOWER_DEPTH_{choice_depth}"
                        if choice_depth is not None
                        else f"NO_CHOICE_LOWER_CERT_THROUGH_D{min(args.probe_depth, 6)}"
                    )
                    choice_lower_depths[choice_bucket] += 1
                    counts[("SUCCESS", action[0], bucket)] += 1
                    rows.append({
                        "signature": source_row["signature"],
                        "recipe_id": bundle["recipe_id"],
                        "time_s": at_s,
                        "action_key": _akey(action),
                        "exact_outcome": "SUCCESS",
                        "first_causal_lower_depth": depth,
                        "first_choice_lower_depth": choice_depth,
                    })
                else:
                    depth = _first_upper_depth(
                        bundle, process, next_t, child, qleft, args.probe_depth,
                    )
                    choice_depth = _first_choice_upper_depth(
                        bundle, process, next_t, child, qleft, min(args.probe_depth, 6),
                    )
                    bucket = f"UPPER_PRUNE_DEPTH_{depth}" if depth is not None else f"NO_UPPER_PRUNE_THROUGH_D{args.probe_depth}"
                    upper_depths[bucket] += 1
                    choice_bucket = (
                        f"CHOICE_UPPER_PRUNE_DEPTH_{choice_depth}"
                        if choice_depth is not None
                        else f"NO_CHOICE_UPPER_PRUNE_THROUGH_D{min(args.probe_depth, 6)}"
                    )
                    choice_upper_depths[choice_bucket] += 1
                    counts[("FAILURE", action[0], bucket)] += 1
                    rows.append({
                        "signature": source_row["signature"],
                        "recipe_id": bundle["recipe_id"],
                        "time_s": at_s,
                        "action_key": _akey(action),
                        "exact_outcome": "FAILURE",
                        "first_causal_upper_prune_depth": depth,
                        "first_choice_upper_prune_depth": choice_depth,
                    })

            if node["action"] == "ISSUE_QUERY":
                break
            stepped = _step(bundle, process, states, at_s, (node["action"], node["arg"]))
            if stepped is None:
                break
            states, at_s = stepped
            node = node["subpolicy"]

    artifact = {
        "schema_version": "0.1",
        "status": "UNRESOLVED_L_U_CERTIFICATE_GAP_DIAGNOSTIC",
        "baseline": "witness_domain + causal_lower_d2 + causal_upper_d0 + exact fallback",
        "probe_depth": args.probe_depth,
        "fallback_count": len(rows),
        "success_lower_depth_distribution": dict(sorted(lower_depths.items())),
        "success_choice_lower_depth_distribution": dict(sorted(choice_lower_depths.items())),
        "failure_upper_depth_distribution": dict(sorted(upper_depths.items())),
        "failure_choice_upper_depth_distribution": dict(sorted(choice_upper_depths.items())),
        "by_outcome_action_and_gap": {
            "|".join(map(str, key)): value for key, value in sorted(counts.items())
        },
        "rows": rows,
        "claim_boundary": [
            "This diagnoses the remaining exact fallbacks after the selected cheap d2-lower/d0-upper stack on twelve frozen cases.",
            "A missing lower certificate through d12 means the current satellite/common structural leaves cannot prove the successful continuation within that bounded causal depth; it does not imply no compact certificate exists.",
            "A missing upper prune through d12 means the current optimistic-flow causal upper cannot prove infeasibility within that bounded depth.",
            "Choice-depth ignores passive WAIT transitions and counts only deliberate send/query decisions; observation splits remain AND nodes but do not consume choice depth.",
            "The choice-depth upper uses the same accounting on the optimistic side: False remains a sound infeasibility certificate, while True is only unresolved/possible.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: artifact[k] for k in [
        "fallback_count", "success_lower_depth_distribution",
        "success_choice_lower_depth_distribution",
        "failure_upper_depth_distribution", "by_outcome_action_and_gap",
        "failure_choice_upper_depth_distribution",
    ]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
