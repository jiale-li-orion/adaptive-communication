#!/usr/bin/env python3
"""Audit bound-only acquisition-control labels against the exact action frontier."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from audit_conditional_acquisition_timing_v0_1 import _initial, _minimal_policy
from causal_evidence_process_v0_1 import attach_causal_evidence
from exact_reference_oracle_v0_1 import _attempt_lattice
from future_choice_bound_controller_v0_1 import bound_future_choice_context
from v8_policy_baselines_v0_1 import _normalize_one, _step


ROOT = Path(__file__).resolve().parents[3]
INPUTS = ROOT / "results/benchmark/layer1-retry-review-inputs.json"
REFERENCE = ROOT / "results/benchmark/layer2-conditional-action-frontier-v0.1.json"
DEFAULT_OUT = ROOT / "results/benchmark/layer2-future-choice-bound-controller-v0.1.json"


VARIANTS = {
    "u0_l1": (0, 1),
    "u0_l2": (0, 2),
    "u0_l3": (0, 3),
    "u0_l4": (0, 4),
    "u0_l6": (0, 6),
    "u4_l2": (4, 2),
    "u4_l3": (4, 3),
}


def _exact_truth(boundary: dict) -> dict[str, bool]:
    certified = set(boundary["certified_action_keys"])
    qkey = "ISSUE_QUERY:gateway_state_summary"
    non_query = [x for x in certified if x != qkey]
    return {
        "stop": boundary["context"]["query_free_completion"] is True,
        "query_harmful": boundary["context"]["query_now_legal"] and qkey not in certified,
        "can_defer": bool(non_query),
        "query_required": qkey in certified and not non_query,
    }


def _check_labels(labels: list[str], truth: dict[str, bool]) -> list[str]:
    errors = []
    mapping = {
        "STOP_ACQUISITION_CERTIFIED": "stop",
        "QUERY_HARMFUL_NOW": "query_harmful",
        "CAN_DEFER_QUERY": "can_defer",
        "QUERY_REQUIRED_NOW": "query_required",
    }
    for label, key in mapping.items():
        if label in labels and not truth[key]:
            errors.append(f"{label}_UNSOUND")
    return errors


def _run_variant(frozen, ref_by_sig, upper_depth: int, lower_depth: int, max_expansions: int):
    label_counts = Counter()
    exact_truth_counts = Counter()
    decisive = 0
    unresolved = 0
    safe = True
    errors = []
    boundaries = 0
    upper_nodes = 0
    lower_nodes = 0

    for source_row in frozen["rows"]:
        bundle = source_row["bundle"]
        sig = str(source_row["signature"])
        chosen = _minimal_policy(bundle, max_expansions)
        if chosen is None:
            continue
        q, b, solved = chosen
        process = attach_causal_evidence(bundle)
        states = _initial(bundle, b)
        at_s = min(_attempt_lattice(bundle))
        node = solved["policy"]
        refs = ref_by_sig[sig]
        idx = 0

        while node and not node.get("terminal") and idx < len(refs):
            branches = _normalize_one(bundle, process, at_s, states)
            if len(branches) != 1 or next(iter(branches)) != "same" or node.get("event") == "OBSERVATION":
                break
            states = next(iter(branches.values()))
            ref = refs[idx]
            truth = _exact_truth(ref)
            result = bound_future_choice_context(
                bundle,
                at_s=at_s,
                states=states,
                query_budget=q,
                upper_depth=upper_depth,
                choice_lower_depth=lower_depth,
            )
            boundaries += 1
            upper_nodes += int(result["bound_cost"]["upper_nodes"])
            lower_nodes += int(result["bound_cost"]["lower_nodes"])
            for key, value in truth.items():
                if value:
                    exact_truth_counts[key] += 1
            for label in result["labels"]:
                label_counts[label] += 1
            bad = _check_labels(result["labels"], truth)
            if bad:
                safe = False
                errors.append({
                    "signature": sig,
                    "recipe_id": bundle["recipe_id"],
                    "time_s": at_s,
                    "labels": result["labels"],
                    "truth": truth,
                    "errors": bad,
                })
            if result["labels"] == ["UNRESOLVED"]:
                unresolved += 1
            else:
                decisive += 1

            if node["action"] == "ISSUE_QUERY":
                break
            stepped = _step(bundle, process, states, at_s, (node["action"], node["arg"]))
            if stepped is None:
                break
            states, at_s = stepped
            node = node["subpolicy"]
            idx += 1

    return {
        "upper_depth": upper_depth,
        "choice_lower_depth": lower_depth,
        "boundary_count": boundaries,
        "safe_against_exact_reference": safe,
        "error_count": len(errors),
        "errors": errors,
        "label_count": dict(sorted(label_counts.items())),
        "exact_truth_count": dict(sorted(exact_truth_counts.items())),
        "decisive_boundary_count": decisive,
        "unresolved_boundary_count": unresolved,
        "decisive_fraction": decisive / boundaries if boundaries else None,
        "upper_nodes": upper_nodes,
        "lower_nodes": lower_nodes,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-expansions", type=int, default=200_000)
    args = ap.parse_args()

    frozen = json.loads(INPUTS.read_text(encoding="utf-8"))
    reference = json.loads(REFERENCE.read_text(encoding="utf-8"))
    ref_by_sig = {str(r["signature"]): r["result"]["boundaries"] for r in reference["rows"]}
    variants = {}
    for name, (upper_depth, lower_depth) in VARIANTS.items():
        variants[name] = _run_variant(
            frozen, ref_by_sig, upper_depth, lower_depth, args.max_expansions,
        )
        print(name, variants[name], flush=True)

    all_safe = all(v["safe_against_exact_reference"] for v in variants.values())
    artifact = {
        "schema_version": "0.1",
        "status": "BOUND_ONLY_FUTURE_CHOICE_CONTROLLER_AUDIT",
        "all_variants_safe_against_exact_reference": all_safe,
        "variants": variants,
        "claim_boundary": [
            "The controller never calls exact continuation; it emits only sound L/U-derived labels or UNRESOLVED.",
            "Coverage is measured on 298 exact-policy-prefix decision boundaries from twelve frozen corrected-source cases.",
            "STOP/DEFER/REQUIRED/HARMFUL are decision semantics over certified future choices, not information relevance scores.",
            "This is still a bounded method diagnostic, not a benchmark-wide online result.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "all_variants_safe_against_exact_reference": all_safe,
        "variants": {
            k: {x: v[x] for x in [
                "decisive_boundary_count", "unresolved_boundary_count", "decisive_fraction",
                "label_count", "upper_nodes", "lower_nodes",
            ]}
            for k, v in variants.items()
        },
    }, ensure_ascii=False, indent=2))
    return 0 if all_safe else 1


if __name__ == "__main__":
    raise SystemExit(main())
