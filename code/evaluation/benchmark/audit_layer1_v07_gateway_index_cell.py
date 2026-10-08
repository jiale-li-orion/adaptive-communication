#!/usr/bin/env python3
"""Run one bounded-selection gateway-local staged exact cell from a frozen index.

This runner deliberately executes exactly one preselected cell.  Shell/cgroup
resource guards are external to the scientific solver; if a guard terminates
the process the caller must record the cell as unresolved computation rather
than reinterpret it as infeasible or hard.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_layer1_v07_gateway_mechanism_pilot import staged_disposition
from layer1_v07_gateway_oracle_adapter import gateway_structure_id


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INDEX = ROOT / "local_research/current/benchmark/v07-gateway-pilot-index.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--ordinal", type=int, required=True)
    parser.add_argument("--max-memo-nodes", type=int, default=50_000)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    index = json.loads(args.index.read_text(encoding="utf-8"))
    matches = [row for row in index["rows"] if int(row["ordinal"]) == args.ordinal]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one indexed row for ordinal {args.ordinal}, got {len(matches)}")
    row = matches[0]
    base = row["base"]
    case = row["case"]
    disposition, references, decisive = staged_disposition(
        base,
        case,
        max_memo_nodes=args.max_memo_nodes,
    )
    payload = {
        "schema_version": "0.1",
        "stage": "V07_GATEWAY_LOCAL_INDEXED_CELL",
        "placement": "GATEWAY_LOCAL_PRIMARY",
        "index": str(args.index),
        "index_generation_manifest_sha256": index["official_generation_manifest_sha256"],
        "ordinal": args.ordinal,
        "axis_cell": row["axis_cell"],
        "case_id": case["case_id"],
        "base_id": case["base_id"],
        "source_structure_id": case["structure_id"],
        "gateway_structure_id": gateway_structure_id(base, case),
        "disposition": disposition,
        "decisive_reference": decisive,
        "references": references,
        "max_memo_nodes_per_reference": args.max_memo_nodes,
        "claim_boundary": [
            "One indexed method-independent pilot cell only; not a benchmark distribution estimate.",
            "SEARCH_LIMIT remains unresolved computation.",
            "External timeout or memory-limit termination must also remain unresolved computation.",
            "No center-placement or paid-remote-evidence claim is made.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"ordinal": args.ordinal, "disposition": disposition}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
