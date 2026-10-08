#!/usr/bin/env python3
"""Same-information ordinary baselines for one indexed v0.7 gateway cell."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from layer1_v06_oracle_adapter import world_bundle_from_v06
from layer1_v07_gateway_oracle_adapter import gateway_process_from_v07
from v8_policy_baselines_v0_1 import (
    _choose_depth_k,
    _choose_latest_feasible,
    _choose_least_slack,
    _choose_shallow,
    _execute_policy,
)


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INDEX = ROOT / "local_research/current/benchmark/v07-gateway-pilot-index.json"


def audit(index: dict[str, Any], ordinal: int) -> dict[str, Any]:
    matches = [row for row in index["rows"] if int(row["ordinal"]) == ordinal]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one indexed row for ordinal {ordinal}, got {len(matches)}")
    row = matches[0]
    base = row["base"]
    case = row["case"]
    bundle = world_bundle_from_v06(base, case)
    process = gateway_process_from_v07(base, case)

    baseline_specs = {
        "shallow_rule": _choose_shallow,
        "least_slack_send_probe": _choose_least_slack,
        "latest_feasible_send": _choose_latest_feasible,
        "myopic_flow_voi": lambda b, p, t, s: _choose_depth_k(b, p, t, s, 1, leaf="flow"),
        "depth_2_flow_terminal": lambda b, p, t, s: _choose_depth_k(b, p, t, s, 2, leaf="flow"),
        "depth_3_flow_terminal": lambda b, p, t, s: _choose_depth_k(b, p, t, s, 3, leaf="flow"),
    }
    results = {}
    for name, chooser in baseline_specs.items():
        out = _execute_policy(bundle, chooser, process=process)
        results[name] = {
            "solvable": bool(out["solvable"]),
            "decisions": int(out["decisions"]),
        }

    return {
        "schema_version": "0.1",
        "stage": "V07_GATEWAY_LOCAL_CANDIDATE_BASELINES",
        "placement": "GATEWAY_LOCAL_PRIMARY",
        "ordinal": ordinal,
        "axis_cell": row["axis_cell"],
        "case_id": case["case_id"],
        "base_id": case["base_id"],
        "feedback_timing": {
            "gateway_receipt_delay_s": case["gateway_receipt_delay_s"],
            "final_ack_delay_s": case["final_ack_delay_s"],
        },
        "query_capabilities": process["query_capabilities"],
        "baselines": results,
        "any_ordinary_success": any(x["solvable"] for x in results.values()),
        "claim_boundary": [
            "All baselines use the same gateway-local causal process and natural feedback as the evaluated policy.",
            "No baseline receives paid query capability or hidden future service state.",
            "A candidate solved by any ordinary baseline is a shortcut/control cell, not a hard admission.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--ordinal", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    payload = audit(json.loads(args.index.read_text(encoding="utf-8")), args.ordinal)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"ordinal": args.ordinal, "any_ordinary_success": payload["any_ordinary_success"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
