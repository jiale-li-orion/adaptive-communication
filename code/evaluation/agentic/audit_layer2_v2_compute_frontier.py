#!/usr/bin/env python3
"""Freeze the deterministic planner-expansion budget frontier on hard dev.

All four compared methods already produce the same exact action-feasibility
surface on 1,053/1,053 reached prefixes.  This audit asks a narrower systems
question without inventing a cherry-picked budget: if each signature is given
an upper bound on planner state expansions, how many exact frontiers can each
method complete?  Every observed per-case expansion cost is used as a frontier
breakpoint.

Expansion count is a deterministic algorithmic-computation proxy.  Wall time
is reported separately and explicitly remains a negative/open strong-control
gate; this artifact must not be cited as a wall-time win.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "results/agentic/layer2-v2-persistent-frontier-4arm-dev.json"

METHOD_KEYS = {
    "v2_conditional_frontier": "persistent_frontier_expanded",
    "ordinary_persistent_exact": "ordinary_incremental_frontier_expanded",
    "dependency_cache_exact": "dependency_cache_frontier_expanded",
    "fresh_exact_per_action": "fresh_frontier_expanded",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    if source.get("status") != "PASS":
        raise SystemExit("four-arm dev source is not PASS")
    rows = []
    costs: dict[str, list[int]] = {name: [] for name in METHOD_KEYS}
    for case in source["cases"]:
        result = case["result"]
        row = {"signature": case["signature"], "recipe_id": case["recipe_id"], "expansions": {}}
        for method, key in METHOD_KEYS.items():
            value = int(result[key])
            costs[method].append(value)
            row["expansions"][method] = value
        rows.append(row)

    budgets = sorted({value for values in costs.values() for value in values})
    frontier = []
    for budget in budgets:
        completion = {
            method: sum(value <= budget for value in values)
            for method, values in costs.items()
        }
        frontier.append({"expansion_budget": budget, "exact_frontier_completion_count": completion})

    v2 = costs["v2_conditional_frontier"]
    ordinary = costs["ordinary_persistent_exact"]
    dependency = costs["dependency_cache_exact"]
    pairwise = {
        "v2_strictly_lower_than_ordinary_count": sum(a < b for a, b in zip(v2, ordinary)),
        "v2_strictly_lower_than_dependency_cache_count": sum(a < b for a, b in zip(v2, dependency)),
        "v2_not_higher_than_ordinary_count": sum(a <= b for a, b in zip(v2, ordinary)),
        "v2_not_higher_than_dependency_cache_count": sum(a <= b for a, b in zip(v2, dependency)),
    }
    frontier_dominance = {
        "v2_never_worse_than_ordinary_over_all_observed_budgets": all(
            row["exact_frontier_completion_count"]["v2_conditional_frontier"]
            >= row["exact_frontier_completion_count"]["ordinary_persistent_exact"]
            for row in frontier
        ),
        "v2_never_worse_than_dependency_cache_over_all_observed_budgets": all(
            row["exact_frontier_completion_count"]["v2_conditional_frontier"]
            >= row["exact_frontier_completion_count"]["dependency_cache_exact"]
            for row in frontier
        ),
        "v2_strictly_better_than_ordinary_at_some_budget": any(
            row["exact_frontier_completion_count"]["v2_conditional_frontier"]
            > row["exact_frontier_completion_count"]["ordinary_persistent_exact"]
            for row in frontier
        ),
        "v2_strictly_better_than_dependency_cache_at_some_budget": any(
            row["exact_frontier_completion_count"]["v2_conditional_frontier"]
            > row["exact_frontier_completion_count"]["dependency_cache_exact"]
            for row in frontier
        ),
    }
    passed = bool(rows) and all(frontier_dominance.values())
    artifact = {
        "schema_version": "0.1",
        "status": "PASS" if passed else "FAIL",
        "experiment": "layer2-v2-planner-expansion-budget-frontier-dev",
        "scope": "same exact action-frontier quality; all observed expansion budgets; wall-time claim excluded",
        "summary": {
            "signature_count": len(rows),
            "budget_breakpoint_count": len(frontier),
            **pairwise,
            **frontier_dominance,
            "aggregate_expansions": {
                method: sum(values) for method, values in costs.items()
            },
            "wall_time_strong_control_gate": "OPEN_NEGATIVE",
        },
        "rules": [
            "No expansion threshold is selected manually; every observed per-case expansion cost is a breakpoint.",
            "All compared methods are exact-frontier correct on the source artifact, so completion count changes only with planner expansion budget.",
            "Expansion count is an algorithmic computation proxy and does not replace wall-time accounting.",
            "The ordinary persistent-exact wall-time advantage remains a separate negative/open gate.",
        ],
        "frontier": frontier,
        "cases": rows,
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": artifact["status"], "summary": artifact["summary"]}, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
