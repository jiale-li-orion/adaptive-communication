#!/usr/bin/env python3
"""V2/V3 dual-path validity audit.

Question:
Does adding a terrestrial path plus an intermittent satellite path create
genuine decision hardness for a single report when there is no cross-report
resource coupling?

Answer is determined exactly, not by model performance.  If the ordinary
earliest-available fallback succeeds whenever any legal path can succeed, the
world has multiple legal options but fails V3 due to a common safe policy.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any


class DualPathAuditError(ValueError):
    pass


def _dt(x: str) -> datetime:
    return datetime.fromisoformat(x)


def _satellite_first_opportunity_s(
    trace_payload: Mapping[str, Any],
    *,
    mask: int,
    release_s: int,
    deadline_s: int,
) -> int | None:
    start = _dt(str(trace_payload["start_utc"]))
    row = trace_payload["thresholds"][str(mask)]
    for window in row["windows_utc"]:
        ws = int((_dt(str(window["start"])) - start).total_seconds())
        we = int((_dt(str(window["end"])) - start).total_seconds())
        if ws > deadline_s:
            return None
        if we <= release_s:
            continue
        return max(release_s, ws)
    return None


def audit_release_phase(
    case: Mapping[str, Any],
    *,
    trace_payload: Mapping[str, Any],
    release_s: int,
    outage_duration_over_deadline: float,
) -> dict[str, Any]:
    world = case.get("world", {})
    if not isinstance(world, Mapping):
        raise DualPathAuditError("case world required")
    interval_s = world.get("report_interval_s")
    geometry = world.get("path_geometry", {})
    if not isinstance(interval_s, int) or interval_s <= 0:
        raise DualPathAuditError("positive report interval required")
    if not isinstance(geometry, Mapping):
        raise DualPathAuditError("path geometry required")
    if outage_duration_over_deadline < 0:
        raise DualPathAuditError("outage ratio must be non-negative")

    deadline_s = release_s + interval_s
    horizon_s = int(trace_payload["hours"]) * 3600
    if deadline_s > horizon_s:
        raise DualPathAuditError("release phase exceeds trace horizon")

    outage_duration_s = int(round(outage_duration_over_deadline * interval_s))
    terrestrial_recovery_s = release_s + outage_duration_s
    terrestrial_success = terrestrial_recovery_s <= deadline_s

    sat_s = _satellite_first_opportunity_s(
        trace_payload,
        mask=int(geometry["elevation_mask_deg"]),
        release_s=release_s,
        deadline_s=deadline_s,
    )
    satellite_success = sat_s is not None

    # Full-state any-path oracle for a single monotone delivery obligation.
    any_path_solvable = terrestrial_success or satellite_success

    # Ordinary auto-fallback / earliest-available policy:
    # use whichever usable path becomes available first.
    candidates: list[tuple[str, int]] = []
    if terrestrial_success:
        candidates.append(("terrestrial", terrestrial_recovery_s))
    if satellite_success:
        candidates.append(("satellite", int(sat_s)))
    if candidates:
        selected_path, delivered_s = min(candidates, key=lambda x: (x[1], x[0]))
        ordinary_success = delivered_s <= deadline_s
    else:
        selected_path, delivered_s, ordinary_success = None, None, False

    # A terrestrial-preferred legal policy differs when both paths can succeed:
    # it waits for recovery instead of consuming satellite service.
    multiple_legal_success_plans = terrestrial_success and satellite_success

    return {
        "release_s": release_s,
        "deadline_s": deadline_s,
        "outage_duration_over_deadline": outage_duration_over_deadline,
        "outage_duration_s": outage_duration_s,
        "terrestrial_recovery_s": terrestrial_recovery_s,
        "terrestrial_success": terrestrial_success,
        "satellite_first_opportunity_s": sat_s,
        "satellite_success": satellite_success,
        "multiple_legal_success_plans": multiple_legal_success_plans,
        "oracle_any_path_solvable": any_path_solvable,
        "ordinary_auto_fallback_success": ordinary_success,
        "ordinary_selected_path": selected_path,
        "ordinary_delivered_s": delivered_s,
        "common_safe_violation": any_path_solvable and not ordinary_success,
        "outcome_difference_when_both_feasible": (
            {
                "satellite_earliest_delivery_s": sat_s,
                "terrestrial_preferred_delivery_s": terrestrial_recovery_s,
                "satellite_uses": [1, 0],
            }
            if multiple_legal_success_plans
            else None
        ),
    }


def audit_phase_surface(
    case: Mapping[str, Any],
    *,
    trace_payload: Mapping[str, Any],
    outage_duration_over_deadline: float,
) -> dict[str, Any]:
    world = case["world"]
    interval_s = int(world["report_interval_s"])
    horizon_s = int(trace_payload["hours"]) * 3600
    step_s = int(trace_payload["step_s"])
    if interval_s > horizon_s:
        return {
            "status": "TRACE_HORIZON_INSUFFICIENT",
            "report_interval_s": interval_s,
            "outage_duration_over_deadline": outage_duration_over_deadline,
            "release_phase_count": 0,
        }

    phases = range(0, horizon_s - interval_s + 1, step_s)
    rows = [
        audit_release_phase(
            case,
            trace_payload=trace_payload,
            release_s=r,
            outage_duration_over_deadline=outage_duration_over_deadline,
        )
        for r in phases
    ]
    oracle_solvable = sum(x["oracle_any_path_solvable"] for x in rows)
    ordinary_success = sum(x["ordinary_auto_fallback_success"] for x in rows)
    multi = sum(x["multiple_legal_success_plans"] for x in rows)
    violations = sum(x["common_safe_violation"] for x in rows)
    return {
        "status": "AUDITED",
        "report_interval_s": interval_s,
        "elevation_mask_deg": int(world["path_geometry"]["elevation_mask_deg"]),
        "outage_duration_over_deadline": outage_duration_over_deadline,
        "release_phase_count": len(rows),
        "oracle_solvable_phase_count": oracle_solvable,
        "ordinary_auto_fallback_success_count": ordinary_success,
        "multiple_legal_success_plan_phase_count": multi,
        "common_safe_violation_count": violations,
        "ordinary_matches_oracle": ordinary_success == oracle_solvable and violations == 0,
        "v2_multiple_legal_options_observed": multi > 0,
        "v3_no_common_safe_policy": violations > 0,
        "disposition": (
            "COMMON_SAFE_POLICY"
            if oracle_solvable > 0 and violations == 0
            else "NEEDS_FURTHER_AUDIT"
        ),
    }
