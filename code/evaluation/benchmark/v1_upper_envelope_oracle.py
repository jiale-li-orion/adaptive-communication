#!/usr/bin/env python3
"""V1 upper-envelope phase-solvability oracle for T1 reporting worlds.

This oracle is deliberately narrow:
- payload must fit one selected-path message;
- service semantics are GEOMETRY_UPPER_ENVELOPE_V0;
- any geometric visibility instant is treated as a successful opportunity;
- release phase is not guessed: every minute-aligned release phase whose
  deadline remains inside the frozen trace horizon is evaluated.

The result is a solvability *surface*, not benchmark admission and not a
field-reliability claim.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any


class V1OracleError(ValueError):
    pass


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _window_seconds(trace_payload: Mapping[str, Any], mask: int) -> list[tuple[int, int]]:
    start = _parse_iso(str(trace_payload["start_utc"]))
    row = trace_payload["thresholds"][str(mask)]
    out: list[tuple[int, int]] = []
    for window in row["windows_utc"]:
        a = int((_parse_iso(str(window["start"])) - start).total_seconds())
        b = int((_parse_iso(str(window["end"])) - start).total_seconds())
        if b <= a:
            raise V1OracleError("non-positive visibility window")
        out.append((a, b))
    return out


def _phase_solvable(
    release_s: int,
    deadline_s: int,
    windows: list[tuple[int, int]],
) -> bool:
    # Window end is exclusive; deadline is inclusive. A visibility window
    # beginning exactly at the deadline is therefore a valid last-chance slot.
    for start_s, end_s in windows:
        if start_s > deadline_s:
            return False
        if end_s > release_s and start_s <= deadline_s:
            return True
    return False


def _compress_unsolved(phases: list[int], step_s: int) -> list[dict[str, int]]:
    if not phases:
        return []
    out: list[dict[str, int]] = []
    start = prev = phases[0]
    for value in phases[1:]:
        if value == prev + step_s:
            prev = value
            continue
        out.append({"start_release_s": start, "end_release_s": prev})
        start = prev = value
    out.append({"start_release_s": start, "end_release_s": prev})
    return out


def solve_phase_surface(
    case: Mapping[str, Any],
    *,
    trace_payload: Mapping[str, Any],
) -> dict[str, Any]:
    world = case.get("world", {})
    if not isinstance(world, Mapping):
        raise V1OracleError("case world must be object")
    if world.get("path_service_success_semantics") != "GEOMETRY_UPPER_ENVELOPE_V0":
        raise V1OracleError("V1 upper-envelope oracle requires named upper-envelope service semantics")

    interval_s = world.get("report_interval_s")
    payload_b = world.get("report_payload_bytes")
    constraints = world.get("selected_path_constraints", {})
    geometry = world.get("path_geometry", {})
    if not isinstance(interval_s, int) or interval_s <= 0:
        raise V1OracleError("positive report_interval_s required")
    if not isinstance(payload_b, int) or payload_b <= 0:
        raise V1OracleError("positive report_payload_bytes required")
    if not isinstance(constraints, Mapping) or not isinstance(geometry, Mapping):
        raise V1OracleError("path constraints and geometry required")

    max_payload_b = constraints.get("max_payload_bytes")
    if not isinstance(max_payload_b, int) or max_payload_b <= 0:
        raise V1OracleError("selected path max_payload_bytes required")
    payload_fit = payload_b <= max_payload_b

    step_s = int(trace_payload["step_s"])
    horizon_s = int(trace_payload["hours"]) * 3600
    mask = int(geometry["elevation_mask_deg"])
    windows = _window_seconds(trace_payload, mask)

    base = {
        "solver_version": "v1-upper-envelope-phase-surface-0.1",
        "service_semantics": "GEOMETRY_UPPER_ENVELOPE_V0",
        "payload_bytes": payload_b,
        "max_payload_bytes": max_payload_b,
        "payload_fit": payload_fit,
        "report_interval_s": interval_s,
        "trace_horizon_s": horizon_s,
        "trace_step_s": step_s,
        "elevation_mask_deg": mask,
        "field_reliability_claim": False,
    }

    if not payload_fit:
        return base | {
            "status": "UNSOLVABLE_PAYLOAD",
            "horizon_sufficient": interval_s <= horizon_s,
            "release_phase_count": 0,
            "solvable_phase_count": 0,
            "solvable_phase_fraction": 0.0,
            "all_phase_solvable": False,
            "phase_binding": False,
            "unsolved_release_ranges": [],
        }

    if interval_s > horizon_s:
        return base | {
            "status": "TRACE_HORIZON_INSUFFICIENT",
            "horizon_sufficient": False,
            "release_phase_count": 0,
            "solvable_phase_count": 0,
            "solvable_phase_fraction": None,
            "all_phase_solvable": None,
            "phase_binding": None,
            "unsolved_release_ranges": [],
        }

    last_release = horizon_s - interval_s
    phases = list(range(0, last_release + 1, step_s))
    solved = [
        release
        for release in phases
        if _phase_solvable(release, release + interval_s, windows)
    ]
    solved_set = set(solved)
    unsolved = [release for release in phases if release not in solved_set]
    n = len(phases)
    frac = len(solved) / n if n else 0.0

    if not solved:
        status = "UNSOLVABLE_ALL_PHASES"
    elif len(solved) == n:
        status = "SOLVABLE_ALL_PHASES"
    else:
        status = "SOLVABLE_SOME_PHASES"

    return base | {
        "status": status,
        "horizon_sufficient": True,
        "release_phase_count": n,
        "solvable_phase_count": len(solved),
        "solvable_phase_fraction": frac,
        "all_phase_solvable": len(solved) == n,
        "phase_binding": 0 < len(solved) < n,
        "unsolved_release_ranges": _compress_unsolved(unsolved, step_s),
    }
