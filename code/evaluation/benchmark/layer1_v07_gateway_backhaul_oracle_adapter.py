#!/usr/bin/env python3
"""Corrected gateway-backhaul adapter for frozen Layer-1 v0.7 ingredients.

This is a bounded correctness adapter, not benchmark admission.  It consumes a
v0.7 base/case only after applying the frozen
T1-GATEWAY-DATA-LIFECYCLE-CONTRACT.v0.1 scope:

* each released obligation is conditionally available in the gateway queue;
* primary/fallback actions originate at the gateway;
* primary forwarding never creates a new gateway receipt;
* center ACK/timeout remains asynchronous completion feedback;
* old gateway-receipt delay is inactive in this slice.

The generic exact kernel still uses SEND_TERR/SEND_SAT as internal opcodes.
Policy witnesses are externalized as FORWARD_PRIMARY/FORWARD_FALLBACK so the
public action contract cannot drift back to the historical end-to-end names.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from exact_reference_oracle_v0_1 import solve_observation_matched
from layer1_v06_oracle_adapter import world_bundle_from_v06


PLACEMENT = "GATEWAY_LOCAL_PRIMARY"
SCOPE = "T1_GATEWAY_BACKHAUL_CONTINUITY"


def gateway_backhaul_process_from_v07(
    base: Mapping[str, Any],
    case: Mapping[str, Any],
) -> dict[str, Any]:
    bundle = world_bundle_from_v06(base, case)
    ack_delay = int(case["final_ack_delay_s"])
    worlds = []
    for world in bundle["worlds"]:
        intervals = [
            [int(window["start_s"]), int(window["end_s"])]
            for window in world["terrestrial_windows"]
        ]
        worlds.append(
            {
                "world_id": str(world["world_id"]),
                "owner": "gateway_communication_subsystem",
                "proposition": "communication.gateway.primary_backhaul_state",
                "terrestrial_intervals": intervals,
                "owner_state_events": [],
                "future_state_visibility": "EVALUATOR_ONLY",
            }
        )

    return {
        "schema_version": "0.7-gateway-backhaul-correctness",
        "process_id": f"{case['case_id']}::gateway-backhaul-process",
        "parent_bundle_id": str(case["case_id"]),
        "recipe_id": str(case["structure_id"]),
        "stage": "CORRECTED_GATEWAY_BACKHAUL_PRE_ADMISSION",
        "policy_placement": PLACEMENT,
        "scope_contract": SCOPE,
        "conditional_entry_boundary": "REPORT_ALREADY_GATEWAY_READY_AT_RELEASE",
        "direct_observation": False,
        "query_capabilities": [],
        "owner_local_state_projections": [
            {
                "projection_id": "gateway_queue_and_send_log",
                "owner": "gateway",
                "network_resource_cost": 0,
                "network_delay_s": 0,
            }
        ],
        "passive_observation_rules": [
            {
                "evidence_id": "center_completion_feedback",
                "trigger": "EXECUTED_GATEWAY_FORWARD",
                "gateway_receipt_delay_s": 0,
                "final_ack_delay_s": ack_delay,
                "negative_observation_after_s": ack_delay,
                "timing_provenance": "FROZEN_V07_FINAL_ACK_AXIS_ONLY",
            }
        ],
        "normal_send_probe_rules": [
            {
                "evidence_id": "primary_forward_as_probe",
                "action": "FORWARD_PRIMARY",
                "kernel_action": "SEND_TERR",
                "extra_tool": False,
                "observation": "center_ack_or_timeout",
            }
        ],
        "world_owner_processes": worlds,
        "control_path_contract": {
            "mode": "OWNER_LOCAL_GATEWAY_FORWARDING",
            "send_command_delay_s": 0,
            "send_command_resource_cost": 0,
            "claim_boundary": "Local forwarding only; no node-uplink control is implied.",
        },
        "resource_contract": {
            "primary_generates_gateway_receipt": False,
            "send_as_probe_has_extra_cost": False,
            "passive_ack_has_acquisition_cost": False,
            "satellite_completion_delay_s": 0,
        },
        "history_contract": {
            "non_anticipative": True,
            "report_location_at_release": "GATEWAY_READY_CONDITIONAL_SLICE",
            "gateway_receipt_visibility": "ENTRY_EVENT_PRECEDES_GATEWAY_FORWARDING",
            "center_completion_visibility": "ONLY_AFTER_ACK_OR_TIMEOUT",
            "future_service_visibility": "FORBIDDEN",
            "same_observable_history_same_action_required": True,
        },
        "legacy_axis_projection": {
            "gateway_receipt_delay_s": "INACTIVE_IN_GATEWAY_BACKHAUL_SLICE",
            "remote_query": "INACTIVE_AT_GATEWAY_PLACEMENT",
        },
    }


def blind_gateway_backhaul_process(process: Mapping[str, Any]) -> dict[str, Any]:
    out = deepcopy(dict(process))
    out["passive_observation_rules"] = []
    out["normal_send_probe_rules"] = []
    out["owner_local_state_projections"] = []
    out["stage"] = "CORRECTED_GATEWAY_BACKHAUL_BLIND_REFERENCE"
    return out


def _externalize_policy(node: dict[str, Any] | None) -> dict[str, Any] | None:
    if node is None:
        return None
    out = deepcopy(node)
    if out.get("action") == "SEND_TERR":
        out["action"] = "FORWARD_PRIMARY"
    elif out.get("action") == "SEND_SAT":
        out["action"] = "FORWARD_FALLBACK"
    if "subpolicy" in out:
        out["subpolicy"] = _externalize_policy(out["subpolicy"])
    if out.get("event") == "OBSERVATION":
        for child in out.get("children", []):
            child["subpolicy"] = _externalize_policy(child.get("subpolicy"))
    return out


def solve_gateway_backhaul_reference(
    base: Mapping[str, Any],
    case: Mapping[str, Any],
    reference: str,
    *,
    max_memo_nodes: int = 50_000,
) -> dict[str, Any]:
    bundle = world_bundle_from_v06(base, case)
    process = gateway_backhaul_process_from_v07(base, case)
    if reference == "blind_open_loop":
        result = solve_observation_matched(
            bundle,
            blind_gateway_backhaul_process(process),
            disable_paid_query=True,
            max_memo_nodes=max_memo_nodes,
        )
    elif reference == "full_current":
        result = solve_observation_matched(
            bundle,
            process,
            disable_paid_query=True,
            force_full_current_state=True,
            max_memo_nodes=max_memo_nodes,
        )
    elif reference == "natural_feedback":
        result = solve_observation_matched(
            bundle,
            process,
            disable_paid_query=True,
            max_memo_nodes=max_memo_nodes,
        )
    else:
        raise ValueError(reference)
    result = deepcopy(result)
    result["policy"] = _externalize_policy(result.get("policy"))
    result["placement"] = PLACEMENT
    result["scope_contract"] = SCOPE
    return result
