"""Frozen model-facing protocol for Agentic Communication planners.

The protocol contains only Runtime-owned, legally materialized artifacts.  It
does not serialize evaluator WorldSnapshot, simulator truth, future exogenous
traces, raw Instance objects, or scorer internals.
"""
from __future__ import annotations

from hashlib import sha256
import json

from .runtime_contracts import PlannerDecisionProposal, PromptAssembly


PROTOCOL_REVISION = "communication-planner-json-v1"


def _fragments(assembly: PromptAssembly) -> dict[str, object]:
    return {fragment.kind: fragment.content for fragment in assembly.fragments}


def render_planner_protocol(assembly: PromptAssembly) -> dict:
    fragments = _fragments(assembly)
    has_harness_state = (
        "investigation_state" in fragments or "evidence_needs" in fragments
    )
    planner_rules = [
        "Use only capabilities present in capabilities.",
        "Use only evidence present in this envelope; missing, stale and unreachable are distinct states.",
    ]
    if has_harness_state:
        planner_rules.append(
            "Observation capabilities may be used to resolve an open evidence need before choosing a device effect."
        )
    else:
        planner_rules.append(
            "Observation capabilities may be used when additional evidence is required before choosing a device effect."
        )
    planner_rules.extend(
        [
            "External side effects must remain within the Runtime TaskContract effect ceiling.",
            "Set stop=true only when no capability invocation is needed for the current runtime state.",
            "Do not invent device state, path reachability, future opportunities, or execution confirmation.",
        ]
    )
    payload = {
        "protocol_revision": PROTOCOL_REVISION,
        "assembly": {
            "assembly_id": assembly.assembly_id,
            "assembly_hash": assembly.assembly_hash,
            "task_run_id": assembly.task_run_id,
            "context_manifest_revision": assembly.context_manifest_revision,
        },
        "task_contract": fragments.get("runtime_task_contract", {}),
        "resource_inventory": fragments.get("resource_inventory", []),
        "evidence": fragments.get("evidence_slice", []),
        "recent_capability_outcomes": fragments.get("recent_capability_outcomes", []),
        "capabilities": fragments.get("capability_catalog", []),
        "planner_rules": planner_rules,
        "output_schema": PlannerDecisionProposal.model_json_schema(),
    }
    if "investigation_state" in fragments:
        payload["investigation_state"] = fragments["investigation_state"]
    if "evidence_needs" in fragments:
        payload["evidence_needs"] = fragments["evidence_needs"]
    return payload


def protocol_bytes(assembly: PromptAssembly) -> bytes:
    return json.dumps(
        render_planner_protocol(assembly),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def protocol_hash(assembly: PromptAssembly) -> str:
    return sha256(protocol_bytes(assembly)).hexdigest()


def assert_no_evaluator_leakage(payload: dict) -> None:
    """Fail loudly if evaluator-only concepts enter a model envelope."""
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()
    forbidden = (
        "worldsnapshot",
        "world_snapshot",
        "hidden_truth",
        "simulator_truth",
        "future_exogenous",
        "oracle_action",
        "scorer_internal",
    )
    leaked = [token for token in forbidden if token in raw]
    if leaked:
        raise ValueError("evaluator-only leakage in model protocol: " + ",".join(leaked))
