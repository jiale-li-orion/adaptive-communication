#!/usr/bin/env python3
"""Audit the placement/visibility boundary before v0.7 exact admission.

The frozen v0.7 generator is method-independent, but its case schema does not
choose a policy placement.  Exact admission must therefore refuse an adapter
that mixes center-side remote-query costs with gateway-local receipt visibility
or instantaneous center control actions.

This audit is intentionally static and cheap.  It does not classify cases and
does not modify the frozen generator or generation axes.
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
from typing import Any

from layer1_v06_oracle_adapter import causal_process_from_v06


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RUN = ROOT / "local_research/current/benchmark/generated/layer1-v0.7-preoracle-r1"
AXES = ROOT / "research/benchmark/GENERATION-AXES.v0.2.json"


def _first_row(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                return json.loads(line)
    raise ValueError(f"empty artifact: {path}")


def _base_by_id(path: Path, base_id: str) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if str(row["base_id"]) == base_id:
                return row
    raise KeyError(base_id)


def audit(run: Path) -> dict[str, Any]:
    axes = json.loads(AXES.read_text(encoding="utf-8"))
    case = _first_row(run / "cases.jsonl.gz")
    base = _base_by_id(run / "base-scenarios.jsonl.gz", str(case["base_id"]))
    process = causal_process_from_v06(base, case)

    query = process["query_capabilities"][0]
    passive = process["passive_observation_rules"][0]
    resource = process["resource_contract"]
    evaluation_coordinates = set(axes["evaluation_coordinates_not_generator_targets"])

    facts = {
        "case_schema_has_policy_placement": "policy_placement" in case,
        "base_schema_has_policy_placement": "policy_placement" in base,
        "process_schema_has_policy_placement": "policy_placement" in process,
        "query_owner": query.get("owner"),
        "query_payload_kind": query.get("payload_kind"),
        "query_uses_real_opportunity": bool(resource.get("query_uses_real_opportunity")),
        "passive_gateway_receipt_enabled": "gateway_receipt_delay_s" in passive,
        "send_control_transport_declared": bool(
            process.get("control_path_contract")
            or process.get("send_command_transport")
        ),
        "placement_is_declared_evaluation_coordinate": (
            "gateway placement vs center placement" in evaluation_coordinates
        ),
    }

    mixed_semantics = (
        facts["query_owner"] == "gateway"
        and facts["query_payload_kind"] == "RECEIPT_SUMMARY"
        and facts["query_uses_real_opportunity"]
        and facts["passive_gateway_receipt_enabled"]
        and not any(
            (
                facts["case_schema_has_policy_placement"],
                facts["base_schema_has_policy_placement"],
                facts["process_schema_has_policy_placement"],
            )
        )
    )
    center_control_gap = (
        facts["query_uses_real_opportunity"]
        and not facts["send_control_transport_declared"]
    )

    if mixed_semantics or center_control_gap:
        disposition = "BLOCK_ORACLE_ADMISSION_PLACEMENT_VISIBILITY_UNRESOLVED"
    else:
        disposition = "PASS_PLACEMENT_VISIBILITY_EXPLICIT"

    return {
        "schema_version": "0.1",
        "stage": "V07_PLACEMENT_VISIBILITY_AUDIT",
        "official_generation_run": run.name,
        "disposition": disposition,
        "facts": facts,
        "violations": {
            "mixed_center_query_and_gateway_local_visibility": mixed_semantics,
            "center_query_cost_without_send_control_transport": center_control_gap,
        },
        "required_resolution": {
            "gateway_placement": [
                "gateway queue/send/receipt state is owner-local",
                "receipt-summary local read is not charged as remote acquisition",
                "gateway-local autonomy is the primary deployment baseline",
            ],
            "center_placement": [
                "gateway receipt is hidden until declared telemetry or legal query arrives",
                "query request/response and send-control command obey declared path and timing",
                "center and gateway placements are reported as separate evaluation coordinates",
            ],
        },
        "claim_boundary": [
            "The v0.7 generated universe remains valid as a pre-oracle construction artifact.",
            "No v0.7 paid-evidence, no-query, or exact-admission statistic is valid until placement and visibility are explicit.",
            "This audit does not request a generator-axis change and does not select cases by method outcome.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    payload = audit(args.run.resolve())
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
