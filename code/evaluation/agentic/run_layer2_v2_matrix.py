#!/usr/bin/env python3
"""Fair Layer-2 v2 vs generic-exact/ordinary-baseline matrix on Layer-1 v0.2.

The runner never changes Layer-1.  It evaluates one representative per frozen
hard solver signature and keeps task quality, acquisition/satellite resources,
and planner compute separate.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from time import perf_counter
from typing import Any

from compositional_recipe_generator_v0_1 import core_recipes
from dynamic_world_materializer_v0_1 import materialize_recipe
from exact_reference_oracle_v0_1 import LocalState, _attempt_lattice, _expired, _normalize, _success
from layer1_v02_exact_continuation import ExactContinuationReference, replay_continuation_policy
from layer2_v2_future_choice import FutureChoiceExactFallback, solve_minimal_resource_v2
from v8_policy_baselines_v0_1 import (
    _legal_actions,
    _step,
    solve_always_query_then_plan,
    solve_depth_k_flow_terminal,
    solve_latest_feasible_send,
    solve_least_slack,
    solve_myopic_flow_voi,
    solve_shallow_rule,
)


ROOT = Path(__file__).resolve().parents[3]
SPLIT = ROOT / "results/benchmark/layer1-structure-aware-split-v0.2-retry-legality.json"


def hard_representatives(split_name: str) -> list[dict[str, Any]]:
    frozen = json.loads(SPLIT.read_text(encoding="utf-8"))
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in frozen["rows"]:
        if row.get("candidate_role") != "HARD_PRE_ADMISSION_SURVIVOR":
            continue
        if split_name != "all" and row.get("split") != split_name:
            continue
        grouped[str(row["signature"])].append(row)
    return [min(rows, key=lambda row: str(row["recipe_id"])) for _, rows in sorted(grouped.items())]


def initial(bundle: dict[str, Any], sat_budget: int) -> dict[str, LocalState]:
    return {
        str(world["world_id"]): LocalState(satellite_budget=sat_budget)
        for world in bundle["worlds"]
    }


def _ordered_actions(bundle: dict[str, Any], at_s: int, actions: list[tuple[str, str | None]]):
    deadlines = {
        str(row["obligation_id"]): int(row["deadline_s"])
        for row in bundle["obligations"]
    }
    preference = {"SEND_TERR": 0, "SEND_SAT": 1, "WAIT": 2, "ISSUE_QUERY": 3}

    def key(action: tuple[str, str | None]):
        oid = str(action[1]) if action[1] is not None else ""
        return (preference.get(action[0], 9), deadlines.get(oid, 10**18) - at_s, repr(action))

    return sorted(actions, key=key)


def solve_fixed_resource_ordered_exact(
    bundle: dict[str, Any],
    *,
    query_budget: int,
    satellite_budget: int,
    max_expansions: int = 200_000,
) -> dict[str, Any]:
    """Exact same-information reference using v2's action order but no L/U.

    This isolates search-order effects from the future-choice bounds/certificates.
    """

    from causal_evidence_process_v0_1 import attach_causal_evidence

    process = attach_causal_evidence(bundle)
    start = min(_attempt_lattice(bundle))
    states = initial(bundle, satellite_budget)
    memo: dict[Any, dict[str, Any] | None] = {}
    expanded = 0
    recursive_calls = 0
    action_steps = 0
    started = perf_counter()

    def canon(support: dict[str, LocalState]):
        return tuple(sorted(support.items()))

    def rec(t: int, support: dict[str, LocalState], qleft: int) -> dict[str, Any] | None:
        nonlocal expanded, recursive_calls, action_steps
        recursive_calls += 1
        branches = _normalize(bundle, process, t, support)
        if len(branches) != 1 or next(iter(branches)) != "same":
            children = []
            for observation, child in sorted(branches.items()):
                sub = rec(t, child, qleft)
                if sub is None:
                    return None
                children.append({"observation": observation, "worlds": sorted(child), "subpolicy": sub})
            return {"time_s": t, "event": "OBSERVATION", "children": children}

        support = next(iter(branches.values()))
        key = (t, qleft, canon(support))
        if key in memo:
            return memo[key]
        if any(_expired(bundle, state, t) for state in support.values()):
            memo[key] = None
            return None
        if all(_success(bundle, state) for state in support.values()):
            memo[key] = {"terminal": True}
            return {"terminal": True}
        if expanded >= max_expansions:
            raise RuntimeError(f"ordered exact expansion limit {max_expansions}")
        expanded += 1

        for action in _ordered_actions(bundle, t, _legal_actions(bundle, process, support, t)):
            dq = int(action[0] == "ISSUE_QUERY")
            if dq > qleft:
                continue
            stepped = _step(bundle, process, support, t, action)
            if stepped is None:
                continue
            action_steps += 1
            child, next_t = stepped
            sub = rec(next_t, child, qleft - dq)
            if sub is None:
                continue
            policy = {
                "time_s": t,
                "action": action[0],
                "arg": action[1],
                "worlds": sorted(support),
                "subpolicy": sub,
            }
            memo[key] = policy
            return policy
        memo[key] = None
        return None

    policy = rec(start, states, query_budget)
    wall_s = perf_counter() - started
    if policy is not None:
        replay_continuation_policy(
            bundle,
            at_s=start,
            states=states,
            policy=policy,
            query_budget=query_budget,
        )
    return {
        "status": "EXACT",
        "solvable": policy is not None,
        "expanded": expanded,
        "recursive_calls": recursive_calls,
        "action_steps": action_steps,
        "wall_s": wall_s,
        "memo_entries": len(memo),
    }


def solve_fixed_resource_v2(
    bundle: dict[str, Any],
    *,
    query_budget: int,
    satellite_budget: int,
    upper_mode: str,
    use_lower: bool,
) -> dict[str, Any]:
    start = min(_attempt_lattice(bundle))
    states = initial(bundle, satellite_budget)
    solver = FutureChoiceExactFallback(
        bundle,
        upper_mode=upper_mode,
        use_lower=use_lower,
    )
    result = solver.solve(start, states, query_budget=query_budget)
    if result["solvable"] is True:
        replay_continuation_policy(
            bundle,
            at_s=start,
            states=states,
            policy=result["policy"],
            query_budget=query_budget,
        )
    return {
        "status": result["status"],
        "solvable": result["solvable"],
        "metrics": solver.metrics.as_dict(),
    }


def solve_minimal_resource_generic_exact(bundle: dict[str, Any]) -> dict[str, Any]:
    start = min(_attempt_lattice(bundle))
    calls = 0
    aggregate_expanded = 0
    aggregate_wall_s = 0.0
    tried = []
    for query_budget in range(len(bundle["obligations"]) + 1):
        for sat_budget in range(int(bundle["public_environment"]["satellite_budget_units"]) + 1):
            solver = ExactContinuationReference(bundle)
            states = initial(bundle, sat_budget)
            started = perf_counter()
            result = solver.solve(start, states, query_budget=query_budget)
            wall_s = perf_counter() - started
            calls += 1
            aggregate_expanded += int(result["expanded"])
            aggregate_wall_s += wall_s
            tried.append(
                {
                    "query_budget": query_budget,
                    "satellite_budget": sat_budget,
                    "status": result["status"],
                    "solvable": result["solvable"],
                    "expanded": result["expanded"],
                    "wall_s": wall_s,
                }
            )
            if result["solvable"] is True:
                replay_continuation_policy(
                    bundle,
                    at_s=start,
                    states=states,
                    policy=result["policy"],
                    query_budget=query_budget,
                )
                return {
                    "status": "EXACT",
                    "solvable": True,
                    "minimal_resource_point": [query_budget, sat_budget],
                    "winning_expanded": int(result["expanded"]),
                    "winning_wall_s": wall_s,
                    "aggregate_calls": calls,
                    "aggregate_expanded": aggregate_expanded,
                    "aggregate_wall_s": aggregate_wall_s,
                    "tried": tried,
                }
    return {
        "status": "EXACT",
        "solvable": False,
        "minimal_resource_point": None,
        "aggregate_calls": calls,
        "aggregate_expanded": aggregate_expanded,
        "aggregate_wall_s": aggregate_wall_s,
        "tried": tried,
    }


def ordinary_baselines(bundle: dict[str, Any]) -> dict[str, Any]:
    rows = {
        "shallow_rule": solve_shallow_rule(bundle),
        "least_slack": solve_least_slack(bundle),
        "latest_feasible_send": solve_latest_feasible_send(bundle),
        "always_query_then_plan": solve_always_query_then_plan(bundle),
        "myopic_flow_voi": solve_myopic_flow_voi(bundle),
        "depth3_flow": solve_depth_k_flow_terminal(bundle, depth=3),
    }
    return {
        name: {
            "solvable": bool(result["solvable"]),
            "decisions": int(result.get("decisions", 0)),
        }
        for name, result in rows.items()
    }


def run_case(
    bundle: dict[str, Any],
    *,
    upper_mode: str = "all_recursive",
    use_lower: bool = True,
) -> dict[str, Any]:
    exact = solve_minimal_resource_generic_exact(bundle)
    v2 = solve_minimal_resource_v2(
        bundle,
        upper_mode=upper_mode,
        use_lower=use_lower,
    )
    if not exact["solvable"]:
        raise RuntimeError("hard signature unexpectedly exact-infeasible")
    q, b = map(int, exact["minimal_resource_point"])
    v2_online = solve_fixed_resource_v2(
        bundle,
        query_budget=q,
        satellite_budget=b,
        upper_mode=upper_mode,
        use_lower=use_lower,
    )
    ordered_exact = solve_fixed_resource_ordered_exact(
        bundle,
        query_budget=q,
        satellite_budget=b,
    )
    if not ordered_exact["solvable"]:
        raise RuntimeError("same-order exact unexpectedly fails at the frozen exact resource point")
    ordinary = ordinary_baselines(bundle)
    same_point = exact["minimal_resource_point"] == v2["minimal_resource_point"]
    exact_expanded = int(exact["aggregate_expanded"])
    v2_expanded = int(v2["aggregate_metrics"]["expanded"])
    exact_wall = float(exact["aggregate_wall_s"])
    v2_wall = float(v2["aggregate_metrics"]["wall_s"])
    return {
        "passed": bool(exact["solvable"] and v2["solvable"] and same_point),
        "resource_point_equal": same_point,
        "exact": exact,
        "ordered_exact": ordered_exact,
        "v2": {
            "status": v2["status"],
            "solvable": v2["solvable"],
            "minimal_resource_point": v2["minimal_resource_point"],
            "winning_metrics": v2.get("winning_metrics"),
            "aggregate_metrics": v2["aggregate_metrics"],
            "online_same_resource": v2_online,
        },
        "ordinary": ordinary,
        "compute_delta": {
            "aggregate_expanded_v2_minus_exact": v2_expanded - exact_expanded,
            "aggregate_expanded_ratio_v2_over_exact": (
                v2_expanded / exact_expanded if exact_expanded else None
            ),
            "aggregate_wall_v2_minus_exact_s": v2_wall - exact_wall,
            "aggregate_wall_ratio_v2_over_exact": v2_wall / exact_wall if exact_wall else None,
            "online_expanded_v2_minus_exact": (
                int(v2_online["metrics"]["expanded"]) - int(exact["winning_expanded"])
            ),
            "online_expanded_ratio_v2_over_exact": (
                int(v2_online["metrics"]["expanded"]) / int(exact["winning_expanded"])
                if int(exact["winning_expanded"]) else None
            ),
            "online_wall_v2_minus_exact_s": (
                float(v2_online["metrics"]["wall_s"]) - float(exact["winning_wall_s"])
            ),
            "online_wall_ratio_v2_over_exact": (
                float(v2_online["metrics"]["wall_s"]) / float(exact["winning_wall_s"])
                if float(exact["winning_wall_s"]) else None
            ),
            "online_expanded_ordered_minus_exact": (
                int(ordered_exact["expanded"]) - int(exact["winning_expanded"])
            ),
            "online_expanded_ratio_ordered_over_exact": (
                int(ordered_exact["expanded"]) / int(exact["winning_expanded"])
                if int(exact["winning_expanded"]) else None
            ),
            "online_wall_ordered_minus_exact_s": (
                float(ordered_exact["wall_s"]) - float(exact["winning_wall_s"])
            ),
            "online_wall_ratio_ordered_over_exact": (
                float(ordered_exact["wall_s"]) / float(exact["winning_wall_s"])
                if float(exact["winning_wall_s"]) else None
            ),
            "online_expanded_v2_minus_ordered": (
                int(v2_online["metrics"]["expanded"]) - int(ordered_exact["expanded"])
            ),
            "online_expanded_ratio_v2_over_ordered": (
                int(v2_online["metrics"]["expanded"]) / int(ordered_exact["expanded"])
                if int(ordered_exact["expanded"]) else None
            ),
            "online_wall_v2_minus_ordered_s": (
                float(v2_online["metrics"]["wall_s"]) - float(ordered_exact["wall_s"])
            ),
            "online_wall_ratio_v2_over_ordered": (
                float(v2_online["metrics"]["wall_s"]) / float(ordered_exact["wall_s"])
                if float(ordered_exact["wall_s"]) else None
            ),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["train", "dev", "test", "all"], default="dev")
    ap.add_argument("--limit", type=int)
    ap.add_argument(
        "--upper-mode",
        choices=["root_query", "query_recursive", "all_recursive", "none"],
        default="all_recursive",
    )
    ap.add_argument("--lower-mode", choices=["on", "off"], default="on")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    reps = hard_representatives(args.split)
    if args.limit is not None:
        reps = reps[: args.limit]
    recipes = {row.recipe_id: row for row in core_recipes()}
    rows = []
    for index, rep in enumerate(reps, 1):
        bundle = materialize_recipe(recipes[str(rep["recipe_id"])])
        result = run_case(
            bundle,
            upper_mode=args.upper_mode,
            use_lower=args.lower_mode == "on",
        )
        rows.append(
            {
                "signature": rep["signature"],
                "split": rep["split"],
                "recipe_id": rep["recipe_id"],
                "result": result,
            }
        )
        print(
            index,
            str(rep["signature"])[:12],
            "PASS" if result["passed"] else "FAIL",
            "point", result["v2"]["minimal_resource_point"],
            "exp-ratio", result["compute_delta"]["aggregate_expanded_ratio_v2_over_exact"],
            flush=True,
        )

    ordinary_names = sorted(rows[0]["result"]["ordinary"]) if rows else []
    summary = {
        "signature_count": len(rows),
        "pass_count": sum(row["result"]["passed"] for row in rows),
        "resource_point_match_count": sum(row["result"]["resource_point_equal"] for row in rows),
        "ordinary_success_count": {
            name: sum(row["result"]["ordinary"][name]["solvable"] for row in rows)
            for name in ordinary_names
        },
        "v2_better_aggregate_expanded_count": sum(
            row["result"]["compute_delta"]["aggregate_expanded_v2_minus_exact"] < 0
            for row in rows
        ),
        "v2_better_online_expanded_count": sum(
            row["result"]["compute_delta"]["online_expanded_v2_minus_exact"] < 0
            for row in rows
        ),
        "v2_better_online_wall_count": sum(
            row["result"]["compute_delta"]["online_wall_v2_minus_exact_s"] < 0
            for row in rows
        ),
        "v2_better_online_wall_than_ordered_count": sum(
            row["result"]["compute_delta"]["online_wall_v2_minus_ordered_s"] < 0
            for row in rows
        ),
        "v2_better_aggregate_wall_count": sum(
            row["result"]["compute_delta"]["aggregate_wall_v2_minus_exact_s"] < 0
            for row in rows
        ),
        "aggregate_exact_expanded": sum(row["result"]["exact"]["aggregate_expanded"] for row in rows),
        "aggregate_v2_expanded": sum(row["result"]["v2"]["aggregate_metrics"]["expanded"] for row in rows),
        "aggregate_exact_wall_s": sum(row["result"]["exact"]["aggregate_wall_s"] for row in rows),
        "aggregate_v2_wall_s": sum(row["result"]["v2"]["aggregate_metrics"]["wall_s"] for row in rows),
        "online_exact_expanded": sum(row["result"]["exact"]["winning_expanded"] for row in rows),
        "online_ordered_exact_expanded": sum(row["result"]["ordered_exact"]["expanded"] for row in rows),
        "online_v2_expanded": sum(row["result"]["v2"]["online_same_resource"]["metrics"]["expanded"] for row in rows),
        "online_exact_wall_s": sum(row["result"]["exact"]["winning_wall_s"] for row in rows),
        "online_ordered_exact_wall_s": sum(row["result"]["ordered_exact"]["wall_s"] for row in rows),
        "online_v2_wall_s": sum(row["result"]["v2"]["online_same_resource"]["metrics"]["wall_s"] for row in rows),
        "upper_prunes": sum(row["result"]["v2"]["aggregate_metrics"]["upper_prunes"] for row in rows),
        "lower_hits": sum(row["result"]["v2"]["aggregate_metrics"]["lower_hits"] for row in rows),
    }
    summary["aggregate_expanded_ratio_v2_over_exact"] = (
        summary["aggregate_v2_expanded"] / summary["aggregate_exact_expanded"]
        if summary["aggregate_exact_expanded"] else None
    )
    summary["aggregate_wall_ratio_v2_over_exact"] = (
        summary["aggregate_v2_wall_s"] / summary["aggregate_exact_wall_s"]
        if summary["aggregate_exact_wall_s"] else None
    )
    summary["online_expanded_ratio_v2_over_exact"] = (
        summary["online_v2_expanded"] / summary["online_exact_expanded"]
        if summary["online_exact_expanded"] else None
    )
    summary["online_wall_ratio_v2_over_exact"] = (
        summary["online_v2_wall_s"] / summary["online_exact_wall_s"]
        if summary["online_exact_wall_s"] else None
    )
    summary["online_expanded_ratio_ordered_over_exact"] = (
        summary["online_ordered_exact_expanded"] / summary["online_exact_expanded"]
        if summary["online_exact_expanded"] else None
    )
    summary["online_wall_ratio_ordered_over_exact"] = (
        summary["online_ordered_exact_wall_s"] / summary["online_exact_wall_s"]
        if summary["online_exact_wall_s"] else None
    )
    summary["online_expanded_ratio_v2_over_ordered"] = (
        summary["online_v2_expanded"] / summary["online_ordered_exact_expanded"]
        if summary["online_ordered_exact_expanded"] else None
    )
    summary["online_wall_ratio_v2_over_ordered"] = (
        summary["online_v2_wall_s"] / summary["online_ordered_exact_wall_s"]
        if summary["online_ordered_exact_wall_s"] else None
    )
    passed = len(rows) > 0 and summary["pass_count"] == len(rows)
    artifact = {
        "schema_version": "0.1",
        "status": "PASS" if passed else "FAIL",
        "experiment": "layer2-v2-future-choice-lu-matrix",
        "split": args.split,
        "upper_mode": args.upper_mode,
        "lower_mode": args.lower_mode,
        "summary": summary,
        "rules": [
            "Layer-1 task/evidence/transition semantics are frozen and shared by every arm.",
            "Generic exact and v2 search the same increasing (paid-query, satellite-budget) rectangle.",
            "Online compute is additionally compared once at the same frozen minimal resource point; resource-envelope sweep cost is reported separately as offline benchmark analysis.",
            "A same-order exact arm uses the identical v2 action ordering with no L/U, isolating search-order gains from future-choice structural gains.",
            "v2 U=0 is an optimistic residual-feasibility impossibility proof; L=1 is a replayable common-opportunity continuation.",
            "Unresolved v2 states fall back to exact same-information AND/OR search with U/L integrated into that single fallback search.",
            "Ordinary policies are reported for saturation context and are not given oracle labels.",
        ],
        "rows": rows,
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": artifact["status"], "summary": summary}, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
