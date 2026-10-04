#!/usr/bin/env python3
"""Compose task cases with compatible capability and geometry-trace profiles.

Composition is explicit and provenance-preserving. It does not run an oracle
or claim decision hardness.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from capability_contract import validate_capability_profile
from case_contract import validate_case_semantics


class CaseAugmentationError(ValueError):
    pass


def _append_source_ref(case: dict[str, Any], source: Mapping[str, Any]) -> None:
    sid = str(source["source_id"])
    existing = {str(row["source_id"]) for row in case["source_refs"]}
    if sid not in existing:
        case["source_refs"].append(deepcopy(dict(source)))


def _append_capability_rows(
    case: dict[str, Any],
    capability_profile: Mapping[str, Any],
) -> None:
    existing = {str(row["capability_id"]) for row in case["capabilities"]}
    for row in capability_profile["capabilities"]:
        cid = str(row["capability_id"])
        if cid in existing:
            continue
        case["capabilities"].append(
            {
                "capability_id": cid,
                "owner": str(row["owner"]),
                "legal": True,
                "cost_model_ref": None,
                "source_ref_ids": list(row["source_ref_ids"]),
            }
        )


def validate_capability_trace_compatibility(
    capability_profile: Mapping[str, Any],
    trace_profile: Mapping[str, Any],
) -> str:
    validate_capability_profile(capability_profile)
    cap_scope = capability_profile.get("scope", {})
    trace_scope = trace_profile.get("scope", {})
    if not isinstance(cap_scope, Mapping) or not isinstance(trace_scope, Mapping):
        raise CaseAugmentationError("capability/trace scope must be objects")

    cap_family = cap_scope.get("service_family")
    trace_family = trace_scope.get("service_family")
    if not cap_family or not trace_family:
        raise CaseAugmentationError(
            "capability-trace composition requires explicit service_family on both profiles"
        )
    if cap_family != trace_family:
        raise CaseAugmentationError(
            f"incompatible capability/trace service families: {cap_family!r} != {trace_family!r}"
        )
    if trace_profile.get("provenance_class") != "MODEL_DERIVED_TRACE":
        raise CaseAugmentationError("trace must be MODEL_DERIVED_TRACE")
    return str(cap_family)




def validate_task_trace_scope(
    case: Mapping[str, Any],
    trace_profile: Mapping[str, Any],
) -> str:
    world = case.get("world", {})
    if not isinstance(world, Mapping):
        raise CaseAugmentationError("case world must be an object")
    task_scope = world.get("profile_scope", {})
    if not isinstance(task_scope, Mapping):
        raise CaseAugmentationError("case profile_scope must be an object")
    jurisdiction = task_scope.get("jurisdiction")
    trace_scope = trace_profile.get("scope", {})
    if not isinstance(trace_scope, Mapping):
        raise CaseAugmentationError("trace scope must be an object")
    allowed = trace_scope.get("task_jurisdiction_compatible", [])
    if not isinstance(jurisdiction, str) or jurisdiction not in allowed:
        raise CaseAugmentationError(
            f"task/trace jurisdiction mismatch: task={jurisdiction!r}, allowed={allowed!r}"
        )
    site_profile_id = trace_scope.get("site_profile_id")
    if not site_profile_id:
        raise CaseAugmentationError(
            "benchmark trace requires explicit source-grounded site_profile_id"
        )
    return str(site_profile_id)

def augment_db44_with_connecta_geometry(
    case: Mapping[str, Any],
    *,
    capability_profile: Mapping[str, Any],
    trace_profile: Mapping[str, Any],
    trace_payload: Mapping[str, Any],
    elevation_mask_deg: int,
) -> dict[str, Any]:
    if case.get("source_profiles") != ["DB44T2457_2024_warning_reporting"]:
        raise CaseAugmentationError("DB44 augmentation received a non-DB44 case")
    service_family = validate_capability_trace_compatibility(
        capability_profile, trace_profile
    )
    site_profile_id = validate_task_trace_scope(case, trace_profile)
    if service_family != "PLAN_S_CONNECTA_D2S":
        raise CaseAugmentationError(
            f"this augmentation path requires PLAN_S_CONNECTA_D2S, got {service_family}"
        )

    thresholds = trace_payload.get("thresholds")
    if not isinstance(thresholds, Mapping):
        raise CaseAugmentationError("trace artifact lacks thresholds")
    key = str(elevation_mask_deg)
    if key not in thresholds:
        raise CaseAugmentationError(
            f"elevation mask {elevation_mask_deg} missing from trace artifact"
        )
    trace_row = thresholds[key]
    if not isinstance(trace_row, Mapping):
        raise CaseAugmentationError("trace threshold row must be an object")

    out = deepcopy(dict(case))
    cap_id = str(capability_profile["capability_profile_id"])
    trace_id = str(trace_profile["trace_profile_id"])
    out["case_id"] = (
        f"{case['case_id']}::cap={cap_id}::trace={trace_id}::mask={elevation_mask_deg}"
    )
    out["generator"]["version"] = "source-profile-v0.3"
    out["generator"]["parent_case_id"] = str(case["case_id"])
    out["generator"]["trace_refs"] = [trace_id]

    for source in capability_profile["source_refs"]:
        _append_source_ref(out, source)

    input_snapshot = trace_profile["input_snapshots"][0]
    _append_source_ref(
        out,
        {
            "source_id": "CONNECTA_GP_TLE_20260922",
            "source_class": "DATASET_TRACE",
            "directness": "TRACE_ONLY",
            "snapshot_ref": input_snapshot["ref"],
            "locator": "Pinned Connecta GP/TLE snapshot used by SGP4 geometry derivation",
        },
    )

    _append_capability_rows(out, capability_profile)
    constraints = deepcopy(capability_profile["capabilities"][0]["constraints"])
    out["world"]["selected_capability_profile"] = cap_id
    out["world"]["selected_service_family"] = service_family
    out["world"]["selected_site_profile"] = site_profile_id
    out["world"]["selected_path_constraints"] = constraints
    out["world"]["path_geometry"] = {
        "trace_profile_id": trace_id,
        "elevation_mask_deg": elevation_mask_deg,
        "window_count": int(trace_row["windows"]),
        "visible_fraction": float(trace_row["visible_fraction"]),
        "max_gap_min": float(trace_row["max_gap_min"]),
        "windows_key": key,
    }

    cap_refs = list(capability_profile["capabilities"][0]["source_ref_ids"])
    out["variable_provenance"]["selected_capability_profile"] = {
        "class": "SOURCE_RANGE",
        "source_ref_ids": cap_refs,
        "sampling_rule": "explicit compatible capability-profile composition",
        "declared_range": [cap_id],
        "stress_rationale": None,
    }
    out["variable_provenance"]["path_geometry_trace"] = {
        "class": "MODEL_DERIVED_TRACE",
        "source_ref_ids": ["CONNECTA_GP_TLE_20260922"],
        "sampling_rule": f"load threshold {key} from frozen trace profile {trace_id}",
        "declared_range": None,
        "stress_rationale": None,
    }
    out["variable_provenance"]["elevation_mask_deg"] = {
        "class": "CONTROLLED_STRESS",
        "source_ref_ids": [],
        "sampling_rule": "enumerate declared geometry sensitivity masks",
        "declared_range": list(
            trace_profile["variables"]["elevation_mask_deg"]["values"]
        ),
        "stress_rationale": str(
            trace_profile["variables"]["elevation_mask_deg"]["stress_rationale"]
        ),
    }

    regimes = list(out["regime"])
    if "R5_HETEROGENEOUS_PATH" not in regimes:
        regimes.append("R5_HETEROGENEOUS_PATH")
    out["regime"] = regimes

    out["validity"]["notes"] = list(out["validity"].get("notes", [])) + [
        "Attached official Plan-S Connecta D2S module capability profile.",
        "Capability and TLE geometry share explicit PLAN_S_CONNECTA_D2S service_family.",
        "Task jurisdiction and trace site scope are explicitly compatible.",
        "Attached model-derived SGP4 geometry trace; visibility is not measured contact or PHY success.",
        "Elevation mask is CONTROLLED_STRESS because no field terrain skyline is asserted.",
    ]
    out["known_limitations"] = list(out.get("known_limitations", [])) + [
        "Path geometry does not define service/PHY success sequence.",
        "Per-message satellite airtime and pass-level success semantics remain unresolved.",
    ]
    validate_case_semantics(out)
    return out


def augment_db44_universe(
    cases: list[Mapping[str, Any]],
    *,
    capability_profile: Mapping[str, Any],
    trace_profile: Mapping[str, Any],
    trace_payload: Mapping[str, Any],
) -> list[dict[str, Any]]:
    masks = trace_profile["variables"]["elevation_mask_deg"]["values"]
    out: list[dict[str, Any]] = []
    for case in cases:
        if case.get("source_profiles") != ["DB44T2457_2024_warning_reporting"]:
            continue
        for mask in masks:
            out.append(
                augment_db44_with_connecta_geometry(
                    case,
                    capability_profile=capability_profile,
                    trace_profile=trace_profile,
                    trace_payload=trace_payload,
                    elevation_mask_deg=int(mask),
                )
            )
    ids = [str(row["case_id"]) for row in out]
    if len(ids) != len(set(ids)):
        raise CaseAugmentationError("augmentation produced duplicate case ids")
    return out
