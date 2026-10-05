#!/usr/bin/env python3
"""Trace certified future-choice sets along exact minimal-resource prefixes."""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from audit_conditional_acquisition_timing_v0_1 import _initial, _minimal_policy
from causal_evidence_process_v0_1 import attach_causal_evidence
from conditional_action_frontier_v0_1 import build_action_frontier
from exact_reference_oracle_v0_1 import _attempt_lattice
from v8_policy_baselines_v0_1 import _normalize_one, _step


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUTS = ROOT / "results/benchmark/layer1-retry-review-inputs.json"
TIMING = ROOT / "results/benchmark/layer2-conditional-acquisition-timing-v0.1.json"
DEFAULT_OUT = ROOT / "results/benchmark/layer2-conditional-action-frontier-v0.1.json"


def _action_key(kind: str, arg: str | None) -> str:
    return f"{kind}:{arg if arg is not None else '-'}"


def _has_reentry(flags: list[bool]) -> bool:
    seen_true = False
    seen_gap = False
    for flag in flags:
        if flag:
            if seen_true and seen_gap:
                return True
            seen_true = True
        elif seen_true:
            seen_gap = True
    return False


def _run_case(bundle, max_expansions: int) -> dict:
    chosen = _minimal_policy(bundle, max_expansions)
    if chosen is None:
        return {"classification": "UNSOLVABLE_IN_BOUNDED_RECTANGLE", "boundaries": []}
    q, b, solved = chosen
    start = min(_attempt_lattice(bundle))
    states = _initial(bundle, b)
    process = attach_causal_evidence(bundle)
    at_s = start
    node = solved["policy"]
    qleft = q
    rows = []
    exact_action_certified = True
    steps = 0

    while node and not node.get("terminal") and steps < 512:
        branches = _normalize_one(bundle, process, at_s, states)
        if len(branches) != 1 or next(iter(branches)) != "same":
            break
        states = next(iter(branches.values()))
        if node.get("event") == "OBSERVATION":
            break

        frontier = build_action_frontier(
            bundle,
            at_s=at_s,
            states=deepcopy(states),
            query_budget=qleft,
            max_expansions=max_expansions,
        )
        exact_key = _action_key(node["action"], node["arg"])
        exact_ok = exact_key in frontier["certified_action_keys"]
        exact_action_certified = exact_action_certified and exact_ok
        rows.append({
            "time_s": at_s,
            "query_budget_remaining": qleft,
            "exact_action_key": exact_key,
            "exact_action_certified": exact_ok,
            "legal_action_keys": frontier["legal_action_keys"],
            "certified_action_keys": frontier["certified_action_keys"],
            "context": frontier["context"],
        })

        if node["action"] == "ISSUE_QUERY":
            break
        stepped = _step(bundle, process, states, at_s, (node["action"], node["arg"]))
        if stepped is None:
            break
        states, at_s = stepped
        node = node["subpolicy"]
        steps += 1

    legal_query_rows = [r for r in rows if r["context"]["query_now_legal"]]
    certified_query_times = [r["time_s"] for r in legal_query_rows if r["context"]["query_now_certified"]]
    legal_but_bad = [r["time_s"] for r in legal_query_rows if r["context"]["query_legal_but_not_certified"]]
    flags = [r["context"]["query_now_certified"] for r in legal_query_rows]

    transitions = 0
    previous = None
    for row in rows:
        current = tuple(row["certified_action_keys"])
        if previous is not None and current != previous:
            transitions += 1
        previous = current

    if q == 0:
        cls = "QUERY_FREE_FROM_INITIAL_BOUNDARY"
    elif _has_reentry(flags):
        cls = "QUERY_CERTIFICATION_REENTRY"
    elif len(certified_query_times) == 1:
        cls = "SINGLE_CERTIFIED_QUERY_TIME"
    elif certified_query_times:
        cls = "CONTIGUOUS_CERTIFIED_QUERY_WINDOW"
    else:
        cls = "NO_CERTIFIED_QUERY_TIME_ON_PREFIX"

    return {
        "classification": cls,
        "minimal_resource_point": [q, b],
        "boundary_count": len(rows),
        "choice_set_transition_count": transitions,
        "exact_action_certified_at_every_boundary": exact_action_certified,
        "certified_query_times_s": certified_query_times,
        "legal_but_uncertified_query_times_s": legal_but_bad,
        "query_certification_reentry": _has_reentry(flags),
        "boundaries": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inputs", type=Path, default=DEFAULT_INPUTS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-expansions", type=int, default=200_000)
    args = ap.parse_args()

    frozen = json.loads(args.inputs.read_text(encoding="utf-8"))
    timing = json.loads(TIMING.read_text(encoding="utf-8"))
    timing_by_sig = {str(r["signature"]): r["result"] for r in timing["rows"]}
    rows = []
    classes = Counter()
    total_boundaries = 0
    total_legal_bad = 0
    all_exact_actions_certified = True
    timing_agreement = True

    for index, source_row in enumerate(frozen["rows"]):
        bundle = source_row["bundle"]
        result = _run_case(bundle, args.max_expansions)
        classes[result["classification"]] += 1
        total_boundaries += result.get("boundary_count", 0)
        total_legal_bad += len(result.get("legal_but_uncertified_query_times_s", []))
        all_exact_actions_certified = all_exact_actions_certified and result.get(
            "exact_action_certified_at_every_boundary", True
        )
        old = timing_by_sig[str(source_row["signature"])]
        old_times = old.get("sufficient_query_times_s", [])
        new_times = result.get("certified_query_times_s", [])
        agree = old_times == new_times
        timing_agreement = timing_agreement and agree
        rows.append({
            "index": index,
            "signature": source_row["signature"],
            "recipe_id": bundle["recipe_id"],
            "process": bundle["public_environment"]["terrestrial_process_class"],
            "timing_frontier_agreement": agree,
            "previous_sufficient_query_times_s": old_times,
            "result": result,
        })
        print(
            index + 1,
            str(source_row["signature"])[:12],
            result["classification"],
            "cert-query=", new_times,
            "legal-bad=", result.get("legal_but_uncertified_query_times_s", []),
            flush=True,
        )

    artifact = {
        "schema_version": "0.1",
        "status": "CERTIFIED_FUTURE_CHOICE_DIAGNOSTIC",
        "inputs_ref": str(args.inputs.relative_to(ROOT)),
        "inputs_sha256": sha256(args.inputs.read_bytes()).hexdigest(),
        "classification_count": dict(sorted(classes.items())),
        "decision_boundary_count": total_boundaries,
        "legal_but_uncertified_query_boundary_count": total_legal_bad,
        "all_exact_policy_actions_certified": all_exact_actions_certified,
        "agrees_with_acquisition_timing_frontier": timing_agreement,
        "rows": rows,
        "claim_boundary": [
            "This traces exact minimal-resource prefixes on twelve frozen corrected-source bundles only.",
            "Certified actions are defined by exact causal continuation plus witness replay, not by a learned score.",
            "Legal-but-uncertified query boundaries demonstrate that information acquisition can be executable yet future-feasibility-destroying.",
            "This artifact is a Layer-2 reference object; it does not yet provide a cheap online L/U approximation.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "classification_count": artifact["classification_count"],
        "decision_boundary_count": total_boundaries,
        "legal_but_uncertified_query_boundary_count": total_legal_bad,
        "all_exact_policy_actions_certified": all_exact_actions_certified,
        "agrees_with_acquisition_timing_frontier": timing_agreement,
        "out": str(args.out),
    }, ensure_ascii=False, indent=2))
    return 0 if all_exact_actions_certified and timing_agreement else 1


if __name__ == "__main__":
    raise SystemExit(main())
