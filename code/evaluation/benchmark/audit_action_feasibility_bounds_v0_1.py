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
    "exact_memo": ("exact_memo", False, False),
    "monotone_memo": ("monotone_memo", False, False),
    "witness_domain": ("witness_domain", False, False),
    "witness_domain_plus_upper": ("witness_domain", True, False),
    "witness_domain_plus_lower_upper": ("witness_domain", True, True),
}


def _run_variant(frozen, ref_by_sig, *, mode: str, use_upper: bool, use_lower: bool,
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
        lazy = LazyActionFeasibility(bundle, mode=mode, use_upper=use_upper, use_lower=use_lower)
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
        "all_certified_action_sets_match_reference": all_sets_match,
        "classified_action_count": classified,
        "classification_source_count": dict(sorted(sources.items())),
        "exact_fallback_calls": fallback,
        "exact_calls_avoided_after_zero_expansion_probe": classified - fallback,
        "exact_fallback_fraction": (fallback / classified) if classified else None,
        "exact_fallback_expanded": int(totals["exact_fallback_expanded"]),
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
    for name, (mode, use_upper, use_lower) in VARIANTS.items():
        variants[name] = _run_variant(
            frozen, ref_by_sig,
            mode=mode, use_upper=use_upper, use_lower=use_lower,
            max_expansions=args.max_expansions,
            keep_rows=(name == "witness_domain_plus_lower_upper"),
        )

    exact = variants["exact_memo"]
    mono = variants["monotone_memo"]
    witness = variants["witness_domain"]
    bounded = variants["witness_domain_plus_upper"]
    full = variants["witness_domain_plus_lower_upper"]
    incremental = {
        "monotone_vs_exact_fallback_call_delta": mono["exact_fallback_calls"] - exact["exact_fallback_calls"],
        "witness_vs_monotone_fallback_call_delta": witness["exact_fallback_calls"] - mono["exact_fallback_calls"],
        "upper_vs_witness_fallback_call_delta": bounded["exact_fallback_calls"] - witness["exact_fallback_calls"],
        "monotone_vs_exact_expansion_delta": mono["exact_fallback_expanded"] - exact["exact_fallback_expanded"],
        "witness_vs_monotone_expansion_delta": witness["exact_fallback_expanded"] - mono["exact_fallback_expanded"],
        "upper_vs_witness_expansion_delta": bounded["exact_fallback_expanded"] - witness["exact_fallback_expanded"],
        "lower_vs_upper_fallback_call_delta": full["exact_fallback_calls"] - bounded["exact_fallback_calls"],
        "lower_vs_upper_expansion_delta": full["exact_fallback_expanded"] - bounded["exact_fallback_expanded"],
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
                "exact_fallback_fraction", "exact_fallback_expanded", "search_limit_count",
            ]}
            for name, row in variants.items()
        },
        "incremental_value": incremental,
    }, ensure_ascii=False, indent=2))
    return 0 if all_match and search_limits == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
