#!/usr/bin/env python3
"""Fail-fast audit for the frozen v0.7 placement/visibility contract."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CONTRACT = ROOT / "research/benchmark/PLACEMENT-VISIBILITY-CONTRACT.v0.1.json"
AXES = ROOT / "research/benchmark/GENERATION-AXES.v0.2.json"


def main() -> int:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    axes = json.loads(AXES.read_text(encoding="utf-8"))

    assert contract["status"] == "FROZEN_GATEWAY_PRIMARY_CENTER_SIMULATOR_GAP"
    placements = contract["placements"]
    assert set(placements) == {"GATEWAY_LOCAL_PRIMARY", "CENTER_REMOTE_CONTROL"}

    gateway = placements["GATEWAY_LOCAL_PRIMARY"]
    assert gateway["role"] == "PRIMARY_EVALUATION"
    assert gateway["admission_status"] == "READY_FOR_GATEWAY_LOCAL_MECHANISM_AUDIT"
    assert gateway["policy_owner"] == gateway["action_execution_owner"] == "gateway"
    assert gateway["control_transport"]["mode"] == "OWNER_LOCAL"
    assert gateway["receipt_summary"]["semantics"] == "OWNER_LOCAL_STATE_PROJECTION"
    assert gateway["receipt_summary"]["action"] is False
    assert gateway["receipt_summary"]["network_resource_cost"] == 0
    assert gateway["receipt_summary"]["network_delay_s"] == 0
    assert gateway["dedicated_query_actions"] == []
    assert "future terrestrial service transitions" in gateway["hidden"]
    assert "paid remote receipt-summary EvidenceNeed" in gateway["forbidden_claims"]

    center = placements["CENTER_REMOTE_CONTROL"]
    assert center["role"] == "POSITION_CONTROL"
    assert center["admission_status"] == "SIMULATOR_GAP"
    assert center["gateway_local_state_visible_without_transport"] is False
    missing = " ".join(center["required_missing_contracts"]).lower()
    assert "query request" in missing and "query response" in missing
    assert "send/control command" in missing
    assert "resource sharing" in missing

    coordinates = set(axes["evaluation_coordinates_not_generator_targets"])
    assert "gateway placement vs center placement" in coordinates
    projection = contract["downstream_projection"]
    assert set(projection["gateway_local_irrelevant_case_axes"]) == {
        "remote_query.response_delay_ratio",
        "remote_query.response_delay_s",
    }

    forbidden = " ".join(contract["global_invariants"]).lower()
    assert "future service transitions" in forbidden
    assert "control commands" in forbidden

    print(
        "PASS v0.7 placement contract: gateway-local owner visibility is primary; "
        "center remote control remains an explicit transport simulator gap"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
