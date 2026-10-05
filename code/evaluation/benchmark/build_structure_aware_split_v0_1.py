#!/usr/bin/env python3
"""Deterministic structure-aware split builder for Layer-1 pre-admission candidates.

Split ownership is at ``task contract × geometry signature``.  Every service,
evidence, overlap, headroom and recovery variant of that pair stays in the same
split, preventing recipe-id/seed leakage across near-identical structural cases.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
from itertools import product
import argparse
import json
from pathlib import Path
from typing import Any

from compositional_recipe_generator_v0_1 import core_recipes, geometry_signatures


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RECIPE_VALIDITY = ROOT / "local_research/current/benchmark/generated/v0-v7-full-v0.1/recipe-validity.jsonl"
RECIPE_EXACT = ROOT / "local_research/current/benchmark/generated/exact-labels-v0.1/recipe-labels.jsonl"
V8_ALL_PASS = ROOT / "results/benchmark/layer1-v8-all-pass-v0.1.json"
V8_SIG_ROWS = ROOT / "local_research/current/benchmark/generated/v8-all-pass-v0.1/signature-v8.jsonl"


def _ref(path: Path) -> str:
    resolved = path.resolve(); root = ROOT.resolve()
    return str(resolved.relative_to(root)) if resolved.is_relative_to(root) else str(resolved)


def _rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _geometry_cluster_map() -> dict[str, str]:
    normalized: dict[tuple[int, ...], list[str]] = defaultdict(list)
    for g in geometry_signatures():
        xs = tuple(int(x) for x in g.relative_slots_s)
        shape = tuple(x - xs[0] for x in xs)
        normalized[shape].append(g.signature_id)
    out = {}
    for idx, (_shape, ids) in enumerate(sorted(normalized.items(), key=lambda kv: kv[1])):
        cid = f"GC{idx:02d}"
        for gid in ids:
            out[gid] = cid
    return out


def _stable_rank(component_key: str) -> int:
    return int.from_bytes(sha256(component_key.encode("utf-8")).digest()[:8], "big")


def _candidate_role(row: dict[str, Any], exact_class: str, v8_survivor: bool) -> str | None:
    pre = str(row["pre_oracle_disposition"])
    vdisp = str(row["v0_v7_disposition"])
    if pre == "EASY_CONFORMANCE" and exact_class == "NO_PAID_QUERY_REQUIRED":
        return "EASY_CONFORMANCE_CONTROL"
    if pre == "NEGATIVE_REGRESSION":
        if vdisp == "V1_PHYSICAL_INVALID":
            return "NEGATIVE_PHYSICAL_INVALID_CONTROL"
        if exact_class == "NO_PAID_QUERY_REQUIRED":
            return "NEGATIVE_SHORTCUT_REGRESSION_CONTROL"
    if exact_class == "INFORMATION_INFEASIBLE":
        return "INFORMATION_INFEASIBLE_DIAGNOSTIC"
    if vdisp == "V0_V7_PASS" and v8_survivor:
        return "HARD_PRE_ADMISSION_SURVIVOR"
    return None


def build(*, recipe_validity: Path = RECIPE_VALIDITY, recipe_exact: Path = RECIPE_EXACT,
          v8_manifest_path: Path = V8_ALL_PASS, v8_signature_rows: Path = V8_SIG_ROWS) -> dict[str, Any]:
    validity = _rows(recipe_validity)
    exact = {str(r["recipe_id"]): r for r in _rows(recipe_exact)}
    v8_rows = _rows(v8_signature_rows)
    v8_survivor_sigs = {
        str(r["signature"])
        for r in v8_rows
        if r["v8_disposition"] == "SURVIVES_V8_LADDER_V0_1"
    }
    v8_manifest = json.loads(v8_manifest_path.read_text(encoding="utf-8"))
    recipe_axes = {
        r.recipe_id: {
            "resource_headroom": r.resource_headroom,
            "report_interval_s": r.report_interval_s,
            "warning_state": r.warning_state,
        }
        for r in core_recipes()
    }

    geometry_clusters = _geometry_cluster_map()

    # Candidate rows are first collected without a split.  We then union rows
    # that share either the translation-invariant geometry shape cluster or the
    # exact solver signature.  Geometry cluster ownership is global: the same
    # empirical trace-window shape may not appear in more than one split.
    provisional = []
    role_counts = Counter()
    for row in validity:
        rid = str(row["recipe_id"])
        erow = exact[rid]
        role = _candidate_role(
            row,
            str(erow["classification"]),
            str(erow["signature"]) in v8_survivor_sigs,
        )
        if role is None:
            continue
        item = {
            "recipe_id": rid,
            "bundle_id": row["bundle_id"],
            "signature": erow["signature"],
            "task_case_id": row["task_case_id"],
            "geometry_signature_id": row["geometry_signature_id"],
            "geometry_shape_cluster": geometry_clusters[str(row["geometry_signature_id"])],
            "service_process": row["service_process"],
            "evidence_regime": row["evidence_regime"],
            "overlap_count": row["overlap_count"],
            "resource_headroom": recipe_axes[rid]["resource_headroom"],
            "recovery_regime": row["recovery_regime"],
            "exact_classification": erow["classification"],
            "v0_v7_disposition": row["v0_v7_disposition"],
            "candidate_role": role,
            "release_status": "PRE_ADMISSION_SPLIT_CANDIDATE"
        }
        provisional.append(item)
        role_counts[role] += 1

    parent = list(range(len(provisional)))
    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    structural_owner: dict[str, int] = {}
    signature_owner: dict[str, int] = {}
    for i, item in enumerate(provisional):
        skey = str(item["geometry_shape_cluster"])
        sig = str(item["signature"])
        if skey in structural_owner:
            union(i, structural_owner[skey])
        else:
            structural_owner[skey] = i
        if sig in signature_owner:
            union(i, signature_owner[sig])
        else:
            signature_owner[sig] = i

    components: dict[int, list[int]] = defaultdict(list)
    for i in range(len(provisional)):
        components[find(i)].append(i)

    selected = []
    split_counts = Counter()
    split_role_counts = Counter()
    component_sizes = []
    component_records = []
    for indices in components.values():
        structural_keys = sorted({str(provisional[i]["geometry_shape_cluster"]) for i in indices})
        signatures = sorted({str(provisional[i]["signature"]) for i in indices})
        canonical = json.dumps({"structural_keys": structural_keys, "signatures": signatures}, sort_keys=True)
        component_sizes.append(len(indices))
        hard_items = [provisional[i] for i in indices if provisional[i]["candidate_role"] == "HARD_PRE_ADMISSION_SURVIVOR"]
        component_records.append({
            "indices": indices,
            "canonical": canonical,
            "rank": _stable_rank(canonical),
            "size": len(indices),
            "hard_axes": {
                "overlap_count": {int(x["overlap_count"]) for x in hard_items},
                "resource_headroom": {str(x["resource_headroom"]) for x in hard_items},
                "recovery_regime": {str(x["recovery_regime"]) for x in hard_items},
            },
        })

    global_hard_axes = {
        "overlap_count": {int(x["overlap_count"]) for x in provisional if x["candidate_role"] == "HARD_PRE_ADMISSION_SURVIVOR"},
        "resource_headroom": {str(x["resource_headroom"]) for x in provisional if x["candidate_role"] == "HARD_PRE_ADMISSION_SURVIVOR"},
        "recovery_regime": {str(x["recovery_regime"]) for x in provisional if x["candidate_role"] == "HARD_PRE_ADMISSION_SURVIVOR"},
    }
    split_names = ("train", "dev", "test")
    target_ratio = {"train": 0.70, "dev": 0.15, "test": 0.15}
    total = max(1, len(provisional))

    # There are only four translation-invariant geometry clusters in v0.1, so
    # exhaustive component assignment is cheap and removes heuristic drift.
    # Score order: hard-axis completeness first, non-empty splits second,
    # distance from the desired 70/15/15 load third, stable hash last.
    best = None
    for labels in product(split_names, repeat=len(component_records)):
        loads = Counter()
        coverage = {
            s: {axis: set() for axis in global_hard_axes}
            for s in split_names
        }
        for ci, split in enumerate(labels):
            comp = component_records[ci]
            loads[split] += comp["size"]
            for axis in global_hard_axes:
                coverage[split][axis].update(comp["hard_axes"][axis])
        empty = sum(loads[s] == 0 for s in split_names)
        missing = sum(
            len(global_hard_axes[axis] - coverage[s][axis])
            for s in split_names
            for axis in global_hard_axes
        )
        ratio_error = sum(abs(loads[s] / total - target_ratio[s]) for s in split_names)
        tie_raw = "|".join(
            f"{component_records[ci]['rank']}:{labels[ci]}"
            for ci in range(len(component_records))
        )
        tie = _stable_rank(tie_raw)
        score = (missing, empty, ratio_error, tie)
        if best is None or score < best[0]:
            best = (score, labels, loads, coverage)
    assert best is not None
    _score, labels, loads, hard_coverage = best
    assignment = {ci: labels[ci] for ci in range(len(component_records))}

    for ci, comp in enumerate(component_records):
        split = assignment[ci]
        for i in comp["indices"]:
            item = dict(provisional[i])
            item["split"] = split
            selected.append(item)
            split_counts[split] += 1
            split_role_counts[(split, str(item["candidate_role"]))] += 1

    # Leakage invariant: structural shape group and exact signature each have exactly one split.
    leakage = []
    structural_splits: dict[str, set[str]] = defaultdict(set)
    signature_splits: dict[str, set[str]] = defaultdict(set)
    for item in selected:
        structural_splits[str(item["geometry_shape_cluster"])].add(str(item["split"]))
        signature_splits[str(item["signature"])].add(str(item["split"]))
    for key, splits in structural_splits.items():
        if len(splits) != 1:
            leakage.append({"kind": "TRACE_GEOMETRY_CLUSTER", "group": key, "splits": sorted(splits)})
    for sig, splits in signature_splits.items():
        if len(splits) != 1:
            leakage.append({"kind": "SOLVER_SIGNATURE", "signature": sig, "splits": sorted(splits)})

    split_signatures: dict[str, set[str]] = defaultdict(set)
    for item in selected:
        split_signatures[str(item["split"])].add(str(item["signature"]))
    signature_overlap = {
        "train_dev": len(split_signatures["train"] & split_signatures["dev"]),
        "train_test": len(split_signatures["train"] & split_signatures["test"]),
        "dev_test": len(split_signatures["dev"] & split_signatures["test"]),
    }

    return {
        "schema_version": "0.1",
        "status": "STRUCTURE_AWARE_PRE_ADMISSION_SPLIT",
        "grouping_key": ["global_translation_invariant_geometry_shape", "solver_signature_connectivity"],
        "geometry_shape_clusters": geometry_clusters,
        "group_assignment": "global trace-shape/exact-signature connected components; exhaustive deterministic assignment minimizes hard-axis missing values, then empty splits, then 70/15/15 load error; stable SHA-256 tie-break; recipe id excluded",
        "candidate_count": len(selected),
        "connected_component_count": len(components),
        "component_size": {
            "min": min(component_sizes) if component_sizes else 0,
            "max": max(component_sizes) if component_sizes else 0,
            "mean": (sum(component_sizes) / len(component_sizes)) if component_sizes else 0.0,
        },
        "lineage_inputs": {
            "recipe_validity": _ref(recipe_validity),
            "recipe_exact": _ref(recipe_exact),
            "v8_manifest": _ref(v8_manifest_path),
            "v8_signature_rows": _ref(v8_signature_rows),
        },
        "by_role": dict(sorted(role_counts.items())),
        "by_split": dict(sorted(split_counts.items())),
        "by_split_role": {
            f"{split}|{role}": n for (split, role), n in sorted(split_role_counts.items())
        },
        "hard_axis_coverage": {
            split: {
                axis: {
                    "observed": sorted(values),
                    "missing": sorted(global_hard_axes[axis] - values),
                }
                for axis, values in axes.items()
            }
            for split, axes in hard_coverage.items()
        },
        "hard_survivor_input": {
            "v8_survivor_signature_count": v8_manifest["survivor_signature_count"],
            "v8_projected_survivor_recipe_count": v8_manifest["projected_survivor_recipe_count"],
        },
        "leakage_audit": {
            "component_split_violations": leakage,
            "solver_signature_overlap": signature_overlap,
            "passed": not leakage and all(v == 0 for v in signature_overlap.values()),
        },
        "rows": sorted(selected, key=lambda x: (x["split"], x["candidate_role"], x["recipe_id"])),
        "release_status": "NOT_BENCHMARK_ADMIT",
    }


if __name__ == "__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument('--recipe-validity',type=Path,default=RECIPE_VALIDITY)
    ap.add_argument('--recipe-exact',type=Path,default=RECIPE_EXACT)
    ap.add_argument('--v8-manifest',type=Path,default=V8_ALL_PASS)
    ap.add_argument('--v8-signature-rows',type=Path,default=V8_SIG_ROWS)
    args=ap.parse_args()
    def rp(p): return p if p.is_absolute() else ROOT/p
    print(json.dumps(build(recipe_validity=rp(args.recipe_validity),recipe_exact=rp(args.recipe_exact),
                           v8_manifest_path=rp(args.v8_manifest),v8_signature_rows=rp(args.v8_signature_rows)),
                     ensure_ascii=False, indent=2, sort_keys=True))
