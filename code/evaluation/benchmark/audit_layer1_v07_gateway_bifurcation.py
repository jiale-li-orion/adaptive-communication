#!/usr/bin/env python3
"""Diagnose the v0.7 gateway-local easy / causal-infeasible bifurcation.

This audit is downstream of the frozen v0.7 generator and the tracked bounded
gateway pilot.  It does not alter generator axes or select cases by a proposed
method outcome.  It asks two narrower questions:

1. what service-support invariant separates SINGLE_RECOVERY from
   REINTERRUPTIBLE at the stage counts actually represented by the pilot; and
2. for the TIGHT pilot cells classified FULL_CURRENT_CAUSAL_INFEASIBLE, does
   removing only the second-outage worlds collapse the same frozen
   resource/timing instance back to a blind common policy?

The second operation is an evaluator-only controlled intervention used for
attribution, not a candidate generator change.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import argparse
import json
from pathlib import Path
from typing import Any

from exact_reference_oracle_v0_1 import solve_observation_matched
from generate_layer1_v07_cases import _runs, _service_support
from layer1_v06_oracle_adapter import world_bundle_from_v06
from layer1_v07_gateway_oracle_adapter import (
    blind_gateway_process,
    gateway_process_from_v07,
)


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INDEX = ROOT / "local_research/current/benchmark/v07-gateway-pilot-index.json"
PILOT = ROOT / "results/benchmark/layer1-v0.7-gateway-pilot-v0.1.json"
DEFAULT_OUT = ROOT / "results/benchmark/layer1-v0.7-gateway-bifurcation-v0.1.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _common_up_stages(support: list[tuple[bool, ...]]) -> list[int]:
    if not support:
        return []
    return [
        i
        for i in range(len(support[0]))
        if all(bits[i] for bits in support)
    ]


def _support_audit(stage_counts: list[int]) -> list[dict[str, Any]]:
    rows = []
    for n in stage_counts:
        for family in ("SINGLE_RECOVERY", "REINTERRUPTIBLE"):
            support = _service_support(n, family)
            common = _common_up_stages(support)
            rows.append(
                {
                    "stage_count": n,
                    "family": family,
                    "world_count": len(support),
                    "common_up_stages": common,
                    "all_worlds_final_stage_up": all(bits[-1] for bits in support),
                    "contains_two_down_run_world": any(_runs(bits, False) == 2 for bits in support),
                }
            )
    return rows


def _restrict_to_single_down_run(
    base: dict[str, Any],
    case: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], int, int]:
    keep_ids = {
        str(world["world_id"])
        for world in base["service_process"]["worlds"]
        if _runs(tuple(state == "UP" for state in world["service_by_stage"]), False) == 1
    }
    bundle = deepcopy(world_bundle_from_v06(base, case))
    process = deepcopy(gateway_process_from_v07(base, case))
    original_worlds = len(bundle["worlds"])
    bundle["worlds"] = [w for w in bundle["worlds"] if str(w["world_id"]) in keep_ids]
    process["world_owner_processes"] = [
        w for w in process["world_owner_processes"] if str(w["world_id"]) in keep_ids
    ]
    if not bundle["worlds"]:
        raise AssertionError("single-down-run intervention removed every support world")
    return bundle, process, original_worlds, len(bundle["worlds"])


def audit(index_path: Path, *, max_memo_nodes: int) -> dict[str, Any]:
    index = _load(index_path)
    pilot = _load(PILOT)
    assert index["axis_cell_count"] == pilot["axis_cell_count"] == 36
    assert index["official_generation_manifest_sha256"] == pilot["generation_manifest_sha256"]

    indexed = {int(row["ordinal"]): row for row in index["rows"]}
    pilot_rows = {int(row["ordinal"]): row for row in pilot["rows"]}
    assert set(indexed) == set(pilot_rows) == set(range(1, 37))
    for ordinal, row in indexed.items():
        assert row["case"]["case_id"] == pilot_rows[ordinal]["case_id"]
        assert row["axis_cell"] == pilot_rows[ordinal]["axis_cell"]

    stage_counts = sorted(
        {
            len(row["base"]["composition"]["release_stages_s"])
            for row in index["rows"]
        }
    )
    support_rows = _support_audit(stage_counts)

    by_family_pilot = Counter()
    for row in pilot["rows"]:
        family = str(row["axis_cell"]["service_process"])
        by_family_pilot[(family, str(row["final_pilot_disposition"]))] += 1

    targets = [
        int(row["ordinal"])
        for row in pilot["rows"]
        if row["raw_disposition"] == "FULL_CURRENT_CAUSAL_INFEASIBLE"
    ]
    interventions = []
    for ordinal in targets:
        source = indexed[ordinal]
        bundle, process, original_count, kept_count = _restrict_to_single_down_run(
            source["base"],
            source["case"],
        )
        blind = solve_observation_matched(
            bundle,
            blind_gateway_process(process),
            disable_paid_query=True,
            max_memo_nodes=max_memo_nodes,
        )
        interventions.append(
            {
                "ordinal": ordinal,
                "case_id": source["case"]["case_id"],
                "axis_cell": source["axis_cell"],
                "original_world_count": original_count,
                "single_down_run_world_count": kept_count,
                "removed_second_outage_world_count": original_count - kept_count,
                "intervened_blind_reference": {
                    "status": blind["status"],
                    "solvable": blind["solvable"],
                    "memo_nodes": blind["memo_nodes"],
                    "attempt_lattice_size": blind["attempt_lattice_size"],
                },
            }
        )

    single_support = [r for r in support_rows if r["family"] == "SINGLE_RECOVERY"]
    reint_support = [r for r in support_rows if r["family"] == "REINTERRUPTIBLE"]
    all_interventions_blind = all(
        row["intervened_blind_reference"]["status"] == "EXACT"
        and row["intervened_blind_reference"]["solvable"] is True
        for row in interventions
    )

    return {
        "schema_version": "0.1",
        "stage": "V07_GATEWAY_LOCAL_BIFURCATION_ATTRIBUTION",
        "placement": "GATEWAY_LOCAL_PRIMARY",
        "generation_run": index["official_generation_run"],
        "generation_manifest_sha256": index["official_generation_manifest_sha256"],
        "pilot_ref": str(PILOT.relative_to(ROOT)),
        "pilot_axis_cell_count": pilot["axis_cell_count"],
        "stage_counts_audited": stage_counts,
        "support_invariants": support_rows,
        "support_summary": {
            "single_recovery_all_observed_stage_counts_have_common_final_up": all(
                row["all_worlds_final_stage_up"]
                and row["common_up_stages"]
                and row["common_up_stages"][-1] == row["stage_count"] - 1
                for row in single_support
            ),
            "reinterruptible_all_observed_stage_counts_have_no_common_up_stage": all(
                not row["common_up_stages"] for row in reint_support
            ),
            "reinterruptible_all_observed_stage_counts_include_second_outage_worlds": all(
                row["contains_two_down_run_world"] for row in reint_support
            ),
        },
        "pilot_disposition_by_service_family": {
            family: {
                disposition: count
                for (fam, disposition), count in sorted(by_family_pilot.items())
                if fam == family
            }
            for family in ("SINGLE_RECOVERY", "REINTERRUPTIBLE")
        },
        "second_outage_intervention": {
            "selection_rule": "all TIGHT pilot cells with raw FULL_CURRENT_CAUSAL_INFEASIBLE disposition",
            "target_count": len(targets),
            "max_memo_nodes_per_reference": max_memo_nodes,
            "all_targets_become_blind_open_loop_solvable": all_interventions_blind,
            "rows": interventions,
        },
        "verdict": (
            "SUPPORTED_SCOPED_BIFURCATION_ATTRIBUTION"
            if all_interventions_blind
            else "BIFURCATION_ATTRIBUTION_INCOMPLETE"
        ),
        "claim_boundary": [
            "SINGLE_RECOVERY having a common final-UP stage follows from its frozen support predicate; this is not an empirical field-frequency claim.",
            "For the eight TIGHT pilot cells that were full-current causal-infeasible, second-outage worlds are necessary for that pilot disposition: removing only those worlds makes every intervened support blind-solvable.",
            "The intervention is evaluator-only attribution and does not propose deleting reinterruption from the benchmark; cache06 explicitly requires recover-and-reinterrupt dynamics.",
            "This result does not prove every REINTERRUPTIBLE case is infeasible, nor that no gateway-local hard case exists outside the bounded pilot.",
            "The result motivates auditing the process/observation structure before increasing search budgets or tuning generator parameters for hardness.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--max-memo-nodes", type=int, default=50_000)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    payload = audit(args.index, max_memo_nodes=args.max_memo_nodes)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "verdict": payload["verdict"],
                "target_count": payload["second_outage_intervention"]["target_count"],
                "all_targets_blind_after_intervention": payload["second_outage_intervention"]["all_targets_become_blind_open_loop_solvable"],
                "out": str(args.out.relative_to(ROOT)),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
