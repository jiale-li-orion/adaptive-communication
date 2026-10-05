#!/usr/bin/env python3
"""Focused online-order audit: cache lookup before structural L/U reasoning."""
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
INPUTS = ROOT / "results/benchmark/layer1-retry-review-inputs.json"
REFERENCE = ROOT / "results/benchmark/layer2-conditional-action-frontier-v0.1.json"
DEFAULT_OUT = ROOT / "results/benchmark/layer2-cache-first-future-choice-bounds-v0.1.json"


VARIANTS = {
    "cache_only": dict(use_upper=False, upper_depth=0, choice_upper_depth=None, choice_lower_depth=None),
    "cache_event_u0": dict(use_upper=True, upper_depth=0, choice_upper_depth=None, choice_lower_depth=None),
    "cache_choice_u2_l2": dict(use_upper=True, upper_depth=0, choice_upper_depth=2, choice_lower_depth=2),
    "cache_choice_u3_l3": dict(use_upper=True, upper_depth=0, choice_upper_depth=3, choice_lower_depth=3),
    "cache_choice_u4_l4": dict(use_upper=True, upper_depth=0, choice_upper_depth=4, choice_lower_depth=4),
    "cache_choice_u4_l6": dict(use_upper=True, upper_depth=0, choice_upper_depth=4, choice_lower_depth=6),
}


def _key(action) -> str:
    return f"{action[0]}:{action[1] if action[1] is not None else '-'}"


def _run_variant(frozen, ref_by_sig, cfg, max_expansions: int):
    totals = Counter(); sources = Counter(); all_match = True
    for source_row in frozen["rows"]:
        bundle = source_row["bundle"]
        sig = str(source_row["signature"])
        chosen = _minimal_policy(bundle, max_expansions)
        if chosen is None:
            continue
        q, b, solved = chosen
        process = attach_causal_evidence(bundle)
        lazy = LazyActionFeasibility(
            bundle,
            mode="witness_domain",
            use_upper=cfg["use_upper"],
            upper_depth=cfg["upper_depth"],
            choice_upper_depth=cfg["choice_upper_depth"],
            choice_lower_depth=cfg["choice_lower_depth"],
            cache_first=True,
        )
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
            expected = set(refs[idx]["certified_action_keys"])
            observed = set()
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
            all_match = all_match and observed == expected
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

    classified = int(totals["classified_actions"])
    fallback = int(totals["exact_fallback_calls"])
    return {
        **cfg,
        "cache_first": True,
        "all_certified_action_sets_match_reference": all_match,
        "classified_action_count": classified,
        "classification_source_count": dict(sorted(sources.items())),
        "exact_fallback_calls": fallback,
        "exact_fallback_fraction": fallback / classified if classified else None,
        "exact_fallback_expanded": int(totals["exact_fallback_expanded"]),
        "upper_nodes": int(totals["upper_nodes"]),
        "choice_upper_nodes": int(totals["choice_upper_nodes"]),
        "choice_lower_nodes": int(totals["choice_lower_nodes"]),
        "search_limit_count": int(totals["search_limits"]),
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
    for name, cfg in VARIANTS.items():
        variants[name] = _run_variant(frozen, ref_by_sig, cfg, args.max_expansions)
        print(name, variants[name], flush=True)

    all_match = all(r["all_certified_action_sets_match_reference"] for r in variants.values())
    artifact = {
        "schema_version": "0.1",
        "status": "CACHE_FIRST_L_U_ORDERING_AUDIT",
        "all_variants_match_exact_action_frontier": all_match,
        "variants": variants,
        "claim_boundary": [
            "All variants use the same exact action frontier as correctness reference.",
            "Cache lookup is zero-expansion and precedes structural U/L reasoning; structural work is paid only on unresolved child boundaries.",
            "Choice-depth counts SEND/QUERY decisions while passive WAIT and observation progression do not consume choice horizon.",
            "This is a 12-case development diagnostic, not a benchmark-wide runtime claim.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"all_match": all_match, "variants": variants}, ensure_ascii=False, indent=2))
    return 0 if all_match and all(r["search_limit_count"] == 0 for r in variants.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
