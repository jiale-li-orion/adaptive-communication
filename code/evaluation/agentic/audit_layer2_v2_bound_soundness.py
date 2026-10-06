#!/usr/bin/env python3
"""Audit Layer-2 v2 L/U soundness on exact-policy reachable prefixes.

For every legal action at every reached decision boundary:

* ``L=1`` must imply an exact causal continuation after forcing that action;
* ``U=0`` must imply exact causal infeasibility after forcing that action;
* ``L<=U`` must hold mechanically.

This is intentionally labelled a *reachable-prefix* audit.  It does not claim
to enumerate every legal off-policy history in the benchmark state space.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
from typing import Any

from causal_evidence_process_v0_1 import attach_causal_evidence
from compositional_recipe_generator_v0_1 import core_recipes
from dynamic_world_materializer_v0_1 import materialize_recipe
from exact_reference_oracle_v0_1 import LocalState, _attempt_lattice, _normalize
from layer1_v02_exact_continuation import ExactContinuationReference
from layer2_v2_future_choice import future_choice_context, solve_minimal_resource_v2
from v8_policy_baselines_v0_1 import _legal_actions, _step


ROOT = Path(__file__).resolve().parents[3]
SPLIT = ROOT / "results/benchmark/layer1-structure-aware-split-v0.2-retry-legality.json"


def _representatives(split_name: str) -> list[dict[str, Any]]:
    frozen = json.loads(SPLIT.read_text(encoding="utf-8"))
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in frozen["rows"]:
        if row.get("candidate_role") == "HARD_PRE_ADMISSION_SURVIVOR" and row.get("split") == split_name:
            grouped[str(row["signature"])].append(row)
    return [min(rows, key=lambda row: str(row["recipe_id"])) for _, rows in sorted(grouped.items())]


def _initial(bundle, sat_budget: int):
    return {
        str(world["world_id"]): LocalState(satellite_budget=sat_budget)
        for world in bundle["worlds"]
    }


def _action_key(action):
    return f"{action[0]}:{action[1] if action[1] is not None else '-'}"


def _walk(
    bundle,
    *,
    at_s,
    states,
    query_budget,
    policy,
    rows,
):
    process = attach_causal_evidence(bundle)
    branches = _normalize(bundle, process, at_s, states)
    if len(branches) != 1 or next(iter(branches)) != "same":
        assert policy.get("event") == "OBSERVATION"
        children = {str(row["observation"]): row for row in policy["children"]}
        assert set(children) == set(branches)
        for observation, child in sorted(branches.items()):
            _walk(
                bundle,
                at_s=at_s,
                states=child,
                query_budget=query_budget,
                policy=children[observation]["subpolicy"],
                rows=rows,
            )
        return

    support = next(iter(branches.values()))
    context = future_choice_context(
        bundle,
        at_s=at_s,
        states=support,
        query_budget=query_budget,
        witness_policy=policy,
    )
    by_key = {row["action_key"]: row for row in context["actions"]}
    exact = ExactContinuationReference(bundle)
    action_rows = []
    for action in _legal_actions(bundle, process, support, at_s):
        key = _action_key(action)
        bound = by_key[key]
        dq = int(action[0] == "ISSUE_QUERY")
        if dq > query_budget:
            exact_solvable = False
        else:
            stepped = _step(bundle, process, support, at_s, action)
            if stepped is None:
                exact_solvable = False
            else:
                child, next_t = stepped
                result = exact.solve(
                    next_t,
                    child,
                    query_budget=query_budget - dq,
                )
                assert result["status"] == "EXACT"
                exact_solvable = bool(result["solvable"])
        lower = int(bound["lower"])
        upper = int(bound["upper"])
        action_rows.append(
            {
                "action_key": key,
                "lower": lower,
                "upper": upper,
                "exact_solvable": exact_solvable,
                "lower_sound": not lower or exact_solvable,
                "upper_sound": upper or not exact_solvable,
                "ordered": lower <= upper,
            }
        )

    rows.append(
        {
            "time_s": at_s,
            "query_budget": query_budget,
            "world_count": len(support),
            "actions": action_rows,
        }
    )
    if policy.get("terminal"):
        return
    action = (str(policy["action"]), policy.get("arg"))
    dq = int(action[0] == "ISSUE_QUERY")
    stepped = _step(bundle, process, support, at_s, action)
    assert stepped is not None
    child, next_t = stepped
    _walk(
        bundle,
        at_s=next_t,
        states=child,
        query_budget=query_budget - dq,
        policy=policy["subpolicy"],
        rows=rows,
    )


def run_case(bundle):
    solved = solve_minimal_resource_v2(bundle, upper_mode="all_recursive")
    assert solved["solvable"] is True
    q, sat = map(int, solved["minimal_resource_point"])
    rows: list[dict[str, Any]] = []
    _walk(
        bundle,
        at_s=min(_attempt_lattice(bundle)),
        states=_initial(bundle, sat),
        query_budget=q,
        policy=solved["policy"],
        rows=rows,
    )
    actions = [action for row in rows for action in row["actions"]]
    return {
        "minimal_resource_point": [q, sat],
        "prefix_count": len(rows),
        "action_count": len(actions),
        "lower_one_count": sum(action["lower"] == 1 for action in actions),
        "upper_zero_count": sum(action["upper"] == 0 for action in actions),
        "lower_sound_count": sum(action["lower_sound"] for action in actions),
        "upper_sound_count": sum(action["upper_sound"] for action in actions),
        "ordered_count": sum(action["ordered"] for action in actions),
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["train", "dev", "test"], default="dev")
    ap.add_argument("--limit", type=int, default=1)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    reps = _representatives(args.split)[: args.limit]
    recipes = {row.recipe_id: row for row in core_recipes()}
    cases = []
    for index, rep in enumerate(reps, 1):
        result = run_case(materialize_recipe(recipes[str(rep["recipe_id"])]))
        cases.append({"signature": rep["signature"], "recipe_id": rep["recipe_id"], "result": result})
        print(
            index,
            str(rep["signature"])[:12],
            result["action_count"],
            "actions",
            "L1",
            result["lower_one_count"],
            "U0",
            result["upper_zero_count"],
            flush=True,
        )

    action_count = sum(row["result"]["action_count"] for row in cases)
    summary = {
        "signature_count": len(cases),
        "prefix_count": sum(row["result"]["prefix_count"] for row in cases),
        "action_count": action_count,
        "lower_one_count": sum(row["result"]["lower_one_count"] for row in cases),
        "upper_zero_count": sum(row["result"]["upper_zero_count"] for row in cases),
        "lower_sound_count": sum(row["result"]["lower_sound_count"] for row in cases),
        "upper_sound_count": sum(row["result"]["upper_sound_count"] for row in cases),
        "ordered_count": sum(row["result"]["ordered_count"] for row in cases),
    }
    passed = bool(cases) and all(
        summary[key] == action_count
        for key in ("lower_sound_count", "upper_sound_count", "ordered_count")
    )
    artifact = {
        "schema_version": "0.1",
        "status": "PASS" if passed else "FAIL",
        "experiment": "layer2-v2-bound-soundness-reachable-prefixes",
        "split": args.split,
        "scope": "exact-policy reachable prefixes only; exhaustive off-policy legal-history audit remains open",
        "summary": summary,
        "cases": cases,
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": artifact["status"], "summary": summary}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
