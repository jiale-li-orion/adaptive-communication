#!/usr/bin/env python3
"""Machine-readable Layer-1 task-surface / historical-closure authority.

Family identity comes from cache06/BENCHMARK-CONSTRUCTION-PROTOCOL.  This file
prevents historical O1-O6 templates, capabilities, or receipt mechanisms from
being silently promoted to new Operational Families.
"""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REGISTRY = ROOT / "research/benchmark/TASK-SURFACE-REGISTRY.v0.1.json"


@lru_cache(maxsize=1)
def load_registry() -> dict[str, Any]:
    data=json.loads(REGISTRY.read_text(encoding="utf-8"))
    validate_registry(data)
    return data


def validate_registry(data: Mapping[str, Any]) -> None:
    families=data.get("families")
    if not isinstance(families, Mapping) or set(families)!={
        "T1_MONITORING_INFORMATION_CONTINUITY",
        "T2_WARNING_DELIVERY_RESPONSE_HANDOFF",
    }:
        raise ValueError("task-surface registry must freeze exactly T1/T2 family identities")
    seen=set()
    for family_id,family in families.items():
        rows=family.get("task_surfaces",[])
        if not rows:
            raise ValueError(f"{family_id} has no task surfaces")
        for row in rows:
            sid=str(row["surface_id"])
            if sid in seen: raise ValueError(f"duplicate surface_id {sid}")
            seen.add(sid)
            if not row.get("source_profiles"):
                raise ValueError(f"{sid} has no source profile authority")
            if not row.get("generator_role") or not row.get("standalone_disposition"):
                raise ValueError(f"{sid} missing closure/generator disposition")
    forbidden=set(map(str,data.get("not_task_surfaces",[])))
    if seen & forbidden:
        raise ValueError("capability/mechanism promoted to task surface")


def surface(surface_id:str) -> dict[str,Any]:
    for family in load_registry()["families"].values():
        for row in family["task_surfaces"]:
            if row["surface_id"]==surface_id:return dict(row)
    raise KeyError(surface_id)


def task_surface_ids_for_profile(profile:Mapping[str,Any],world:Mapping[str,Any]) -> list[str]:
    pid=str(profile.get("profile_id",""))
    out=[]
    if pid.startswith("DB44T2457"):
        state=world.get("warning_state")
        out.append("T1.S0_STEADY_MONITORING")
        if state not in (None,"none_stable"):
            out.append("T1.S1_WARNING_CADENCE_TRANSITION")
    elif pid.startswith("JIAOZUO_2024"):
        out += ["T1.S0_STEADY_MONITORING","T1.S6_HETEROGENEOUS_PATH_PRIORITY"]
    elif pid.startswith("DB11T1677"):
        out += ["T1.S0_STEADY_MONITORING","T1.S3_ENERGY_CONSTRAINED_CONTINUITY","T1.S6_HETEROGENEOUS_PATH_PRIORITY"]
        if world.get("rain_state")=="rain":out.append("T1.S1_WARNING_CADENCE_TRANSITION")
    elif pid.startswith("DZT0450"):
        out += ["T1.S2_INTERMITTENT_BACKHAUL_FALLBACK","T1.S4_OUTAGE_CACHE_RETENTION","T1.S5_RECOVERY_RECONCILIATION","T1.S6_HETEROGENEOUS_PATH_PRIORITY"]
    elif pid.startswith("YINING_2025"):
        out += ["T2.S0_AUTHORITY_GATED_PUBLICATION","T2.S1_HIERARCHICAL_WARNING_DELIVERY_ACK"]
    elif pid.startswith("BAOSHAN_1262"):
        out += ["T2.S2_PROGRESSIVE_CALL_RESPONSE"]
    return sorted(set(out))


def closure_records(surface_ids:list[str]) -> list[dict[str,str]]:
    return [
        {
            "surface_id":sid,
            "standalone_disposition":surface(sid)["standalone_disposition"],
            "generator_role":surface(sid)["generator_role"],
            "closure":surface(sid)["closure"],
        }
        for sid in surface_ids
    ]
