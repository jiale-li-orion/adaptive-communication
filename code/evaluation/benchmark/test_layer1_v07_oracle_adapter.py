#!/usr/bin/env python3
from __future__ import annotations

from layer1_v07_oracle_adapter import causal_process_from_v07, world_bundle_from_v07


def main() -> int:
    base = {
        "schema_version": "0.7",
        "base_id": "B",
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
                {"world_id": "W-DOWN-UP", "service_by_stage": ["DOWN"]},
            ]
        },
    }
    case = {
        "schema_version": "0.7",
        "base_id": "B",
        "case_id": "C",
        "structure_id": "S",
        "physical_status": "ALL_WORLD_PHYSICAL",
        "fallback_budget_units": 1,
        "gateway_receipt_delay_s": 2,
        "final_ack_delay_s": 4,
        "remote_query": {
            "capability_id": "receipt_summary",
            "owner": "gateway",
            "proposition": "communication.gateway.receipt_summary",
            "response_delay_s": 3,
        },
    }
    bundle = world_bundle_from_v07(base, case)
    process = causal_process_from_v07(base, case)
    assert bundle["bundle_id"] == "C"
    assert process["query_capabilities"][0]["payload_kind"] == "RECEIPT_SUMMARY"
    assert process["resource_contract"]["query_uses_real_opportunity"] is True
    print("PASS v0.7 oracle adapter: schema-only binding reuses shared receipt-summary exact semantics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
