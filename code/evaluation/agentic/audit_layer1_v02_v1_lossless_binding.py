#!/usr/bin/env python3
"""Audit the thin Layer-1 v0.2 -> Layer-2 v1 evaluation binding.

The audit traverses every reachable decision boundary of one exact
minimal-resource policy tree for each of the 41 frozen hard signatures.  At
each boundary, candidate invocations must round-trip exactly to the benchmark's
legal action surface.  Serialized binding artifacts must not contain hidden
world IDs or terrestrial future-window tables.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path

from causal_evidence_process_v0_1 import attach_causal_evidence
from compositional_recipe_generator_v0_1 import core_recipes
from dynamic_world_materializer_v0_1 import materialize_recipe
from exact_reference_oracle_v0_1 import LocalState, _attempt_lattice
from layer1_v02_exact_continuation import ExactContinuationReference, replay_continuation_policy
from layer1_v02_v1_binding import (
    action_from_invocation,
    candidate_context_from_boundary,
    task_contract_from_bundle,
)
from v8_policy_baselines_v0_1 import _legal_actions, _normalize_one, _step


ROOT = Path(__file__).resolve().parents[3]
SPLIT = ROOT / "results/benchmark/layer1-structure-aware-split-v0.2-retry-legality.json"


def _hard_representatives() -> list[dict]:
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in split["rows"]:
        if row.get("candidate_role") == "HARD_PRE_ADMISSION_SURVIVOR":
            grouped[str(row["signature"])].append(row)
    return [min(rows, key=lambda x: str(x["recipe_id"])) for _, rows in sorted(grouped.items())]


def _initial(bundle: dict, sat_budget: int) -> dict[str, LocalState]:
    return {
        str(w["world_id"]): LocalState(satellite_budget=sat_budget)
        for w in bundle["worlds"]
    }


def _minimal_policy(bundle: dict) -> tuple[int, int, dict]:
    start = min(_attempt_lattice(bundle))
    for q in range(len(bundle["obligations"]) + 1):
        for b in range(int(bundle["public_environment"]["satellite_budget_units"]) + 1):
            result = ExactContinuationReference(bundle).solve(start, _initial(bundle, b), query_budget=q)
            if result["solvable"] is True:
                replay_continuation_policy(
                    bundle,
                    at_s=start,
                    states=_initial(bundle, b),
                    policy=result["policy"],
                    query_budget=q,
                )
                return q, b, result
    raise RuntimeError(bundle["recipe_id"])


FORBIDDEN_KEYS = {
    "world_id",
    "world_ids",
    "worlds",
    "terrestrial_windows",
    "oracle_witness",
    "recommended_action",
    "exact_label",
    "exact_classification",
}


def _forbidden_paths(value: object, prefix: str = "$") -> list[str]:
    out: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}"
            if str(key) in FORBIDDEN_KEYS:
                out.append(path)
            out.extend(_forbidden_paths(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            out.extend(_forbidden_paths(child, f"{prefix}[{index}]"))
    return out


def _audit_case(bundle: dict) -> dict:
    task = task_contract_from_bundle(bundle)
    bound_obligations = task.desired_state["obligations"]
    source_obligations = json.loads(json.dumps([dict(row) for row in bundle["obligations"]], ensure_ascii=False))
    obligation_lossless = bound_obligations == source_obligations
    task_forbidden_paths = _forbidden_paths(task.model_dump(mode="json"))

    q, b, solved = _minimal_policy(bundle)
    process = attach_causal_evidence(bundle)
    boundary_count = 0
    action_count = 0
    mismatches = []
    forbidden_contexts = 0
    forbidden_context_paths: list[dict] = []

    def visit(at_s: int, states: dict[str, LocalState], node: dict, qleft: int) -> None:
        nonlocal boundary_count, action_count, forbidden_contexts
        branches = _normalize_one(bundle, process, at_s, states)
        if len(branches) != 1 or next(iter(branches)) != "same":
            assert node.get("event") == "OBSERVATION"
            by_obs = {str(row["observation"]): row for row in node["children"]}
            assert set(by_obs) == set(branches)
            for obs, child in branches.items():
                visit(at_s, child, by_obs[obs]["subpolicy"], qleft)
            return

        states = next(iter(branches.values()))
        if node.get("terminal"):
            return
        boundary_count += 1
        legal = _legal_actions(bundle, process, states, at_s)
        context = candidate_context_from_boundary(bundle, at_s=at_s, states=states)
        bad_paths = _forbidden_paths(context)
        if bad_paths:
            forbidden_contexts += 1
            forbidden_context_paths.append({"time_s": at_s, "paths": bad_paths})
        decoded = [
            action_from_invocation(plan["invocations"][0])
            for plan in context["candidate_plans"]
        ]
        action_count += len(decoded)
        if decoded != legal:
            mismatches.append(
                {
                    "time_s": at_s,
                    "expected": legal,
                    "decoded": decoded,
                }
            )

        action = (str(node["action"]), node.get("arg"))
        stepped = _step(bundle, process, states, at_s, action)
        assert stepped is not None
        child, next_t = stepped
        visit(next_t, child, node["subpolicy"], qleft - int(action[0] == "ISSUE_QUERY"))

    visit(min(_attempt_lattice(bundle)), _initial(bundle, b), solved["policy"], q)
    passed = obligation_lossless and not task_forbidden_paths and forbidden_contexts == 0 and not mismatches
    return {
        "passed": passed,
        "minimal_query_budget": q,
        "minimal_satellite_budget": b,
        "obligation_contract_lossless": obligation_lossless,
        "task_contract_forbidden_hidden_paths": task_forbidden_paths,
        "candidate_context_forbidden_hidden_field_count": forbidden_contexts,
        "candidate_context_forbidden_hidden_paths": forbidden_context_paths,
        "decision_boundary_count": boundary_count,
        "candidate_action_count": action_count,
        "action_roundtrip_mismatch_count": len(mismatches),
        "mismatches": mismatches,
    }


def main() -> int:
    recipes = {r.recipe_id: r for r in core_recipes()}
    rows = []
    for rep in _hard_representatives():
        bundle = materialize_recipe(recipes[str(rep["recipe_id"])])
        result = _audit_case(bundle)
        rows.append(
            {
                "signature": rep["signature"],
                "split": rep["split"],
                "recipe_id": rep["recipe_id"],
                "result": result,
            }
        )

    summary = {
        "signature_count": len(rows),
        "pass_count": sum(row["result"]["passed"] for row in rows),
        "fail_count": sum(not row["result"]["passed"] for row in rows),
        "split_counts": dict(sorted(Counter(row["split"] for row in rows).items())),
        "decision_boundary_count": sum(row["result"]["decision_boundary_count"] for row in rows),
        "candidate_action_count": sum(row["result"]["candidate_action_count"] for row in rows),
        "action_roundtrip_mismatch_count": sum(
            row["result"]["action_roundtrip_mismatch_count"] for row in rows
        ),
        "forbidden_hidden_field_count": sum(
            row["result"]["candidate_context_forbidden_hidden_field_count"]
            + len(row["result"]["task_contract_forbidden_hidden_paths"])
            for row in rows
        ),
    }
    passed = len(rows) == 41 and summary["pass_count"] == 41
    artifact = {
        "schema_version": "0.1",
        "status": "PASS" if passed else "FAIL",
        "classification": "B_COMPATIBILITY_GAP_CLOSED_BY_THIN_LOSSLESS_BINDING",
        "summary": summary,
        "rules": [
            "TaskContract preserves every source-grounded obligation record exactly.",
            "Candidate plans encode only the benchmark-defined legal action surface and remain conditional; no future-feasibility label is introduced.",
            "Every typed invocation round-trips to the exact Layer-1 legal action at every reached policy boundary.",
            "Serialized binding artifacts expose no world IDs, hidden terrestrial future-window tables, oracle labels or recommended actions.",
        ],
        "claim_boundary": "This closes evaluation compatibility only. It does not make frozen Layer-2 v1 decision semantics correct on Layer-1 v0.2.",
        "rows": rows,
    }
    print(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
