#!/usr/bin/env python3
"""Independent execution-trace evaluator for Layer-1 T1 world bundles.

The evaluator consumes executed actions, not planner text.  It checks action
ownership, physical opportunity/capacity, satellite budget, protected subject
and source-owned deadlines.  It does not consult the policy/oracle decision.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

from causal_evidence_process_v0_1 import FINAL_ACK_DELAY_S, SATELLITE_COMPLETION_DELAY_S


EXECUTION_OWNER = "communication_subsystem"


def _fail(code: str, **extra: Any) -> dict[str, Any]:
    return {"success": False, "reason_code": code, **extra}


def evaluate_execution_trace(
    bundle: Mapping[str, Any],
    *,
    world_id: str,
    actions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    world = next((w for w in bundle["worlds"] if str(w["world_id"]) == world_id), None)
    if world is None:
        return _fail("UNKNOWN_WORLD")
    obligations = {str(o["obligation_id"]): o for o in bundle["obligations"]}
    terr = {str(w["window_id"]): w for w in world["terrestrial_windows"]}
    sat = {str(w["window_id"]): w for w in bundle["public_environment"]["satellite_windows"]}
    used = Counter()
    sat_used = 0
    completed: dict[str, int] = {}

    for index, action in enumerate(actions):
        kind = str(action.get("action"))
        oid = str(action.get("obligation_id"))
        actor = str(action.get("actor"))
        resource_id = str(action.get("resource_id"))
        at_s = action.get("at_s")
        subject = action.get("protected_subject")
        if actor != EXECUTION_OWNER:
            return _fail("AUTHORITY_VIOLATION", action_index=index, actor=actor)
        if oid not in obligations:
            return _fail("UNKNOWN_OBLIGATION", action_index=index, obligation_id=oid)
        o = obligations[oid]
        if subject != o["protected_subject"]:
            return _fail("PROTECTED_SUBJECT_MISMATCH", action_index=index, obligation_id=oid)
        if oid in completed:
            return _fail("DUPLICATE_COMPLETION", action_index=index, obligation_id=oid)
        if not isinstance(at_s, int):
            return _fail("INVALID_ACTION_TIME", action_index=index)
        if at_s < int(o["release_s"]):
            return _fail("BEFORE_RELEASE", action_index=index, obligation_id=oid)

        if kind == "SEND_TERR":
            w = terr.get(resource_id)
            if w is None:
                return _fail("PHYSICALLY_UNEXECUTED_TERR_ACTION", action_index=index, resource_id=resource_id)
            if not (int(w["start_s"]) <= at_s < int(w["end_s"])):
                return _fail("OUTSIDE_TERR_SERVICE_WINDOW", action_index=index, resource_id=resource_id)
            used[resource_id] += 1
            if used[resource_id] > int(w["capacity_units"]):
                return _fail("TERR_CAPACITY_EXCEEDED", action_index=index, resource_id=resource_id)
            completed_at = at_s + FINAL_ACK_DELAY_S
        elif kind == "SEND_SAT":
            w = sat.get(resource_id)
            if w is None:
                return _fail("PHYSICALLY_UNEXECUTED_SAT_ACTION", action_index=index, resource_id=resource_id)
            if not (int(w["start_s"]) <= at_s < int(w["end_s"])):
                return _fail("OUTSIDE_SAT_SERVICE_WINDOW", action_index=index, resource_id=resource_id)
            used[resource_id] += 1
            if used[resource_id] > int(w["capacity_units"]):
                return _fail("SAT_WINDOW_CAPACITY_EXCEEDED", action_index=index, resource_id=resource_id)
            sat_used += 1
            if sat_used > int(bundle["public_environment"]["satellite_budget_units"]):
                return _fail("SATELLITE_BUDGET_EXCEEDED", action_index=index)
            completed_at = at_s + SATELLITE_COMPLETION_DELAY_S
        else:
            return _fail("UNKNOWN_EXECUTION_ACTION", action_index=index, action=kind)

        if completed_at > int(o["deadline_s"]):
            return _fail(
                "MISSED_SOURCE_DEADLINE",
                action_index=index,
                obligation_id=oid,
                completed_at_s=completed_at,
                deadline_s=int(o["deadline_s"]),
            )
        completed[oid] = completed_at

    missing = sorted(set(obligations) - set(completed))
    if missing:
        return _fail("MISSING_EXECUTED_COMPLETION", missing_obligation_ids=missing)
    return {
        "success": True,
        "reason_code": "PASS",
        "completed_at_s": dict(sorted(completed.items())),
        "scalarization_used": False,
    }


def witness_to_execution_trace(bundle: Mapping[str, Any], witness: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    obligations = {str(o["obligation_id"]): o for o in bundle["obligations"]}
    rows = []
    for item in witness:
        oid = str(item["obligation_id"])
        path = str(item["path"])
        rows.append(
            {
                "action": "SEND_TERR" if path == "TERRESTRIAL" else "SEND_SAT",
                "obligation_id": oid,
                "actor": EXECUTION_OWNER,
                "resource_id": str(item["resource_id"]),
                "at_s": int(item["send_at_s"]),
                "protected_subject": obligations[oid]["protected_subject"],
            }
        )
    return sorted(rows, key=lambda x: (int(x["at_s"]), str(x["obligation_id"])))
