#!/usr/bin/env python3
"""Audit a generated Layer-1 v0.6 pre-oracle universe.

The audit is intentionally streaming for the multi-million-case artifact.
It verifies input/artifact hashes, deterministic IDs, frozen-axis membership,
base references, and fallback-budget derivation.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any, Iterator

from generate_layer1_v06_cases import (
    AXES_PATH,
    CONTRACT_PATH,
    DEFAULT_OUT,
    PROFILE_MANIFEST_PATH,
    ROOT,
    _canonical,
    _id,
    _read_json,
    _sha_file,
    generate,
)


def _rows(path: Path) -> Iterator[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def _canonical_uncompressed_sha(path: Path) -> tuple[str, int]:
    h = hashlib.sha256()
    n = 0
    for row in _rows(path):
        h.update(_canonical(row))
        n += 1
    return h.hexdigest(), n


def _artifact_check(root: Path, meta: dict[str, Any]) -> None:
    path = ROOT / meta["path"] if not Path(meta["path"]).is_absolute() else Path(meta["path"])
    if root != DEFAULT_OUT.resolve():
        path = root / Path(meta["path"]).name
    assert path.exists(), path
    assert path.stat().st_size == meta["bytes"]
    assert _sha_file(path) == meta["sha256"]
    canonical_sha, rows = _canonical_uncompressed_sha(path)
    assert canonical_sha == meta["canonical_uncompressed_sha256"]
    assert rows == meta["rows"]


def audit(out_dir: Path) -> dict[str, Any]:
    out_dir = out_dir.resolve()
    complete_path = out_dir / "COMPLETE.json"
    assert complete_path.exists(), "official generation run is incomplete: COMPLETE.json missing"
    complete = _read_json(complete_path)
    assert complete["status"] == "COMPLETE"
    manifest = _read_json(out_dir / "MANIFEST.json")
    assert complete["manifest_sha256"] == _sha_file(out_dir / "MANIFEST.json")
    assert complete["generator_code_sha256"] == manifest["inputs"]["generator_code_sha256"]
    assert complete["generation_axes_sha256"] == manifest["inputs"]["generation_axes_sha256"]
    axes = _read_json(AXES_PATH)
    inputs = manifest["inputs"]
    assert inputs["generation_axes_sha256"] == _sha_file(AXES_PATH)
    assert inputs["environment_contract_sha256"] == _sha_file(CONTRACT_PATH)
    assert inputs["profile_bundle_manifest_sha256"] == _sha_file(PROFILE_MANIFEST_PATH)
    trace = ROOT / inputs["trace"]
    assert inputs["trace_sha256"] == _sha_file(trace)

    for meta in manifest["artifacts"].values():
        _artifact_check(out_dir, meta)

    geometry_path = out_dir / "geometry-signatures.jsonl.gz"
    geometry_ids = set()
    geometry_shapes: dict[str, list[list[int]]] = {}
    for row in _rows(geometry_path):
        expected = _id("GEO6", {
            "elevation_mask_deg": row["elevation_mask_deg"],
            "horizon_s": row["horizon_s"],
            "rounded_shape_s": row["rounded_shape_s"],
        })
        assert row["geometry_signature_id"] == expected
        assert row["elevation_mask_deg"] in axes["model_derived"]["satellite_geometry"]["elevation_mask_deg"]
        assert row["equivalent_slice_count"] == len(row["equivalent_slice_starts_s"])
        assert row["equivalent_slice_starts_s"] == sorted(row["equivalent_slice_starts_s"])
        assert row["representative_slice_start_s"] == row["equivalent_slice_starts_s"][0]
        assert row["equivalent_slice_count"] == len(row["equivalent_slice_starts_s"])
        assert row["equivalent_slice_starts_s"] == sorted(row["equivalent_slice_starts_s"])
        assert row["representative_slice_start_s"] == row["equivalent_slice_starts_s"][0]
        geometry_ids.add(expected)
        geometry_shapes[expected] = row["rounded_shape_s"]

    base_path = out_dir / "base-scenarios.jsonl.gz"
    bases: dict[str, dict[str, Any]] = {}
    base_structures = set()
    physical_counts = Counter()
    for row in _rows(base_path):
        stored_id = row["base_id"]
        stored_structure = row["base_structure_id"]
        content = dict(row)
        content.pop("base_id")
        content.pop("base_structure_id")
        assert stored_id == _id("T1V06B", content)
        structure_payload = {
            "report_interval_s": row["task"]["report_interval_s"],
            "per_stream": row["composition"]["obligations_per_stream"],
            "phase_mode": row["composition"]["phase_mode"],
            "service_family": row["service_process"]["family"],
            "terr_capacity": row["terrestrial"]["capacity_units_per_opportunity"],
            "geometry_shape": geometry_shapes[row["satellite"]["geometry_signature_id"]],
            "elevation_mask_deg": row["satellite"]["elevation_mask_deg"],
        }
        assert stored_structure == _id("T1V06BS", structure_payload)
        assert row["satellite"]["geometry_signature_id"] in geometry_ids
        tight = row["physical"]["tight_fallback_budget_units"]
        demands = [w["min_backup_demand"] for w in row["service_process"]["worlds"]]
        if row["physical"]["status"] == "ALL_WORLD_PHYSICAL":
            assert all(d is not None for d in demands)
            assert tight == max(demands)
        else:
            assert tight is None
        bases[stored_id] = {
            "base_structure_id": stored_structure,
            "tight": tight,
            "n_obligations": len(row["composition"]["obligations"]),
            "status": row["physical"]["status"],
        }
        base_structures.add(stored_structure)
        physical_counts[row["physical"]["status"]] += 1

    case_path = out_dir / "cases.jsonl.gz"
    case_count = 0
    structures = set()
    fallback_counts = Counter()
    valid_feedback = {r["id"] for r in axes["controlled_stress"]["feedback_timing_profiles"]}
    valid_query = {float(x) for x in axes["controlled_stress"]["remote_query_response_delay_over_deadline"]}
    valid_modes = {r["id"] for r in axes["controlled_stress"]["fallback_budget_modes"]}
    for row in _rows(case_path):
        case_count += 1
        base = bases[row["base_id"]]
        assert base["status"] == "ALL_WORLD_PHYSICAL"
        content = dict(row)
        stored_case = content.pop("case_id")
        stored_structure = content.pop("structure_id")
        assert stored_case == _id("T1V06C", content)
        assert row["feedback_profile"] in valid_feedback
        assert float(row["remote_query"]["response_delay_ratio"]) in valid_query
        assert row["fallback_budget_mode"] in valid_modes
        if row["fallback_budget_mode"] == "TIGHT":
            expected_budget = base["tight"]
        elif row["fallback_budget_mode"] == "BALANCED":
            expected_budget = min(int(base["tight"]) + 1, base["n_obligations"])
        else:
            expected_budget = base["n_obligations"]
        assert row["fallback_budget_units"] == expected_budget
        expected_structure = _id("T1V06S", {
            "base_structure_id": base["base_structure_id"],
            "feedback_profile": row["feedback_profile"],
            "query_ratio": float(row["remote_query"]["response_delay_ratio"]),
            "fallback_budget_mode": row["fallback_budget_mode"],
        })
        assert stored_structure == expected_structure
        structures.add(stored_structure)
        fallback_counts[row["fallback_budget_mode"]] += 1

    assert len(bases) == manifest["counts"]["base_scenarios"]
    assert len(base_structures) == manifest["counts"]["base_structures"]
    assert case_count == manifest["counts"]["cases"]
    assert len(structures) == manifest["counts"]["structures"]
    return {
        "base_count": len(bases),
        "case_count": case_count,
        "structure_count": len(structures),
        "physical_counts": dict(sorted(physical_counts.items())),
        "fallback_counts": dict(sorted(fallback_counts.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--reproduce", action="store_true")
    args = parser.parse_args()
    result = audit(args.out)
    if args.reproduce:
        repro_parent = ROOT / "local_research/current/benchmark/generated"
        repro_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="layer1-v06-repro-", dir=repro_parent) as td:
            repro = Path(td)
            generated = generate(repro)
            original = _read_json(args.out.resolve() / "MANIFEST.json")
            for name in original["artifacts"]:
                assert generated["artifacts"][name]["canonical_uncompressed_sha256"] == original["artifacts"][name]["canonical_uncompressed_sha256"]
                assert generated["artifacts"][name]["rows"] == original["artifacts"][name]["rows"]
            result["reproduction"] = "BYTE_CANONICAL_MATCH"
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

