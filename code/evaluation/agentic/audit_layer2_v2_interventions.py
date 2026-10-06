#!/usr/bin/env python3
"""Controlled mechanism interventions for Layer-2 v2 hard-dev cases.

The benchmark/generator remains frozen.  Every intervention is applied only to
a deep-copied evaluation bundle or to a temporary exact-oracle timing constant
and is reported as a diagnostic counterfactual, never as a new benchmark case.

The audit separates causes that *remove* the information problem from tempting
but insufficient explanations such as ACK latency alone or deadline length
alone.  This implements cache06.md mechanism gate 9.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from collections import defaultdict
import json
from pathlib import Path
from typing import Any

import causal_evidence_process_v0_1 as evidence_module
import exact_reference_oracle_v0_1 as exact_module
from causal_evidence_process_v0_1 import (
    FINAL_ACK_DELAY_S,
    attach_causal_evidence,
)
from compositional_recipe_generator_v0_1 import core_recipes
from dynamic_world_materializer_v0_1 import materialize_recipe


ROOT = Path(__file__).resolve().parents[3]
SPLIT = ROOT / "results/benchmark/layer1-structure-aware-split-v0.2-retry-legality.json"


def _representatives() -> list[dict[str, Any]]:
    frozen = json.loads(SPLIT.read_text(encoding="utf-8"))
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in frozen["rows"]:
        if (
            row.get("candidate_role") == "HARD_PRE_ADMISSION_SURVIVOR"
            and row.get("split") == "dev"
        ):
            grouped[str(row["signature"])].append(row)
    return [min(rows, key=lambda row: str(row["recipe_id"])) for _, rows in sorted(grouped.items())]


def _solve(
    bundle: dict[str, Any],
    *,
    no_paid_query: bool = False,
    full_current: bool = False,
) -> dict[str, Any]:
    result = exact_module.solve_observation_matched(
        bundle,
        attach_causal_evidence(bundle),
        disable_paid_query=no_paid_query,
        force_full_current_state=full_current,
        max_memo_nodes=500_000,
    )
    return {
        "status": result["status"],
        "solvable": result["solvable"],
        "memo_nodes": int(result["memo_nodes"]),
    }


def _relax_satellite_budget_only(bundle: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(bundle)
    out["public_environment"]["satellite_budget_units"] = len(out["obligations"])
    return out


def _remove_backup_scarcity(bundle: dict[str, Any]) -> dict[str, Any]:
    """Remove global backup-budget and public backup-window capacity scarcity."""

    out = _relax_satellite_budget_only(bundle)
    capacity = len(out["obligations"])
    for window in out["public_environment"]["satellite_windows"]:
        window["capacity_units"] = max(int(window["capacity_units"]), capacity)
    return out


def _relax_deadlines_only(bundle: dict[str, Any]) -> dict[str, Any]:
    """Remove deadline pressure without inventing any new communication opportunity."""

    out = deepcopy(bundle)
    last_end = max(
        [
            int(window["end_s"])
            for world in out["worlds"]
            for window in world["terrestrial_windows"]
        ]
        + [
            int(window["end_s"])
            for window in out["public_environment"]["satellite_windows"]
        ]
    )
    relaxed = last_end + max(
        int(evidence_module.FINAL_ACK_DELAY_S),
        int(evidence_module.SATELLITE_COMPLETION_DELAY_S),
    ) + 1
    for obligation in out["obligations"]:
        obligation["deadline_s"] = max(int(obligation["deadline_s"]), relaxed)
    return out


def _add_common_late_recovery(bundle: dict[str, Any]) -> dict[str, Any]:
    """Remove finite-window urgency via one late common terrestrial recovery.

    This diagnostic deliberately changes both the availability process and the
    deadlines so the added common opportunity is actually usable.  It is not a
    source-backed deployment claim; it tests whether the frozen hard structure
    depends on crossing finite opportunities rather than deadline syntax alone.
    """

    out = deepcopy(bundle)
    capacity = len(out["obligations"])
    last_end = max(
        [
            int(window["end_s"])
            for world in out["worlds"]
            for window in world["terrestrial_windows"]
        ]
        + [
            int(window["end_s"])
            for window in out["public_environment"]["satellite_windows"]
        ]
    )
    start = last_end + 60
    end = start + 3600
    for world in out["worlds"]:
        world["terrestrial_windows"].append(
            {
                "window_id": "INTERVENTION_COMMON_LATE_RECOVERY",
                "start_s": start,
                "end_s": end,
                "capacity_units": capacity,
            }
        )
    for obligation in out["obligations"]:
        obligation["deadline_s"] = max(
            int(obligation["deadline_s"]),
            start + int(FINAL_ACK_DELAY_S) + 1,
        )
    return out


def _instant_execution_feedback_no_query(bundle: dict[str, Any]) -> dict[str, Any]:
    """Counterfactual: normal-send receipt/final ACK/negative feedback is instant.

    Dedicated query delay is intentionally unchanged.  Constants are restored
    before returning so this diagnostic cannot leak into another case/run.
    """

    names = ("GATEWAY_RECEIPT_DELAY_S", "FINAL_ACK_DELAY_S", "ACK_TIMEOUT_S")
    old_exact = {name: getattr(exact_module, name) for name in names}
    old_evidence = {name: getattr(evidence_module, name) for name in names}
    try:
        for name in names:
            setattr(exact_module, name, 0)
            setattr(evidence_module, name, 0)
        result = exact_module.solve_observation_matched(
            bundle,
            evidence_module.attach_causal_evidence(bundle),
            disable_paid_query=True,
            max_memo_nodes=500_000,
        )
        return {
            "status": result["status"],
            "solvable": result["solvable"],
            "memo_nodes": int(result["memo_nodes"]),
        }
    finally:
        for name, value in old_exact.items():
            setattr(exact_module, name, value)
        for name, value in old_evidence.items():
            setattr(evidence_module, name, value)


def _case(bundle: dict[str, Any]) -> dict[str, Any]:
    rows = {
        "original_exact": _solve(bundle),
        "original_no_paid_query": _solve(bundle, no_paid_query=True),
        "satellite_budget_only_relaxed_no_query": _solve(
            _relax_satellite_budget_only(bundle), no_paid_query=True
        ),
        "backup_scarcity_removed_no_query": _solve(
            _remove_backup_scarcity(bundle), no_paid_query=True
        ),
        "perfect_current_observation_no_query": _solve(
            bundle, no_paid_query=True, full_current=True
        ),
        "instant_execution_feedback_no_query": _instant_execution_feedback_no_query(bundle),
        "deadlines_only_relaxed_no_query": _solve(
            _relax_deadlines_only(bundle), no_paid_query=True
        ),
        "common_late_recovery_no_query": _solve(
            _add_common_late_recovery(bundle), no_paid_query=True
        ),
    }
    if any(row["status"] != "EXACT" for row in rows.values()):
        raise RuntimeError("intervention audit hit exact search limit")
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    reps = _representatives()
    recipes = {row.recipe_id: row for row in core_recipes()}
    cases = []
    for index, rep in enumerate(reps, 1):
        result = _case(materialize_recipe(recipes[str(rep["recipe_id"])]))
        cases.append(
            {
                "signature": rep["signature"],
                "recipe_id": rep["recipe_id"],
                "interventions": result,
            }
        )
        print(
            index,
            str(rep["signature"])[:12],
            {name: bool(row["solvable"]) for name, row in result.items()},
            flush=True,
        )

    names = list(cases[0]["interventions"]) if cases else []
    success = {
        name: sum(bool(case["interventions"][name]["solvable"]) for case in cases)
        for name in names
    }
    mean_memo = {
        name: (
            sum(case["interventions"][name]["memo_nodes"] for case in cases) / len(cases)
            if cases
            else None
        )
        for name in names
    }
    expected = {
        "base_information_gap_present": success.get("original_no_paid_query") == 0,
        "perfect_current_information_removes_gap": success.get(
            "perfect_current_observation_no_query"
        ) == len(cases),
        "removing_backup_scarcity_removes_gap": success.get(
            "backup_scarcity_removed_no_query"
        ) == len(cases),
        "late_common_recovery_removes_gap": success.get(
            "common_late_recovery_no_query"
        ) == len(cases),
        "budget_only_relaxation_has_directional_effect": success.get(
            "satellite_budget_only_relaxed_no_query", 0
        ) > success.get("original_no_paid_query", 0),
    }
    passed = bool(cases) and all(expected.values())
    artifact = {
        "schema_version": "0.1",
        "status": "PASS" if passed else "FAIL",
        "experiment": "layer2-v2-controlled-mechanism-interventions-dev",
        "scope": "diagnostic counterfactuals on frozen hard-dev bundles; generator/test unchanged",
        "summary": {
            "signature_count": len(cases),
            "success_count": success,
            "mean_exact_memo_nodes": mean_memo,
            "registered_directional_checks": expected,
            "negative_intervention_findings": {
                "instant_execution_feedback_no_query_success_count": success.get(
                    "instant_execution_feedback_no_query", 0
                ),
                "deadlines_only_relaxed_no_query_success_count": success.get(
                    "deadlines_only_relaxed_no_query", 0
                ),
            },
        },
        "interpretation": [
            "Perfect current information removes the paid-query information gap without revealing future transitions.",
            "Removing both global satellite budget scarcity and backup-window capacity scarcity removes the no-query gap; relaxing only the budget helps only a subset, so capacity/opportunity coupling also matters.",
            "Adding a common late terrestrial recovery opportunity plus usable deadlines removes the gap, tying hardness to finite crossing opportunity structure rather than deadline syntax alone.",
            "Instant execution ACK/negative feedback alone does not make no-query policies feasible on this dev set; irreversible opportunity commitment, not ACK latency alone, remains causal.",
            "Extending deadlines without adding a future service opportunity also does not remove the information gap; deadline length alone is not the source of hardness.",
        ],
        "rules": [
            "Every intervention is evaluator-only and applied to a deep copy or temporary restored timing constant.",
            "No intervention modifies the frozen Layer-1 generator, split, source grounding or final test.",
            "A negative intervention is retained as a mechanism boundary rather than forced into a positive result.",
            "Bytes/airtime/energy are not inferred by these counterfactuals.",
        ],
        "cases": cases,
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps({"status": artifact["status"], "summary": artifact["summary"]}, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
