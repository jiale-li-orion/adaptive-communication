#!/usr/bin/env python3
"""Freeze the three-ledger accounting required by cache06.md for Layer-2 v2.

The ledgers are deliberately non-scalar:

1. task-quality ledger: obligation completion and exact minimal resource point;
2. acquisition/communication ledger: actual policy actions on the worst causal
   branch (remote owner queries, terrestrial report sends, satellite sends);
3. planner-compute ledger: expansions, memo hits, L/U work and wall time.

Bytes, airtime and energy remain ``null`` because Layer-1 has no calibrated
source for them.  Action counts are never converted into synthetic energy.
"""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
from typing import Any, Mapping

from compositional_recipe_generator_v0_1 import core_recipes
from dynamic_world_materializer_v0_1 import materialize_recipe
from layer2_v2_future_choice import solve_minimal_resource_v2


ROOT = Path(__file__).resolve().parents[3]
SPLIT = ROOT / "results/benchmark/layer1-structure-aware-split-v0.2-retry-legality.json"
EXACT = ROOT / "results/agentic/layer2-v2-matrix-dev.json"
BASELINES = ROOT / "results/agentic/layer2-v2-baseline-ladder-dev.json"


def _representatives() -> list[dict[str, Any]]:
    frozen = json.loads(SPLIT.read_text(encoding="utf-8"))
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in frozen["rows"]:
        if row.get("candidate_role") == "HARD_PRE_ADMISSION_SURVIVOR" and row.get("split") == "dev":
            grouped[str(row["signature"])].append(row)
    return [min(rows, key=lambda row: str(row["recipe_id"])) for _, rows in sorted(grouped.items())]


def _branch_cost(policy: Mapping[str, Any] | None) -> dict[str, int]:
    if not policy or policy.get("terminal"):
        return {
            "remote_owner_queries": 0,
            "terrestrial_report_sends": 0,
            "satellite_report_sends": 0,
            "wait_actions": 0,
            "total_actions": 0,
        }
    if policy.get("event") == "OBSERVATION":
        rows = [_branch_cost(row["subpolicy"]) for row in policy["children"]]
        keys = (
            "remote_owner_queries",
            "terrestrial_report_sends",
            "satellite_report_sends",
            "wait_actions",
            "total_actions",
        )
        return {key: max((row[key] for row in rows), default=0) for key in keys}
    child = _branch_cost(policy["subpolicy"])
    action = str(policy["action"])
    return {
        "remote_owner_queries": child["remote_owner_queries"] + int(action == "ISSUE_QUERY"),
        "terrestrial_report_sends": child["terrestrial_report_sends"] + int(action == "SEND_TERR"),
        "satellite_report_sends": child["satellite_report_sends"] + int(action == "SEND_SAT"),
        "wait_actions": child["wait_actions"] + int(action == "WAIT"),
        "total_actions": child["total_actions"] + 1,
    }


def _mean(rows: list[float | int]) -> float | None:
    return sum(rows) / len(rows) if rows else None


def main() -> int:
    exact_artifact = json.loads(EXACT.read_text(encoding="utf-8"))
    exact_by_signature = {str(row["signature"]): row["result"]["exact"] for row in exact_artifact["rows"]}
    baseline_artifact = json.loads(BASELINES.read_text(encoding="utf-8"))
    baseline_by_signature = {str(row["signature"]): row["baselines"] for row in baseline_artifact["cases"]}
    recipes = {row.recipe_id: row for row in core_recipes()}

    cases = []
    for index, rep in enumerate(_representatives(), 1):
        signature = str(rep["signature"])
        bundle = materialize_recipe(recipes[str(rep["recipe_id"])])
        solved = solve_minimal_resource_v2(bundle, upper_mode="all_recursive")
        if solved["solvable"] is not True:
            raise AssertionError(f"v2 unexpectedly unsolved on {signature}")
        exact_point = exact_by_signature[signature]["minimal_resource_point"]
        if solved["minimal_resource_point"] != exact_point:
            raise AssertionError(f"resource-point mismatch on {signature}")
        acquisition = _branch_cost(solved["policy"])
        aggregate_compute = solved["aggregate_metrics"]
        winning_compute = solved["winning_metrics"]
        cases.append(
            {
                "signature": signature,
                "recipe_id": rep["recipe_id"],
                "task_quality": {
                    "all_obligations_completed": True,
                    "obligation_count": len(bundle["obligations"]),
                    "minimal_resource_point": solved["minimal_resource_point"],
                    "matches_generic_exact_minimal_resource_point": True,
                },
                "acquisition_communication": {
                    **acquisition,
                    "gateway_local_reads": 0,
                    "passive_ack_acquisition_cost": 0,
                    "bytes": None,
                    "airtime": None,
                    "energy": None,
                    "uncalibrated_fields": ["bytes", "airtime", "energy"],
                },
                "planner_compute": {
                    "winning_resource_cell": winning_compute,
                    "minimal_resource_sweep": aggregate_compute,
                },
                "baseline_context": baseline_by_signature.get(signature, {}),
            }
        )
        print(
            index,
            signature[:12],
            "point",
            solved["minimal_resource_point"],
            "query/sat/actions",
            acquisition["remote_owner_queries"],
            acquisition["satellite_report_sends"],
            acquisition["total_actions"],
            flush=True,
        )

    query_counts = [row["acquisition_communication"]["remote_owner_queries"] for row in cases]
    terr_counts = [row["acquisition_communication"]["terrestrial_report_sends"] for row in cases]
    sat_counts = [row["acquisition_communication"]["satellite_report_sends"] for row in cases]
    action_counts = [row["acquisition_communication"]["total_actions"] for row in cases]
    winning_expanded = [row["planner_compute"]["winning_resource_cell"]["expanded"] for row in cases]
    winning_wall = [row["planner_compute"]["winning_resource_cell"]["wall_s"] for row in cases]
    sweep_expanded = [row["planner_compute"]["minimal_resource_sweep"]["expanded"] for row in cases]
    sweep_wall = [row["planner_compute"]["minimal_resource_sweep"]["wall_s"] for row in cases]
    summary = {
        "signature_count": len(cases),
        "task_quality": {
            "success_count": sum(row["task_quality"]["all_obligations_completed"] for row in cases),
            "exact_resource_point_match_count": sum(
                row["task_quality"]["matches_generic_exact_minimal_resource_point"] for row in cases
            ),
        },
        "acquisition_communication": {
            "total_remote_owner_queries_worst_branch_sum": sum(query_counts),
            "mean_remote_owner_queries_worst_branch": _mean(query_counts),
            "total_terrestrial_report_sends_worst_branch_sum": sum(terr_counts),
            "mean_terrestrial_report_sends_worst_branch": _mean(terr_counts),
            "total_satellite_report_sends_worst_branch_sum": sum(sat_counts),
            "mean_satellite_report_sends_worst_branch": _mean(sat_counts),
            "mean_total_actions_worst_branch": _mean(action_counts),
            "bytes_airtime_energy_calibrated": False,
        },
        "planner_compute": {
            "winning_cell_expanded_sum": sum(winning_expanded),
            "winning_cell_wall_s_sum": sum(winning_wall),
            "mean_winning_cell_expanded": _mean(winning_expanded),
            "mean_winning_cell_wall_s": _mean(winning_wall),
            "resource_sweep_expanded_sum": sum(sweep_expanded),
            "resource_sweep_wall_s_sum": sum(sweep_wall),
        },
    }
    artifact = {
        "schema_version": "0.1",
        "status": "PASS",
        "experiment": "layer2-v2-three-ledger-accounting-dev",
        "summary": summary,
        "rules": [
            "Task quality, acquisition/communication and planner compute remain separate ledgers; no scalar reward is introduced.",
            "Remote query and send counts are actual worst-branch policy actions, not API-field counts.",
            "Passive ACK has zero additional acquisition cost but remains part of causal observation semantics.",
            "Bytes, airtime and energy remain unknown because the benchmark has no calibrated source for them.",
            "Planner compute reports both winning-resource-cell cost and the whole minimal-resource sweep.",
        ],
        "cases": cases,
    }
    out = ROOT / "results/agentic/layer2-v2-three-ledgers-dev.json"
    out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": artifact["status"], "summary": summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
