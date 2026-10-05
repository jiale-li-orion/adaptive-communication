#!/usr/bin/env python3
"""Build method-only structural-scaling bundles from frozen Layer-1 hard parents.

This artifact is NOT a benchmark expansion.  It reuses the existing declared
CONTROLLED_STRESS workload-density coordinate and the authoritative v0.2
materializer while holding task/source/service/evidence/recovery semantics fixed.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path

from compositional_recipe_generator_v0_1 import core_recipes, _budget_for, _hardness
from dynamic_world_materializer_v0_1 import materialize_recipe


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SPLIT = ROOT / "results/benchmark/layer1-structure-aware-split-v0.2-retry-legality.json"
DEFAULT_OUT = ROOT / "results/benchmark/layer2-future-choice-structural-stress-v0.1.json"


def _stress_recipe(base, overlap: int):
    provenance = {k: dict(v) for k, v in base.variable_provenance.items()}
    provenance["overlap_count"] = dict(provenance["overlap_count"])
    provenance["overlap_count"].update({
        "class": "CONTROLLED_STRESS",
        "value": overlap,
        "method_eval_only": True,
        "stress_rationale": (
            "method-only scaling of coupled recurring-report workload density; "
            "each obligation keeps the source-resolved reporting deadline"
        ),
    })
    provenance["satellite_budget"] = dict(provenance["satellite_budget"])
    provenance["satellite_budget"].update({
        "value": _budget_for(overlap, base.resource_headroom),
        "method_eval_only": True,
    })
    rid_payload = {
        "parent_recipe_id": base.recipe_id,
        "overlap_count": overlap,
        "purpose": "FUTURE_CHOICE_STRUCTURAL_SCALING_V0_1",
    }
    rid = "T1S-" + sha256(
        json.dumps(rid_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:14]
    return replace(
        base,
        recipe_id=rid,
        overlap_count=overlap,
        hardness=_hardness(
            base.service_process_class,
            overlap,
            base.evidence_regime,
            base.recovery_regime,
        ),
        variable_provenance=provenance,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--split", type=Path, default=DEFAULT_SPLIT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--overlaps", default="4,6,8,10,12")
    args = ap.parse_args()

    overlaps = tuple(sorted({int(x) for x in args.overlaps.split(",") if x.strip()}))
    if any(x < 2 for x in overlaps):
        raise ValueError("overlap stress must remain >=2")
    split = json.loads(args.split.read_text(encoding="utf-8"))
    grouped = defaultdict(list)
    for row in split["rows"]:
        if row.get("candidate_role") == "HARD_PRE_ADMISSION_SURVIVOR":
            grouped[str(row["signature"])].append(row)
    parents = []
    for signature, rows in sorted(grouped.items()):
        representative = min(rows, key=lambda x: str(x["recipe_id"]))
        splits = {str(r["split"]) for r in rows}
        if len(splits) != 1:
            raise ValueError(f"hard signature crosses splits: {signature}")
        parents.append({
            "signature": signature,
            "representative_recipe_id": str(representative["recipe_id"]),
            "split": next(iter(splits)),
            "recipe_multiplicity": len(rows),
        })
    if len(parents) != int(split["hard_survivor_input"]["v8_survivor_signature_count"]):
        raise ValueError("reconstructed hard parent count disagrees with frozen split authority")
    recipe_index = {r.recipe_id: r for r in core_recipes()}
    rows = []
    by_overlap = Counter()
    by_split = Counter()
    for parent in parents:
        parent_rid = str(parent["representative_recipe_id"])
        if parent_rid not in recipe_index:
            raise KeyError(f"frozen hard parent recipe missing from current generator: {parent_rid}")
        base = recipe_index[parent_rid]
        for overlap in overlaps:
            recipe = _stress_recipe(base, overlap)
            bundle = materialize_recipe(recipe)
            bundle["release_status"] = "METHOD_EVAL_ONLY_NOT_BENCHMARK_ADMIT"
            bundle["next_stage"] = "METHOD_ONLY_CAUSAL_EVIDENCE_AND_PLANNING_EVAL"
            bundle["provenance"]["method_structural_scaling"] = {
                "class": "CONTROLLED_STRESS",
                "parent_signature": parent["signature"],
                "parent_recipe_id": parent_rid,
                "parent_split": parent["split"],
                "scaled_coordinate": "overlap_count",
                "scaled_value": overlap,
                "benchmark_membership": False,
                "rule": (
                    "hold source-owned obligation deadline, task contract, geometry, "
                    "service process, evidence regime, recovery semantics and headroom class fixed"
                ),
            }
            rows.append({
                "parent_signature": parent["signature"],
                "parent_recipe_id": parent_rid,
                "parent_split": parent["split"],
                "overlap_count": overlap,
                "report_interval_s": recipe.report_interval_s,
                "resource_headroom": recipe.resource_headroom,
                "bundle": bundle,
            })
            by_overlap[overlap] += 1
            by_split[str(parent["split"])] += 1

    artifact = {
        "schema_version": "0.1",
        "status": "METHOD_EVAL_ONLY_CONTROLLED_STRESS",
        "benchmark_membership": False,
        "parents_ref": str(args.split.relative_to(ROOT)),
        "parents_sha256": sha256(args.split.read_bytes()).hexdigest(),
        "parent_selection_rule": (
            "HARD_PRE_ADMISSION_SURVIVOR rows grouped by solver signature; "
            "lexicographically smallest recipe_id is the deterministic representative"
        ),
        "parent_signature_count": len(parents),
        "overlap_values": list(overlaps),
        "bundle_count": len(rows),
        "by_overlap": {str(k): v for k, v in sorted(by_overlap.items())},
        "by_parent_split": dict(sorted(by_split.items())),
        "invariants": [
            "This artifact never changes Layer-1 benchmark membership, split, labels or release identity.",
            "Only overlap_count and the same headroom-class satellite budget scale with workload density.",
            "Every obligation keeps the source-resolved report interval as its deadline width.",
            "Geometry trace, service process, evidence regime, recovery regime and task/source authority remain fixed per parent.",
            "All scaled worlds are materialized by the same authoritative Layer-1 materializer.",
        ],
        "rows": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": artifact["status"],
        "parent_signature_count": artifact["parent_signature_count"],
        "overlap_values": artifact["overlap_values"],
        "bundle_count": artifact["bundle_count"],
        "by_overlap": artifact["by_overlap"],
        "out": str(args.out),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
