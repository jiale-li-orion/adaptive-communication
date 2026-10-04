#!/usr/bin/env python3
"""Semantic guards for normalized benchmark source profiles."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

PROVENANCE_CLASSES = {
    "FIXED_BY_SOURCE",
    "SOURCE_RANGE",
    "EMPIRICAL_TRACE",
    "MODEL_DERIVED_TRACE",
    "CONTROLLED_STRESS",
    "UNRESOLVED",
}

DIRECT_TASK_AUTHORITY = "DIRECT_TASK_AUTHORITY"
ADJACENT_DIRECTNESS = {"ADJACENT_MECHANISM", "TRACE_ONLY"}


class SourceProfileContractError(ValueError):
    """Raised when a source profile violates corpus-first generation rules."""


def _source_index(profile: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    refs = profile.get("source_refs")
    if not isinstance(refs, list) or not refs:
        raise SourceProfileContractError("source_refs must be a non-empty list")
    out: dict[str, Mapping[str, Any]] = {}
    for row in refs:
        if not isinstance(row, Mapping):
            raise SourceProfileContractError("source_refs entries must be objects")
        sid = row.get("source_id")
        if not isinstance(sid, str) or not sid:
            raise SourceProfileContractError("every source_ref needs source_id")
        if sid in out:
            raise SourceProfileContractError(f"duplicate source_id {sid!r}")
        out[sid] = row
    return out


def _validate_variable(name: str, spec: Mapping[str, Any], source_ids: set[str]) -> None:
    klass = spec.get("provenance_class")
    if klass not in PROVENANCE_CLASSES:
        raise SourceProfileContractError(
            f"variable {name!r} has unknown provenance_class {klass!r}"
        )
    refs = spec.get("source_ref_ids")
    if not isinstance(refs, list):
        raise SourceProfileContractError(f"variable {name!r} source_ref_ids must be a list")
    missing = set(map(str, refs)) - source_ids
    if missing:
        raise SourceProfileContractError(
            f"variable {name!r} references unknown sources {sorted(missing)}"
        )

    if klass == "FIXED_BY_SOURCE" and "value" not in spec:
        raise SourceProfileContractError(
            f"FIXED_BY_SOURCE variable {name!r} requires value"
        )
    if klass == "SOURCE_RANGE" and "range" not in spec:
        raise SourceProfileContractError(
            f"SOURCE_RANGE variable {name!r} requires range"
        )
    if klass in {"EMPIRICAL_TRACE", "MODEL_DERIVED_TRACE"} and not spec.get("trace_ref"):
        raise SourceProfileContractError(
            f"{klass} variable {name!r} requires trace_ref"
        )
    if klass == "CONTROLLED_STRESS" and not spec.get("stress_rationale"):
        raise SourceProfileContractError(
            f"CONTROLLED_STRESS variable {name!r} requires stress_rationale"
        )
    if klass == "UNRESOLVED" and not spec.get("unresolved_reason"):
        raise SourceProfileContractError(
            f"UNRESOLVED variable {name!r} requires unresolved_reason"
        )


def answer_relevant_unresolved(profile: Mapping[str, Any]) -> list[str]:
    variables = profile.get("variables")
    if not isinstance(variables, Mapping):
        raise SourceProfileContractError("variables must be an object")
    return sorted(
        str(name)
        for name, spec in variables.items()
        if isinstance(spec, Mapping)
        and spec.get("provenance_class") == "UNRESOLVED"
        and bool(spec.get("answer_relevant"))
    )


def _validate_obligations(
    profile: Mapping[str, Any],
    sources: Mapping[str, Mapping[str, Any]],
) -> None:
    obligations = profile.get("obligation_templates")
    if not isinstance(obligations, list):
        raise SourceProfileContractError("obligation_templates must be a list")
    for row in obligations:
        if not isinstance(row, Mapping):
            raise SourceProfileContractError("obligation_templates entries must be objects")
        tid = row.get("template_id")
        refs = row.get("task_authority_source_ref_ids")
        if not isinstance(refs, list) or not refs:
            raise SourceProfileContractError(
                f"obligation {tid!r} requires task_authority_source_ref_ids"
            )
        for sid in refs:
            source = sources.get(str(sid))
            if source is None:
                raise SourceProfileContractError(
                    f"obligation {tid!r} references unknown task-authority source {sid!r}"
                )
            if source.get("directness") != DIRECT_TASK_AUTHORITY:
                raise SourceProfileContractError(
                    f"obligation {tid!r} uses {sid!r} as task authority, "
                    f"but directness={source.get('directness')!r}"
                )


def _validate_capabilities(
    profile: Mapping[str, Any],
    source_ids: set[str],
) -> None:
    capabilities = profile.get("capabilities")
    if not isinstance(capabilities, list):
        raise SourceProfileContractError("capabilities must be a list")
    for row in capabilities:
        if not isinstance(row, Mapping):
            raise SourceProfileContractError("capability entries must be objects")
        cid = row.get("capability_id")
        refs = row.get("source_ref_ids")
        if not isinstance(refs, list) or not refs:
            raise SourceProfileContractError(
                f"capability {cid!r} requires source_ref_ids"
            )
        missing = set(map(str, refs)) - source_ids
        if missing:
            raise SourceProfileContractError(
                f"capability {cid!r} references unknown sources {sorted(missing)}"
            )


def validate_source_profile(profile: Mapping[str, Any]) -> None:
    """Validate a normalized source profile independent of simulator code."""

    sources = _source_index(profile)
    source_ids = set(sources)

    variables = profile.get("variables")
    if not isinstance(variables, Mapping):
        raise SourceProfileContractError("variables must be an object")
    for name, spec in variables.items():
        if not isinstance(spec, Mapping):
            raise SourceProfileContractError(
                f"variable {name!r} must be an object"
            )
        _validate_variable(str(name), spec, source_ids)

    _validate_obligations(profile, sources)
    _validate_capabilities(profile, source_ids)

    status = profile.get("generator_status")
    obligations = profile.get("obligation_templates", [])
    unresolved = answer_relevant_unresolved(profile)

    if status == "READY":
        if not obligations:
            raise SourceProfileContractError(
                "READY profile requires at least one obligation template"
            )
        if unresolved:
            raise SourceProfileContractError(
                f"READY profile has answer-relevant UNRESOLVED variables: {unresolved}"
            )
        direct_task_sources = [
            src
            for src in sources.values()
            if src.get("directness") == DIRECT_TASK_AUTHORITY
        ]
        if not direct_task_sources:
            raise SourceProfileContractError(
                "READY profile requires a DIRECT_TASK_AUTHORITY source"
            )

    if status == "ADJACENT_ONLY":
        if obligations:
            raise SourceProfileContractError(
                "ADJACENT_ONLY profile cannot own obligation templates"
            )
        non_adjacent = [
            sid
            for sid, src in sources.items()
            if src.get("directness") not in ADJACENT_DIRECTNESS
        ]
        if non_adjacent:
            raise SourceProfileContractError(
                f"ADJACENT_ONLY profile contains non-adjacent source refs: {non_adjacent}"
            )


def validate_source_profile_registry(
    profiles: Sequence[Mapping[str, Any]],
) -> None:
    """Validate uniqueness and every profile's semantic contract."""

    ids: set[str] = set()
    for profile in profiles:
        validate_source_profile(profile)
        pid = profile.get("profile_id")
        if not isinstance(pid, str) or not pid:
            raise SourceProfileContractError("profile_id must be a non-empty string")
        if pid in ids:
            raise SourceProfileContractError(f"duplicate profile_id {pid!r}")
        ids.add(pid)
