#!/usr/bin/env python3
"""Does the v2 conflict frontier structurally certify harmful acquisition?

The frozen v1 failure surface contains query-legal boundaries where taking the
owner query destroys all causal task-completion continuations.  This audit
tests whether Layer-2 v2 can detect that failure *structurally* before invoking
an exact continuation search.

At every query-legal prefix before the exact policy's first paid query:

1. execute the real query transition (including terrestrial capacity cost),
2. build the post-query obligation/opportunity conflict frontier,
3. declare ``structural U=0`` only when perfect-information physical matching
   is already impossible in at least one compatible world,
4. compare that certificate with the exact causal continuation label.

False harmful certificates are forbidden.  Missed harmful cases remain
``UNRESOLVED`` and correctly fall back to exact search.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from causal_evidence_process_v0_1 import attach_causal_evidence
from compositional_recipe_generator_v0_1 import core_recipes
from dynamic_world_materializer_v0_1 import materialize_recipe
from exact_reference_oracle_v0_1 import LocalState, _attempt_lattice
from layer1_v02_exact_continuation import ExactContinuationReference, replay_continuation_policy
from layer2_v2_conflict_frontier import (
    build_world_certificate,
    aggregate_snapshot,
    first_observation_causal_upper,
)
from v8_policy_baselines_v0_1 import _legal_actions, _normalize_one, _step


ROOT = Path(__file__).resolve().parents[3]
SPLIT = ROOT / "results/benchmark/layer1-structure-aware-split-v0.2-retry-legality.json"
QUERY = ("ISSUE_QUERY", "gateway_state_summary")


def _initial(bundle: dict, satellite_budget: int) -> dict[str, LocalState]:
    return {
        str(world["world_id"]): LocalState(satellite_budget=satellite_budget)
        for world in bundle["worlds"]
    }


def _representatives(split_name: str | None) -> list[dict[str, Any]]:
    frozen = json.loads(SPLIT.read_text(encoding="utf-8"))
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in frozen["rows"]:
        if row.get("candidate_role") != "HARD_PRE_ADMISSION_SURVIVOR":
            continue
        if split_name is not None and row.get("split") != split_name:
            continue
        grouped[str(row["signature"])].append(row)
    return [min(rows, key=lambda row: str(row["recipe_id"])) for _, rows in sorted(grouped.items())]


def _minimal_resource_policy(bundle: dict) -> tuple[int, int, dict[str, Any]]:
    start = min(_attempt_lattice(bundle))
    for query_budget in range(len(bundle["obligations"]) + 1):
        for satellite_budget in range(int(bundle["public_environment"]["satellite_budget_units"]) + 1):
            states = _initial(bundle, satellite_budget)
            result = ExactContinuationReference(bundle).solve(
                start,
                states,
                query_budget=query_budget,
            )
            if result["solvable"] is True:
                replay_continuation_policy(
                    bundle,
                    at_s=start,
                    states=states,
                    policy=result["policy"],
                    query_budget=query_budget,
                )
                return query_budget, satellite_budget, result
    raise RuntimeError(f"no exact policy for {bundle['recipe_id']}")


def _conflict_snapshot(bundle: dict, *, at_s: int, states: dict[str, LocalState]):
    return aggregate_snapshot(
        at_s=at_s,
        worlds=(
            build_world_certificate(
                bundle,
                world_id=world_id,
                state=state,
                at_s=at_s,
            )
            for world_id, state in sorted(states.items())
        ),
    )


def _run_case(bundle: dict) -> dict[str, Any]:
    query_budget, satellite_budget, solved = _minimal_resource_policy(bundle)
    process = attach_causal_evidence(bundle)
    states = _initial(bundle, satellite_budget)
    at_s = min(_attempt_lattice(bundle))
    node = solved["policy"]
    rows = []
    steps = 0

    while node and not node.get("terminal") and steps < 512:
        branches = _normalize_one(bundle, process, at_s, states)
        if len(branches) != 1 or next(iter(branches)) != "same":
            break
        states = next(iter(branches.values()))

        if QUERY in _legal_actions(bundle, process, states, at_s):
            before = _conflict_snapshot(bundle, at_s=at_s, states=states)
            stepped = _step(bundle, process, states, at_s, QUERY)
            assert stepped is not None
            child, next_t = stepped
            after = _conflict_snapshot(bundle, at_s=next_t, states=child)
            structural_harm = not after.optimistic_feasible_all_worlds
            causal_metrics: dict[str, int] = {}
            causal_upper_ok = first_observation_causal_upper(
                bundle,
                process,
                at_s=next_t,
                states=deepcopy(child),
                query_budget=max(0, query_budget - 1),
                metrics=causal_metrics,
            )
            causal_harm = not causal_upper_ok

            continuation = ExactContinuationReference(bundle).solve(
                next_t,
                deepcopy(child),
                query_budget=max(0, query_budget - 1),
            )
            exact_safe = continuation["solvable"] is True
            if exact_safe:
                replay_continuation_policy(
                    bundle,
                    at_s=next_t,
                    states=child,
                    policy=continuation["policy"],
                    query_budget=max(0, query_budget - 1),
                )
            rows.append(
                {
                    "time_s": at_s,
                    "exact_query_safe": exact_safe,
                    "exact_query_harmful": not exact_safe,
                    "structural_u_zero": structural_harm,
                    "first_observation_u_zero": causal_harm,
                    "sound": not (structural_harm and exact_safe),
                    "first_observation_sound": not (causal_harm and exact_safe),
                    "first_observation_nodes": int(causal_metrics.get("nodes", 0)),
                    "first_observation_action_checks": int(causal_metrics.get("action_checks", 0)),
                    "first_observation_leaves": int(causal_metrics.get("observation_leaves", 0)),
                    "before_backup_lower_bound": before.worst_case_backup_lower_bound,
                    "after_backup_lower_bound": after.worst_case_backup_lower_bound,
                    "backup_lower_bound_delta": (
                        after.worst_case_backup_lower_bound
                        - before.worst_case_backup_lower_bound
                    ),
                    "before_conflict_obligations": list(before.conflict_obligations),
                    "after_conflict_obligations": list(after.conflict_obligations),
                    "continuation_expanded": int(continuation["expanded"]),
                }
            )

        if node.get("action") == "ISSUE_QUERY":
            break
        stepped = _step(bundle, process, states, at_s, (node["action"], node.get("arg")))
        if stepped is None:
            raise AssertionError("exact policy contains a non-executable action")
        states, at_s = stepped
        node = node["subpolicy"]
        steps += 1

    harmful = [row for row in rows if row["exact_query_harmful"]]
    safe = [row for row in rows if row["exact_query_safe"]]
    structural = [row for row in rows if row["structural_u_zero"]]
    causal = [row for row in rows if row["first_observation_u_zero"]]
    return {
        "minimal_query_budget": query_budget,
        "minimal_satellite_budget": satellite_budget,
        "query_legal_boundary_count": len(rows),
        "exact_harmful_count": len(harmful),
        "exact_safe_count": len(safe),
        "structural_u_zero_count": len(structural),
        "structurally_certified_harmful_count": sum(
            row["exact_query_harmful"] and row["structural_u_zero"] for row in rows
        ),
        "structural_false_harmful_count": sum(
            row["exact_query_safe"] and row["structural_u_zero"] for row in rows
        ),
        "first_observation_u_zero_count": len(causal),
        "first_observation_certified_harmful_count": sum(
            row["exact_query_harmful"] and row["first_observation_u_zero"] for row in rows
        ),
        "first_observation_false_harmful_count": sum(
            row["exact_query_safe"] and row["first_observation_u_zero"] for row in rows
        ),
        "first_observation_nodes": sum(row["first_observation_nodes"] for row in rows),
        "first_observation_action_checks": sum(row["first_observation_action_checks"] for row in rows),
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["train", "dev", "test", "all"], default="dev")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    split_name = None if args.split == "all" else args.split
    reps = _representatives(split_name)
    if args.limit is not None:
        reps = reps[: args.limit]
    recipes = {row.recipe_id: row for row in core_recipes()}
    cases = []
    for index, rep in enumerate(reps, 1):
        result = _run_case(materialize_recipe(recipes[str(rep["recipe_id"])]))
        cases.append({"signature": rep["signature"], "split": rep["split"], "recipe_id": rep["recipe_id"], "result": result})
        print(
            index,
            str(rep["signature"])[:12],
            "harm", result["exact_harmful_count"],
            "struct", result["structurally_certified_harmful_count"],
            "false", result["structural_false_harmful_count"],
            flush=True,
        )

    legal = sum(case["result"]["query_legal_boundary_count"] for case in cases)
    harmful = sum(case["result"]["exact_harmful_count"] for case in cases)
    safe = sum(case["result"]["exact_safe_count"] for case in cases)
    structural = sum(case["result"]["structurally_certified_harmful_count"] for case in cases)
    false = sum(case["result"]["structural_false_harmful_count"] for case in cases)
    causal = sum(case["result"]["first_observation_certified_harmful_count"] for case in cases)
    causal_false = sum(case["result"]["first_observation_false_harmful_count"] for case in cases)
    causal_nodes = sum(case["result"]["first_observation_nodes"] for case in cases)
    causal_actions = sum(case["result"]["first_observation_action_checks"] for case in cases)
    summary = {
        "signature_count": len(cases),
        "split_counts": dict(sorted(Counter(case["split"] for case in cases).items())),
        "query_legal_boundary_count": legal,
        "exact_harmful_count": harmful,
        "exact_safe_count": safe,
        "structurally_certified_harmful_count": structural,
        "structural_false_harmful_count": false,
        "harmful_coverage": structural / harmful if harmful else None,
        "exact_fallback_harmful_count": harmful - structural,
        "first_observation_certified_harmful_count": causal,
        "first_observation_false_harmful_count": causal_false,
        "first_observation_harmful_coverage": causal / harmful if harmful else None,
        "first_observation_exact_fallback_harmful_count": harmful - causal,
        "first_observation_nodes": causal_nodes,
        "first_observation_action_checks": causal_actions,
    }
    artifact = {
        "schema_version": "0.1",
        "status": "PASS" if cases and false == 0 and causal_false == 0 else "FAIL",
        "experiment": "layer2-v2-structural-query-harm-certificate",
        "split": args.split,
        "summary": summary,
        "cases": cases,
        "claim_boundary": [
            "structural U=0 is only an impossibility certificate; U=1 remains unresolved",
            "first-observation U respects non-anticipativity until the next asynchronous evidence event, then grants perfect information optimistically",
            "query safety/harm ground truth remains exact same-information causal continuation",
            "zero false-harm is mandatory for both upper bounds",
            "uncovered harmful queries correctly fall back to exact planning",
        ],
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": artifact["status"], "summary": summary}, indent=2))
    return 0 if artifact["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
