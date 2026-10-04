#!/usr/bin/env python3
"""Compile READY source profiles into nominal, pre-oracle benchmark cases.

This stage is intentionally conservative:
- it expands only source-defined nominal coordinates;
- it does not invent outages, hidden state, resource scarcity, or rewards;
- every generated case is H0 / VALIDITY_PENDING until later generator stages
  add source-backed or declared stress structure and run V1-V9.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from collections.abc import Iterable, Mapping
from typing import Any

from case_contract import validate_case_semantics
from profile_contract import validate_source_profile
from profile_expansion import expand_nominal_profile


FAMILY_IDS = {
    "T1": "T1_MONITORING_INFORMATION_CONTINUITY",
    "T2": "T2_WARNING_DELIVERY_RESPONSE_HANDOFF",
}


class CaseGenerationError(ValueError):
    """Raised when a source profile cannot be compiled without inventing semantics."""


def _canonical_digest(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()[:12]


def _world_from_coordinate(
    profile: Mapping[str, Any],
    coordinate: Mapping[str, Any],
) -> dict[str, Any]:
    world: dict[str, Any] = {}
    fixed = coordinate.get("fixed_by_source", {})
    ranged = coordinate.get("source_range_assignment", {})
    contextual = coordinate.get("contextual_source_ranges", {})
    if (
        not isinstance(fixed, Mapping)
        or not isinstance(ranged, Mapping)
        or not isinstance(contextual, Mapping)
    ):
        raise CaseGenerationError("coordinate fixed/ranged/contextual assignments must be mappings")
    world.update(deepcopy(dict(fixed)))
    world.update(deepcopy(dict(ranged)))
    world.update(deepcopy(dict(contextual)))
    world["profile_scope"] = deepcopy(profile.get("scope", {}))
    return world


def _provenance_map(
    profile: Mapping[str, Any],
    coordinate: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    variables = profile.get("variables", {})
    if not isinstance(variables, Mapping):
        raise CaseGenerationError("profile variables must be an object")
    selected = {
        **dict(coordinate.get("fixed_by_source", {})),
        **dict(coordinate.get("source_range_assignment", {})),
        **dict(coordinate.get("contextual_source_ranges", {})),
    }
    out: dict[str, dict[str, Any]] = {}
    for name, raw in variables.items():
        if not isinstance(raw, Mapping):
            raise CaseGenerationError(f"variable {name!r} must be an object")
        klass = raw.get("provenance_class")
        if klass not in {"FIXED_BY_SOURCE", "SOURCE_RANGE"}:
            # Nominal expansion deliberately excludes traces/stress/unresolved.
            continue
        if name not in selected:
            raise CaseGenerationError(f"expanded variable {name!r} missing selected value")
        out[str(name)] = {
            "class": klass,
            "source_ref_ids": list(raw.get("source_ref_ids", [])),
            "sampling_rule": raw.get("sampling_rule"),
            "declared_range": deepcopy(raw.get("range")) if klass == "SOURCE_RANGE" else None,
            "stress_rationale": None,
        }
    return out


def _trigger_is_active(trigger: Mapping[str, Any], world: Mapping[str, Any]) -> bool:
    field = trigger.get("field")
    if field is None:
        return True
    if field not in world:
        # A trigger can be resolved later by a family runtime event.  At nominal
        # compilation time keep it rather than silently deleting an obligation.
        return True
    if "equals" in trigger:
        return world.get(field) == trigger.get("equals")
    return True


def _instantiate_obligations(
    profile: Mapping[str, Any],
    world: Mapping[str, Any],
) -> list[dict[str, Any]]:
    templates = profile.get("obligation_templates", [])
    if not isinstance(templates, list):
        raise CaseGenerationError("obligation_templates must be a list")
    obligations: list[dict[str, Any]] = []
    for template in templates:
        if not isinstance(template, Mapping):
            raise CaseGenerationError("obligation template must be an object")
        trigger = template.get("trigger", {})
        if not isinstance(trigger, Mapping):
            raise CaseGenerationError("obligation trigger must be an object")
        if not _trigger_is_active(trigger, world):
            continue
        obligations.append(
            {
                "obligation_id": str(template["template_id"]),
                "protected_subject": str(template["protected_subject"]),
                "release": deepcopy(dict(trigger)),
                "completion_predicate": deepcopy(template["completion_predicate"]),
                "timing_semantics": deepcopy(template["timing_semantics"]),
                "authority_owner": str(template["authority_owner"]),
                "source_priority": template.get("source_priority"),
                "expiration_rule": deepcopy(template.get("expiration_rule")),
                "source_ref_ids": list(template.get("task_authority_source_ref_ids", [])),
            }
        )
    if not obligations:
        raise CaseGenerationError(
            f"profile {profile.get('profile_id')!r} coordinate activates no obligations"
        )
    return obligations


def _capabilities(profile: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = profile.get("capabilities", [])
    if not isinstance(rows, list):
        raise CaseGenerationError("capabilities must be a list")
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise CaseGenerationError("capability entry must be an object")
        out.append(
            {
                "capability_id": str(row["capability_id"]),
                "owner": str(row["owner"]),
                "legal": True,
                "cost_model_ref": None,
                "source_ref_ids": list(row.get("source_ref_ids", [])),
            }
        )
    return out


def _authority(
    profile: Mapping[str, Any],
    obligations: list[dict[str, Any]],
    capabilities: list[dict[str, Any]],
) -> dict[str, Any]:
    actors = {
        str(o["authority_owner"]) for o in obligations
    } | {
        str(c["owner"]) for c in capabilities
    }
    return {
        "actors": sorted(actors),
        "legal_action_owners": {
            str(c["capability_id"]): str(c["owner"]) for c in capabilities
        },
        "invariants": list(profile.get("authority_invariants", [])),
    }


def _regime(profile: Mapping[str, Any], world: Mapping[str, Any]) -> list[str]:
    pid = str(profile.get("profile_id", ""))
    if pid.startswith("DB11T1677"):
        return [
            "R1_WARNING_ESCALATION"
            if world.get("rain_state") == "rain"
            else "R0_NORMAL"
        ]
    if pid.startswith("DB44T2457"):
        return [
            "R0_NORMAL"
            if world.get("warning_state") == "none_stable"
            else "R1_WARNING_ESCALATION"
        ]
    if pid.startswith("JIAOZUO_2024"):
        return ["R0_NORMAL", "R5_HETEROGENEOUS_PATH"]
    if pid.startswith("YINING_2025") or pid.startswith("BAOSHAN_1262"):
        return ["R7_WARNING_DISSEMINATION"]
    return ["R0_NORMAL"]


def _hardness(profile: Mapping[str, Any]) -> list[str]:
    # Nominal source coordinates are not yet decision-hard.  T2 preserves its
    # authority-gated structure, but still awaits oracle/validity before admission.
    families = set(map(str, profile.get("families", [])))
    if families == {"T2"}:
        return ["H6_AUTHORITY_GATED_DELIVERY"]
    return ["H0_CONFORMANCE"]


def compile_nominal_case(
    profile: Mapping[str, Any],
    coordinate: Mapping[str, Any],
    *,
    generator_version: str = "source-profile-v0.1",
) -> dict[str, Any]:
    """Compile one source-derived nominal coordinate into a VALIDITY_PENDING case."""

    validate_source_profile(profile)
    if profile.get("generator_status") != "READY":
        raise CaseGenerationError("only READY profiles compile into nominal cases")

    family_codes = list(map(str, profile.get("families", [])))
    if len(family_codes) != 1 or family_codes[0] not in FAMILY_IDS:
        raise CaseGenerationError(
            f"nominal compiler requires exactly one known family, got {family_codes!r}"
        )

    world = _world_from_coordinate(profile, coordinate)
    obligations = _instantiate_obligations(profile, world)
    capabilities = _capabilities(profile)
    authority = _authority(profile, obligations, capabilities)
    heldout_groups = deepcopy(dict(profile.get("heldout_groups", {})))
    coordinate_payload = {
        "profile_id": profile["profile_id"],
        "coordinate_index": coordinate["coordinate_index"],
        "fixed_by_source": coordinate.get("fixed_by_source", {}),
        "source_range_assignment": coordinate.get("source_range_assignment", {}),
    }
    digest = _canonical_digest(coordinate_payload)

    case = {
        "schema_version": "0.1",
        "case_id": f"{profile['profile_id']}::nominal::{coordinate['coordinate_index']:04d}::{digest}",
        "family": FAMILY_IDS[family_codes[0]],
        "source_profiles": [str(profile["profile_id"])],
        "source_refs": deepcopy(list(profile.get("source_refs", []))),
        "generator": {
            "version": generator_version,
            "seed": 0,
            "world_template_id": f"{profile['profile_id']}::nominal",
            "parent_case_id": None,
        },
        "regime": _regime(profile, world),
        "hardness": _hardness(profile),
        "world": world,
        "variable_provenance": _provenance_map(profile, coordinate),
        "obligations": obligations,
        "authority": authority,
        "capabilities": capabilities,
        "observation": {
            "visible_state": deepcopy(world),
            "hidden_fields": [],
            "alias_world_ids": [],
            "separating_evidence_ids": [],
            "projection_provenance": "FULL_OBSERVATION",
        },
        "oracle": {
            "solver_version": "PENDING",
            "mode": "FULL_STATE_FEASIBILITY",
            "solvable": False,
            "feasible_success_plan_count": 0,
            "valid_terminal_state_count": 0,
            "plan_set_ref": None,
            "terminal_state_set_ref": None,
            "pareto_frontier_ref": None,
            "binding_constraints": [],
            "scalarization_used": False,
            "scalarization_source_ref": None,
        },
        "validity": {
            "filters": [
                {
                    "filter_id": "V0_SOURCE_COMPLETE",
                    "passed": True,
                    "reason_code": "PASS",
                    "evidence_ref": f"profile://{profile['profile_id']}",
                }
            ],
            "decision_benchmark_eligible": False,
            "disposition": "DECISION_CANDIDATE",
            "notes": [
                "Nominal source-derived coordinate only; V1-V9 have not run.",
                "No controlled stress, hidden state, or simulator-specific action has been added.",
            ],
        },
        "baseline_audit": [],
        "split": {
            "name": "research_hold",
            "heldout_axes": sorted(heldout_groups),
            "group_ids": heldout_groups,
        },
        "release_status": "VALIDITY_PENDING",
        "known_limitations": [
            "Oracle/world dynamics not yet instantiated.",
            "Nominal coordinate is not evidence of decision hardness.",
        ],
    }
    validate_case_semantics(case)
    return case


def compile_ready_profile(profile: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        compile_nominal_case(profile, coordinate)
        for coordinate in expand_nominal_profile(profile)
    ]


def compile_ready_registry(
    profiles: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for profile in profiles:
        if profile.get("generator_status") == "READY":
            cases.extend(compile_ready_profile(profile))
    ids = [case["case_id"] for case in cases]
    if len(ids) != len(set(ids)):
        raise CaseGenerationError("generated duplicate case_id values")
    return cases
