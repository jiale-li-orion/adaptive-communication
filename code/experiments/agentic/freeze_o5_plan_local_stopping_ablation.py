#!/usr/bin/env python3
"""Freeze a three-event O5 ablation for plan-local EvidenceNeed stopping.

The source envelopes are the already-frozen O5 action-conditioned compact
inputs.  Task, evidence, capabilities and candidate actions stay byte-for-byte
shared at the source level.  The five arms isolate the two semantics that were
confounded in the first h8 diagnosis:

1. baseline: no plan-local EvidenceNeed semantics;
2. binding_only: open fallback needs carry ``blocking_plan_ids``;
3. rule_only: planner is told unresolved alternative evidence is non-blocking;
4. plan_local_blocking: binding + explicit rule;
5. sufficiency_stop: plan-local blocking + Runtime closure certificate.

This is a model-diagnosis dev set.  It does not change simulator physics or
gold actions and therefore cannot by itself support a physical-outcome claim.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = ROOT / "results" / "agentic" / "o5-context-transition-devset-v1"
OUT = ROOT / "results" / "agentic" / "o5-plan-local-stopping-devset-v1"
BASE_CONTEXT = "action_conditioned_compact"
FALLBACK_PLAN = "consider_gateway_backup"
PRIMARY_PLAN = "install_required_profile"

PLAN_LOCAL_RULE = (
    "An open evidence_need blocks only the candidate plans listed in its blocking_plan_ids; "
    "it does not block another supported plan whose own guards are already resolved."
)
RULE_ONLY = (
    "Treat each unresolved evidence need as local to the alternative candidate it distinguishes; "
    "do not delay an already-supported plan whose own unresolved_conditions are empty."
)
SUFFICIENCY_RULE = (
    "When decision_sufficiency.status is sufficient_for_primary_action, execute the supported "
    "primary plan now; nonblocking open needs may be investigated later and must not delay it."
)


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def bind_open_needs(env: dict, *, include_scope: bool) -> list[str]:
    bound: list[str] = []
    for need in env.get("evidence_needs", []):
        if need.get("status") != "open":
            continue
        need["blocking_plan_ids"] = [FALLBACK_PLAN]
        if include_scope:
            need["blocking_scope"] = "plan_local"
        bound.append(str(need.get("need_id")))
    return bound


def candidate(env: dict, plan_id: str) -> dict:
    plans = (env.get("candidate_action_context") or {}).get("candidate_plans", [])
    matches = [p for p in plans if p.get("plan_id") == plan_id]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {plan_id!r} candidate, got {len(matches)}")
    return matches[0]


def make_variants(base: dict) -> dict[str, dict]:
    primary = candidate(base, PRIMARY_PLAN)
    fallback = candidate(base, FALLBACK_PLAN)
    if primary.get("feasibility") != "supported" or primary.get("unresolved_conditions"):
        raise ValueError("O5 stopping probe requires a supported, guard-closed primary plan")
    if fallback.get("feasibility") != "conditional":
        raise ValueError("O5 stopping probe requires a conditional gateway-backup alternative")

    variants: dict[str, dict] = {BASE_CONTEXT: copy.deepcopy(base)}

    binding = copy.deepcopy(base)
    bind_open_needs(binding, include_scope=False)
    variants["binding_only"] = binding

    rule = copy.deepcopy(base)
    rule.setdefault("planner_rules", []).append(RULE_ONLY)
    variants["rule_only"] = rule

    plan_local = copy.deepcopy(base)
    bound_ids = bind_open_needs(plan_local, include_scope=True)
    plan_local.setdefault("planner_rules", []).append(PLAN_LOCAL_RULE)
    variants["plan_local_blocking"] = plan_local

    sufficient = copy.deepcopy(plan_local)
    sufficient["decision_sufficiency"] = {
        "status": "sufficient_for_primary_action",
        "primary_plan_id": PRIMARY_PLAN,
        "primary_plan_feasibility": primary.get("feasibility"),
        "primary_unresolved_conditions": list(primary.get("unresolved_conditions") or []),
        "nonblocking_open_need_ids": bound_ids,
        "nonblocking_reason": (
            "these open needs only distinguish the optional gateway-backup alternative; "
            "they do not change the already-supported current Task configuration action"
        ),
    }
    sufficient.setdefault("planner_rules", []).append(SUFFICIENCY_RULE)
    variants["sufficiency_stop"] = sufficient
    return variants


def main() -> int:
    manifest = json.loads((SOURCE_ROOT / "manifest.json").read_text(encoding="utf-8"))
    contexts = [
        BASE_CONTEXT,
        "binding_only",
        "rule_only",
        "plan_local_blocking",
        "sufficiency_stop",
    ]
    for event in manifest["events"]:
        event_id = event["event_id"]
        base = json.loads(
            (SOURCE_ROOT / "inputs" / event_id / f"{BASE_CONTEXT}.json").read_text(
                encoding="utf-8"
            )
        )
        variants = make_variants(base)
        for name in contexts:
            dump(OUT / "inputs" / event_id / f"{name}.json", variants[name])

    out_manifest = {
        "experiment": "o5-plan-local-stopping-devset-v1",
        "source": str((SOURCE_ROOT / "manifest.json").relative_to(ROOT)),
        "events": manifest["events"],
        "contexts": contexts,
        "invariant": (
            "Task, evidence, capabilities and candidate actions are fixed; only EvidenceNeed-to-plan "
            "binding, stopping semantics and explicit sufficiency metadata differ."
        ),
        "claim_ceiling": "Three-event single-model diagnostic only.",
    }
    dump(OUT / "manifest.json", out_manifest)
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
