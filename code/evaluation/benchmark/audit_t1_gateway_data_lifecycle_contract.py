#!/usr/bin/env python3
"""Fail-fast checks for the corrected T1 gateway backhaul lifecycle."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CONTRACT = ROOT / "research/benchmark/T1-GATEWAY-DATA-LIFECYCLE-CONTRACT.v0.1.json"


def main() -> int:
    c = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert c["status"] == "FROZEN_PRE_ORACLE_GATEWAY_BACKHAUL_SCOPE"
    assert c["scope"]["placement"] == "GATEWAY_LOCAL_PRIMARY"
    assert c["scope"]["conditional_entry_boundary"] == "the report has reached the gateway queue"
    assert c["entry_event"]["id"] == "GATEWAY_RECEIPT"
    assert c["entry_event"]["policy_action"] is False
    assert c["entry_event"]["network_acquisition_cost_for_gateway_policy"] == 0
    actions = {row["id"] for row in c["gateway_legal_actions"]}
    assert actions == {"FORWARD_PRIMARY", "FORWARD_FALLBACK", "WAIT"}
    assert c["legacy_mapping"]["old_SEND_TERR"] == "NOT_DIRECTLY_ADMISSIBLE_AS_GATEWAY_ACTION"
    assert c["legacy_mapping"]["old_gateway_receipt_after_SEND_TERR"] == "REPLACED_BY_ENTRY_EVENT_BEFORE_GATEWAY_FORWARDING"
    forbidden = " ".join(c["forbidden_gateway_shortcuts"])
    assert "instantaneous gateway-local action" in forbidden
    assert "obligation complete at gateway receipt" in forbidden
    implementation = " ".join(c["implementation_gate"])
    assert "report location" in implementation
    assert "gateway_receipt_delay" in implementation
    print("PASS T1 gateway lifecycle: data location, gateway receipt, forwarding ownership and center completion are separated before oracle implementation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
