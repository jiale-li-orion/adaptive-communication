#!/usr/bin/env python3
"""Run the baseline ladder frozen by cache06.md on Layer-1 v0.2 hard dev.

This audit separates three roles:

* placement/communication policies: gateway local autonomy, passive feedback,
  normal-send-as-probe and fixed owner reads;
* finite-planning policies: fixed query schedules, myopic/shallow/depth-k and
  receding horizon with a generic residual-flow terminal value;
* exact/strong structural controls: loaded from already-frozen exact and
  persistent-incremental artifacts rather than recomputed here.

No baseline receives hidden-world identity at a center placement.  The two
gateway/world-local baselines are explicitly placement-specific and are scored
as robust only if they succeed in every frozen world.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
from time import perf_counter
from typing import Any, Mapping

from compositional_recipe_generator_v0_1 import core_recipes
from dynamic_world_materializer_v0_1 import materialize_recipe
from ordinary_baselines_compositional_v0_1 import (
    fixed_owner_read_edf,
    gateway_local_edf_reserve,
    send_probe_ack_fallback,
)
from v8_policy_baselines_v0_1 import (
    _choose_depth_k,
    _execute_policy,
    solve_always_query_then_plan,
    solve_depth_k,
    solve_fixed_query_schedule,
    solve_myopic_flow_voi,
    solve_shallow_rule,
)


ROOT = Path(__file__).resolve().parents[3]
SPLIT = ROOT / "results/benchmark/layer1-structure-aware-split-v0.2-retry-legality.json"
EXACT = ROOT / "results/agentic/layer2-v2-matrix-dev.json"
STRONG = ROOT / "results/agentic/layer2-v2-persistent-frontier-4arm-dev-branchisolated.json"


def _representatives(split_name: str) -> list[dict[str, Any]]:
    frozen = json.loads(SPLIT.read_text(encoding="utf-8"))
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in frozen["rows"]:
        if row.get("candidate_role") == "HARD_PRE_ADMISSION_SURVIVOR" and row.get("split") == split_name:
            grouped[str(row["signature"])].append(row)
    return [min(rows, key=lambda row: str(row["recipe_id"])) for _, rows in sorted(grouped.items())]


def _policy_cost(policy: Mapping[str, Any] | None) -> dict[str, int]:
    if not policy or policy.get("terminal"):
        return {"remote_queries": 0, "terrestrial_sends": 0, "satellite_sends": 0, "actions": 0}
    if policy.get("event") == "OBSERVATION":
        rows = [_policy_cost(row["subpolicy"]) for row in policy["children"]]
        return {
            key: max((row[key] for row in rows), default=0)
            for key in ("remote_queries", "terrestrial_sends", "satellite_sends", "actions")
        }
    child = _policy_cost(policy["subpolicy"])
    action = str(policy["action"])
    return {
        "remote_queries": child["remote_queries"] + int(action == "ISSUE_QUERY"),
        "terrestrial_sends": child["terrestrial_sends"] + int(action == "SEND_TERR"),
        "satellite_sends": child["satellite_sends"] + int(action == "SEND_SAT"),
        "actions": child["actions"] + 1,
    }


def _run_causal(name: str, fn) -> dict[str, Any]:
    started = perf_counter()
    result = fn()
    wall_s = perf_counter() - started
    return {
        "baseline": name,
        "success": bool(result["solvable"]),
        "policy_cost_worst_branch": _policy_cost(result.get("policy")),
        "planner_decisions": int(result.get("decisions", 0)),
        "wall_s": wall_s,
    }


def _receding_flow(bundle, horizon: int) -> dict[str, Any]:
    out = _execute_policy(
        bundle,
        lambda b, p, t, s: _choose_depth_k(b, p, t, s, horizon, leaf="flow"),
    )
    return {"baseline": f"receding_flow_terminal_{horizon}", "horizon_decisions": horizon, **out}


def _world_actions_cost(actions: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "remote_queries": sum(row["action"] == "OWNER_QUERY" for row in actions),
        "terrestrial_sends": sum(row["action"] == "SEND_TERR" for row in actions),
        "satellite_sends": sum(row["action"] == "SEND_SAT" for row in actions),
        "actions": len(actions),
    }


def _run_world_local(bundle, name: str, fn) -> dict[str, Any]:
    started = perf_counter()
    rows = [fn(bundle, world) for world in bundle["worlds"]]
    wall_s = perf_counter() - started
    costs = [_world_actions_cost(row["actions"]) for row in rows]
    return {
        "baseline": name,
        "success": all(row["success"] for row in rows),
        "world_success_count": sum(row["success"] for row in rows),
        "world_count": len(rows),
        "policy_cost_worst_world": {
            key: max((row[key] for row in costs), default=0)
            for key in ("remote_queries", "terrestrial_sends", "satellite_sends", "actions")
        },
        "wall_s": wall_s,
        "placement": "gateway/world-local causal execution",
    }


def _case(bundle) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    rows["gateway_local_autonomy"] = _run_world_local(
        bundle, "gateway_local_autonomy", gateway_local_edf_reserve
    )
    rows["normal_send_as_probe"] = _run_world_local(
        bundle, "normal_send_as_probe", send_probe_ack_fallback
    )
    rows["fixed_owner_read_edf"] = _run_world_local(
        bundle, "fixed_owner_read_edf", fixed_owner_read_edf
    )
    rows["always_query_then_plan"] = _run_causal(
        "always_query_then_plan", lambda: solve_always_query_then_plan(bundle)
    )
    for mode in ("FIRST_RELEASE", "EVERY_RELEASE", "SATELLITE_START", "EVERY_SECOND_EVENT"):
        key = f"fixed_query_{mode.lower()}"
        rows[key] = _run_causal(key, lambda mode=mode: solve_fixed_query_schedule(bundle, mode=mode))
    rows["myopic_flow_voi"] = _run_causal("myopic_flow_voi", lambda: solve_myopic_flow_voi(bundle))
    rows["shallow_rule"] = _run_causal("shallow_rule", lambda: solve_shallow_rule(bundle))
    for depth in (2, 3):
        key = f"true_depth_{depth}_belief"
        rows[key] = _run_causal(key, lambda depth=depth: solve_depth_k(bundle, depth=depth))
    for horizon in (2, 3, 4):
        key = f"receding_flow_terminal_{horizon}"
        rows[key] = _run_causal(key, lambda horizon=horizon: _receding_flow(bundle, horizon))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev"], default="dev")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    reps = _representatives(args.split)
    if args.limit is not None:
        reps = reps[: args.limit]
    recipes = {row.recipe_id: row for row in core_recipes()}
    cases = []
    for index, rep in enumerate(reps, 1):
        rows = _case(materialize_recipe(recipes[str(rep["recipe_id"])]))
        cases.append({"signature": rep["signature"], "recipe_id": rep["recipe_id"], "baselines": rows})
        print(
            index,
            str(rep["signature"])[:12],
            "successes",
            [name for name, row in rows.items() if row["success"]],
            flush=True,
        )

    names = sorted(cases[0]["baselines"]) if cases else []
    exact = json.loads(EXACT.read_text(encoding="utf-8"))
    strong = json.loads(STRONG.read_text(encoding="utf-8"))
    exact_rows = {str(row["signature"]): row for row in exact["rows"]}
    no_query_exact_success = 0
    generic_exact_success = 0
    for case in cases:
        row = exact_rows[str(case["signature"])]["result"]["exact"]
        generic_exact_success += int(bool(row["solvable"]))
        no_query_exact_success += int(any(
            item["query_budget"] == 0 and item["solvable"] is True
            for item in row["tried"]
        ))

    summary = {
        "signature_count": len(cases),
        "success_count": {
            name: sum(case["baselines"][name]["success"] for case in cases)
            for name in names
        },
        "no_paid_query_exact_success_count": no_query_exact_success,
        "generic_exact_success_count": generic_exact_success,
        "strong_control_reference": {
            "source_artifact": STRONG.name,
            "frontier_match_count": strong["summary"]["frontier_match_count"],
            "ordinary_incremental_frontier_expanded": strong["summary"]["ordinary_incremental_frontier_expanded"],
            "dependency_cache_frontier_expanded": strong["summary"]["dependency_cache_frontier_expanded"],
            "fresh_frontier_expanded": strong["summary"]["fresh_frontier_expanded"],
        },
    }
    artifact = {
        "schema_version": "0.1",
        "status": "PASS" if cases else "FAIL",
        "experiment": "layer2-v2-cache06-baseline-ladder",
        "split": args.split,
        "summary": summary,
        "rules": [
            "Gateway/world-local baselines are placement-specific and count as robust only when every frozen world succeeds.",
            "Fixed-query, myopic, shallow, depth-k and receding-flow policies use the same observation-matched Layer-1 process.",
            "Receding-flow terminal baselines use only a generic per-world residual-flow terminal relaxation, not the proposed conditional frontier.",
            "No-query exact is reported as an information ceiling, not as an ordinary deployable policy.",
            "Bytes/airtime/energy remain uncalibrated and are not inferred from action counts.",
        ],
        "cases": cases,
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": artifact["status"], "summary": summary}, ensure_ascii=False, indent=2))
    return 0 if artifact["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
