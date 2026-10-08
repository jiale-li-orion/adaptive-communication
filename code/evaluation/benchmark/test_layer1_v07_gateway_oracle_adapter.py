#!/usr/bin/env python3
"""Conformance tests for the v0.7 gateway-local exact adapter."""
from __future__ import annotations

from layer1_v07_gateway_oracle_adapter import (
    gateway_process_from_v07,
    gateway_structure_id,
)


def main() -> int:
    base = {
        "schema_version": "0.7",
        "base_id": "B",
        "base_structure_id": "BS",
        "composition": {
            "horizon_s": 20,
            "obligations": [
                {"oid": "A0", "release_s": 0, "deadline_s": 10, "stream": "A", "ordinal": 0}
            ],
        },
        "satellite": {
            "opportunities": [
                {"opportunity_id": "sat@5", "time_s": 5, "window_end_s": 6, "capacity_units": 1}
            ]
        },
        "terrestrial": {
            "opportunities": [
                {"opportunity_id": "terr@2", "time_s": 2, "capacity_units": 1, "service_stage_index": 0}
            ]
        },
        "service_process": {
            "worlds": [
                {"world_id": "W-UP", "service_by_stage": ["UP"]},
                {"world_id": "W-DOWN", "service_by_stage": ["DOWN"]},
            ]
        },
    }
    case = {
        "schema_version": "0.7",
        "base_id": "B",
        "case_id": "C0",
        "structure_id": "S0",
        "physical_status": "ALL_WORLD_PHYSICAL",
        "fallback_budget_mode": "TIGHT",
        "fallback_budget_units": 1,
        "feedback_profile": "EARLY_RECEIPT_MID_ACK",
        "gateway_receipt_delay_s": 2,
        "final_ack_delay_s": 4,
        "remote_query": {
            "capability_id": "receipt_summary",
            "response_delay_ratio": 0.25,
            "response_delay_s": 3,
        },
    }
    case_other_query_delay = {
        **case,
        "case_id": "C1",
        "structure_id": "S1",
        "remote_query": {
            **case["remote_query"],
            "response_delay_ratio": 0.5,
            "response_delay_s": 6,
        },
    }

    process = gateway_process_from_v07(base, case)
    assert process["policy_placement"] == "GATEWAY_LOCAL_PRIMARY"
    assert process["query_capabilities"] == []
    local = process["owner_local_state_projections"][0]
    assert local["projection_id"] == "receipt_summary"
    assert local["action"] is False
    assert local["network_resource_cost"] == 0
    assert local["network_delay_s"] == 0
    assert process["resource_contract"]["query_uses_real_opportunity"] is False
    assert process["control_path_contract"]["mode"] == "OWNER_LOCAL"
    assert gateway_structure_id(base, case) == gateway_structure_id(base, case_other_query_delay)

    print(
        "PASS v0.7 gateway adapter: owner-local receipt visibility, local control and "
        "query-delay dedupe follow the frozen placement contract"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
