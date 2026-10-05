#!/usr/bin/env python3
"""Scale, coverage and near-duplicate audit for the Layer-1 pre-admission split."""
from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from compositional_recipe_generator_v0_1 import core_recipes


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SPLIT = ROOT / "results/benchmark/layer1-structure-aware-split-v0.1.json"


def _axis_index() -> dict[str, dict[str, Any]]:
    return {
        r.recipe_id: {
            "resource_headroom": r.resource_headroom,
            "warning_state": r.warning_state,
            "monitoring_grade": r.monitoring_grade,
            "report_interval_s": r.report_interval_s,
            "hardness": list(r.hardness),
            "task_surface_ids": list(r.task_surface_ids),
        }
        for r in core_recipes()
    }


def _fingerprint(row: dict[str, Any], axis: dict[str, Any], *, drop: str | None = None) -> str:
    payload = {
        "geometry_shape_cluster": row["geometry_shape_cluster"],
        "service_process": row["service_process"],
        "evidence_regime": row["evidence_regime"],
        "overlap_count": row["overlap_count"],
        "resource_headroom": axis["resource_headroom"],
        "recovery_regime": row["recovery_regime"],
        "report_interval_s": axis["report_interval_s"],
        "warning_state": axis["warning_state"],
        "monitoring_grade": axis["monitoring_grade"],
    }
    if drop is not None:
        payload.pop(drop, None)
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(raw.encode("utf-8")).hexdigest()


def audit() -> dict[str, Any]:
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    rows = split["rows"]
    axes = _axis_index()
    by_split = defaultdict(lambda: {
        "recipes": 0,
        "signatures": set(),
        "task_cases": set(),
        "geometry_clusters": set(),
        "service_processes": set(),
        "evidence_regimes": set(),
        "overlap_counts": set(),
        "resource_headroom": set(),
        "recovery_regimes": set(),
        "warning_states": set(),
        "report_intervals_s": set(),
        "roles": Counter(),
        "hardness": Counter(),
        "task_surfaces": Counter(),
    })
    sig_mult = defaultdict(Counter)
    for row in rows:
        s = str(row["split"])
        a = axes[str(row["recipe_id"])]
        x = by_split[s]
        x["recipes"] += 1
        x["signatures"].add(str(row["signature"]))
        x["task_cases"].add(str(row["task_case_id"]))
        x["geometry_clusters"].add(str(row["geometry_shape_cluster"]))
        x["service_processes"].add(str(row["service_process"]))
        x["evidence_regimes"].add(str(row["evidence_regime"]))
        x["overlap_counts"].add(int(row["overlap_count"]))
        x["resource_headroom"].add(str(a["resource_headroom"]))
        x["recovery_regimes"].add(str(row["recovery_regime"]))
        x["warning_states"].add(str(a["warning_state"]))
        x["report_intervals_s"].add(int(a["report_interval_s"]))
        x["roles"][str(row["candidate_role"])] += 1
        for h in a["hardness"]:
            x["hardness"][str(h)] += 1
        for ts in a["task_surface_ids"]:
            x["task_surfaces"][str(ts)] += 1
        sig_mult[s][str(row["signature"])] += 1

    rendered = {}
    for s, x in sorted(by_split.items()):
        rendered[s] = {
            "recipe_count": x["recipes"],
            "unique_signature_count": len(x["signatures"]),
            "signature_projection_ratio": x["recipes"] / max(1, len(x["signatures"])),
            "max_signature_multiplicity": max(sig_mult[s].values(), default=0),
            "task_case_count": len(x["task_cases"]),
            "geometry_shape_clusters": sorted(x["geometry_clusters"]),
            "service_processes": sorted(x["service_processes"]),
            "evidence_regimes": sorted(x["evidence_regimes"]),
            "overlap_counts": sorted(x["overlap_counts"]),
            "resource_headroom": sorted(x["resource_headroom"]),
            "recovery_regimes": sorted(x["recovery_regimes"]),
            "warning_states": sorted(x["warning_states"]),
            "report_intervals_s": sorted(x["report_intervals_s"]),
            "roles": dict(sorted(x["roles"].items())),
            "hardness": dict(sorted(x["hardness"].items())),
            "task_surfaces": dict(sorted(x["task_surfaces"].items())),
        }

    # Near-duplicate audit: if two rows in different splits become identical
    # after dropping one semantic axis, they are one-axis neighbors.  This is
    # reported rather than automatically rejected; exact signatures and
    # translation-equivalent geometry shapes are already component-locked.
    drop_axes = [
        "resource_headroom",
        "recovery_regime",
        "evidence_regime",
        "overlap_count",
        "report_interval_s",
        "warning_state",
        "monitoring_grade",
    ]
    near = {}
    for drop in drop_axes:
        owners: dict[str, set[str]] = defaultdict(set)
        counts: Counter[str] = Counter()
        for row in rows:
            fp = _fingerprint(row, axes[str(row["recipe_id"])], drop=drop)
            owners[fp].add(str(row["split"]))
            counts[fp] += 1
        cross = [fp for fp, splits in owners.items() if len(splits) > 1]
        near[drop] = {
            "cross_split_neighbor_fingerprint_count": len(cross),
            "rows_in_cross_split_neighbor_fingerprints": sum(counts[fp] for fp in cross),
        }

    hard_rows = [r for r in rows if r["candidate_role"] == "HARD_PRE_ADMISSION_SURVIVOR"]
    hard_by_split = Counter(str(r["split"]) for r in hard_rows)
    hard_sig_by_split = defaultdict(set)
    for r in hard_rows:
        hard_sig_by_split[str(r["split"])].add(str(r["signature"]))

    required_axes = {
        "service_processes": {"FINITE_CROSSING_WINDOWS"},
        "evidence_regimes": {"GATEWAY_SUMMARY_QUERY"},
        "overlap_counts": {3, 4},
        "resource_headroom": {"TIGHT", "BALANCED", "SLACK"},
        "recovery_regimes": {"NO_RECOVERY_STATE", "OUTAGE_CACHE_RETAIN", "RECONNECT_RECONCILE_OBJECTIVE_CHECK"},
    }
    hard_coverage = {}
    for s in ("train", "dev", "test"):
        subset = [r for r in hard_rows if r["split"] == s]
        observed = {
            "service_processes": {str(r["service_process"]) for r in subset},
            "evidence_regimes": {str(r["evidence_regime"]) for r in subset},
            "overlap_counts": {int(r["overlap_count"]) for r in subset},
            "resource_headroom": {str(axes[str(r["recipe_id"])]["resource_headroom"]) for r in subset},
            "recovery_regimes": {str(r["recovery_regime"]) for r in subset},
        }
        hard_coverage[s] = {
            k: {
                "observed": sorted(v),
                "missing_from_global_hard_axes": sorted(required_axes[k] - v),
            }
            for k, v in observed.items()
        }

    return {
        "schema_version": "0.1",
        "status": "SCALE_COVERAGE_NEAR_DUPLICATE_AUDIT",
        "split_summary": rendered,
        "hard_survivor": {
            "recipe_count": len(hard_rows),
            "recipe_by_split": dict(sorted(hard_by_split.items())),
            "signature_by_split": {s: len(v) for s, v in sorted(hard_sig_by_split.items())},
            "axis_coverage": hard_coverage,
        },
        "near_duplicate_one_axis": near,
        "hard_invariants": {
            "structural_component_leakage_passed": bool(split["leakage_audit"]["passed"]),
            "exact_solver_signature_cross_split_overlap": split["leakage_audit"]["solver_signature_overlap"],
        },
        "release_status": "NOT_BENCHMARK_ADMIT",
    }


if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False, indent=2, sort_keys=True))
