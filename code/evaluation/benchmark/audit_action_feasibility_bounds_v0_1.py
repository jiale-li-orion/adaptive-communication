#!/usr/bin/env python3
"""Compare L/U + exact fallback against the exact certified-action frontier."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from action_feasibility_bounds_v0_1 import LazyActionFeasibility
from audit_conditional_acquisition_timing_v0_1 import _initial, _minimal_policy
from causal_evidence_process_v0_1 import attach_causal_evidence
from exact_reference_oracle_v0_1 import _attempt_lattice
from v8_policy_baselines_v0_1 import _legal_actions, _normalize_one, _step


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUTS = ROOT / "results/benchmark/layer1-retry-review-inputs.json"
REFERENCE = ROOT / "results/benchmark/layer2-conditional-action-frontier-v0.1.json"
DEFAULT_OUT = ROOT / "results/benchmark/layer2-action-feasibility-bounds-v0.1.json"


def _key(action) -> str:
    return f"{action[0]}:{action[1] if action[1] is not None else '-'}"


VARIANTS = {
    "exact_memo": ("exact_memo", False, False, False, 0, None, None),
    "monotone_memo": ("monotone_memo", False, False, False, 0, None, None),
    "witness_domain": ("witness_domain", False, False, False, 0, None, None),
    "witness_domain_plus_upper_d0": ("witness_domain", True, False, False, 0, None, None),
    "witness_domain_plus_upper_d1": ("witness_domain", True, False, False, 1, None, None),
    "witness_domain_plus_upper_d2": ("witness_domain", True, False, False, 2, None, None),
    "witness_domain_plus_upper_d4": ("witness_domain", True, False, False, 4, None, None),
    "witness_domain_plus_upper_d6": ("witness_domain", True, False, False, 6, None, None),
    "witness_domain_plus_lower_upper": ("witness_domain", True, True, False, 0, None, None),
    "witness_domain_plus_common_lower_upper": ("witness_domain", True, True, True, 0, None, None),
    "witness_domain_plus_causal_lower_d1_upper_d0": ("witness_domain", True, False, False, 0, 1, None),
    "witness_domain_plus_causal_lower_d2_upper_d0": ("witness_domain", True, False, False, 0, 2, None),
    "witness_domain_plus_causal_lower_d4_upper_d0": ("witness_domain", True, False, False, 0, 4, None),
    "witness_domain_plus_causal_lower_d6_upper_d0": ("witness_domain", True, False, False, 0, 6, None),
    "witness_domain_plus_choice_lower_d1_upper_d0": ("witness_domain", True, False, False, 0, None, 1),
    "witness_domain_plus_choice_lower_d2_upper_d0": ("witness_domain", True, False, False, 0, None, 2),
    "witness_domain_plus_choice_lower_d3_upper_d0": ("witness_domain", True, False, False, 0, None, 3),
    "witness_domain_plus_choice_lower_d4_upper_d0": ("witness_domain", True, False, False, 0, None, 4),
    "witness_domain_plus_choice_lower_d6_upper_d0": ("witness_domain", True, False, False, 0, None, 6),
}


def _run_variant(frozen, ref_by_sig, *, mode: str, use_upper: bool, use_lower: bool,
                 use_common_lower: bool, upper_depth: int, causal_lower_depth: int | None,
                 choice_lower_depth: int | None,
                 max_expansions: int, keep_rows: bool):
    sources = Counter()
    totals = Counter()
    rows = []
    all_sets_match = True

    for source_row in frozen["rows"]:
        bundle = source_row["bundle"]
        signature = str(source_row["signature"])
        chosen = _minimal_policy(bundle, max_expansions)
        if chosen is None:
            continue
        q, b, solved = chosen
        process = attach_causal_evidence(bundle)
        lazy = LazyActionFeasibility(
            bundle, mode=mode, use_upper=use_upper, use_lower=use_lower,
            use_common_lower=use_common_lower, upper_depth=upper_depth,
            causal_lower_depth=causal_lower_depth, choice_lower_depth=choice_lower_depth,
        )
        states = _initial(bundle, b)
        at_s = min(_attempt_lattice(bundle))
        node = solved["policy"]
        ref_rows = ref_by_sig[signature]
        case_rows = []
        idx = 0
        while node and not node.get("terminal") and idx < len(ref_rows):
            branches = _normalize_one(bundle, process, at_s, states)
            if len(branches) != 1 or next(iter(branches)) != "same" or node.get("event") == "OBSERVATION":
                break
            states = next(iter(branches.values()))
            expected = set(ref_rows[idx]["certified_action_keys"])
            observed = set()
            action_rows = []
            for action in _legal_actions(bundle, process, states, at_s):
                result = lazy.classify(
                    at_s=at_s,
                    states=states,
                    query_budget=q,
                    action=action,
                    max_expansions=max_expansions,
                )
                sources[result["source"]] += 1
                if result["solvable"] is True:
                    observed.add(_key(action))
                action_rows.append({"action_key": _key(action), **result})
            match = observed == expected
            all_sets_match = all_sets_match and match
            case_rows.append({
                "time_s": at_s,
                "expected_certified": sorted(expected),
                "observed_certified": sorted(observed),
                "match": match,
                "actions": action_rows,
            })
            if node["action"] == "ISSUE_QUERY":
                break
            stepped = _step(bundle, process, states, at_s, (node["action"], node["arg"]))
            if stepped is None:
                break
            states, at_s = stepped
            node = node["subpolicy"]
            idx += 1

        for k, v in lazy.counts.items():
            totals[k] += v
        if keep_rows:
            rows.append({
                "signature": signature,
                "recipe_id": bundle["recipe_id"],
                "boundary_count": len(case_rows),
                "all_sets_match": all(r["match"] for r in case_rows),
                "lazy_counts": lazy.counts,
                "boundaries": case_rows,
            })

    classified = int(totals["classified_actions"])
    fallback = int(totals["exact_fallback_calls"])
    return {
        "mode": mode,
        "use_upper": use_upper,
        "use_lower": use_lower,
        "use_common_lower": use_common_lower,
        "upper_depth": upper_depth,
        "causal_lower_depth": causal_lower_depth,
        "choice_lower_depth": choice_lower_depth,
        "all_certified_action_sets_match_reference": all_sets_match,
        "classified_action_count": classified,
        "classification_source_count": dict(sorted(sources.items())),
        "exact_fallback_calls": fallback,
        "exact_calls_avoided_after_zero_expansion_probe": classified - fallback,
        "exact_fallback_fraction": (fallback / classified) if classified else None,
        "exact_fallback_expanded": int(totals["exact_fallback_expanded"]),
        "upper_nodes": int(totals["upper_nodes"]),
        "lower_nodes": int(totals["lower_nodes"]),
        "choice_lower_nodes": int(totals["choice_lower_nodes"]),
        "search_limit_count": int(totals["search_limits"]),
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inputs", type=Path, default=DEFAULT_INPUTS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-expansions", type=int, default=200_000)
    args = ap.parse_args()

    frozen = json.loads(args.inputs.read_text(encoding="utf-8"))
    reference = json.loads(REFERENCE.read_text(encoding="utf-8"))
    ref_by_sig = {str(r["signature"]): r["result"]["boundaries"] for r in reference["rows"]}
    variants = {}
    for name, (mode, use_upper, use_lower, use_common_lower, upper_depth, causal_lower_depth, choice_lower_depth) in VARIANTS.items():
        variants[name] = _run_variant(
            frozen, ref_by_sig,
            mode=mode, use_upper=use_upper, use_lower=use_lower,
            use_common_lower=use_common_lower, upper_depth=upper_depth,
            causal_lower_depth=causal_lower_depth,
            choice_lower_depth=choice_lower_depth,
            max_expansions=args.max_expansions,
            keep_rows=(name == "witness_domain_plus_choice_lower_d4_upper_d0"),
        )

    exact = variants["exact_memo"]
    mono = variants["monotone_memo"]
    witness = variants["witness_domain"]
    bounded0 = variants["witness_domain_plus_upper_d0"]
    bounded1 = variants["witness_domain_plus_upper_d1"]
    bounded2 = variants["witness_domain_plus_upper_d2"]
    bounded4 = variants["witness_domain_plus_upper_d4"]
    bounded6 = variants["witness_domain_plus_upper_d6"]
    full = variants["witness_domain_plus_lower_upper"]
    common = variants["witness_domain_plus_common_lower_upper"]
    lower1 = variants["witness_domain_plus_causal_lower_d1_upper_d0"]
    lower2 = variants["witness_domain_plus_causal_lower_d2_upper_d0"]
    lower4 = variants["witness_domain_plus_causal_lower_d4_upper_d0"]
    lower6 = variants["witness_domain_plus_causal_lower_d6_upper_d0"]
    choice1 = variants["witness_domain_plus_choice_lower_d1_upper_d0"]
    choice2 = variants["witness_domain_plus_choice_lower_d2_upper_d0"]
    choice3 = variants["witness_domain_plus_choice_lower_d3_upper_d0"]
    choice4 = variants["witness_domain_plus_choice_lower_d4_upper_d0"]
    choice6 = variants["witness_domain_plus_choice_lower_d6_upper_d0"]
    incremental = {
        "monotone_vs_exact_fallback_call_delta": mono["exact_fallback_calls"] - exact["exact_fallback_calls"],
        "witness_vs_monotone_fallback_call_delta": witness["exact_fallback_calls"] - mono["exact_fallback_calls"],
        "upper_d0_vs_witness_fallback_call_delta": bounded0["exact_fallback_calls"] - witness["exact_fallback_calls"],
        "upper_d1_vs_d0_fallback_call_delta": bounded1["exact_fallback_calls"] - bounded0["exact_fallback_calls"],
        "upper_d2_vs_d1_fallback_call_delta": bounded2["exact_fallback_calls"] - bounded1["exact_fallback_calls"],
        "upper_d4_vs_d2_fallback_call_delta": bounded4["exact_fallback_calls"] - bounded2["exact_fallback_calls"],
        "upper_d6_vs_d4_fallback_call_delta": bounded6["exact_fallback_calls"] - bounded4["exact_fallback_calls"],
        "monotone_vs_exact_expansion_delta": mono["exact_fallback_expanded"] - exact["exact_fallback_expanded"],
        "witness_vs_monotone_expansion_delta": witness["exact_fallback_expanded"] - mono["exact_fallback_expanded"],
        "upper_d0_vs_witness_expansion_delta": bounded0["exact_fallback_expanded"] - witness["exact_fallback_expanded"],
        "upper_d1_vs_d0_expansion_delta": bounded1["exact_fallback_expanded"] - bounded0["exact_fallback_expanded"],
        "upper_d2_vs_d1_expansion_delta": bounded2["exact_fallback_expanded"] - bounded1["exact_fallback_expanded"],
        "upper_d4_vs_d2_expansion_delta": bounded4["exact_fallback_expanded"] - bounded2["exact_fallback_expanded"],
        "upper_d6_vs_d4_expansion_delta": bounded6["exact_fallback_expanded"] - bounded4["exact_fallback_expanded"],
        "lower_vs_upper_fallback_call_delta": full["exact_fallback_calls"] - bounded0["exact_fallback_calls"],
        "lower_vs_upper_expansion_delta": full["exact_fallback_expanded"] - bounded0["exact_fallback_expanded"],
        "common_lower_vs_satellite_lower_fallback_call_delta": common["exact_fallback_calls"] - full["exact_fallback_calls"],
        "common_lower_vs_satellite_lower_expansion_delta": common["exact_fallback_expanded"] - full["exact_fallback_expanded"],
        "causal_lower_d1_vs_upper_d0_fallback_call_delta": lower1["exact_fallback_calls"] - bounded0["exact_fallback_calls"],
        "causal_lower_d2_vs_d1_fallback_call_delta": lower2["exact_fallback_calls"] - lower1["exact_fallback_calls"],
        "causal_lower_d4_vs_d2_fallback_call_delta": lower4["exact_fallback_calls"] - lower2["exact_fallback_calls"],
        "causal_lower_d6_vs_d4_fallback_call_delta": lower6["exact_fallback_calls"] - lower4["exact_fallback_calls"],
        "causal_lower_d1_vs_upper_d0_expansion_delta": lower1["exact_fallback_expanded"] - bounded0["exact_fallback_expanded"],
        "causal_lower_d2_vs_d1_expansion_delta": lower2["exact_fallback_expanded"] - lower1["exact_fallback_expanded"],
        "causal_lower_d4_vs_d2_expansion_delta": lower4["exact_fallback_expanded"] - lower2["exact_fallback_expanded"],
        "causal_lower_d6_vs_d4_expansion_delta": lower6["exact_fallback_expanded"] - lower4["exact_fallback_expanded"],
        "choice_lower_d1_vs_upper_d0_fallback_call_delta": choice1["exact_fallback_calls"] - bounded0["exact_fallback_calls"],
        "choice_lower_d2_vs_d1_fallback_call_delta": choice2["exact_fallback_calls"] - choice1["exact_fallback_calls"],
        "choice_lower_d3_vs_d2_fallback_call_delta": choice3["exact_fallback_calls"] - choice2["exact_fallback_calls"],
        "choice_lower_d4_vs_d3_fallback_call_delta": choice4["exact_fallback_calls"] - choice3["exact_fallback_calls"],
        "choice_lower_d6_vs_d4_fallback_call_delta": choice6["exact_fallback_calls"] - choice4["exact_fallback_calls"],
        "choice_lower_d1_vs_upper_d0_expansion_delta": choice1["exact_fallback_expanded"] - bounded0["exact_fallback_expanded"],
        "choice_lower_d2_vs_d1_expansion_delta": choice2["exact_fallback_expanded"] - choice1["exact_fallback_expanded"],
        "choice_lower_d3_vs_d2_expansion_delta": choice3["exact_fallback_expanded"] - choice2["exact_fallback_expanded"],
        "choice_lower_d4_vs_d3_expansion_delta": choice4["exact_fallback_expanded"] - choice3["exact_fallback_expanded"],
        "choice_lower_d6_vs_d4_expansion_delta": choice6["exact_fallback_expanded"] - choice4["exact_fallback_expanded"],
    }
    all_match = all(v["all_certified_action_sets_match_reference"] for v in variants.values())
    search_limits = sum(v["search_limit_count"] for v in variants.values())
    artifact = {
        "schema_version": "0.1",
        "status": "L_U_EXACT_FALLBACK_BASELINE_DECOMPOSITION",
        "all_variants_match_exact_action_frontier": all_match,
        "variants": variants,
        "incremental_value": incremental,
        "claim_boundary": [
            "U=0 uses only per-world optimistic residual flow after the forced action.",
            "L=1 uses only previously cached replayable causal witnesses; unresolved actions fall back to exact continuation.",
            "Exact-state memo, ordinary resource monotonicity, witness-tightened domains, and structural U-pruning are reported separately.",
            "This measures repeated classification on the same twelve frozen cases and exact-policy-prefix boundaries, not benchmark-wide speedup.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "all_variants_match_exact_action_frontier": all_match,
        "variants": {
            name: {k: row[k] for k in [
                "classified_action_count", "classification_source_count", "exact_fallback_calls",
                "exact_fallback_fraction", "exact_fallback_expanded", "upper_nodes", "lower_nodes", "search_limit_count",
                "choice_lower_nodes",
            ]}
            for name, row in variants.items()
        },
        "incremental_value": incremental,
    }, ensure_ascii=False, indent=2))
    return 0 if all_match and search_limits == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
