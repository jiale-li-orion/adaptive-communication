#!/usr/bin/env python3
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


class SiteContractError(ValueError):
    pass


def validate_site_profile(profile: Mapping[str, Any]) -> None:
    coords = profile.get("coordinates")
    if not isinstance(coords, Mapping):
        raise SiteContractError("coordinates required")
    lat, lon = coords.get("lat_deg"), coords.get("lon_deg")
    if not isinstance(lat, (int, float)) or not -90 <= float(lat) <= 90:
        raise SiteContractError("invalid latitude")
    if not isinstance(lon, (int, float)) or not -180 <= float(lon) <= 180:
        raise SiteContractError("invalid longitude")
    refs = profile.get("source_refs")
    if not isinstance(refs, list) or len(refs) < 2:
        raise SiteContractError("field site requires independent coordinate + field-use evidence")
    variables = profile.get("variables", {})
    altitude = variables.get("altitude_m", {}) if isinstance(variables, Mapping) else {}
    if altitude.get("provenance_class") == "UNRESOLVED" and altitude.get("answer_relevant"):
        raise SiteContractError("answer-relevant altitude cannot remain unresolved")


def compatible_with_task_jurisdiction(
    site: Mapping[str, Any],
    task_scope: Mapping[str, Any],
) -> bool:
    task_j = task_scope.get("jurisdiction")
    allowed = site.get("scope", {}).get("task_jurisdiction_compatible", [])
    return isinstance(task_j, str) and task_j in allowed


def validate_site_registry(profiles: Sequence[Mapping[str, Any]]) -> None:
    ids: set[str] = set()
    for p in profiles:
        validate_site_profile(p)
        pid = p.get("site_profile_id")
        if not isinstance(pid, str) or not pid or pid in ids:
            raise SiteContractError("site_profile_id missing/duplicate")
        ids.add(pid)
