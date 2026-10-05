#!/usr/bin/env python3
"""Machine pre-audit for the 23-item Q11 human/source review package.

This script never promotes Q11 to PASS.  It only precomputes consistency checks
and evidence pointers so a human reviewer can focus on semantic/source judgment.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from causal_evidence_process_v0_1 import attach_causal_evidence, validate_causal_process
from compositional_recipe_generator_v0_1 import _db44_resolved_cases, core_recipes
from dynamic_world_materializer_v0_1 import iter_world_bundles, validate_world_bundle
from exact_reference_oracle_v0_1 import hindsight_bundle_reference
from execution_trace_evaluator_v0_1 import evaluate_execution_trace, witness_to_execution_trace


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
R = ROOT / "results/benchmark"
B = ROOT / "research/benchmark"
EXACT_RECIPE = ROOT / "local_research/current/benchmark/generated/exact-labels-v0.1/recipe-labels.jsonl"
VALIDITY_RECIPE = ROOT / "local_research/current/benchmark/generated/v0-v7-full-v0.1/recipe-validity.jsonl"
V8_SIG = ROOT / "local_research/current/benchmark/generated/v8-all-pass-v0.1/signature-v8.jsonl"


def _jsonl_index(path: Path, key: str) -> dict[str, dict[str, Any]]:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            out[str(row[key])] = row
    return out


def _check(name: str, passed: bool, detail: Any) -> dict[str, Any]:
    return {"check": name, "passed": bool(passed), "detail": detail}


def _role_expectation(role: str) -> dict[str, Any]:
    table = {
        "EASY_CONFORMANCE_CONTROL": {
            "exact": "NO_PAID_QUERY_REQUIRED",
            "v0v7": None,
            "v8": None,
        },
        "NEGATIVE_SHORTCUT_REGRESSION_CONTROL": {
            "exact": "NO_PAID_QUERY_REQUIRED",
            "v0v7": None,
            "v8": None,
        },
        "NEGATIVE_PHYSICAL_INVALID_CONTROL": {
            "exact": "MIXED_WORLD_SOLVABILITY",
            "v0v7": "V1_PHYSICAL_INVALID",
            "v8": None,
        },
        "INFORMATION_INFEASIBLE_DIAGNOSTIC": {
            "exact": "INFORMATION_INFEASIBLE",
            "v0v7": "INFORMATION_INFEASIBLE_DIAGNOSTIC",
            "v8": None,
        },
        "HARD_PRE_ADMISSION_SURVIVOR": {
            "exact": "PAID_EVIDENCE_REQUIRED",
            "v0v7": "V0_V7_PASS",
            "v8": "SURVIVES_V8_LADDER_V0_1",
        },
    }
    return table[role]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--audit', type=Path, default=R / 'layer1-human-source-audit-v0.1.json')
    ap.add_argument('--split', type=Path, default=R / 'layer1-structure-aware-split-v0.1.json')
    ap.add_argument('--exact-recipe', type=Path, default=EXACT_RECIPE)
    ap.add_argument('--validity-recipe', type=Path, default=VALIDITY_RECIPE)
    ap.add_argument('--v8-signature', type=Path, default=V8_SIG)
    args = ap.parse_args()

    def resolve(path: Path) -> Path:
        return path if path.is_absolute() else ROOT / path

    audit_path = resolve(args.audit)
    split_path = resolve(args.split)
    exact_path = resolve(args.exact_recipe)
    validity_path = resolve(args.validity_recipe)
    v8_path = resolve(args.v8_signature)

    human = json.loads(audit_path.read_text(encoding="utf-8"))
    split = json.loads(split_path.read_text(encoding="utf-8"))
    split_by_recipe = {str(r["recipe_id"]): r for r in split["rows"]}
    recipe_by_id = {r.recipe_id: r for r in core_recipes()}
    task_cases = {str(x["case_id"]): x for x in _db44_resolved_cases()}
    profiles = {
        str(x["profile_id"]): x
        for x in json.loads((B / "profiles/v0.1/SOURCE-PROFILE-REGISTRY.v0.1.json").read_text(encoding="utf-8"))["profiles"]
    }
    exact = _jsonl_index(exact_path, "recipe_id")
    validity = _jsonl_index(validity_path, "recipe_id")
    v8 = _jsonl_index(v8_path, "signature")
    wanted = {str(x["recipe_id"]) for x in human["samples"]}
    bundles = {}
    for b in iter_world_bundles():
        rid = str(b["recipe_id"])
        if rid in wanted:
            bundles[rid] = b
            if len(bundles) == len(wanted):
                break

    rendered = []
    all_machine_pass = True
    for sample in human["samples"]:
        rid = str(sample["recipe_id"])
        recipe = recipe_by_id[rid]
        bundle = bundles[rid]
        process = attach_causal_evidence(bundle)
        split_row = split_by_recipe[rid]
        erow = exact[rid]
        vrow = validity[rid]
        sig = str(erow["signature"])
        v8row = v8.get(sig)
        task = task_cases[recipe.task_case_id]
        expectation = _role_expectation(str(sample["candidate_role"]))

        source_checks = []
        source_checks.append(_check(
            "sample_source_profiles_match_recipe",
            sorted(sample["source_profiles"]) == sorted(recipe.source_profiles),
            {"sample": sample["source_profiles"], "recipe": list(recipe.source_profiles)},
        ))
        source_checks.append(_check(
            "all_declared_profiles_exist_and_include_T1",
            all(p in profiles and "T1" in profiles[p].get("families", []) for p in recipe.source_profiles),
            {
                p: {
                    "generator_status": profiles[p]["generator_status"],
                    "source_refs": profiles[p]["source_refs"],
                    "unknowns": profiles[p].get("unknowns", []),
                }
                for p in recipe.source_profiles
            },
        ))
        source_checks.append(_check(
            "task_contract_matches_DB44_source_expansion",
            int(task["world"]["report_interval_s"]) == recipe.report_interval_s
            and int(task["world"]["monitoring_grade"]) == recipe.monitoring_grade
            and str(task["world"]["warning_state"]) == recipe.warning_state,
            {
                "recipe": {
                    "report_interval_s": recipe.report_interval_s,
                    "monitoring_grade": recipe.monitoring_grade,
                    "warning_state": recipe.warning_state,
                },
                "source_expansion": task["world"],
                "variable_provenance": task.get("variable_provenance", {}),
            },
        ))
        source_checks.append(_check(
            "sampled_axes_have_no_UNRESOLVED_provenance",
            all(str(v.get("class")) != "UNRESOLVED" for v in recipe.variable_provenance.values()),
            recipe.variable_provenance,
        ))

        authority_checks = []
        try:
            validate_world_bundle(bundle)
            world_valid = True
            world_error = None
        except Exception as exc:
            world_valid = False
            world_error = repr(exc)
        try:
            validate_causal_process(bundle, process)
            process_valid = True
            process_error = None
        except Exception as exc:
            process_valid = False
            process_error = repr(exc)
        authority_checks.append(_check("world_bundle_validator", world_valid, world_error or "PASS"))
        authority_checks.append(_check("causal_process_validator", process_valid, process_error or "PASS"))
        authority_checks.append(_check(
            "source_owned_deadline_exactly_release_plus_interval",
            all(int(o["deadline_s"]) == int(o["release_s"]) + int(o["source_interval_s"]) for o in bundle["obligations"]),
            [
                {
                    "obligation_id": o["obligation_id"],
                    "release_s": o["release_s"],
                    "deadline_s": o["deadline_s"],
                    "source_interval_s": o["source_interval_s"],
                }
                for o in bundle["obligations"]
            ],
        ))
        authority_checks.append(_check(
            "public_satellite_geometry_not_hidden",
            not any("satellite" in str(x).lower() for x in bundle["observation_projection"].get("hidden_fields", [])),
            bundle["observation_projection"],
        ))
        authority_checks.append(_check(
            "unresolved_reconnect_priority_preserved_not_filled",
            bundle.get("recovery", {}).get("unresolved_field") in {None, "reconnect_backlog_priority"},
            bundle.get("recovery", {}),
        ))

        task_checks = []
        task_checks.append(_check(
            "T1_family_identity",
            recipe.family == "T1_MONITORING_INFORMATION_CONTINUITY"
            and all(str(x).startswith("T1.") for x in recipe.task_surface_ids),
            {"family": recipe.family, "task_surface_ids": list(recipe.task_surface_ids)},
        ))
        task_checks.append(_check(
            "task_case_identity_matches_sample_and_split",
            sample["task_case_id"] == recipe.task_case_id == split_row["task_case_id"],
            {"sample": sample["task_case_id"], "recipe": recipe.task_case_id, "split": split_row["task_case_id"]},
        ))
        task_checks.append(_check(
            "split_role_identity_matches_sample",
            sample["candidate_role"] == split_row["candidate_role"] and sample["split"] == split_row["split"],
            {"sample_role": sample["candidate_role"], "split_role": split_row["candidate_role"], "sample_split": sample["split"], "frozen_split": split_row["split"]},
        ))

        oracle_checks = []
        oracle_checks.append(_check(
            "exact_classification_matches_role_expectation",
            expectation["exact"] == erow["classification"],
            {"expected": expectation["exact"], "actual": erow["classification"]},
        ))
        if expectation["v0v7"] is not None:
            oracle_checks.append(_check(
                "V0_V7_disposition_matches_role_expectation",
                expectation["v0v7"] == vrow["v0_v7_disposition"],
                {"expected": expectation["v0v7"], "actual": vrow["v0_v7_disposition"]},
            ))
        if expectation["v8"] is not None:
            oracle_checks.append(_check(
                "V8_disposition_matches_hard_survivor",
                v8row is not None and expectation["v8"] == v8row["v8_disposition"],
                {"expected": expectation["v8"], "actual": None if v8row is None else v8row["v8_disposition"]},
            ))
        physical = hindsight_bundle_reference(bundle)
        if erow["classification"] == "MIXED_WORLD_SOLVABILITY":
            oracle_checks.append(_check(
                "mixed_physical_support_has_both_solvable_and_infeasible_worlds",
                bool(physical["any_world_solvable"]) and not bool(physical["all_worlds_solvable"]),
                {"all_worlds_solvable": physical["all_worlds_solvable"], "any_world_solvable": physical["any_world_solvable"]},
            ))
        else:
            oracle_checks.append(_check(
                "all_physical_worlds_solvable_for_nonphysical-invalid_role",
                bool(physical["all_worlds_solvable"]),
                {"all_worlds_solvable": physical["all_worlds_solvable"], "any_world_solvable": physical["any_world_solvable"]},
            ))

        evaluator_checks = []
        replayed = 0
        replay_failures = []
        first_trace = None
        first_wid = None
        for wr in physical["worlds"]:
            if not wr["solvable"] or not wr.get("witness"):
                continue
            trace = witness_to_execution_trace(bundle, wr["witness"])
            result = evaluate_execution_trace(bundle, world_id=str(wr["world_id"]), actions=trace)
            replayed += 1
            if not result["success"]:
                replay_failures.append({"world_id": wr["world_id"], "reason": result})
            if first_trace is None:
                first_trace = trace
                first_wid = str(wr["world_id"])
        evaluator_checks.append(_check(
            "all_solvable_physical_witnesses_replay_successfully",
            replayed > 0 and not replay_failures,
            {"replayed_world_count": replayed, "failures": replay_failures},
        ))
        if first_trace is not None and first_wid is not None:
            no_op = evaluate_execution_trace(bundle, world_id=first_wid, actions=[])
            evaluator_checks.append(_check(
                "no_op_cannot_claim_success",
                not no_op["success"],
                no_op,
            ))
            mutated = deepcopy(first_trace)
            mutated[0]["actor"] = "unauthorized-controller"
            bad = evaluate_execution_trace(bundle, world_id=first_wid, actions=mutated)
            evaluator_checks.append(_check(
                "authority_mutation_rejected",
                not bad["success"] and bad["reason_code"] == "AUTHORITY_VIOLATION",
                bad,
            ))

        groups = {
            "source_extraction_semantics": source_checks,
            "authority_priority_time_semantics": authority_checks,
            "task_family_identity": task_checks,
            "oracle_success_set": oracle_checks,
            "evaluator_trace": evaluator_checks,
        }
        group_status = {
            name: "MACHINE_PASS" if all(x["passed"] for x in checks) else "MACHINE_FAIL"
            for name, checks in groups.items()
        }
        machine_pass = all(x == "MACHINE_PASS" for x in group_status.values())
        all_machine_pass = all_machine_pass and machine_pass
        rendered.append({
            "sample_id": sample["sample_id"],
            "recipe_id": rid,
            "candidate_role": sample["candidate_role"],
            "split": sample["split"],
            "machine_status": "MACHINE_PASS" if machine_pass else "MACHINE_FAIL",
            "group_status": group_status,
            "checks": groups,
            "human_review_remains_required": True,
        })

    artifact = {
        "schema_version": "0.1",
        "status": "MACHINE_PREAUDIT_COMPLETE" if all_machine_pass else "MACHINE_PREAUDIT_HAS_FAILURES",
        "audit_ref": str(audit_path.relative_to(ROOT)),
        "split_ref": str(split_path.relative_to(ROOT)),
        "exact_recipe_ref": str(exact_path.relative_to(ROOT)),
        "validity_recipe_ref": str(validity_path.relative_to(ROOT)),
        "v8_signature_ref": str(v8_path.relative_to(ROOT)),
        "sample_count": len(rendered),
        "machine_pass_count": sum(x["machine_status"] == "MACHINE_PASS" for x in rendered),
        "machine_fail_count": sum(x["machine_status"] == "MACHINE_FAIL" for x in rendered),
        "q11_status": "BLOCKED_PENDING_HUMAN_REVIEW",
        "rule": "Machine consistency checks reduce reviewer burden but cannot set Q11 PASS or fill reviewer identity.",
        "samples": rendered,
    }
    print(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
