#!/usr/bin/env python3
"""Expand source-defined profile ranges into nominal generator coordinates.

This stage deliberately stops before simulator/world instantiation.  It expands
only SOURCE_RANGE variables from READY profiles and carries FIXED_BY_SOURCE
values verbatim. EMPIRICAL_TRACE, MODEL_DERIVED_TRACE and CONTROLLED_STRESS are attached later by
the case generator; answer-relevant UNRESOLVED values block expansion.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from itertools import product
from typing import Any

from profile_contract import (
    SourceProfileContractError,
    answer_relevant_unresolved,
    validate_source_profile,
)


def _range_values(name: str, spec: Mapping[str, Any]) -> list[Any]:
    values = spec.get("range")
    if not isinstance(values, list) or not values:
        raise SourceProfileContractError(
            f"SOURCE_RANGE variable {name!r} must expose a non-empty discrete list "
            "before nominal expansion; continuous/source-table sampling needs an explicit sampler"
        )
    return list(values)


def expand_nominal_profile(profile: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return source-derived base coordinates for one READY source profile."""

    validate_source_profile(profile)
    if profile.get("generator_status") != "READY":
        raise SourceProfileContractError(
            f"profile {profile.get('profile_id')!r} is not READY"
        )
    unresolved = answer_relevant_unresolved(profile)
    if unresolved:
        raise SourceProfileContractError(
            f"cannot expand answer-relevant UNRESOLVED fields: {unresolved}"
        )

    fixed: dict[str, Any] = {}
    ranged: list[tuple[str, list[Any]]] = []
    contextual_ranges: dict[str, list[Any]] = {}
    variables = profile.get("variables", {})
    if not isinstance(variables, Mapping):
        raise SourceProfileContractError("variables must be an object")

    for name, spec in variables.items():
        if not isinstance(spec, Mapping):
            raise SourceProfileContractError(f"variable {name!r} must be an object")
        klass = spec.get("provenance_class")
        if klass == "FIXED_BY_SOURCE":
            fixed[str(name)] = spec.get("value")
        elif klass == "SOURCE_RANGE":
            values = _range_values(str(name), spec)
            if bool(spec.get("answer_relevant")):
                ranged.append((str(name), values))
            else:
                # Keep the full source-allowed set as context.  Do not multiply
                # nominal cases by a variable declared irrelevant to the answer.
                contextual_ranges[str(name)] = values
        elif klass in {"EMPIRICAL_TRACE", "MODEL_DERIVED_TRACE", "CONTROLLED_STRESS"}:
            # These are attached at later generator stages and must not inflate
            # the nominal source-derived coordinate count.
            continue
        elif klass == "UNRESOLVED":
            # Only answer-irrelevant unresolved values can survive READY
            # validation; omit them from the nominal world.
            continue
        else:
            raise SourceProfileContractError(
                f"unknown provenance class for {name!r}: {klass!r}"
            )

    ranged.sort(key=lambda item: item[0])
    names = [name for name, _ in ranged]
    domains = [values for _, values in ranged]
    assignments = product(*domains) if domains else [()]

    rows: list[dict[str, Any]] = []
    for index, values in enumerate(assignments):
        selected = dict(fixed)
        selected.update(dict(zip(names, values, strict=True)))
        rows.append(
            {
                "profile_id": profile["profile_id"],
                "families": list(profile["families"]),
                "coordinate_index": index,
                "source_range_assignment": {
                    name: selected[name] for name in names
                },
                "fixed_by_source": dict(fixed),
                "contextual_source_ranges": dict(contextual_ranges),
                "heldout_groups": dict(profile.get("heldout_groups", {})),
            }
        )
    return rows


def expand_ready_registry(
    profiles: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Expand every READY profile, excluding PARTIAL/SIMULATOR/ADJACENT profiles."""

    rows: list[dict[str, Any]] = []
    for profile in profiles:
        if profile.get("generator_status") != "READY":
            continue
        rows.extend(expand_nominal_profile(profile))
    return rows
