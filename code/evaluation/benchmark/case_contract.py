#!/usr/bin/env python3
"""Semantic guards for source-grounded benchmark case artifacts.

This module intentionally does not own task semantics or simulator physics.
It enforces the construction contract around provenance, oracle usage,
validity-filter ordering and held-out split integrity.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

PROVENANCE_CLASSES = {
    "FIXED_BY_SOURCE",
    "SOURCE_RANGE",
    "EMPIRICAL_TRACE",
    "CONTROLLED_STRESS",
    "UNRESOLVED",
}

FILTER_ORDER = (
    "V0_SOURCE_COMPLETE",
    "V1_SOLVABLE",
    "V2_MULTIPLE_LEGAL_OPTIONS",
    "V3_COMMON_SAFE_ACTION",
    "V4_OBSERVATION_RELEVANCE",
    "V5_BINDING_CONSTRAINT",
    "V6_OUTCOME_SEPARATION",
    "V7_OBJECTIVE_DEFINED",
    "V8_SHORTCUT_AUDIT",
    "V9_EVALUATOR_SOUNDNESS",
)

HARD_DISPOSITION_BY_REASON = {
    "SOURCE_GAP": "SOURCE_RESEARCH_QUEUE",
    "OBJECTIVE_AMBIGUOUS": "SOURCE_RESEARCH_QUEUE",
    "SIMULATOR_GAP": "SIMULATOR_GAP",
    "GENERATOR_INVALID": "REJECT_GENERATOR_INVALID",
    "SOURCE_INFEASIBLE": "IMPOSSIBLE_SPLIT",
    "UNIQUE_READY": "CONFORMANCE",
    "COMMON_SAFE_ACTION": "CONFORMANCE",
    "EVALUATOR_INVALID": "REJECT_EVALUATOR_INVALID",
}

RELEASE_STATUSES_REQUIRING_RESOLVED_PROVENANCE = {
    "VALIDITY_PENDING",
    "ADMISSION_READY",
    "BENCHMARK_ADMIT",
    "CONFORMANCE_ONLY",
}

MIN_BENCHMARK_ADMIT_BASELINES = {
    "NO_OP",
    "DETERMINISTIC_SEARCH",
    "FULL_STATE_ORACLE",
}


class CaseContractError(ValueError):
    """Raised when a case violates benchmark-construction semantics."""


def _filters(case: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    validity = case.get("validity")
    if not isinstance(validity, Mapping):
        raise CaseContractError("missing validity object")
    filters = validity.get("filters")
    if not isinstance(filters, list):
        raise CaseContractError("validity.filters must be a list")
    if not all(isinstance(row, Mapping) for row in filters):
        raise CaseContractError("every validity filter result must be an object")
    return filters


def validate_filter_sequence(filters: Sequence[Mapping[str, Any]]) -> None:
    """Require a unique prefix of V0..V9, never reordered or skipped."""

    ids = [row.get("filter_id") for row in filters]
    if len(ids) != len(set(ids)):
        raise CaseContractError(f"duplicate validity filter ids: {ids}")
    expected = list(FILTER_ORDER[: len(ids)])
    if ids != expected:
        raise CaseContractError(
            f"validity filters must be an ordered prefix of V0..V9: got {ids}, expected {expected}"
        )


def first_failed_filter(
    filters: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    for row in filters:
        if not bool(row.get("passed")):
            return row
    return None


def unresolved_variables(case: Mapping[str, Any]) -> list[str]:
    provenance = case.get("variable_provenance")
    if not isinstance(provenance, Mapping):
        raise CaseContractError("variable_provenance must be an object")
    unresolved: list[str] = []
    for name, meta in provenance.items():
        if not isinstance(meta, Mapping):
            raise CaseContractError(f"variable provenance for {name!r} must be an object")
        klass = meta.get("class")
        if klass not in PROVENANCE_CLASSES:
            raise CaseContractError(f"unknown provenance class for {name!r}: {klass!r}")
        if klass == "UNRESOLVED":
            unresolved.append(str(name))
    return unresolved


def validate_oracle_contract(case: Mapping[str, Any]) -> None:
    oracle = case.get("oracle")
    if not isinstance(oracle, Mapping):
        raise CaseContractError("missing oracle object")
    scalarization = bool(oracle.get("scalarization_used"))
    source_ref = oracle.get("scalarization_source_ref")
    if scalarization and not source_ref:
        raise CaseContractError(
            "oracle scalarization requires scalarization_source_ref; arbitrary reward weights are forbidden"
        )
    if not scalarization and source_ref not in (None, ""):
        raise CaseContractError(
            "scalarization_source_ref must be null when scalarization_used=false"
        )


def validate_declared_disposition(case: Mapping[str, Any]) -> None:
    validity = case["validity"]
    filters = _filters(case)
    failed = first_failed_filter(filters)
    if failed is None:
        return
    reason = failed.get("reason_code")
    required = HARD_DISPOSITION_BY_REASON.get(str(reason))
    if required is None:
        return
    actual = validity.get("disposition")
    if actual != required:
        raise CaseContractError(
            f"reason {reason} requires disposition {required}, got {actual}"
        )


def _all_filters_pass(filters: Sequence[Mapping[str, Any]]) -> bool:
    return len(filters) == len(FILTER_ORDER) and all(
        bool(row.get("passed")) for row in filters
    )


def validate_release_gate(case: Mapping[str, Any]) -> None:
    release_status = case.get("release_status")
    unresolved = unresolved_variables(case)
    if (
        release_status in RELEASE_STATUSES_REQUIRING_RESOLVED_PROVENANCE
        and unresolved
    ):
        raise CaseContractError(
            f"{release_status} case contains UNRESOLVED answer-relevant variables: {unresolved}"
        )

    filters = _filters(case)
    validity = case["validity"]
    decision_eligible = bool(validity.get("decision_benchmark_eligible"))

    if decision_eligible and not _all_filters_pass(filters):
        raise CaseContractError(
            "decision_benchmark_eligible requires all V0-V9 filters to pass"
        )

    if release_status == "BENCHMARK_ADMIT":
        if not decision_eligible:
            raise CaseContractError(
                "BENCHMARK_ADMIT requires decision_benchmark_eligible=true"
            )
        if validity.get("disposition") != "DECISION_CANDIDATE":
            raise CaseContractError(
                "BENCHMARK_ADMIT requires DECISION_CANDIDATE disposition"
            )
        oracle = case.get("oracle", {})
        if not oracle.get("solvable"):
            raise CaseContractError("BENCHMARK_ADMIT requires a solvable oracle world")
        baseline_rows = case.get("baseline_audit")
        if not isinstance(baseline_rows, list):
            raise CaseContractError(
                "BENCHMARK_ADMIT requires baseline_audit"
            )
        baseline_classes = {
            row.get("class")
            for row in baseline_rows
            if isinstance(row, Mapping)
        }
        missing = MIN_BENCHMARK_ADMIT_BASELINES - baseline_classes
        if missing:
            raise CaseContractError(
                f"BENCHMARK_ADMIT missing minimum baseline classes: {sorted(missing)}"
            )


def validate_case_semantics(case: Mapping[str, Any]) -> None:
    """Validate benchmark-construction semantics independent of family physics."""

    filters = _filters(case)
    validate_filter_sequence(filters)
    unresolved_variables(case)
    validate_oracle_contract(case)
    validate_declared_disposition(case)
    validate_release_gate(case)


def controlled_stress_fields(case: Mapping[str, Any]) -> list[str]:
    provenance = case.get("variable_provenance", {})
    if not isinstance(provenance, Mapping):
        raise CaseContractError("variable_provenance must be an object")
    return sorted(
        str(name)
        for name, meta in provenance.items()
        if isinstance(meta, Mapping) and meta.get("class") == "CONTROLLED_STRESS"
    )


def assert_heldout_group_disjoint(
    cases: Iterable[Mapping[str, Any]],
    *,
    axes: Sequence[str],
    split_names: Sequence[str] = ("train", "dev", "test"),
) -> None:
    """Reject group leakage across primary train/dev/test partitions.

    For each requested axis, a group id may appear in at most one primary split.
    Cases without that axis are ignored for that axis; the caller decides which
    axes are mandatory for a release.
    """

    owners: dict[tuple[str, str], str] = {}
    for case in cases:
        split = case.get("split")
        if not isinstance(split, Mapping):
            raise CaseContractError("case missing split object")
        split_name = split.get("name")
        if split_name not in split_names:
            continue
        groups = split.get("group_ids")
        if not isinstance(groups, Mapping):
            raise CaseContractError("split.group_ids must be an object")
        for axis in axes:
            group = groups.get(axis)
            if group in (None, ""):
                continue
            key = (axis, str(group))
            previous = owners.get(key)
            if previous is not None and previous != split_name:
                raise CaseContractError(
                    f"held-out leakage: {axis} group {group!r} occurs in {previous} and {split_name}"
                )
            owners[key] = str(split_name)
