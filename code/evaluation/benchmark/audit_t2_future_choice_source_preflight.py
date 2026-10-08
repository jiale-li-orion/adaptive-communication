#!/usr/bin/env python3
"""Source-only future-choice preflight for T2 warning handoff.

The T2 task family is source-supported, but task validity and method headroom
are different questions.  This audit reads the frozen source-profile registry
and asks whether the *source-backed contract itself* already contains a
persistent/shared resource through which an early retry/contact action can
destroy a later handoff continuation.

If the sources only fix actor order, deadlines, ACK/retry semantics and channel
priority -- while channel capacity/contact duration/quota remain unspecified --
then T2 is a valid benchmark surface but is not yet a source-closed
future-choice method task.  In that case, any later scarcity mechanism must be
grounded by an empirical trace or independently preregistered controlled-stress
profile; it may not be invented after seeing method results.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / "research/benchmark/profiles/v0.1/SOURCE-PROFILE-REGISTRY.v0.1.json"
TASKS = ROOT / "research/benchmark/TASK-SURFACE-REGISTRY.v0.1.json"

TARGETS = {
    "YINING_2025_pre_disaster_warning_delivery",
    "BAOSHAN_1262_progressive_call_response",
}


def _profiles(doc: Any) -> list[dict[str, Any]]:
    if isinstance(doc, list):
        return [x for x in doc if isinstance(x, dict)]
    for key in ("profiles", "source_profiles", "items"):
        value = doc.get(key) if isinstance(doc, dict) else None
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]
    raise ValueError("unrecognized source profile registry shape")


def _resource_fields(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect source-backed variables/capability constraints that could couple stages."""

    hits = []
    resource_terms = {
        "capacity", "quota", "budget", "duration", "airtime", "energy",
        "concurrency", "parallel", "occupancy", "contact_time", "attempt_time",
    }
    for name, spec in (profile.get("variables") or {}).items():
        low = str(name).lower()
        if any(term in low for term in resource_terms):
            hits.append({"kind": "variable", "name": name, "spec": spec})
    for cap in profile.get("capabilities") or []:
        constraints = cap.get("constraints") or {}
        if constraints:
            hits.append({
                "kind": "capability_constraint",
                "capability_id": cap.get("capability_id"),
                "constraints": constraints,
            })
    return hits


def main() -> int:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    task_registry = json.loads(TASKS.read_text(encoding="utf-8"))
    selected = {
        p["profile_id"]: p
        for p in _profiles(registry)
        if p.get("profile_id") in TARGETS
    }
    assert set(selected) == TARGETS, sorted(selected)

    rows = {}
    for pid, profile in sorted(selected.items()):
        obligations = profile.get("obligation_templates") or []
        capabilities = profile.get("capabilities") or []
        rows[pid] = {
            "generator_status": profile.get("generator_status"),
            "direct_task_authority": any(
                ref.get("directness") == "DIRECT_TASK_AUTHORITY"
                for ref in profile.get("source_refs") or []
            ),
            "obligation_count": len(obligations),
            "obligations": [
                {
                    "template_id": o.get("template_id"),
                    "trigger": o.get("trigger"),
                    "completion_predicate": o.get("completion_predicate"),
                    "timing_semantics": o.get("timing_semantics"),
                    "source_priority": o.get("source_priority"),
                }
                for o in obligations
            ],
            "capabilities": [
                {
                    "capability_id": c.get("capability_id"),
                    "owner": c.get("owner"),
                    "constraints": c.get("constraints") or {},
                }
                for c in capabilities
            ],
            "source_fixed_shared_resource_fields": _resource_fields(profile),
            "authority_invariants": profile.get("authority_invariants") or [],
            "unknowns": profile.get("unknowns") or [],
        }

    # The task registry must still classify the T2 surfaces as environment gaps;
    # this prevents the preflight from silently pretending an execution model exists.
    t2 = task_registry["families"]["T2_WARNING_DELIVERY_RESPONSE_HANDOFF"]
    t2_surfaces = {
        row["surface_id"]: row["standalone_disposition"]
        for row in t2["task_surfaces"]
    }

    all_direct = all(row["direct_task_authority"] for row in rows.values())
    any_shared_resource = any(
        row["source_fixed_shared_resource_fields"] for row in rows.values()
    )
    capabilities_have_declared_constraints = any(
        cap["constraints"]
        for row in rows.values()
        for cap in row["capabilities"]
    )
    all_t2_gaps = all(v == "SIMULATOR_GAP" for v in t2_surfaces.values())

    disposition = (
        "SOURCE_VALID_TASK_BUT_FUTURE_CHOICE_RESOURCE_NOT_CLOSED"
        if all_direct and not any_shared_resource and not capabilities_have_declared_constraints
        else "REVIEW_SOURCE_RESOURCE_CONTRACT"
    )

    payload = {
        "stage": "T2_FUTURE_CHOICE_SOURCE_PREFLIGHT",
        "profiles": rows,
        "task_surface_dispositions": t2_surfaces,
        "checks": {
            "direct_task_authority_present": all_direct,
            "actor_deadline_ack_workflow_present": all(
                row["obligation_count"] > 0 for row in rows.values()
            ),
            "source_fixed_shared_resource_present": any_shared_resource,
            "capability_constraints_present": capabilities_have_declared_constraints,
            "environment_still_explicit_simulator_gap": all_t2_gaps,
        },
        "disposition": disposition,
        "scientific_interpretation": {
            "task_validity": "SUPPORTED",
            "future_choice_method_headroom": "NOT_SOURCE_CLOSED",
            "reason": (
                "The frozen sources define actor/authority chains, deadlines, ACK/retry/alternate-contact semantics, "
                "channel priority and feedback duties, but do not fix a cross-stage contact-capacity/quota/duration/energy "
                "resource whose current consumption would make a later handoff impossible. Under a zero-duration, "
                "independent-channel abstraction the workflow decomposes into ordinary deadline-aware retry/handoff stages."
            ),
        },
        "allowed_next_step": (
            "Only reopen T2 for future-choice hardness after an empirical recipient/channel reachability trace or a "
            "preregistered CONTROLLED_STRESS communication-capacity model is fixed independently of method outcomes."
        ),
        "forbidden_next_step": [
            "Invent a phone/WeChat/SMS shared quota after observing method performance.",
            "Assign arbitrary contact durations or concurrency limits solely to create cross-stage conflict.",
            "Treat the valid 15/15/30 or 30/50 minute deadlines alone as evidence that future-choice hardness exists.",
        ],
    }

    out = ROOT / "local_research/current/benchmark/t2-future-choice-source-preflight.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "out": str(out),
        "disposition": disposition,
        **payload["checks"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
