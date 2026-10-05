#!/usr/bin/env python3
"""Thin lossless Layer-1 v0.2 -> frozen Layer-2 v1 contract binding.

The binding translates public benchmark semantics only:

* source-grounded obligation contracts -> v1 ``TaskContract``;
* benchmark-defined legal next actions -> v1 candidate plans / typed invocations;
* public owner query -> a v1 observation capability row.

It deliberately does **not** compute future feasibility, EvidenceNeed, oracle
labels, hidden-world identity or recommended actions.  All legal actions are
materialized as ``conditional`` candidates so a downstream method must still
decide which action preserves the task.
"""
from __future__ import annotations

import json
from typing import Any, Mapping

from agentic_communication.runtime_contracts import EffectCeiling, TaskContract, TaskKind
from causal_evidence_process_v0_1 import attach_causal_evidence
from exact_reference_oracle_v0_1 import LocalState
from v8_policy_baselines_v0_1 import _legal_actions


Action = tuple[str, str | None]

CAP_WAIT = "layer1.v02.wait"
CAP_SEND_TERR = "layer1.v02.send_terr"
CAP_SEND_SAT = "layer1.v02.send_sat"
CAP_GATEWAY_SUMMARY = "communication.gateway.state_summary"


def _json_safe(value: Any) -> Any:
    """Normalize tuples/enums/etc. into the v1 JsonValue surface without dropping fields."""

    return json.loads(json.dumps(value, ensure_ascii=False))


def task_contract_from_bundle(bundle: Mapping[str, Any]) -> TaskContract:
    obligations = [_json_safe(dict(row)) for row in bundle["obligations"]]
    public = bundle["public_environment"]
    return TaskContract(
        task_contract_id=f"layer1-v02:{bundle['recipe_id']}",
        contract_revision=1,
        principal="external-emergency-monitoring-authority",
        task_kind=TaskKind.CONTROL,
        target_resources=["gw0"],
        desired_state={
            "family": str(bundle["family"]),
            "obligations": obligations,
            "completion_semantics": "all_applicable_obligations_by_deadline",
        },
        evidence_contract={
            "lawful_paid_query": "gateway_state_summary",
            "passive_feedback": ["gateway_receipt", "final_ack", "timeout"],
            "normal_send_as_probe": True,
            "future_service_schedule_visible": False,
        },
        output_contract={
            "decision_surface": "legal_action_candidates",
            "oracle_fields_exposed": False,
        },
        temporal_contract={
            "horizon_s": int(public["horizon_s"]),
            "satellite_windows": [_json_safe(dict(row)) for row in public["satellite_windows"]],
            "satellite_budget_units": int(public["satellite_budget_units"]),
            "terrestrial_process_class": str(public["terrestrial_process_class"]),
        },
        effect_ceiling=EffectCeiling.EXTERNAL_SIDE_EFFECT,
        completion_predicate={
            "type": "all_obligations_completed_by_deadline",
            "obligation_ids": [str(row["obligation_id"]) for row in obligations],
        },
        policy_revision="layer1-v0.2-retry-legality-binding-v1",
    )


def capability_catalog_rows() -> list[dict[str, Any]]:
    """Model-visible synthetic bindings for evaluation; no implementation authority."""

    return [
        {
            "capability_id": CAP_WAIT,
            "action": "wait_until_next_declared_event",
            "effect_semantics": "external_side_effect",
            "binding_scope": "evaluation_only_layer1_v02",
        },
        {
            "capability_id": CAP_SEND_TERR,
            "action": "send_obligation_over_terrestrial",
            "effect_semantics": "external_side_effect",
            "binding_scope": "evaluation_only_layer1_v02",
        },
        {
            "capability_id": CAP_SEND_SAT,
            "action": "send_obligation_over_satellite",
            "effect_semantics": "external_side_effect",
            "binding_scope": "evaluation_only_layer1_v02",
        },
        {
            "capability_id": CAP_GATEWAY_SUMMARY,
            "action": "observe_gateway_state_summary",
            "effect_semantics": "observation",
            "binding_scope": "evaluation_only_layer1_v02",
        },
    ]


def _plan_id(action: Action) -> str:
    kind, arg = action
    return f"layer1-v02::{kind}::{arg if arg is not None else '-'}"


def invocation_from_action(action: Action) -> dict[str, Any]:
    kind, arg = action
    if kind == "WAIT":
        return {"capability_id": CAP_WAIT, "resource": "task-clock", "canonical_arguments": {}}
    if kind == "SEND_TERR":
        oid = str(arg)
        return {
            "capability_id": CAP_SEND_TERR,
            "resource": oid,
            "canonical_arguments": {"obligation_id": oid},
        }
    if kind == "SEND_SAT":
        oid = str(arg)
        return {
            "capability_id": CAP_SEND_SAT,
            "resource": oid,
            "canonical_arguments": {"obligation_id": oid},
        }
    if kind == "ISSUE_QUERY" and arg == "gateway_state_summary":
        return {
            "capability_id": CAP_GATEWAY_SUMMARY,
            "resource": "gw0",
            "canonical_arguments": {"gateway_id": "gw0"},
        }
    raise ValueError(f"unbound Layer-1 action: {action!r}")


def action_from_invocation(row: Mapping[str, Any]) -> Action:
    cid = str(row["capability_id"])
    args = row.get("canonical_arguments") or {}
    if cid == CAP_WAIT:
        return ("WAIT", None)
    if cid == CAP_SEND_TERR:
        return ("SEND_TERR", str(args["obligation_id"]))
    if cid == CAP_SEND_SAT:
        return ("SEND_SAT", str(args["obligation_id"]))
    if cid == CAP_GATEWAY_SUMMARY:
        return ("ISSUE_QUERY", "gateway_state_summary")
    raise ValueError(f"unknown evaluation binding capability: {cid}")


def candidate_context_from_boundary(
    bundle: Mapping[str, Any],
    *,
    at_s: int,
    states: Mapping[str, LocalState],
) -> dict[str, Any]:
    process = attach_causal_evidence(bundle)
    legal = _legal_actions(bundle, process, states, at_s)
    plans = []
    for action in legal:
        plans.append(
            {
                "plan_id": _plan_id(action),
                "kind": action[0].lower(),
                "feasibility": "conditional",
                "legal_now": True,
                "unresolved_conditions": [],
                "support_refs": [],
                "invocations": [invocation_from_action(action)],
                "binding_note": "legal action only; no future-feasibility or oracle label",
            }
        )
    common_sat_budget = sorted({int(st.satellite_budget) for st in states.values()})
    return {
        "schema_version": "layer1-v02-v1-binding-v1",
        "time_s": int(at_s),
        "candidate_plans": plans,
        "dependencies": [],
        "decision_sufficiency": {
            "status": "UNRESOLVED_BY_BINDING",
            "primary_plan_id": None,
            "reason": "binding preserves legality only; downstream method owns sufficiency",
        },
        "public_resource_summary": {
            "satellite_budget_units": common_sat_budget,
        },
        "hidden_state_exposed": False,
    }
