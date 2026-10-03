#!/usr/bin/env python3
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from case_contract import (  # noqa: E402
    CaseContractError,
    FILTER_ORDER,
    assert_heldout_group_disjoint,
    controlled_stress_fields,
    validate_case_semantics,
)


def base_case() -> dict:
    filters = [
        {"filter_id": fid, "passed": True, "reason_code": "PASS", "evidence_ref": None}
        for fid in FILTER_ORDER
    ]
    return {
        "schema_version": "0.1",
        "case_id": "T1-demo",
        "family": "T1_MONITORING_INFORMATION_CONTINUITY",
        "source_profiles": ["demo"],
        "source_refs": [],
        "generator": {"version": "dev", "seed": 0, "world_template_id": "demo"},
        "regime": ["R1_WARNING_ESCALATION"],
        "hardness": ["H1_PARTIAL_OBSERVATION"],
        "world": {},
        "variable_provenance": {
            "cadence": {
                "class": "FIXED_BY_SOURCE",
                "source_ref_ids": ["s1"],
                "sampling_rule": None,
                "declared_range": None,
                "stress_rationale": None,
            }
        },
        "obligations": [],
        "authority": {
            "actors": ["device"],
            "legal_action_owners": {},
            "invariants": [],
        },
        "capabilities": [],
        "observation": {
            "visible_state": {},
            "hidden_fields": [],
            "alias_world_ids": [],
            "projection_provenance": "FULL_OBSERVATION",
        },
        "oracle": {
            "solver_version": "dev",
            "mode": "FULL_STATE_FEASIBILITY",
            "solvable": True,
            "feasible_success_plan_count": 2,
            "valid_terminal_state_count": 2,
            "scalarization_used": False,
            "scalarization_source_ref": None,
        },
        "validity": {
            "filters": filters,
            "decision_benchmark_eligible": True,
            "disposition": "DECISION_CANDIDATE",
        },
        "baseline_audit": [
            {"baseline_id": "noop", "class": "NO_OP", "success": False},
            {
                "baseline_id": "search",
                "class": "DETERMINISTIC_SEARCH",
                "success": True,
            },
            {
                "baseline_id": "oracle",
                "class": "FULL_STATE_ORACLE",
                "success": True,
            },
        ],
        "split": {
            "name": "train",
            "heldout_axes": ["JURISDICTION"],
            "group_ids": {"JURISDICTION": "A"},
        },
        "release_status": "BENCHMARK_ADMIT",
    }


def expect_error(case: dict, contains: str) -> None:
    try:
        validate_case_semantics(case)
    except CaseContractError as exc:
        assert contains in str(exc), (contains, str(exc))
        return
    raise AssertionError(f"expected CaseContractError containing {contains!r}")


def main() -> int:
    case = base_case()
    validate_case_semantics(case)

    unresolved = deepcopy(case)
    unresolved["variable_provenance"]["cadence"]["class"] = "UNRESOLVED"
    expect_error(unresolved, "UNRESOLVED")

    scalarized = deepcopy(case)
    scalarized["oracle"]["scalarization_used"] = True
    scalarized["oracle"]["scalarization_source_ref"] = None
    expect_error(scalarized, "scalarization_source_ref")

    reordered = deepcopy(case)
    reordered["validity"]["filters"][2], reordered["validity"]["filters"][3] = (
        reordered["validity"]["filters"][3],
        reordered["validity"]["filters"][2],
    )
    expect_error(reordered, "ordered prefix")

    unique = deepcopy(case)
    unique["release_status"] = "CONFORMANCE_ONLY"
    unique["validity"]["decision_benchmark_eligible"] = False
    unique["validity"]["filters"] = unique["validity"]["filters"][:3]
    unique["validity"]["filters"][2] = {
        "filter_id": "V2_MULTIPLE_LEGAL_OPTIONS",
        "passed": False,
        "reason_code": "UNIQUE_READY",
        "evidence_ref": "oracle://unique",
    }
    unique["validity"]["disposition"] = "CONFORMANCE"
    validate_case_semantics(unique)

    wrong_unique = deepcopy(unique)
    wrong_unique["validity"]["disposition"] = "DECISION_CANDIDATE"
    expect_error(wrong_unique, "requires disposition CONFORMANCE")

    stress = deepcopy(case)
    stress["variable_provenance"]["outage"] = {
        "class": "CONTROLLED_STRESS",
        "source_ref_ids": ["stress-envelope-v1"],
        "sampling_rule": "fixed boundary cell",
        "declared_range": None,
        "stress_rationale": "failure coverage",
    }
    assert controlled_stress_fields(stress) == ["outage"]

    train = deepcopy(case)
    train["case_id"] = "train-a"
    train["split"]["name"] = "train"
    train["split"]["group_ids"] = {"JURISDICTION": "A"}
    test = deepcopy(case)
    test["case_id"] = "test-b"
    test["split"]["name"] = "test"
    test["split"]["group_ids"] = {"JURISDICTION": "B"}
    assert_heldout_group_disjoint([train, test], axes=("JURISDICTION",))

    leaked = deepcopy(test)
    leaked["split"]["group_ids"] = {"JURISDICTION": "A"}
    try:
        assert_heldout_group_disjoint([train, leaked], axes=("JURISDICTION",))
    except CaseContractError as exc:
        assert "held-out leakage" in str(exc)
    else:
        raise AssertionError("expected held-out leakage to fail")

    print(
        "PASS benchmark case contract: provenance/oracle/filter/disposition/release/split guards"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
