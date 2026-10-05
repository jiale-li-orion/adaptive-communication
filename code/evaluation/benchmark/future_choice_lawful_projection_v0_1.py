#!/usr/bin/env python3
"""Lawful model-facing projection for future-choice supervision.

The projection is intentionally stricter than the exact oracle state.  It may
contain public task/capability/resource coordinates and the controller's own
action history, but never a realized hidden world, latent terrestrial service,
delivery acceptance, or other evaluator-only state.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "future-choice-lawful-projection-v0.1"

# These names are forbidden recursively inside the feature object.  Oracle
# labels live outside ``features`` and are allowed to depend on hidden truth.
FORBIDDEN_FEATURE_KEYS = {
    "worlds",
    "world_id",
    "alias_world_ids",
    "latent_state",
    "terrestrial_windows",
    "delivery_receipt_state",
    "accepted",
    "delivered",
    "pending_deliveries",
    "gateway_receipt_seen",
    "last_query_signature",
    "last_direct_signature",
}


def _obligation_index(bundle: Mapping[str, Any]) -> dict[str, int]:
    return {
        str(o["obligation_id"]): int(o.get("stream_index", i))
        for i, o in enumerate(bundle["obligations"])
    }


def canonical_action(bundle: Mapping[str, Any], kind: str, arg: str | None) -> str:
    if kind in {"SEND_TERR", "SEND_SAT"} and arg is not None:
        idx = _obligation_index(bundle).get(str(arg))
        if idx is None:
            raise ValueError(f"unknown obligation action arg {arg!r}")
        return f"{kind}:stream_{idx}"
    return f"{kind}:{arg if arg is not None else '-'}"


def _phase(now: int, start: int, end: int) -> str:
    if now < start:
        return "FUTURE"
    if now < end:
        return "OPEN"
    return "ENDED"


def _relative(value: int, now: int) -> int:
    return int(value) - int(now)


def project_features(
    bundle: Mapping[str, Any],
    *,
    at_s: int,
    query_budget_remaining: int,
    action_history: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Project one decision boundary without evaluator-only physical truth."""
    env = bundle["public_environment"]
    obligations = []
    for i, o in enumerate(sorted(bundle["obligations"], key=lambda x: int(x.get("stream_index", 0)))):
        release = int(o["release_s"])
        deadline = int(o["deadline_s"])
        obligations.append({
            "stream_index": int(o.get("stream_index", i)),
            "protected_subject": str(o["protected_subject"]),
            "release_in_s": _relative(release, at_s),
            "deadline_in_s": _relative(deadline, at_s),
            "source_interval_s": int(o.get("source_interval_s", deadline - release)),
            "phase": (
                "FUTURE" if at_s < release
                else "ACTIVE" if at_s <= deadline
                else "EXPIRED"
            ),
        })

    satellite = []
    for w in env["satellite_windows"]:
        start = int(w["start_s"]); end = int(w["end_s"])
        if end <= at_s:
            continue
        satellite.append({
            "window_id": str(w["window_id"]),
            "start_in_s": _relative(start, at_s),
            "end_in_s": _relative(end, at_s),
            "capacity_units": int(w["capacity_units"]),
            "phase": _phase(at_s, start, end),
        })

    history = []
    sat_attempts = 0
    query_attempts = 0
    for row in action_history:
        kind = str(row["action"])
        arg = row.get("arg")
        if kind == "SEND_SAT":
            sat_attempts += 1
        if kind == "ISSUE_QUERY":
            query_attempts += 1
        history.append({
            "time_ago_s": int(at_s) - int(row["time_s"]),
            "action": canonical_action(bundle, kind, None if arg is None else str(arg)),
        })

    evidence_surfaces = []
    for surface in bundle["observation_projection"].get("evidence_surfaces", []):
        evidence_surfaces.append({
            k: surface[k]
            for k in ("evidence_id", "kind", "owner", "source_capability")
            if k in surface
        })

    transition = env.get("warning_transition") or {}
    features = {
        "schema_version": SCHEMA_VERSION,
        "time_s": int(at_s),
        "task": {
            "family": str(bundle["family"]),
            "task_surface_ids": list(bundle.get("task_surface_ids", [])),
            "obligations": obligations,
            "warning_state": str((transition.get("to") or {}).get("warning_state", "")),
            "report_interval_s": int(
                (transition.get("to") or {}).get(
                    "report_interval_s", obligations[0]["source_interval_s"]
                )
            ),
        },
        "communication": {
            "terrestrial_process_class": str(env.get("terrestrial_process_class", "UNSPECIFIED_FIXTURE")),
            "satellite_windows": satellite,
            "satellite_budget_initial": int(env["satellite_budget_units"]),
            "satellite_attempt_count": sat_attempts,
            "geometry_mask_deg": (
                None if env.get("geometry_mask_deg") is None else int(env["geometry_mask_deg"])
            ),
            "horizon_remaining_s": int(env.get("horizon_s", max(o["deadline_s"] for o in bundle["obligations"]))) - int(at_s),
        },
        "evidence_contract": {
            "regime": str(bundle["observation_projection"]["evidence_regime"]),
            "surfaces": evidence_surfaces,
            "query_budget_remaining": int(query_budget_remaining),
            "query_attempt_count": query_attempts,
        },
        "recovery": {
            k: bundle["recovery"][k]
            for k in ("regime", "enabled", "local_cache_min_days", "reconnect_objective_status")
            if k in bundle["recovery"]
        },
        "own_action_history": history,
    }
    assert_lawful_features(features)
    return features


def _walk_keys(value: Any):
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield str(key)
            yield from _walk_keys(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _walk_keys(child)


def assert_lawful_features(features: Mapping[str, Any]) -> None:
    leaked = sorted(set(_walk_keys(features)) & FORBIDDEN_FEATURE_KEYS)
    if leaked:
        raise ValueError(f"future-choice feature projection leaks evaluator-only keys: {leaked}")


def feature_digest(features: Mapping[str, Any]) -> str:
    assert_lawful_features(features)
    raw = json.dumps(features, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(raw.encode()).hexdigest()


def canonicalize_action_keys(bundle: Mapping[str, Any], keys: Sequence[str]) -> list[str]:
    out = []
    for key in keys:
        kind, arg = str(key).split(":", 1)
        out.append(canonical_action(bundle, kind, None if arg == "-" else arg))
    return out
