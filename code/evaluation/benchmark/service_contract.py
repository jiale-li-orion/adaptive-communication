#!/usr/bin/env python3
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


class ServiceContractError(ValueError):
    pass


def validate_service_profile(profile: Mapping[str, Any]) -> None:
    if profile.get("schema_version") != "0.1":
        raise ServiceContractError("unsupported service profile schema")
    if profile.get("provenance_class") != "CONTROLLED_STRESS":
        raise ServiceContractError("current service profiles must be CONTROLLED_STRESS")
    if not profile.get("stress_rationale"):
        raise ServiceContractError("controlled service profile requires stress_rationale")
    boundaries = profile.get("claim_boundary")
    if not isinstance(boundaries, list) or not boundaries:
        raise ServiceContractError("service profile requires claim_boundary")
    if profile.get("service_trace_profile_id") == "GEOMETRY_UPPER_ENVELOPE_V0":
        rule = str(profile.get("service_rule"))
        if "geometry window succeeds" not in rule:
            raise ServiceContractError("upper-envelope rule drifted")


def validate_service_registry(profiles: Sequence[Mapping[str, Any]]) -> None:
    seen: set[str] = set()
    for p in profiles:
        validate_service_profile(p)
        pid = p.get("service_trace_profile_id")
        if not isinstance(pid, str) or not pid or pid in seen:
            raise ServiceContractError("service_trace_profile_id missing/duplicate")
        seen.add(pid)
