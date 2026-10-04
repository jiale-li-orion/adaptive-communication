#!/usr/bin/env python3
"""Resolve source-table/range semantics into concrete benchmark child cases.

This is still pre-oracle.  It may only derive values already encoded by the
source profile and an explicit coverage sampler.  It must not inject stress or
model-dependent hardness.
"""
from __future__ import annotations

from copy import deepcopy
import re
from collections.abc import Mapping
from typing import Any

from case_contract import validate_case_semantics

_WARNING_INDEX = {
    "none_stable": 0,
    "blue": 1,
    "yellow": 2,
    "orange": 3,
    "red": 4,
}

_DURATION = re.compile(r"^(?P<lo>\d+)(?:-(?P<hi>\d+))?(?P<unit>d|h|min)$")
_UNIT_S = {"d": 86400, "h": 3600, "min": 60}


class SourceDerivationError(ValueError):
    pass


def parse_interval_range_s(text: str) -> tuple[int, int]:
    match = _DURATION.match(text)
    if not match:
        raise SourceDerivationError(f"unsupported source cadence {text!r}")
    lo = int(match.group("lo"))
    hi = int(match.group("hi") or lo)
    if hi < lo:
        raise SourceDerivationError(f"invalid source cadence range {text!r}")
    scale = _UNIT_S[match.group("unit")]
    return lo * scale, hi * scale


def db44_reporting_range_s(case: Mapping[str, Any]) -> tuple[int, int]:
    world = case.get("world", {})
    if not isinstance(world, Mapping):
        raise SourceDerivationError("case world must be an object")
    grade = world.get("monitoring_grade")
    warning = world.get("warning_state")
    table = world.get("cadence_table")
    if grade not in {1, 2, 3} or warning not in _WARNING_INDEX:
        raise SourceDerivationError("DB44 case lacks monitoring_grade/warning_state")
    if not isinstance(table, Mapping):
        raise SourceDerivationError("DB44 case lacks cadence_table")
    row = table.get(f"grade{grade}")
    if not isinstance(row, list) or len(row) != 5:
        raise SourceDerivationError("DB44 cadence table row must contain five warning cells")
    return parse_interval_range_s(str(row[_WARNING_INDEX[str(warning)]]))


def _derived_id(parent_id: str, interval_s: int) -> str:
    return f"{parent_id}::report-{interval_s}s"


def expand_db44_reporting_boundaries(case: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Expand one DB44 nominal cell to source-range boundary cases.

    A single-valued cell yields one child.  A range yields lower/upper boundary
    children.  We deliberately do not invent a probability distribution or
    midpoint.
    """

    if case.get("source_profiles") != ["DB44T2457_2024_warning_reporting"]:
        return [deepcopy(dict(case))]

    lo, hi = db44_reporting_range_s(case)
    values = [lo] if lo == hi else [lo, hi]
    out: list[dict[str, Any]] = []
    for interval_s in values:
        child = deepcopy(dict(case))
        child["case_id"] = _derived_id(str(case["case_id"]), interval_s)
        child["generator"]["parent_case_id"] = str(case["case_id"])
        child["generator"]["version"] = "source-profile-v0.2"
        child["world"]["report_interval_s"] = interval_s
        child["variable_provenance"]["report_interval_s"] = {
            "class": "SOURCE_RANGE",
            "source_ref_ids": ["DB44T2457_2024"],
            "sampling_rule": "enumerate source-range lower/upper boundaries; exact cells emit once",
            "declared_range": [lo, hi],
            "stress_rationale": None,
        }
        for obligation in child["obligations"]:
            if obligation["obligation_id"] == "warning_state_reporting":
                obligation["timing_semantics"] = {
                    "kind": "source_reporting_interval",
                    "max_interval_s": interval_s,
                    "source_range_s": [lo, hi],
                }
        child["validity"]["notes"] = list(child["validity"].get("notes", [])) + [
            "DB44 source-table cadence resolved by explicit boundary coverage sampler."
        ]
        validate_case_semantics(child)
        out.append(child)
    return out


def expand_source_ranges(cases: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for case in cases:
        out.extend(expand_db44_reporting_boundaries(case))
    ids = [row["case_id"] for row in out]
    if len(ids) != len(set(ids)):
        raise SourceDerivationError("source derivation produced duplicate case ids")
    return out
