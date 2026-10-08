#!/usr/bin/env python3
"""Correctness smoke for the gateway-backhaul action/data-location contract."""
from __future__ import annotations

import json

from layer1_v07_gateway_backhaul_oracle_adapter import (
    gateway_backhaul_process_from_v07,
    solve_gateway_backhaul_reference,
)
from layer1_v06_oracle_adapter import world_bundle_from_v06
from v8_policy_baselines_v0_1 import _choose_least_slack, _execute_policy


def _base() -> dict:
    return {
        "schema_version": "0.7",
        "base_id": "B",
        "base_structure_id": "BS",
        "composition": {
            "horizon_s": 16,
            "obligations": [
                {"oid": "A", "release_s": 0, "deadline_s": 6, "stream": "A", "ordinal": 0},
                {"oid": "B", "release_s": 7, "deadline_s": 15, "stream": "B", "ordinal": 0},
            ],
        },
        "satellite": {
            "opportunities": [
                {"opportunity_id": "sat@5", "time_s": 5, "window_end_s": 6, "capacity_units": 1},
                {"opportunity_id": "sat@12", "time_s": 12, "window_end_s": 13, "capacity_units": 1},
            ]
        },
        "terrestrial": {
            "opportunities": [
                {"opportunity_id": "primary@2", "time_s": 2, "capacity_units": 1, "service_stage_index": 0},
                {"opportunity_id": "primary@9", "time_s": 9, "capacity_units": 1, "service_stage_index": 1},
            ]
        },
        "service_process": {
            "worlds": [
                {"world_id": "EARLY", "service_by_stage": ["UP", "DOWN"]},
                {"world_id": "LATE", "service_by_stage": ["DOWN", "UP"]},
            ]
        },
    }


def _case(receipt_delay: int) -> dict:
    return {
        "schema_version": "0.7",
        "base_id": "B",
        "case_id": f"C-{receipt_delay}",
        "structure_id": "S",
        "physical_status": "ALL_WORLD_PHYSICAL",
        "fallback_budget_mode": "TIGHT",
        "fallback_budget_units": 1,
        "feedback_profile": "SMOKE",
        "gateway_receipt_delay_s": receipt_delay,
        "final_ack_delay_s": 0,
        "remote_query": {"capability_id": "receipt_summary", "response_delay_s": 3},
    }


def _policy_text(result: dict) -> str:
    return json.dumps(result.get("policy"), ensure_ascii=False, sort_keys=True)


def main() -> int:
    base = _base()
    case0 = _case(0)
    case999 = _case(999)
    process = gateway_backhaul_process_from_v07(base, case999)
    assert process["resource_contract"]["primary_generates_gateway_receipt"] is False
    assert process["legacy_axis_projection"]["gateway_receipt_delay_s"] == "INACTIVE_IN_GATEWAY_BACKHAUL_SLICE"
    assert process["query_capabilities"] == []

    blind = solve_gateway_backhaul_reference(base, case0, "blind_open_loop")
    natural = solve_gateway_backhaul_reference(base, case0, "natural_feedback")
    natural_other_receipt_delay = solve_gateway_backhaul_reference(base, case999, "natural_feedback")
    assert blind["status"] == "EXACT" and blind["solvable"] is False
    assert natural["status"] == "EXACT" and natural["solvable"] is True
    text = _policy_text(natural)
    assert "FORWARD_PRIMARY" in text and "FORWARD_FALLBACK" in text
    assert "SEND_TERR" not in text and "SEND_SAT" not in text
    assert "gateway_receipt:" not in text
    assert "final_ack:" in text
    assert natural["solvable"] == natural_other_receipt_delay["solvable"]
    assert natural["memo_nodes"] == natural_other_receipt_delay["memo_nodes"]
    assert _policy_text(natural) == _policy_text(natural_other_receipt_delay)

    # Ordinary baselines must consume the same corrected process.  This smoke
    # only checks event semantics, not that least-slack solves the fixture.
    bundle = world_bundle_from_v06(base, case0)
    baseline = _execute_policy(
        bundle,
        _choose_least_slack,
        process=gateway_backhaul_process_from_v07(base, case0),
    )
    trace_text = json.dumps(baseline, ensure_ascii=False, sort_keys=True)
    assert "gateway_receipt:" not in trace_text

    print(
        "PASS corrected gateway backhaul adapter: report starts gateway-ready; "
        "primary/fallback forwarding is local; center ACK/timeout is feedback; "
        "legacy gateway-receipt delay is inactive"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
