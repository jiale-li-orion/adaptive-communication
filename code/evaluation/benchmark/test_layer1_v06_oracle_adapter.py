#!/usr/bin/env python3
from __future__ import annotations

from layer1_v06_oracle_adapter import (
    causal_process_from_v06,
    world_bundle_from_v06,
)


def main() -> int:
    base = {
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
                {"world_id": "W-DOWN", "service_by_stage": ["DOWN"]},
            ]
        },
    }
    case = {
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
    bundle = world_bundle_from_v06(base, case)
    process = causal_process_from_v06(base, case)
    up = next(w for w in bundle["worlds"] if w["world_id"] == "W-UP")
    down = next(w for w in bundle["worlds"] if w["world_id"] == "W-DOWN")
    assert len(up["terrestrial_windows"]) == 1
    assert down["terrestrial_windows"] == []
    q = process["query_capabilities"][0]
    assert q["payload_kind"] == "RECEIPT_SUMMARY"
    assert q["response_delay_s"] == 3 and q["timeout_s"] == 3
    passive = process["passive_observation_rules"][0]
    assert passive["gateway_receipt_delay_s"] == 2
    assert passive["final_ack_delay_s"] == 4
    assert passive["negative_observation_after_s"] == 4
    assert process["resource_contract"]["satellite_completion_delay_s"] == 0
    print("PASS v0.6 oracle adapter: frozen case timing, receipt-summary payload and shared-resource IR are explicit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
