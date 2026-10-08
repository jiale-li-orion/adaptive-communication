#!/usr/bin/env python3
"""Gateway-local exact-reference adapter for frozen Layer-1 v0.7 cases.

The adapter consumes the frozen pre-oracle universe without modifying generator
axes.  It implements only the placement admitted by
PLACEMENT-VISIBILITY-CONTRACT.v0.1.json:

* gateway receipt/queue/resource state is owner-local;
* receipt-summary is a state projection, not a paid communication action;
* SEND_TERR / SEND_SAT / WAIT execute locally at the gateway;
* future service transitions and final center completion remain hidden until
  lawful feedback arrives.

Center placement is intentionally absent and remains a simulator gap.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping

from exact_reference_oracle_v0_1 import solve_observation_matched
from layer1_v06_oracle_adapter import world_bundle_from_v06


PLACEMENT = "GATEWAY_LOCAL_PRIMARY"


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def gateway_structure_id(base: Mapping[str, Any], case: Mapping[str, Any]) -> str:
    """Placement-specific structure identity.

    Remote-query delay is intentionally absent: receipt-summary is owner-local
    at the gateway and v0.7 query-delay variants are therefore exact duplicates
    under this placement.
    """

    payload = {
        "placement": PLACEMENT,
        "base_structure_id": str(base["base_structure_id"]),
        "feedback_profile": str(case["feedback_profile"]),
        "fallback_budget_mode": str(case["fallback_budget_mode"]),
    }
    return "T1V07GW-" + sha256(_canonical(payload)).hexdigest()[:16]


def gateway_process_from_v07(
    base: Mapping[str, Any],
    case: Mapping[str, Any],
) -> dict[str, Any]:
    bundle = world_bundle_from_v06(base, case)
    receipt_delay = int(case["gateway_receipt_delay_s"])
    ack_delay = int(case["final_ack_delay_s"])

    world_processes = []
    for world in bundle["worlds"]:
        intervals = [
            [int(window["start_s"]), int(window["end_s"])]
            for window in world["terrestrial_windows"]
        ]
        world_processes.append(
            {
                "world_id": str(world["world_id"]),
                "owner": "gateway",
                "proposition": "communication.gateway.local_execution_state",
                "terrestrial_intervals": intervals,
                "owner_state_events": [],
                "future_state_visibility": "EVALUATOR_ONLY",
            }
        )

    return {
        "schema_version": "0.7-gateway-local",
        "process_id": f"{case['case_id']}::gateway-local-process",
        "parent_bundle_id": str(case["case_id"]),
        "recipe_id": str(case["structure_id"]),
        "stage": "CAUSAL_EVIDENCE_PRE_ORACLE",
        "policy_placement": PLACEMENT,
        "evidence_regime": "GATEWAY_LOCAL_NATURAL_FEEDBACK",
        "direct_observation": False,
        "query_capabilities": [],
        "owner_local_state_projections": [
            {
                "projection_id": "receipt_summary",
                "owner": "gateway",
                "action": False,
                "network_resource_cost": 0,
                "network_delay_s": 0,
                "payload_rule": "gateway receipts that have occurred by observation time",
            }
        ],
        "passive_observation_rules": [
            {
                "evidence_id": "delivery_feedback",
                "trigger": "EXECUTED_TERRESTRIAL_SEND",
                "gateway_receipt_delay_s": receipt_delay,
                "final_ack_delay_s": ack_delay,
                "negative_observation_after_s": ack_delay,
                "timing_provenance": "FROZEN_V07_CASE",
            }
        ],
        "normal_send_probe_rules": [
            {
                "evidence_id": "normal_send_probe",
                "action": "SEND_TERR",
                "extra_tool": False,
                "observation": "gateway_receipt_final_ack_or_timeout",
            }
        ],
        "world_owner_processes": world_processes,
        "control_path_contract": {
            "mode": "OWNER_LOCAL",
            "send_command_delay_s": 0,
            "send_command_resource_cost": 0,
        },
        "resource_contract": {
            "query_uses_real_opportunity": False,
            "query_capacity_units": 0,
            "send_as_probe_has_extra_cost": False,
            "passive_ack_has_acquisition_cost": False,
            "satellite_completion_delay_s": 0,
        },
        "history_contract": {
            "non_anticipative": True,
            "gateway_receipt_visibility": "OWNER_LOCAL_AFTER_RECEIPT_EVENT",
            "final_center_completion_visibility": "ONLY_AFTER_FINAL_ACK_OR_TIMEOUT",
            "future_service_visibility": "FORBIDDEN",
            "same_observable_history_same_action_required": True,
        },
    }


def blind_gateway_process(process: Mapping[str, Any]) -> dict[str, Any]:
    blind = deepcopy(dict(process))
    blind["evidence_regime"] = "GATEWAY_LOCAL_BLIND_OPEN_LOOP_REFERENCE"
    blind["passive_observation_rules"] = []
    blind["normal_send_probe_rules"] = []
    blind["owner_local_state_projections"] = []
    return blind


def solve_gateway_reference(
    base: Mapping[str, Any],
    case: Mapping[str, Any],
    reference: str,
    *,
    max_memo_nodes: int = 200_000,
) -> dict[str, Any]:
    bundle = world_bundle_from_v06(base, case)
    process = gateway_process_from_v07(base, case)

    if reference == "blind_open_loop":
        return solve_observation_matched(
            bundle,
            blind_gateway_process(process),
            disable_paid_query=True,
            max_memo_nodes=max_memo_nodes,
        )
    if reference == "full_current":
        return solve_observation_matched(
            bundle,
            process,
            disable_paid_query=True,
            force_full_current_state=True,
            max_memo_nodes=max_memo_nodes,
        )
    if reference == "natural_feedback":
        return solve_observation_matched(
            bundle,
            process,
            disable_paid_query=True,
            max_memo_nodes=max_memo_nodes,
        )
    raise ValueError(f"unknown gateway-local reference {reference!r}")

