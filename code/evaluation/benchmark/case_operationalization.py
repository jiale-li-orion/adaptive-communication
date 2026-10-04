#!/usr/bin/env python3
"""Attach explicit payload and service-sanity semantics to augmented Layer-1 worlds."""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from case_contract import validate_case_semantics
from payload_contract import validate_payload_profile
from service_contract import validate_service_profile


class CaseOperationalizationError(ValueError):
    pass


def operationalize_upper_envelope(
    case: Mapping[str, Any],
    *,
    payload_profile: Mapping[str, Any],
    service_profile: Mapping[str, Any],
) -> dict[str, Any]:
    validate_payload_profile(payload_profile)
    validate_service_profile(service_profile)

    world = case.get("world", {})
    if not isinstance(world, Mapping):
        raise CaseOperationalizationError("case world must be object")
    constraints = world.get("selected_path_constraints", {})
    if not isinstance(constraints, Mapping):
        raise CaseOperationalizationError("selected_path_constraints required")

    max_payload = constraints.get("max_payload_bytes")
    payload_bytes = payload_profile.get("encoded_bytes")
    if not isinstance(max_payload, int) or not isinstance(payload_bytes, int):
        raise CaseOperationalizationError("integer payload limits required")
    if payload_bytes > max_payload:
        raise CaseOperationalizationError(
            f"payload {payload_bytes} B exceeds selected path maximum {max_payload} B"
        )

    out = deepcopy(dict(case))
    out["generator"]["version"] = "source-profile-v0.4"
    out["world"]["report_payload_profile"] = str(payload_profile["payload_profile_id"])
    out["world"]["report_payload_bytes"] = payload_bytes
    out["world"]["path_service_success_semantics"] = str(
        service_profile["service_trace_profile_id"]
    )
    out["world"]["service_rule"] = str(service_profile["service_rule"])

    # Payload source is an independent national communication-format example,
    # not task authority. Keep it separate in provenance.
    for source in payload_profile["source_refs"]:
        sid = str(source["source_id"])
        if sid not in {str(x["source_id"]) for x in out["source_refs"]}:
            out["source_refs"].append(deepcopy(dict(source)))

    out["variable_provenance"]["report_payload_bytes"] = {
        "class": "FIXED_BY_SOURCE",
        "source_ref_ids": [str(x["source_id"]) for x in payload_profile["source_refs"]],
        "sampling_rule": "exact standard Type-1 single-sensor example payload",
        "declared_range": None,
        "stress_rationale": None,
    }
    out["variable_provenance"]["path_service_success_semantics"] = {
        "class": "CONTROLLED_STRESS",
        "source_ref_ids": [],
        "sampling_rule": "attach named upper-envelope service sanity profile",
        "declared_range": [str(service_profile["service_trace_profile_id"])],
        "stress_rationale": str(service_profile["stress_rationale"]),
    }
    out["known_limitations"] = list(out.get("known_limitations", [])) + [
        "32 B payload is one exact DZ/T 0450 Type-1 standard example, not a report-size distribution.",
        "GEOMETRY_UPPER_ENVELOPE_V0 is a controlled V1 solvability sanity track, not measured reliability.",
    ]
    validate_case_semantics(out)
    return out
