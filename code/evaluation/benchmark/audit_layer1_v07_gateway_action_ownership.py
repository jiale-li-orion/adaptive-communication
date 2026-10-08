#!/usr/bin/env python3
"""Audit v0.7 gateway placement against the repository's data-location lifecycle.

This is a static contract audit.  It intentionally does not run an oracle or
baseline.  The question is whether the current gateway-local adapter gives the
gateway policy an action whose execution owner is compatible with the event it
later calls a gateway receipt.
"""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SYSTEM = ROOT / "research/substrate/SYSTEM-MODEL-v1.md"
V05 = ROOT / "research/benchmark/V0.5-RECEIPT-RACE.md"
PLACEMENT = ROOT / "research/benchmark/PLACEMENT-VISIBILITY-CONTRACT.v0.1.json"
ADAPTER = ROOT / "code/evaluation/benchmark/layer1_v07_gateway_oracle_adapter.py"
ORACLE = ROOT / "code/evaluation/benchmark/exact_reference_oracle_v0_1.py"
OUT = ROOT / "results/benchmark/layer1-v0.7-gateway-action-ownership-review.json"


def main() -> int:
    system = SYSTEM.read_text(encoding="utf-8")
    v05 = V05.read_text(encoding="utf-8")
    placement = json.loads(PLACEMENT.read_text(encoding="utf-8"))
    adapter = ADAPTER.read_text(encoding="utf-8")
    oracle = ORACLE.read_text(encoding="utf-8")

    gateway = placement["placements"]["GATEWAY_LOCAL_PRIMARY"]
    facts = {
        "system_model_separates_node_uplink_from_gateway_backhaul": (
            "一次 uplink 成功被 gateway 听到" in system
            and "Gateway, primary backhaul, backup and DtS" in system
            and "gateway queue" in system
        ),
        "system_model_completion_is_center_arrival": (
            "最终到达 center" in system or "t_s^{center}" in system
        ),
        "v05_send_precedes_gateway_receipt_then_center_ack": (
            "A 先走正常 terrestrial send" in v05
            and "gateway-local receipt 早于 center final ACK" in v05
        ),
        "v07_gateway_policy_and_action_execution_owner_are_gateway": (
            gateway["policy_owner"] == "gateway"
            and gateway["action_execution_owner"] == "gateway"
        ),
        "v07_gateway_contract_exposes_gateway_receipt_after_event": (
            "gateway receipt after the declared receipt event"
            in gateway["visible_when_released_or_executed"]
        ),
        "v07_adapter_declares_send_terr_local_at_gateway": (
            "SEND_TERR / SEND_SAT / WAIT execute locally at the gateway" in adapter
        ),
        "exact_send_terr_creates_future_gateway_receipt": (
            'elif action == "SEND_TERR"' in oracle
            and "gateway_receipt_at_s=(at_s + _gateway_receipt_delay(process) if accepted else None)" in oracle
        ),
    }
    assert all(facts.values()), facts

    violations = {
        "gateway_local_send_owner_conflicts_with_receipt_stage": True,
        "data_location_not_explicit_in_v07_exact_state": True,
        "node_to_gateway_and_gateway_to_center_actions_not_separated": True,
    }
    payload = {
        "schema_version": "0.1",
        "stage": "V07_GATEWAY_ACTION_OWNERSHIP_REVIEW",
        "facts": facts,
        "violations": violations,
        "disposition": "BLOCK_GATEWAY_EXACT_ADMISSION_DATA_LOCATION_ACTION_OWNERSHIP_OPEN",
        "required_closure": [
            "Represent report/data location explicitly enough to distinguish not-yet-at-gateway, gateway-queued/in-flight, and center-delivered states.",
            "Define which transitions are exogenous/report-schedule events and which are policy actions at gateway placement.",
            "If gateway controls node uplink, declare the gateway-to-node command/access transport; otherwise node-to-gateway receipt must not be caused by an instantaneous gateway-local SEND_TERR action.",
            "Define gateway-to-center primary/fallback forwarding actions separately from the node-to-gateway receipt event.",
            "Re-run gateway exact/mechanism admission only after the action/data-location contract is frozen and audited.",
        ],
        "claim_boundary": [
            "This audit does not invalidate the frozen v0.7 source task, geometry or service-support generation lineage.",
            "It invalidates interpreting the current gateway-local exact adapter as a deployment-faithful admission oracle.",
            "The existing 36-cell gateway pilot and bifurcation result remain useful diagnostics of the provisional abstract kernel, but not benchmark-admission evidence.",
            "Center placement remains separately blocked by its previously documented telemetry/query/control transport gap.",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"disposition": payload["disposition"], "facts": facts}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
