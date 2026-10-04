#!/usr/bin/env python3
"""Preflight Layer-1 cases before full-state oracle solving.

The preflight never invents defaults.  It answers whether a source-resolved
case has enough task, environment, and capability semantics to enter V1.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any


class OraclePreflightError(ValueError):
    pass


def _profile_id(case: Mapping[str, Any]) -> str:
    profiles = case.get("source_profiles")
    if not isinstance(profiles, list) or len(profiles) != 1:
        raise OraclePreflightError("preflight currently requires one source profile")
    return str(profiles[0])


def preflight_case(
    case: Mapping[str, Any],
    *,
    mapping: Mapping[str, Any],
    capability_profiles: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    pid = _profile_id(case)
    family = str(case.get("family"))

    if family == "T2_WARNING_DELIVERY_RESPONSE_HANDOFF":
        return {
            "case_id": case["case_id"],
            "family": family,
            "source_profile": pid,
            "mapping_disposition": "SIMULATOR_GAP",
            "oracle_ready": False,
            "compatible_capability_profiles": [],
            "blocking_fields": [
                "actor_chain_runtime",
                "recipient_reachability",
                "delivery_attempt_duration_or_trace",
                "acknowledgement_transition",
                "response_handoff_transition",
            ],
            "notes": [
                "T2 source obligation is valid, but current sensor communication substrate lacks the actor/authority delivery state machine."
            ],
        }

    if family != "T1_MONITORING_INFORMATION_CONTINUITY":
        raise OraclePreflightError(f"unknown family {family!r}")

    profile_map = mapping.get("profiles", {})
    if not isinstance(profile_map, Mapping) or pid not in profile_map:
        raise OraclePreflightError(f"missing simulator mapping for profile {pid!r}")
    row = profile_map[pid]
    disposition = str(row.get("disposition"))

    if disposition == "SUPPORT_ONLY":
        return {
            "case_id": case["case_id"],
            "family": family,
            "source_profile": pid,
            "mapping_disposition": disposition,
            "oracle_ready": False,
            "compatible_capability_profiles": [],
            "blocking_fields": [str(row.get("blocking_gap"))],
            "notes": [
                "Source profile is retained for capability/conformance coverage but does not independently define timed decision-hard communication."
            ],
        }

    compatible: list[str] = []
    for cap in capability_profiles:
        status = cap.get("oracle_status")
        scope = cap.get("scope", {})
        if status != "READY_FOR_COMPATIBILITY" or not isinstance(scope, Mapping):
            continue
        if scope.get("domain") == "geohazard monitoring data communication":
            compatible.append(str(cap["capability_profile_id"]))

    blockers: list[str] = []
    world = case.get("world", {})
    if not isinstance(world, Mapping):
        raise OraclePreflightError("case world must be object")
    if "report_interval_s" not in world:
        blockers.append("report_interval_s")

    if "selected_capability_profile" not in world:
        blockers.append("selected_capability_profile")

    path_geometry = world.get("path_geometry")
    if not isinstance(path_geometry, Mapping):
        blockers.append("path_opportunity_trace")
    else:
        # Geometry is enough to define when a satellite can be considered as a
        # candidate opportunity, but not whether service/PHY delivery succeeds.
        if not path_geometry.get("trace_profile_id"):
            blockers.append("path_opportunity_trace")

    # Payload size/class and service semantics are explicit oracle inputs.
    # They may be source-derived or controlled-stress, but never implicit.
    if "report_payload_bytes" not in world and "report_payload_profile" not in world:
        blockers.append("report_payload_bytes_or_source_payload_class")
    if "path_service_success_semantics" not in world:
        blockers.append("path_service_success_semantics")

    return {
        "case_id": case["case_id"],
        "family": family,
        "source_profile": pid,
        "mapping_disposition": disposition,
        "oracle_ready": not blockers,
        "compatible_capability_profiles": sorted(compatible),
        "blocking_fields": blockers,
        "notes": [
            "Compatible capability profiles are candidates only; they are not silently attached to the task case.",
            "Task/capability/geometry composition can clear selection/opportunity blockers, but payload and service-success semantics remain explicit until source/stress provenance is supplied.",
        ],
    }


def preflight_universe(
    cases: Sequence[Mapping[str, Any]],
    *,
    mapping: Mapping[str, Any],
    capability_profiles: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [
        preflight_case(
            deepcopy(dict(case)),
            mapping=mapping,
            capability_profiles=capability_profiles,
        )
        for case in cases
    ]
