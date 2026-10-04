#!/usr/bin/env python3
"""Semantic guards for Layer-1 communication capability profiles."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


class CapabilityContractError(ValueError):
    pass


def unresolved_answer_fields(profile: Mapping[str, Any]) -> list[str]:
    variables = profile.get("variables")
    if not isinstance(variables, Mapping):
        raise CapabilityContractError("variables must be an object")
    return sorted(
        str(name)
        for name, spec in variables.items()
        if isinstance(spec, Mapping)
        and spec.get("provenance_class") == "UNRESOLVED"
        and bool(spec.get("answer_relevant"))
    )


def validate_capability_profile(profile: Mapping[str, Any]) -> None:
    refs = profile.get("source_refs")
    if not isinstance(refs, list) or not refs:
        raise CapabilityContractError("source_refs must be non-empty")
    ids = {str(row.get("source_id")) for row in refs if isinstance(row, Mapping)}
    if len(ids) != len(refs) or "" in ids:
        raise CapabilityContractError("source_refs require unique source_id values")

    capabilities = profile.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        raise CapabilityContractError("capabilities must be non-empty")
    for cap in capabilities:
        if not isinstance(cap, Mapping):
            raise CapabilityContractError("capability must be an object")
        missing = set(map(str, cap.get("source_ref_ids", []))) - ids
        if missing:
            raise CapabilityContractError(
                f"capability {cap.get('capability_id')!r} references unknown sources {sorted(missing)}"
            )

    status = profile.get("oracle_status")
    unresolved = unresolved_answer_fields(profile)
    if status == "READY_FOR_COMPATIBILITY" and unresolved:
        raise CapabilityContractError(
            f"READY_FOR_COMPATIBILITY has answer-relevant unresolved fields: {unresolved}"
        )
    if status == "PARTIAL_SOURCE_GAP" and not unresolved:
        raise CapabilityContractError(
            "PARTIAL_SOURCE_GAP requires at least one answer-relevant unresolved field"
        )


def validate_capability_registry(profiles: Sequence[Mapping[str, Any]]) -> None:
    seen: set[str] = set()
    for profile in profiles:
        validate_capability_profile(profile)
        pid = profile.get("capability_profile_id")
        if not isinstance(pid, str) or not pid:
            raise CapabilityContractError("capability_profile_id must be non-empty")
        if pid in seen:
            raise CapabilityContractError(f"duplicate capability_profile_id {pid!r}")
        seen.add(pid)
