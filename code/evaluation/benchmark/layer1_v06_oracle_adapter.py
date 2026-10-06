#!/usr/bin/env python3
"""Adapt frozen Layer-1 v0.6 pre-oracle cases to the exact AND/OR kernel.

This module is downstream of the official r4 generator. It must not rewrite
generation axes or choose cases by method performance. It only translates the
frozen case/base schema into the already-audited exact execution IR.

Two timing values absent as independent v0.6 axes are derived, not tuned:

* failed SEND_TERR timeout = the case's expected final-ACK delay;
* remote-query timeout = the case's expected query-response delay;
* satellite completion delay = 0 because the v0.6 physical admission treats a
  satellite opportunity timestamp as the completion opportunity itself.

These rules add no new free parameter and are recorded in the oracle contract.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from exact_reference_oracle_v0_1 import solve_observation_matched


class V06OracleAdapterError(ValueError):
    pass


def _terr_windows(base: Mapping[str, Any], service_by_stage: list[str]) -> list[dict[str, Any]]:
    out = []
    for row in base["terrestrial"]["opportunities"]:
        idx = int(row["service_stage_index"])
        if str(service_by_stage[idx]) != "UP":
            continue
        t = int(row["time_s"])
        out.append(
            {
                "window_id": str(row["opportunity_id"]),
                "start_s": t,
                "end_s": t + 1,
                "capacity_units": int(row["capacity_units"]),
                "provenance_class": "CONTROLLED_STRESS",
            }
        )
    return out


def world_bundle_from_v06(base: Mapping[str, Any], case: Mapping[str, Any]) -> dict[str, Any]:
    if str(case["base_id"]) != str(base["base_id"]):
        raise V06OracleAdapterError("case/base mismatch")
    if str(case["physical_status"]) != "ALL_WORLD_PHYSICAL":
        raise V06OracleAdapterError("exact admission only consumes ALL_WORLD_PHYSICAL v0.6 cases")

    obligations = [
        {
            "obligation_id": str(o["oid"]),
            "release_s": int(o["release_s"]),
            "deadline_s": int(o["deadline_s"]),
            "stream": str(o["stream"]),
            "ordinal": int(o["ordinal"]),
        }
        for o in base["composition"]["obligations"]
    ]
    satellite = [
        {
            "window_id": str(w["opportunity_id"]),
            "start_s": int(w["time_s"]),
            "end_s": int(w["window_end_s"]),
            "capacity_units": int(w["capacity_units"]),
            "provenance_class": "MODEL_DERIVED_TRACE",
        }
        for w in base["satellite"]["opportunities"]
        if int(w["window_end_s"]) > int(w["time_s"])
    ]
    worlds = []
    for world in base["service_process"]["worlds"]:
        worlds.append(
            {
                "world_id": str(world["world_id"]),
                "terrestrial_windows": _terr_windows(base, list(world["service_by_stage"])),
            }
        )

    return {
        "schema_version": "0.6-oracle-adapter",
        "bundle_id": str(case["case_id"]),
        "recipe_id": str(case["structure_id"]),
        "stage": "WORLD_BUNDLE_PRE_EVIDENCE_PRE_ORACLE",
        "obligations": obligations,
        "worlds": worlds,
        "public_environment": {
            "horizon_s": int(base["composition"]["horizon_s"]),
            "satellite_windows": satellite,
            "satellite_budget_units": int(case["fallback_budget_units"]),
        },
        "observation_projection": {
            "evidence_regime": "V06_RECEIPT_SUMMARY_QUERY_WITH_NATURAL_FEEDBACK",
            "evidence_surfaces": [
                {"kind": "OWNER_QUERY"},
                {"kind": "PASSIVE_ACK"},
                {"kind": "NORMAL_SEND_AS_PROBE"},
            ],
        },
    }


def causal_process_from_v06(base: Mapping[str, Any], case: Mapping[str, Any]) -> dict[str, Any]:
    bundle = world_bundle_from_v06(base, case)
    q = case["remote_query"]
    query_delay = int(q["response_delay_s"])
    receipt_delay = int(case["gateway_receipt_delay_s"])
    ack_delay = int(case["final_ack_delay_s"])

    world_processes = []
    for world in bundle["worlds"]:
        intervals = [
            [int(w["start_s"]), int(w["end_s"])]
            for w in world["terrestrial_windows"]
        ]
        world_processes.append(
            {
                "world_id": str(world["world_id"]),
                "owner": "gateway",
                "proposition": str(q["proposition"]),
                "terrestrial_intervals": intervals,
                "owner_state_events": [],
                "future_state_visibility": "EVALUATOR_ONLY",
            }
        )

    return {
        "schema_version": "0.6-oracle-adapter",
        "process_id": f"{case['case_id']}::receipt-process",
        "parent_bundle_id": str(case["case_id"]),
        "recipe_id": str(case["structure_id"]),
        "stage": "CAUSAL_EVIDENCE_PRE_ORACLE",
        "evidence_regime": "V06_RECEIPT_SUMMARY_QUERY_WITH_NATURAL_FEEDBACK",
        "direct_observation": False,
        "query_capabilities": [
            {
                "query_id": str(q["capability_id"]),
                "capability_id": str(q["capability_id"]),
                "owner": str(q["owner"]),
                "payload_kind": "RECEIPT_SUMMARY",
                "response_delay_s": query_delay,
                "timeout_s": query_delay,
                "resource_cost": {"terrestrial_window_capacity_units": 1},
                "future_state_access": False,
            }
        ],
        "passive_observation_rules": [
            {
                "evidence_id": "delivery_feedback",
                "gateway_receipt_delay_s": receipt_delay,
                "final_ack_delay_s": ack_delay,
                "negative_observation_after_s": ack_delay,
                "timing_provenance": "DERIVED_FROM_FROZEN_V06_CASE",
            }
        ],
        "normal_send_probe_rules": [
            {
                "evidence_id": "normal_send_probe",
                "action": "SEND_TERR",
                "extra_tool": False,
            }
        ],
        "world_owner_processes": world_processes,
        "resource_contract": {
            "query_uses_real_opportunity": True,
            "query_capacity_units": 1,
            "send_as_probe_has_extra_cost": False,
            "passive_ack_has_acquisition_cost": False,
            "satellite_completion_delay_s": 0,
        },
        "history_contract": {
            "non_anticipative": True,
            "query_payload": "gateway receipts observed at sample time only",
            "future_state_visibility": "FORBIDDEN",
        },
    }


def blind_process(process: Mapping[str, Any]) -> dict[str, Any]:
    blind = deepcopy(dict(process))
    blind["evidence_regime"] = "V06_BLIND_OPEN_LOOP_REFERENCE"
    blind["query_capabilities"] = []
    blind["passive_observation_rules"] = []
    blind["normal_send_probe_rules"] = []
    return blind


def solve_v06_references(
    base: Mapping[str, Any],
    case: Mapping[str, Any],
    *,
    max_memo_nodes: int = 200_000,
) -> dict[str, Any]:
    bundle = world_bundle_from_v06(base, case)
    process = causal_process_from_v06(base, case)
    exact = solve_observation_matched(bundle, process, max_memo_nodes=max_memo_nodes)
    no_query = solve_observation_matched(
        bundle,
        process,
        disable_paid_query=True,
        max_memo_nodes=max_memo_nodes,
    )
    full_current = solve_observation_matched(
        bundle,
        process,
        disable_paid_query=True,
        force_full_current_state=True,
        max_memo_nodes=max_memo_nodes,
    )
    blind = solve_observation_matched(
        bundle,
        blind_process(process),
        disable_paid_query=True,
        max_memo_nodes=max_memo_nodes,
    )
    return {
        "case_id": str(case["case_id"]),
        "base_id": str(base["base_id"]),
        "structure_id": str(case["structure_id"]),
        "references": {
            "full_current": full_current,
            "observation_matched_exact": exact,
            "no_paid_query": no_query,
            "blind_open_loop": blind,
        },
    }

