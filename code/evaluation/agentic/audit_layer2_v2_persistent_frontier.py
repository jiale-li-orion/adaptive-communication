#!/usr/bin/env python3
"""Prefix-level audit for the Layer-2 v2 persistent conditional frontier.

Four arms are compared on exactly the same reachable causal prefixes:
1. proposed persistent conditional frontier (L/U + certificate domains),
2. ordinary persistent exact with same action order / memo / early stop,
3. ordinary dependency-cache exact with replay-gated dead-history projection,
4. fresh exact-per-action rebuild used only as the correctness reference.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from copy import deepcopy
import json
from pathlib import Path
from time import perf_counter
from typing import Any, Mapping

from causal_evidence_process_v0_1 import attach_causal_evidence
from compositional_recipe_generator_v0_1 import core_recipes
from dynamic_world_materializer_v0_1 import materialize_recipe
from exact_reference_oracle_v0_1 import LocalState, _attempt_lattice, _normalize
from layer1_v02_exact_continuation import ExactContinuationReference
from layer2_v2_dependency_cache_baseline import PersistentDependencyExact
from layer2_v2_future_choice import solve_minimal_resource_v2
from layer2_v2_incremental_exact_baseline import PersistentOrderedExact
from layer2_v2_persistent_frontier import PersistentFutureChoiceFrontier
from v8_policy_baselines_v0_1 import _legal_actions, _step


ROOT = Path(__file__).resolve().parents[3]
SPLIT = ROOT / "results/benchmark/layer1-structure-aware-split-v0.2-retry-legality.json"


def _representatives(split_name: str) -> list[dict[str, Any]]:
    frozen = json.loads(SPLIT.read_text(encoding="utf-8"))
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in frozen["rows"]:
        if row.get("candidate_role") != "HARD_PRE_ADMISSION_SURVIVOR":
            continue
        if row.get("split") != split_name:
            continue
        grouped[str(row["signature"])].append(row)
    return [min(rows, key=lambda row: str(row["recipe_id"])) for _, rows in sorted(grouped.items())]


def _initial(bundle: Mapping[str, Any], sat_budget: int) -> dict[str, LocalState]:
    return {
        str(world["world_id"]): LocalState(satellite_budget=sat_budget)
        for world in bundle["worlds"]
    }


def _action_key(action) -> str:
    return f"{action[0]}:{action[1] if action[1] is not None else '-'}"


def _fresh_action_frontier(bundle, *, at_s, states, query_budget):
    process = attach_causal_evidence(bundle)
    branches = _normalize(bundle, process, at_s, states)
    assert len(branches) == 1 and next(iter(branches)) == "same"
    support = next(iter(branches.values()))
    out: dict[str, bool] = {}
    total_expanded = 0
    started = perf_counter()
    for action in _legal_actions(bundle, process, support, at_s):
        dq = int(action[0] == "ISSUE_QUERY")
        key = _action_key(action)
        if dq > query_budget:
            out[key] = False
            continue
        stepped = _step(bundle, process, support, at_s, action)
        assert stepped is not None
        child, next_t = stepped
        result = ExactContinuationReference(bundle).solve(
            next_t,
            deepcopy(child),
            query_budget=query_budget - dq,
        )
        assert result["status"] == "EXACT"
        total_expanded += int(result["expanded"])
        out[key] = bool(result["solvable"])
    return {
        "actions": out,
        "expanded": total_expanded,
        "wall_s": perf_counter() - started,
    }


def _walk_policy(
    bundle,
    *,
    runtime,
    ordinary_incremental,
    dependency_cache,
    at_s,
    states,
    query_budget,
    policy,
    rows,
):
    process = runtime.process
    branches = _normalize(bundle, process, at_s, states)
    if len(branches) != 1 or next(iter(branches)) != "same":
        assert policy.get("event") == "OBSERVATION"
        children = {str(row["observation"]): row for row in policy["children"]}
        assert set(children) == set(branches)
        for observation, child in sorted(branches.items()):
            _walk_policy(
                bundle,
                runtime=deepcopy(runtime),
                ordinary_incremental=deepcopy(ordinary_incremental),
                dependency_cache=deepcopy(dependency_cache),
                at_s=at_s,
                states=child,
                query_budget=query_budget,
                policy=children[observation]["subpolicy"],
                rows=rows,
            )
        return

    support = next(iter(branches.values()))
    carried = runtime.lookup_certificate(
        at_s=at_s,
        states=support,
        query_budget=query_budget,
    )
    persistent = runtime.build_frontier(
        at_s=at_s,
        states=support,
        query_budget=query_budget,
    )
    ordinary = ordinary_incremental.build_frontier(
        at_s=at_s,
        states=support,
        query_budget=query_budget,
    )
    dependency = dependency_cache.build_frontier(
        at_s=at_s,
        states=support,
        query_budget=query_budget,
    )
    fresh = _fresh_action_frontier(
        bundle,
        at_s=at_s,
        states=support,
        query_budget=query_budget,
    )

    persistent_actions = {
        key: bool(row["solvable"])
        for key, row in persistent["actions"].items()
    }
    assert ordinary["actions"] == fresh["actions"]
    assert dependency["actions"] == fresh["actions"]

    rows.append(
        {
            "time_s": at_s,
            "world_count": len(support),
            "query_budget": query_budget,
            "satellite_budget": min(state.satellite_budget for state in support.values()),
            "carried_certificate_hit": carried is not None,
            "persistent_frontier": persistent_actions,
            "ordinary_incremental_frontier": ordinary["actions"],
            "dependency_cache_frontier": dependency["actions"],
            "fresh_frontier": fresh["actions"],
            "frontier_match": persistent_actions == fresh["actions"],
            "persistent_wall_s": persistent["wall_s"],
            "ordinary_incremental_wall_s": ordinary["wall_s"],
            "dependency_cache_wall_s": dependency["wall_s"],
            "fresh_wall_s": fresh["wall_s"],
            "persistent_expanded": int(persistent["solver_delta"]["expanded"]),
            "ordinary_incremental_expanded": int(ordinary["metrics"]["expanded"]),
            "dependency_cache_expanded": int(dependency["metrics"]["expanded"]),
            "fresh_expanded": int(fresh["expanded"]),
            "dependency_cache_separator_replay_success": int(
                dependency["metrics"]["separator_replay_success"]
            ),
            "persistent_certificate_action_count": sum(
                row["source"] == "certificate-domain"
                for row in persistent["actions"].values()
            ),
            "persistent_fallback_action_count": sum(
                row["source"] == "kernel-fallback"
                for row in persistent["actions"].values()
            ),
        }
    )

    if policy.get("terminal"):
        return
    action = (str(policy["action"]), policy.get("arg"))
    dq = int(action[0] == "ISSUE_QUERY")
    stepped = _step(bundle, process, support, at_s, action)
    assert stepped is not None
    child, next_t = stepped
    _walk_policy(
        bundle,
        runtime=runtime,
        ordinary_incremental=ordinary_incremental,
        dependency_cache=dependency_cache,
        at_s=next_t,
        states=child,
        query_budget=query_budget - dq,
        policy=policy["subpolicy"],
        rows=rows,
    )


def run_case(bundle, *, upper_mode: str = "all_recursive", use_lower: bool = True):
    solved = solve_minimal_resource_v2(
        bundle,
        upper_mode=upper_mode,
        use_lower=use_lower,
    )
    assert solved["solvable"] is True
    q, sat = map(int, solved["minimal_resource_point"])
    start = min(_attempt_lattice(bundle))
    states = _initial(bundle, sat)
    runtime = PersistentFutureChoiceFrontier(
        bundle,
        upper_mode=upper_mode,
        use_lower=use_lower,
    )
    ordinary_incremental = PersistentOrderedExact(bundle)
    dependency_cache = PersistentDependencyExact(bundle)
    rows = []
    _walk_policy(
        bundle,
        runtime=runtime,
        ordinary_incremental=ordinary_incremental,
        dependency_cache=dependency_cache,
        at_s=start,
        states=states,
        query_budget=q,
        policy=solved["policy"],
        rows=rows,
    )
    return {
        "minimal_resource_point": [q, sat],
        "prefix_count": len(rows),
        "frontier_match_count": sum(row["frontier_match"] for row in rows),
        "certificate_domain_hit_count": sum(row["carried_certificate_hit"] for row in rows),
        "persistent_frontier_expanded": sum(row["persistent_expanded"] for row in rows),
        "ordinary_incremental_frontier_expanded": sum(
            row["ordinary_incremental_expanded"] for row in rows
        ),
        "dependency_cache_frontier_expanded": sum(
            row["dependency_cache_expanded"] for row in rows
        ),
        "fresh_frontier_expanded": sum(row["fresh_expanded"] for row in rows),
        "persistent_frontier_wall_s": sum(row["persistent_wall_s"] for row in rows),
        "ordinary_incremental_frontier_wall_s": sum(
            row["ordinary_incremental_wall_s"] for row in rows
        ),
        "dependency_cache_frontier_wall_s": sum(
            row["dependency_cache_wall_s"] for row in rows
        ),
        "fresh_frontier_wall_s": sum(row["fresh_wall_s"] for row in rows),
        "dependency_cache_separator_replay_success": sum(
            row["dependency_cache_separator_replay_success"] for row in rows
        ),
        "persistent_certificate_action_count": sum(
            row["persistent_certificate_action_count"] for row in rows
        ),
        "persistent_fallback_action_count": sum(
            row["persistent_fallback_action_count"] for row in rows
        ),
        "runtime_inventory": runtime.inventory(),
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["train", "dev", "test"], default="dev")
    ap.add_argument("--limit", type=int, default=1)
    ap.add_argument("--out", type=Path)
    ap.add_argument(
        "--upper-mode",
        choices=["all_recursive", "query_recursive", "root_query", "none"],
        default="all_recursive",
    )
    ap.add_argument("--no-lower", action="store_true")
    args = ap.parse_args()

    reps = _representatives(args.split)[: args.limit]
    recipes = {row.recipe_id: row for row in core_recipes()}
    cases = []
    for index, rep in enumerate(reps, 1):
        bundle = materialize_recipe(recipes[str(rep["recipe_id"])])
        result = run_case(
            bundle,
            upper_mode=args.upper_mode,
            use_lower=not args.no_lower,
        )
        cases.append({"signature": rep["signature"], "recipe_id": rep["recipe_id"], "result": result})
        print(
            index,
            str(rep["signature"])[:12],
            result["frontier_match_count"],
            "/",
            result["prefix_count"],
            "frontiers",
            "cert-hits",
            result["certificate_domain_hit_count"],
            flush=True,
        )

    prefix_count = sum(row["result"]["prefix_count"] for row in cases)
    match_count = sum(row["result"]["frontier_match_count"] for row in cases)
    summary = {
        "signature_count": len(cases),
        "prefix_count": prefix_count,
        "frontier_match_count": match_count,
        "certificate_domain_hit_count": sum(
            row["result"]["certificate_domain_hit_count"] for row in cases
        ),
        "persistent_frontier_expanded": sum(
            row["result"]["persistent_frontier_expanded"] for row in cases
        ),
        "ordinary_incremental_frontier_expanded": sum(
            row["result"]["ordinary_incremental_frontier_expanded"] for row in cases
        ),
        "dependency_cache_frontier_expanded": sum(
            row["result"]["dependency_cache_frontier_expanded"] for row in cases
        ),
        "fresh_frontier_expanded": sum(
            row["result"]["fresh_frontier_expanded"] for row in cases
        ),
        "persistent_frontier_wall_s": sum(
            row["result"]["persistent_frontier_wall_s"] for row in cases
        ),
        "ordinary_incremental_frontier_wall_s": sum(
            row["result"]["ordinary_incremental_frontier_wall_s"] for row in cases
        ),
        "dependency_cache_frontier_wall_s": sum(
            row["result"]["dependency_cache_frontier_wall_s"] for row in cases
        ),
        "fresh_frontier_wall_s": sum(
            row["result"]["fresh_frontier_wall_s"] for row in cases
        ),
        "dependency_cache_separator_replay_success": sum(
            row["result"]["dependency_cache_separator_replay_success"] for row in cases
        ),
        "persistent_certificate_action_count": sum(
            row["result"]["persistent_certificate_action_count"] for row in cases
        ),
        "persistent_fallback_action_count": sum(
            row["result"]["persistent_fallback_action_count"] for row in cases
        ),
    }
    ratios = [
        ("expanded_ratio_persistent_over_fresh", "persistent_frontier_expanded", "fresh_frontier_expanded"),
        ("expanded_ratio_persistent_over_incremental_exact", "persistent_frontier_expanded", "ordinary_incremental_frontier_expanded"),
        ("expanded_ratio_persistent_over_dependency_cache", "persistent_frontier_expanded", "dependency_cache_frontier_expanded"),
        ("wall_ratio_persistent_over_fresh", "persistent_frontier_wall_s", "fresh_frontier_wall_s"),
        ("wall_ratio_persistent_over_incremental_exact", "persistent_frontier_wall_s", "ordinary_incremental_frontier_wall_s"),
        ("wall_ratio_persistent_over_dependency_cache", "persistent_frontier_wall_s", "dependency_cache_frontier_wall_s"),
    ]
    for out_key, num_key, den_key in ratios:
        summary[out_key] = summary[num_key] / summary[den_key] if summary[den_key] else None

    artifact = {
        "schema_version": "0.2",
        "status": "PASS" if cases and prefix_count == match_count else "FAIL",
        "experiment": "layer2-v2-persistent-frontier-four-arm-prefix-audit",
        "split": args.split,
        "upper_mode": args.upper_mode,
        "use_lower": not args.no_lower,
        "summary": summary,
        "cases": cases,
        "rules": [
            "All four arms receive identical Layer-1 v0.2 states, legal actions, query budgets and transition semantics.",
            "Dependency-cache cross-state failure reuse is forbidden; success reuse is replay-gated.",
            "Fresh exact-per-action is a correctness rebuild reference, not the main performance baseline.",
            "The method must match the exact action-feasibility frontier at every audited prefix.",
        ],
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": artifact["status"], "summary": summary}, indent=2))
    return 0 if artifact["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
