#!/usr/bin/env python3
"""Thin v0.7 binding to the validated Layer-1 exact oracle adapter.

v0.7 changes only the generated terrestrial process-support sets and the
minimum-release-stage admission rule. Case-level evidence/timing/resource
semantics remain identical to v0.6, so the downstream exact adapter must not
fork. This module only validates the frozen v0.7 schema then delegates to the
shared adapter implementation.
"""
from __future__ import annotations

from typing import Any, Mapping

from layer1_v06_oracle_adapter import (
    causal_process_from_v06,
    solve_v06_references,
    world_bundle_from_v06,
)


def _assert_v07(base: Mapping[str, Any], case: Mapping[str, Any]) -> None:
    if str(base.get("schema_version")) != "0.7":
        raise ValueError(f"expected v0.7 base schema, got {base.get('schema_version')!r}")
    if str(case.get("schema_version")) != "0.7":
        raise ValueError(f"expected v0.7 case schema, got {case.get('schema_version')!r}")
    if str(case.get("base_id")) != str(base.get("base_id")):
        raise ValueError("v0.7 case/base mismatch")


def world_bundle_from_v07(base: Mapping[str, Any], case: Mapping[str, Any]) -> dict[str, Any]:
    _assert_v07(base, case)
    return world_bundle_from_v06(base, case)


def causal_process_from_v07(base: Mapping[str, Any], case: Mapping[str, Any]) -> dict[str, Any]:
    _assert_v07(base, case)
    return causal_process_from_v06(base, case)


def solve_v07_references(
    base: Mapping[str, Any],
    case: Mapping[str, Any],
    *,
    max_memo_nodes: int = 200_000,
) -> dict[str, Any]:
    _assert_v07(base, case)
    result = solve_v06_references(base, case, max_memo_nodes=max_memo_nodes)
    result["oracle_binding"] = "V07_THIN_BINDING_TO_SHARED_RECEIPT_SUMMARY_EXACT_KERNEL"
    return result

