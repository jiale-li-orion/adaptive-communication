#!/usr/bin/env python3
"""Freeze four h8 counterfactual Contexts for decision-sufficiency diagnosis.

All variants preserve the same Task, evidence and capability surface.  They only
change whether open EvidenceNeed objects are scoped to the optional fallback plan
and whether Runtime exposes an explicit decision-sufficiency certificate.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = ROOT / "results" / "agentic" / "o5-context-transition-devset-v1"
OUT = ROOT / "results" / "agentic" / "o5-decision-sufficiency-devset-v1"
EVENT = "backhaul_recovery_before_task_recovery"
FALLBACK_PLAN = "consider_gateway_backup"
PRIMARY_PLAN = "install_required_profile"


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def bind_open_needs_to_fallback(env: dict) -> None:
    for need in env.get("evidence_needs", []):
        if need.get("status") == "open":
            need["blocking_plan_ids"] = [FALLBACK_PLAN]
            need["blocking_scope"] = "plan_local"
    env.setdefault("planner_rules", []).append(
        "An open evidence_need blocks only the candidate plans listed in its blocking_plan_ids; "
        "it does not block another supported plan whose own guards are already resolved."
    )


def remove_fallback(env: dict) -> None:
    ctx = env.get("candidate_action_context") or {}
    ctx["candidate_plans"] = [
        p for p in ctx.get("candidate_plans", []) if p.get("plan_id") != FALLBACK_PLAN
    ]
    env["evidence_needs"] = [
        need
        for need in env.get("evidence_needs", [])
        if need.get("purpose")
        not in {
            "compare primary-path continuation with gateway-backup execution",
            "separate access receipt from center-side delivery loss before fallback",
        }
    ]
    state = env.get("investigation_state") or {}
    open_need_ids = {need.get("need_id") for need in env.get("evidence_needs", [])}
    state["open_need_ids"] = [
        x for x in state.get("open_need_ids", []) if x in open_need_ids
    ]


def main() -> int:
    source_manifest = json.loads((SOURCE_ROOT / "manifest.json").read_text(encoding="utf-8"))
    source_event = next(x for x in source_manifest["events"] if x["event_id"] == EVENT)
    base = json.loads(
        (SOURCE_ROOT / "inputs" / EVENT / "action_conditioned_compact.json").read_text(
            encoding="utf-8"
        )
    )

    variants: dict[str, dict] = {}
    variants["action_conditioned_compact"] = copy.deepcopy(base)

    scoped = copy.deepcopy(base)
    bind_open_needs_to_fallback(scoped)
    variants["plan_local_blocking"] = scoped

    sufficient = copy.deepcopy(scoped)
    ctx = sufficient.get("candidate_action_context") or {}
    primary = next(p for p in ctx.get("candidate_plans", []) if p.get("plan_id") == PRIMARY_PLAN)
    open_ids = [
        need.get("need_id")
        for need in sufficient.get("evidence_needs", [])
        if need.get("status") == "open"
    ]
    sufficient["decision_sufficiency"] = {
        "status": "sufficient_for_primary_action",
        "primary_plan_id": PRIMARY_PLAN,
        "primary_plan_feasibility": primary.get("feasibility"),
        "primary_unresolved_conditions": list(primary.get("unresolved_conditions") or []),
        "nonblocking_open_need_ids": open_ids,
        "nonblocking_reason": (
            "these open needs only distinguish the optional gateway-backup alternative; "
            "they do not change the already-supported current Task configuration action"
        ),
    }
    sufficient.setdefault("planner_rules", []).append(
        "When decision_sufficiency.status is sufficient_for_primary_action, execute the supported "
        "primary plan now; nonblocking open needs may be investigated later and must not delay it."
    )
    variants["sufficiency_stop"] = sufficient

    stripped = copy.deepcopy(base)
    remove_fallback(stripped)
    variants["remove_fallback"] = stripped

    for name, env in variants.items():
        dump(OUT / "inputs" / EVENT / f"{name}.json", env)

    manifest = {
        "experiment": "o5-decision-sufficiency-devset-v1",
        "source": str((SOURCE_ROOT / "manifest.json").relative_to(ROOT)),
        "events": [source_event],
        "contexts": list(variants),
        "invariant": (
            "TaskContract, evidence payloads, capabilities, current physical observation and gold action "
            "remain fixed across arms; only plan-local blocking/stopping semantics change."
        ),
        "claim_ceiling": (
            "Single-event counterfactual model diagnosis. No general model-quality or physical-outcome claim."
        ),
    }
    dump(OUT / "manifest.json", manifest)
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
