#!/usr/bin/env python3
"""Audit conditional Q×B acquisition timing against exact causal ground truth."""
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
from layer2_v2_conditional_resource_frontier import ConditionalResourceFrontierRuntime
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
    for q in range(len(bundle["obligations"]) + 1):
        for b in range(int(bundle["public_environment"]["satellite_budget_units"]) + 1):
            states = _initial(bundle, b)
            result = ExactContinuationReference(bundle).solve(
                start,
                states,
                query_budget=q,
            )
            if result["solvable"] is True:
                replay_continuation_policy(
                    bundle,
                    at_s=start,
                    states=states,
                    policy=result["policy"],
                    query_budget=q,
                )
                return q, b, result
    raise RuntimeError(f"no exact policy for {bundle['recipe_id']}")


def _run_case(bundle: dict) -> dict[str, Any]:
    q, b, solved = _minimal_resource_policy(bundle)
    runtime = ConditionalResourceFrontierRuntime(bundle)
    process = attach_causal_evidence(bundle)
    states = _initial(bundle, b)
    at_s = min(_attempt_lattice(bundle))
    node = solved["policy"]
    rows = []
    steps = 0

    # Materialize the initial rectangle once; this seeds both success witness
    # domains and exact-failure antichains for later boundaries.
    initial_frontier = runtime.build_frontier(
        at_s=at_s,
        states=states,
        qmax=q,
        bmax=b,
    )

    while node and not node.get("terminal") and steps < 512:
        branches = _normalize_one(bundle, process, at_s, states)
        if len(branches) != 1 or next(iter(branches)) != "same":
            break
        states = next(iter(branches.values()))

        if QUERY in _legal_actions(bundle, process, states, at_s):
            before_metrics = dict(runtime.metrics)
            decision = runtime.classify_acquisition(
                at_s=at_s,
                states=states,
                query_budget=q,
            )
            delta = {
                key: runtime.metrics[key] - before_metrics[key]
                for key in runtime.metrics
            }

            stepped = _step(bundle, process, states, at_s, QUERY)
            assert stepped is not None
            child, next_t = stepped
            exact = ExactContinuationReference(bundle).solve(
                next_t,
                deepcopy(child),
                query_budget=max(0, q - 1),
            )
            exact_safe = exact["solvable"] is True
            if exact_safe:
                replay_continuation_policy(
                    bundle,
                    at_s=next_t,
                    states=child,
                    policy=exact["policy"],
                    query_budget=max(0, q - 1),
                )
            rows.append(
                {
                    "time_s": at_s,
                    "exact_query_safe": exact_safe,
                    "frontier_query_safe": decision["query_safe"],
                    "query_match": decision["query_safe"] is exact_safe,
                    "labels": decision["labels"],
                    "query_child_source": decision["query_child_source"],
                    "non_query_safe_action_count": len(decision["non_query_safe_actions"]),
                    "runtime_delta": delta,
                    "exact_continuation_expanded": int(exact["expanded"]),
                }
            )

        if node.get("action") == "ISSUE_QUERY":
            break
        stepped = _step(bundle, process, states, at_s, (node["action"], node.get("arg")))
        if stepped is None:
            raise AssertionError("exact policy contains non-executable action")
        states, at_s = stepped
        node = node["subpolicy"]
        steps += 1

    harmful = [row for row in rows if not row["exact_query_safe"]]
    safe = [row for row in rows if row["exact_query_safe"]]
    return {
        "minimal_resource_point": [q, b],
        "initial_pareto_success": [list(row) for row in initial_frontier.pareto_success],
        "initial_maximal_failure": [list(row) for row in initial_frontier.maximal_failure],
        "initial_evidence_gain_type": initial_frontier.evidence_gain_type,
        "query_legal_boundary_count": len(rows),
        "query_match_count": sum(row["query_match"] for row in rows),
        "exact_harmful_count": len(harmful),
        "exact_safe_count": len(safe),
        "harmful_label_count": sum("QUERY_HARMFUL_NOW" in row["labels"] for row in rows),
        "required_label_count": sum("QUERY_REQUIRED_NOW" in row["labels"] for row in rows),
        "defer_label_count": sum("CAN_DEFER_QUERY" in row["labels"] for row in rows),
        "stop_label_count": sum("STOP_ACQUISITION_FOR_FEASIBILITY" in row["labels"] for row in rows),
        "runtime_metrics": dict(runtime.metrics),
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["train", "dev", "test", "all"], default="dev")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    reps = _representatives(None if args.split == "all" else args.split)
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
            result["query_match_count"],
            "/",
            result["query_legal_boundary_count"],
            "harm",
            result["exact_harmful_count"],
            "fallback",
            result["runtime_metrics"]["exact_cell_fallbacks"],
            flush=True,
        )

    legal = sum(case["result"]["query_legal_boundary_count"] for case in cases)
    match = sum(case["result"]["query_match_count"] for case in cases)
    summary = {
        "signature_count": len(cases),
        "split_counts": dict(sorted(Counter(case["split"] for case in cases).items())),
        "query_legal_boundary_count": legal,
        "query_match_count": match,
        "exact_harmful_count": sum(case["result"]["exact_harmful_count"] for case in cases),
        "exact_safe_count": sum(case["result"]["exact_safe_count"] for case in cases),
        "harmful_label_count": sum(case["result"]["harmful_label_count"] for case in cases),
        "required_label_count": sum(case["result"]["required_label_count"] for case in cases),
        "defer_label_count": sum(case["result"]["defer_label_count"] for case in cases),
        "stop_label_count": sum(case["result"]["stop_label_count"] for case in cases),
        "cell_queries": sum(case["result"]["runtime_metrics"]["cell_queries"] for case in cases),
        "success_domain_hits": sum(case["result"]["runtime_metrics"]["success_domain_hits"] for case in cases),
        "failure_domain_hits": sum(case["result"]["runtime_metrics"]["failure_domain_hits"] for case in cases),
        "exact_cell_fallbacks": sum(case["result"]["runtime_metrics"]["exact_cell_fallbacks"] for case in cases),
    }
    summary["domain_hit_count"] = summary["success_domain_hits"] + summary["failure_domain_hits"]
    summary["domain_hit_rate"] = (
        summary["domain_hit_count"] / summary["cell_queries"]
        if summary["cell_queries"] else None
    )
    artifact = {
        "schema_version": "0.1",
        "status": "PASS" if cases and legal == match else "FAIL",
        "experiment": "layer2-v2-conditional-resource-query-timing",
        "split": args.split,
        "summary": summary,
        "cases": cases,
        "rules": [
            "Q and B are remaining resource coordinates, not source SLAs.",
            "Every unknown cell falls back to the same-information exact kernel.",
            "Success domains are replayable and upward-monotone; exact failure domains are downward-monotone.",
            "QUERY_HARMFUL_NOW is defined by child-frontier infeasibility after executing the real query transition.",
        ],
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": artifact["status"], "summary": summary}, indent=2))
    return 0 if artifact["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
