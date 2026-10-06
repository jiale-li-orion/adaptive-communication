#!/usr/bin/env python3
"""Generate the method-independent Layer-1 v0.6 pre-oracle case universe.

The generator consumes only:
  * source-resolved DB44 landslide reporting cells;
  * the frozen Layer-1 environment/generation contract and generation axes;
  * the frozen Connecta geometry trace.

It deliberately does not import or read ordinary baselines, Layer-2, Layer-3,
or hard-case labels.  Hardness is a downstream measurement.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
from typing import Any, Iterable

from compositional_recipe_generator_v0_1 import _db44_resolved_cases


ROOT = Path(__file__).resolve().parents[3]
AXES_PATH = ROOT / "research/benchmark/GENERATION-AXES.v0.1.json"
CONTRACT_PATH = ROOT / "research/benchmark/ENVIRONMENT-GENERATION-CONTRACT.v0.1.md"
PROFILE_MANIFEST_PATH = ROOT / "research/benchmark/PROFILE-BUNDLE-MANIFEST.v0.1.json"
TRACE_REGISTRY_PATH = ROOT / "research/benchmark/profiles/v0.1/TRACE-PROFILE-REGISTRY.v0.1.json"
DEFAULT_OUT = ROOT / "local_research/current/benchmark/generated/layer1-v0.6-preoracle"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_file(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def _canonical(obj: Any) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _id(prefix: str, payload: Any) -> str:
    return f"{prefix}-{_sha_bytes(_canonical(payload))[:16]}"


def _write_gzip_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    canonical_hasher = hashlib.sha256()
    count = 0
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as gz:
            for row in rows:
                line = _canonical(row)
                canonical_hasher.update(line)
                gz.write(line)
                count += 1
    return {
        "path": str(path.relative_to(ROOT)),
        "rows": count,
        "bytes": path.stat().st_size,
        "sha256": _sha_file(path),
        "canonical_uncompressed_sha256": canonical_hasher.hexdigest(),
    }


def _git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "UNKNOWN"


@dataclass(frozen=True)
class Obligation:
    oid: str
    stream: str
    ordinal: int
    release_s: int
    deadline_s: int


def _task_cells() -> list[dict[str, Any]]:
    rows = []
    for case in _db44_resolved_cases():
        rows.append({
            "task_case_id": str(case["case_id"]),
            "monitoring_grade": int(case["world"]["monitoring_grade"]),
            "warning_state": str(case["world"]["warning_state"]),
            "report_interval_s": int(case["world"]["report_interval_s"]),
            "source_profile_id": str(case["source_profiles"][0]),
            "report_interval_provenance": case["variable_provenance"]["report_interval_s"],
        })
    return sorted(rows, key=lambda r: r["task_case_id"])


def _obligations(interval_s: int, per_stream: int, phase_mode: str) -> list[Obligation]:
    b_phase = 0 if phase_mode == "ALIGNED" else interval_s // 2
    rows: list[Obligation] = []
    for i in range(per_stream):
        for stream, phase in (("A", 0), ("B", b_phase)):
            release = i * interval_s + phase
            rows.append(Obligation(
                oid=f"{stream}{i}",
                stream=stream,
                ordinal=i,
                release_s=release,
                deadline_s=release + interval_s,
            ))
    return sorted(rows, key=lambda o: (o.release_s, o.stream, o.ordinal))


def _release_stages(obligations: list[Obligation]) -> list[int]:
    return sorted({o.release_s for o in obligations})


def _runs(bits: tuple[bool, ...], value: bool) -> int:
    runs = 0
    inside = False
    for bit in bits:
        if bit == value and not inside:
            runs += 1
            inside = True
        elif bit != value:
            inside = False
    return runs


def _service_support(stage_count: int, family: str) -> list[tuple[bool, ...]]:
    if stage_count <= 0:
        return []
    out: list[tuple[bool, ...]] = []
    for mask in range(1 << stage_count):
        bits = tuple(bool(mask & (1 << i)) for i in range(stage_count))  # True=UP
        down_runs = _runs(bits, False)
        if family == "SINGLE_RECOVERY" and down_runs <= 1:
            out.append(bits)
        elif family == "REINTERRUPTIBLE" and down_runs <= 2:
            out.append(bits)
        elif family == "FULL_BINARY_SUPPORT":
            out.append(bits)
    return sorted(out)


def _terr_opportunities(obligations: list[Obligation], interval_s: int, ratios: list[float], capacity: int) -> list[dict[str, Any]]:
    times = set()
    for o in obligations:
        for ratio in ratios:
            t = o.release_s + int(round(interval_s * float(ratio)))
            if o.release_s <= t <= o.deadline_s:
                times.add(t)
    stages = _release_stages(obligations)
    rows = []
    for t in sorted(times):
        stage_idx = max(i for i, s in enumerate(stages) if s <= t)
        rows.append({
            "opportunity_id": f"terr@{t}",
            "time_s": t,
            "capacity_units": int(capacity),
            "service_stage_index": stage_idx,
        })
    return rows


def _parse_trace_windows(trace: dict[str, Any], mask: int) -> list[tuple[int, int]]:
    t0 = datetime.fromisoformat(trace["start_utc"])
    rows = []
    for w in trace["thresholds"][str(mask)]["windows_utc"]:
        start = int((datetime.fromisoformat(w["start"]) - t0).total_seconds())
        end = int((datetime.fromisoformat(w["end"]) - t0).total_seconds())
        rows.append((start, end))
    return rows


def _round300(x: int) -> int:
    return int(round(x / 300.0) * 300)


def _geometry_catalog(trace: dict[str, Any], axes: dict[str, Any], horizon_s: int) -> tuple[list[dict[str, Any]], dict[str, int]]:
    cfg = axes["model_derived"]["satellite_geometry"]
    stride = int(cfg["slice_start_stride_s"])
    trace_horizon_s = int(trace["hours"]) * 3600
    masks = [int(x) for x in cfg["elevation_mask_deg"]]
    raw_slices = 0
    by_shape: dict[tuple[int, tuple[tuple[int, int], ...]], dict[str, Any]] = {}
    for mask in masks:
        windows = _parse_trace_windows(trace, mask)
        for start in range(0, trace_horizon_s - horizon_s + 1, stride):
            raw_slices += 1
            end = start + horizon_s
            rel = tuple(
                (ws - start, min(we, end) - start)
                for ws, we in windows
                if start <= ws < end
            )
            rounded = tuple((_round300(a), _round300(b)) for a, b in rel)
            key = (mask, rounded)
            if key not in by_shape:
                by_shape[key] = {
                    "elevation_mask_deg": mask,
                    "horizon_s": horizon_s,
                    "representative_slice_start_s": start,
                    "equivalent_slice_count": 0,
                    "equivalent_slice_starts_s": [],
                    "relative_windows_s": [[a, b] for a, b in rel],
                    "rounded_shape_s": [[a, b] for a, b in rounded],
                }
            by_shape[key]["equivalent_slice_count"] += 1
            by_shape[key]["equivalent_slice_starts_s"].append(start)
    rows = []
    for (_mask, _shape), row in sorted(by_shape.items(), key=lambda kv: (kv[0][0], kv[1]["representative_slice_start_s"], kv[0][1])):
        payload = {
            "elevation_mask_deg": row["elevation_mask_deg"],
            "horizon_s": row["horizon_s"],
            "rounded_shape_s": row["rounded_shape_s"],
        }
        row["geometry_signature_id"] = _id("GEO6", payload)
        rows.append(row)
    return rows, {"raw_slice_count": raw_slices, "signature_count": len(rows)}


def _edf_feasible(obligations: list[Obligation], selected: tuple[int, ...], opportunities: list[dict[str, Any]]) -> bool:
    """Exact feasibility for unit jobs on discrete opportunities with capacities.

    For release/deadline interval jobs, scheduling the available job with the
    earliest deadline at each discrete capacity unit is feasibility-optimal.
    """
    pending = {i for i in selected}
    for opportunity in sorted(opportunities, key=lambda row: int(row["time_s"])):
        t = int(opportunity["time_s"])
        if any(obligations[i].deadline_s < t for i in pending if obligations[i].release_s <= t):
            return False
        for _ in range(int(opportunity["capacity_units"])):
            ready = [
                i for i in pending
                if obligations[i].release_s <= t <= obligations[i].deadline_s
            ]
            if not ready:
                break
            pick = min(ready, key=lambda i: (obligations[i].deadline_s, obligations[i].release_s, obligations[i].oid))
            pending.remove(pick)
    return not pending


def _min_backup_demand(obligations: list[Obligation], terr: list[dict[str, Any]], sat: list[dict[str, Any]], service_bits: tuple[bool, ...]) -> int | None:
    active_terr = [
        row for row in terr
        if service_bits[int(row["service_stage_index"])]
    ]
    n = len(obligations)
    all_idx = tuple(range(n))
    # At most six obligations by contract: enumerate satellite-assignment
    # subsets in ascending cardinality.  The first feasible partition is the
    # exact minimum backup demand.
    for sat_count in range(n + 1):
        from itertools import combinations
        for sat_idx in combinations(all_idx, sat_count):
            sat_set = set(sat_idx)
            terr_idx = tuple(i for i in all_idx if i not in sat_set)
            if _edf_feasible(obligations, terr_idx, active_terr) and _edf_feasible(obligations, tuple(sat_idx), sat):
                return sat_count
    return None


class _GzipJsonlWriter:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.raw = self.path.open("wb")
        self.gz = gzip.GzipFile(filename="", mode="wb", fileobj=self.raw, mtime=0, compresslevel=9)
        self.hasher = hashlib.sha256()
        self.count = 0

    def write(self, row: dict[str, Any]) -> None:
        line = _canonical(row)
        self.hasher.update(line)
        self.gz.write(line)
        self.count += 1

    def close(self) -> dict[str, Any]:
        self.gz.close()
        self.raw.close()
        return {
            "path": str(self.path.relative_to(ROOT)),
            "rows": self.count,
            "bytes": self.path.stat().st_size,
            "sha256": _sha_file(self.path),
            "canonical_uncompressed_sha256": self.hasher.hexdigest(),
        }


def _world_rows(obligations: list[Obligation], terr: list[dict[str, Any]], sat: list[dict[str, Any]], support: list[tuple[bool, ...]]) -> tuple[list[dict[str, Any]], str, int | None]:
    rows = []
    demands: list[int | None] = []
    for idx, bits in enumerate(support):
        demand = _min_backup_demand(obligations, terr, sat, bits)
        demands.append(demand)
        rows.append({
            "world_id": f"W{idx:03d}-" + "".join("U" if b else "D" for b in bits),
            "service_by_stage": ["UP" if b else "DOWN" for b in bits],
            "min_backup_demand": demand,
        })
    feasible = sum(d is not None for d in demands)
    if feasible == len(demands):
        status = "ALL_WORLD_PHYSICAL"
        tight = max(int(d) for d in demands if d is not None)
    elif feasible == 0:
        status = "NO_WORLD_PHYSICAL"
        tight = None
    else:
        status = "MIXED_WORLD_PHYSICAL"
        tight = None
    return rows, status, tight


def _artifact_inputs() -> dict[str, Any]:
    axes = _read_json(AXES_PATH)
    trace_path = ROOT / axes["model_derived"]["satellite_geometry"]["trace_path"]
    return {
        "generator_code": str(Path(__file__).resolve().relative_to(ROOT)),
        "generator_code_sha256": _sha_file(Path(__file__).resolve()),
        "generation_axes": str(AXES_PATH.relative_to(ROOT)),
        "generation_axes_sha256": _sha_file(AXES_PATH),
        "environment_contract": str(CONTRACT_PATH.relative_to(ROOT)),
        "environment_contract_sha256": _sha_file(CONTRACT_PATH),
        "profile_bundle_manifest": str(PROFILE_MANIFEST_PATH.relative_to(ROOT)),
        "profile_bundle_manifest_sha256": _sha_file(PROFILE_MANIFEST_PATH),
        "trace": str(trace_path.relative_to(ROOT)),
        "trace_sha256": _sha_file(trace_path),
        "git_commit": _git_head(),
    }


def generate(out_dir: Path) -> dict[str, Any]:
    axes = _read_json(AXES_PATH)
    trace_path = ROOT / axes["model_derived"]["satellite_geometry"]["trace_path"]
    trace = _read_json(trace_path)
    cs = axes["controlled_stress"]
    source_cells = _task_cells()

    composition_rows = []
    preflight = Counter()
    for cell in source_cells:
        interval = int(cell["report_interval_s"])
        for per_stream in cs["obligation_composition"]["obligations_per_stream"]:
            for phase_mode in cs["obligation_composition"]["stream_phase_modes"]:
                obs = _obligations(interval, int(per_stream), str(phase_mode))
                stages = _release_stages(obs)
                horizon = max(o.deadline_s for o in obs)
                if len(stages) < 3:
                    preflight["EXCLUDED_LT3_RELEASE_STAGES"] += 1
                    continue
                if horizon > int(trace["hours"]) * 3600:
                    preflight["EXCLUDED_GEOMETRY_HORIZON"] += 1
                    continue
                composition_rows.append((cell, int(per_stream), str(phase_mode), obs, stages, horizon))
                preflight["ELIGIBLE_COMPOSITION"] += 1

    geometry_cache: dict[int, tuple[list[dict[str, Any]], dict[str, int]]] = {}
    geometry_rows_by_id: dict[str, dict[str, Any]] = {}
    base_status = Counter()
    axis_counts = Counter()
    physical_cache: dict[tuple[Any, ...], tuple[list[dict[str, Any]], str, int | None, list[dict[str, Any]]]] = {}
    support_cache: dict[tuple[int, str], list[tuple[bool, ...]]] = {}
    base_structure_ids: set[str] = set()
    physical_base_structure_ids: set[str] = set()
    physical_base_count = 0

    out_dir.mkdir(parents=True, exist_ok=True)
    base_writer = _GzipJsonlWriter(out_dir / "base-scenarios.jsonl.gz")
    case_writer = _GzipJsonlWriter(out_dir / "cases.jsonl.gz")

    for cell, per_stream, phase_mode, obs, stages, horizon in composition_rows:
        if horizon not in geometry_cache:
            geometry_cache[horizon] = _geometry_catalog(trace, axes, horizon)
        geometries, _geo_stats = geometry_cache[horizon]
        for geo in geometries:
            geometry_rows_by_id.setdefault(geo["geometry_signature_id"], geo)
            sat = [
                {
                    "opportunity_id": f"sat@{int(start)}",
                    "time_s": int(start),
                    "window_end_s": int(end),
                    "capacity_units": int(cs["satellite_window_capacity_units"]),
                }
                for start, end in geo["relative_windows_s"]
            ]
            for family in cs["terrestrial_service_process"]["support_families"]:
                support_key = (len(stages), str(family["id"]))
                support = support_cache.setdefault(support_key, _service_support(*support_key))
                for terr_capacity in cs["terrestrial_opportunities"]["capacity_units"]:
                    physical_key = (
                        int(cell["report_interval_s"]),
                        per_stream,
                        phase_mode,
                        geo["geometry_signature_id"],
                        str(family["id"]),
                        int(terr_capacity),
                    )
                    if physical_key in physical_cache:
                        worlds, physical_status, tight, terr = physical_cache[physical_key]
                    else:
                        terr = _terr_opportunities(obs, int(cell["report_interval_s"]), cs["terrestrial_opportunities"]["phase_ratios"], int(terr_capacity))
                        worlds, physical_status, tight = _world_rows(obs, terr, sat, support)
                        physical_cache[physical_key] = (worlds, physical_status, tight, terr)
                    base_payload = {
                        "schema_version": "0.6",
                        "task": cell,
                        "composition": {
                            "stream_count": 2,
                            "obligations_per_stream": per_stream,
                            "phase_mode": phase_mode,
                            "obligations": [o.__dict__ for o in obs],
                            "release_stages_s": stages,
                            "horizon_s": horizon,
                        },
                        "service_process": {
                            "family": family["id"],
                            "definition": family["definition"],
                            "world_count": len(worlds),
                            "worlds": worlds,
                            "probability_model": None,
                        },
                        "terrestrial": {
                            "capacity_units_per_opportunity": int(terr_capacity),
                            "opportunities": terr,
                        },
                        "satellite": {
                            "trace_profile": axes["model_derived"]["satellite_geometry"]["trace_profile"],
                            "geometry_signature_id": geo["geometry_signature_id"],
                            "elevation_mask_deg": geo["elevation_mask_deg"],
                            "representative_slice_start_s": geo["representative_slice_start_s"],
                            "equivalent_slice_count": geo["equivalent_slice_count"],
                            "opportunities": sat,
                            "window_capacity_units": int(cs["satellite_window_capacity_units"]),
                        },
                        "physical": {
                            "status": physical_status,
                            "tight_fallback_budget_units": tight,
                            "derivation": "full-state min-cost obligation-to-opportunity matching; terrestrial cost 0, satellite cost 1",
                        },
                        "provenance": {
                            "source_profiles": [
                                axes["scope"]["primary_task_profile"],
                                *axes["scope"]["supporting_operational_profiles"],
                            ],
                            "model_trace": axes["model_derived"]["satellite_geometry"]["trace_profile"],
                            "controlled_stress_axes": [
                                "obligation_composition",
                                "terrestrial_service_process",
                                "terrestrial_opportunities",
                                "satellite_window_capacity_units",
                            ],
                        },
                    }
                    base_id = _id("T1V06B", base_payload)
                    base_payload["base_id"] = base_id
                    structure_payload = {
                        "report_interval_s": cell["report_interval_s"],
                        "per_stream": per_stream,
                        "phase_mode": phase_mode,
                        "service_family": family["id"],
                        "terr_capacity": int(terr_capacity),
                        "geometry_shape": geo["rounded_shape_s"],
                        "elevation_mask_deg": geo["elevation_mask_deg"],
                    }
                    base_payload["base_structure_id"] = _id("T1V06BS", structure_payload)
                    base_structure_ids.add(base_payload["base_structure_id"])
                    base_writer.write(base_payload)
                    base_status[physical_status] += 1
                    axis_counts[f"service::{family['id']}"] += 1
                    axis_counts[f"phase::{phase_mode}"] += 1
                    axis_counts[f"per_stream::{per_stream}"] += 1
                    axis_counts[f"terr_capacity::{terr_capacity}"] += 1
                    axis_counts[f"mask::{geo['elevation_mask_deg']}"] += 1

                    if physical_status != "ALL_WORLD_PHYSICAL":
                        continue
                    physical_base_count += 1
                    physical_base_structure_ids.add(base_payload["base_structure_id"])
                    n_obligations = len(obs)
                    for feedback in cs["feedback_timing_profiles"]:
                        receipt_delay = int(round(float(feedback["gateway_receipt_delay_over_deadline"]) * int(cell["report_interval_s"])))
                        ack_delay = int(round(float(feedback["final_ack_delay_over_deadline"]) * int(cell["report_interval_s"])))
                        for query_ratio in cs["remote_query_response_delay_over_deadline"]:
                            query_delay = int(round(float(query_ratio) * int(cell["report_interval_s"])))
                            for mode in cs["fallback_budget_modes"]:
                                if mode["id"] == "TIGHT":
                                    budget = int(tight)
                                elif mode["id"] == "BALANCED":
                                    budget = min(int(tight) + 1, n_obligations)
                                elif mode["id"] == "SLACK_CONTROL":
                                    budget = n_obligations
                                else:
                                    raise ValueError(mode["id"])
                                variant = {
                                    "schema_version": "0.6",
                                    "base_id": base_id,
                                    "feedback_profile": feedback["id"],
                                    "gateway_receipt_delay_s": receipt_delay,
                                    "final_ack_delay_s": ack_delay,
                                    "remote_query": {
                                        "capability_id": cs["evidence_capabilities"]["dedicated_query"]["id"],
                                        "proposition": cs["evidence_capabilities"]["dedicated_query"]["proposition"],
                                        "owner": cs["evidence_capabilities"]["dedicated_query"]["owner"],
                                        "response_delay_ratio": float(query_ratio),
                                        "response_delay_s": query_delay,
                                        "center_transport": cs["remote_query_transport"]["center_placement"],
                                        "future_state_access": False,
                                    },
                                    "natural_feedback": list(axes["natural_feedback_always_enabled"]),
                                    "fallback_budget_mode": mode["id"],
                                    "fallback_budget_units": budget,
                                    "physical_status": physical_status,
                                    "provenance_classes": {
                                        "deadline": "FIXED_BY_SOURCE",
                                        "satellite_geometry": "MODEL_DERIVED_TRACE",
                                        "feedback_timing": "CONTROLLED_STRESS",
                                        "query_timing": "CONTROLLED_STRESS",
                                        "fallback_headroom": "MODEL_DERIVED_FROM_FULL_STATE_PHYSICAL_MATCHING",
                                    },
                                }
                                case_id = _id("T1V06C", variant)
                                variant["case_id"] = case_id
                                variant["structure_id"] = _id("T1V06S", {
                                    "base_structure_id": base_payload["base_structure_id"],
                                    "feedback_profile": feedback["id"],
                                    "query_ratio": float(query_ratio),
                                    "fallback_budget_mode": mode["id"],
                                })
                                case_writer.write(variant)

    base_artifact = base_writer.close()
    case_artifact = case_writer.close()
    geometry_rows = sorted(geometry_rows_by_id.values(), key=lambda r: r["geometry_signature_id"])
    artifacts = {
        "geometry_signatures": _write_gzip_jsonl(out_dir / "geometry-signatures.jsonl.gz", geometry_rows),
        "base_scenarios": base_artifact,
        "cases": case_artifact,
    }
    variant_count = (
        len(cs["feedback_timing_profiles"])
        * len(cs["remote_query_response_delay_over_deadline"])
        * len(cs["fallback_budget_modes"])
    )
    structure_count = len(physical_base_structure_ids) * variant_count
    base_structure_count = len(base_structure_ids)
    geometry_stats = {
        str(h): stats for h, (_rows, stats) in sorted(geometry_cache.items())
    }
    manifest = {
        "schema_version": "0.6",
        "status": "PRE_ORACLE_GENERATED",
        "generator_id": "LAYER1_T1_DYNAMIC_PREORACLE_V06",
        "inputs": _artifact_inputs(),
        "generation_pipeline": "research/benchmark/CASE-GENERATION-PIPELINE.v0.1.md",
        "counts": {
            "source_task_cells": len(source_cells),
            "eligible_compositions": len(composition_rows),
            "geometry_signatures": len(geometry_rows),
            "base_scenarios": base_artifact["rows"],
            "base_structures": base_structure_count,
            "cases": case_artifact["rows"],
            "structures": structure_count,
            "all_world_physical_bases": physical_base_count,
            "all_world_physical_base_structures": len(physical_base_structure_ids),
            "variants_per_physical_base": variant_count,
        },
        "preflight_counts": dict(sorted(preflight.items())),
        "base_physical_status": dict(sorted(base_status.items())),
        "base_axis_counts": dict(sorted(axis_counts.items())),
        "geometry_by_horizon": geometry_stats,
        "derivation_cache": {
            "physical_topology_entries": len(physical_cache),
            "service_support_entries": len(support_cache),
            "note": "cache keys contain only source/geometry/stress topology, never baseline or method results",
        },
        "artifacts": artifacts,
        "regenerate": "PYTHONPATH=code/evaluation/benchmark python3 code/evaluation/benchmark/generate_layer1_v06_cases.py",
        "claim_boundary": [
            "PRE_ORACLE_GENERATED is not BENCHMARK_ADMIT and is not a hardness claim.",
            "No baseline, Layer-2 or Layer-3 result is read by this generator.",
            "Service supports and timing/resource stress axes are controlled stress, not field frequencies.",
            "Connecta geometry is model-derived visibility, not measured contact or PHY success.",
            "Only ALL_WORLD_PHYSICAL base scenarios expand to dynamic case variants; invalid/mixed bases remain in base-scenarios for diagnostics.",
        ],
    }
    (out_dir / "MANIFEST.json").write_bytes(_canonical(manifest))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--print-manifest", action="store_true")
    args = parser.parse_args()
    manifest = generate(args.out.resolve())
    if args.print_manifest:
        print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps({
            "status": manifest["status"],
            "counts": manifest["counts"],
            "base_physical_status": manifest["base_physical_status"],
            "artifacts": manifest["artifacts"],
        }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
