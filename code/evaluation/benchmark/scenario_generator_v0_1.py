#!/usr/bin/env python3
"""Deterministic Layer-1 scenario generator with exact feasibility oracle.

Generator ID: T1_ESCALATION_RESOURCE_COUPLING_V0

The generator combines source-backed task/capability/site/payload/geometry
primitives with preregistered controlled stress axes. It mines decision-valid
cases using exact feasibility properties only; model performance is never read.
"""
from __future__ import annotations

from bisect import bisect_left
from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
from itertools import product
from pathlib import Path
from typing import Any, Iterable, Mapping
import argparse
import gzip
import json
import math

from source_derivation import parse_interval_range_s

ROOT = Path(__file__).resolve().parents[3]
BENCH = ROOT / "research/benchmark"
PROFILE_DIR = BENCH / "profiles/v0.1"
TRACE_DIR = BENCH / "traces/v0.1"

WARNING_INDEX = {
    "none_stable": 0,
    "blue": 1,
    "yellow": 2,
    "orange": 3,
    "red": 4,
}


class GeneratorError(ValueError):
    pass


@dataclass(frozen=True)
class Obligation:
    obligation_id: str
    release_s: int
    deadline_s: int


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _canonical_hash(payload: Mapping[str, Any], n: int = 16) -> str:
    raw = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return sha256(raw).hexdigest()[:n]


def _range_boundaries(text: str) -> list[int]:
    lo, hi = parse_interval_range_s(text)
    return [lo] if lo == hi else [lo, hi]


def _cadence_values(
    task_profile: Mapping[str, Any],
    *,
    grade: int,
    warning_state: str,
) -> list[int]:
    table = task_profile["variables"]["cadence_table"]["value"]
    row = table[f"grade{grade}"]
    return _range_boundaries(str(row[WARNING_INDEX[warning_state]]))


def _trace_slots(trace_payload: Mapping[str, Any], mask: int) -> list[int]:
    """Return every minute-aligned visible slot as seconds from trace start."""
    from datetime import datetime

    start = datetime.fromisoformat(str(trace_payload["start_utc"]))
    step = int(trace_payload["step_s"])
    row = trace_payload["thresholds"][str(mask)]
    slots: list[int] = []
    for window in row["windows_utc"]:
        ws = int((datetime.fromisoformat(window["start"]) - start).total_seconds())
        we = int((datetime.fromisoformat(window["end"]) - start).total_seconds())
        slots.extend(range(ws, we, step))
    return sorted(set(slots))


def _phase_bins(max_start_s: int, *, bins: int, step_s: int) -> list[int]:
    if max_start_s < 0:
        return []
    if max_start_s == 0 or bins <= 1:
        return [0]
    raw: list[int] = []
    for i in range(bins):
        x = i * max_start_s / (bins - 1)
        aligned = int(math.floor(x / step_s)) * step_s
        raw.append(min(max_start_s, aligned))
    return sorted(set(raw))


def _allocate_interval_jobs(
    jobs: list[Obligation],
    slots: list[int],
) -> dict[str, int] | None:
    """Exact interval matching for unit jobs on ordered discrete slots.

    Jobs have interval feasibility [release, deadline]. Sorting by deadline and
    assigning the earliest unused feasible slot is optimal for unit interval
    scheduling.
    """
    available = list(slots)
    plan: dict[str, int] = {}
    for job in sorted(jobs, key=lambda x: (x.deadline_s, x.release_s, x.obligation_id)):
        idx = bisect_left(available, job.release_s)
        if idx >= len(available) or available[idx] > job.deadline_s:
            return None
        plan[job.obligation_id] = available.pop(idx)
    return plan


def _terrestrial_slots(
    *,
    recovery_s: int,
    horizon_s: int,
    step_s: int,
    capacity_per_step: int,
) -> list[int]:
    if capacity_per_step <= 0:
        return []
    slots: list[int] = []
    first = int(math.ceil(recovery_s / step_s)) * step_s
    for t in range(first, horizon_s + 1, step_s):
        slots.extend([t] * capacity_per_step)
    return slots


def _satellite_slots(
    trace_slots: list[int],
    *,
    scenario_start_s: int,
    horizon_s: int,
    capacity_per_step: int,
) -> list[int]:
    if capacity_per_step <= 0:
        return []
    lo = bisect_left(trace_slots, scenario_start_s)
    hi = bisect_left(trace_slots, horizon_s + 1)
    slots: list[int] = []
    for t in trace_slots[lo:hi]:
        slots.extend([t] * capacity_per_step)
    return slots


def _solve_assignment(
    obligations: list[Obligation],
    *,
    terrestrial_slots: list[int],
    satellite_slots: list[int],
    satellite_budget: int,
    forced_paths: Mapping[str, str] | None = None,
    fixed_satellite_delivery: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    forced_paths = dict(forced_paths or {})
    fixed_satellite_delivery = dict(fixed_satellite_delivery or {})
    by_id = {o.obligation_id: o for o in obligations}

    fixed_ids = set(fixed_satellite_delivery)
    if not fixed_ids <= by_id.keys():
        raise GeneratorError("fixed delivery references unknown obligation")
    if len(fixed_ids) > satellite_budget:
        return {
            "solvable": False,
            "feasible_assignment_count": 0,
            "min_satellite_uses": None,
            "witness": None,
        }

    sat_slots = list(satellite_slots)
    fixed_plan: dict[str, dict[str, Any]] = {}
    for oid, t in fixed_satellite_delivery.items():
        o = by_id[oid]
        if not (o.release_s <= t <= o.deadline_s):
            return {
                "solvable": False,
                "feasible_assignment_count": 0,
                "min_satellite_uses": None,
                "witness": None,
            }
        try:
            sat_slots.remove(t)
        except ValueError:
            return {
                "solvable": False,
                "feasible_assignment_count": 0,
                "min_satellite_uses": None,
                "witness": None,
            }
        fixed_plan[oid] = {"path": "satellite", "delivery_s": t}

    remaining = [o for o in obligations if o.obligation_id not in fixed_ids]
    free_budget = satellite_budget - len(fixed_ids)
    feasible = 0
    min_sat: int | None = None
    witness: dict[str, Any] | None = None

    for bits in product((0, 1), repeat=len(remaining)):
        assignment = {
            o.obligation_id: ("satellite" if bit else "terrestrial")
            for o, bit in zip(remaining, bits)
        }
        legal = True
        for oid, path in forced_paths.items():
            if oid in fixed_ids:
                if path != "satellite":
                    legal = False
                    break
            elif assignment.get(oid) != path:
                legal = False
                break
        if not legal:
            continue

        sat_jobs = [o for o in remaining if assignment[o.obligation_id] == "satellite"]
        terr_jobs = [o for o in remaining if assignment[o.obligation_id] == "terrestrial"]
        if len(sat_jobs) > free_budget:
            continue

        sat_plan = _allocate_interval_jobs(sat_jobs, sat_slots)
        if sat_plan is None:
            continue
        terr_plan = _allocate_interval_jobs(terr_jobs, terrestrial_slots)
        if terr_plan is None:
            continue

        feasible += 1
        sat_uses = len(fixed_ids) + len(sat_jobs)
        if min_sat is None or sat_uses < min_sat:
            min_sat = sat_uses
            merged = dict(fixed_plan)
            for oid, t in sat_plan.items():
                merged[oid] = {"path": "satellite", "delivery_s": t}
            for oid, t in terr_plan.items():
                merged[oid] = {"path": "terrestrial", "delivery_s": t}
            witness = merged

    return {
        "solvable": feasible > 0,
        "feasible_assignment_count": feasible,
        "min_satellite_uses": min_sat,
        "witness": witness,
    }


def _first_satellite_decision_slot(
    satellite_slots: list[int],
    *,
    scenario_start_s: int,
    transition_s: int,
    routine_deadline_s: int,
) -> int | None:
    idx = bisect_left(satellite_slots, scenario_start_s)
    if idx >= len(satellite_slots):
        return None
    t = satellite_slots[idx]
    if t >= transition_s or t > routine_deadline_s:
        return None
    return t


def _scenario_oracle(
    obligations: list[Obligation],
    *,
    terrestrial_slots: list[int],
    satellite_slots: list[int],
    satellite_budget: int,
    transition_s: int,
    scenario_start_s: int,
) -> dict[str, Any]:
    routine = obligations[0]
    base = _solve_assignment(
        obligations,
        terrestrial_slots=terrestrial_slots,
        satellite_slots=satellite_slots,
        satellite_budget=satellite_budget,
    )
    lower_budget = _solve_assignment(
        obligations,
        terrestrial_slots=terrestrial_slots,
        satellite_slots=satellite_slots,
        satellite_budget=max(0, satellite_budget - 1),
    )

    decision_slot = _first_satellite_decision_slot(
        satellite_slots,
        scenario_start_s=scenario_start_s,
        transition_s=transition_s,
        routine_deadline_s=routine.deadline_s,
    )

    if decision_slot is None:
        forced_send = {
            "solvable": False,
            "feasible_assignment_count": 0,
            "min_satellite_uses": None,
            "witness": None,
        }
    else:
        forced_send = _solve_assignment(
            obligations,
            terrestrial_slots=terrestrial_slots,
            satellite_slots=satellite_slots,
            satellite_budget=satellite_budget,
            fixed_satellite_delivery={routine.obligation_id: decision_slot},
        )

    forced_wait = _solve_assignment(
        obligations,
        terrestrial_slots=terrestrial_slots,
        satellite_slots=satellite_slots,
        satellite_budget=satellite_budget,
        forced_paths={routine.obligation_id: "terrestrial"},
    )

    return {
        "base": base,
        "budget_minus_one": lower_budget,
        "decision_slot_s": decision_slot,
        "forced_send": forced_send,
        "forced_wait": forced_wait,
        "resource_binding": bool(
            base["solvable"] and not lower_budget["solvable"]
        ),
        "multiple_legal_first_actions": bool(
            decision_slot is not None and forced_wait["solvable"]
        ),
        "forced_send_wait_outcome_separation": bool(
            decision_slot is not None
            and forced_wait["solvable"] != forced_send["solvable"]
        ),
        # Ordinary per-obligation automatic fallback sends the already-released
        # routine report at the first satellite opportunity during outage.
        "greedy_baseline_success": bool(forced_send["solvable"]),
    }


def _disposition(
    oracle: Mapping[str, Any],
    *,
    hard_filter: Mapping[str, Any],
) -> str:
    if hard_filter.get("require_oracle_solvable") and not oracle["base"]["solvable"]:
        return "V1_UNSOLVABLE"
    if (
        hard_filter.get("require_multiple_legal_first_actions")
        and not oracle["multiple_legal_first_actions"]
    ):
        return "V2_NO_MULTIPLE_FIRST_ACTIONS"
    if hard_filter.get("require_satellite_budget_binding") and not oracle["resource_binding"]:
        return "V5_RESOURCE_NOT_BINDING"
    if (
        hard_filter.get("require_forced_send_wait_outcome_separation")
        and not oracle["forced_send_wait_outcome_separation"]
    ):
        return "V6_NO_OUTCOME_SEPARATION"
    if hard_filter.get("require_greedy_baseline_failure") and oracle["greedy_baseline_success"]:
        return "V8_GREEDY_BASELINE_SUCCEEDS"
    return "HARD_CANDIDATE"


def _obligations(
    *,
    scenario_start_s: int,
    pre_interval_s: int,
    transition_offset_s: int,
    post_interval_s: int,
    post_count: int,
) -> list[Obligation]:
    out = [
        Obligation(
            obligation_id="pre_warning_routine",
            release_s=scenario_start_s,
            deadline_s=scenario_start_s + pre_interval_s,
        )
    ]
    transition_abs = scenario_start_s + transition_offset_s
    for i in range(post_count):
        release = transition_abs + i * post_interval_s
        out.append(
            Obligation(
                obligation_id=f"post_warning_{i:02d}",
                release_s=release,
                deadline_s=release + post_interval_s,
            )
        )
    return out


def _build_context(config: Mapping[str, Any]) -> dict[str, Any]:
    source_registry = _load(PROFILE_DIR / "SOURCE-PROFILE-REGISTRY.v0.1.json")
    capability_registry = _load(PROFILE_DIR / "CAPABILITY-PROFILE-REGISTRY.v0.1.json")
    site_registry = _load(PROFILE_DIR / "SITE-PROFILE-REGISTRY.v0.1.json")
    trace_registry = _load(PROFILE_DIR / "TRACE-PROFILE-REGISTRY.v0.1.json")
    payload_registry = _load(PROFILE_DIR / "PAYLOAD-PROFILE-REGISTRY.v0.1.json")
    service_registry = _load(PROFILE_DIR / "SERVICE-TRACE-PROFILE-REGISTRY.v0.1.json")

    task = next(
        x for x in source_registry["profiles"]
        if x["profile_id"] == config["task_profile_id"]
    )
    capability = next(
        x for x in capability_registry["profiles"]
        if x["capability_profile_id"] == config["capability_profile_id"]
    )
    site = next(
        x for x in site_registry["profiles"]
        if x["site_profile_id"] == config["site_profile_id"]
    )
    trace = next(
        x for x in trace_registry["profiles"]
        if x["trace_profile_id"] == config["trace_profile_id"]
    )
    payload = next(
        x for x in payload_registry["profiles"]
        if x["payload_profile_id"] == config["payload_profile_id"]
    )
    service = next(
        x for x in service_registry["profiles"]
        if x["service_trace_profile_id"] == config["service_profile_id"]
    )

    if task["scope"]["jurisdiction"] not in trace["scope"]["task_jurisdiction_compatible"]:
        raise GeneratorError("task/trace jurisdiction mismatch")
    if trace["scope"]["site_profile_id"] != site["site_profile_id"]:
        raise GeneratorError("trace/site mismatch")
    if trace["scope"]["service_family"] != capability["scope"]["service_family"]:
        raise GeneratorError("trace/capability service-family mismatch")
    max_payload = capability["variables"]["max_payload_bytes"]["value"]
    if payload["encoded_bytes"] > max_payload:
        raise GeneratorError("payload does not fit selected satellite capability")
    if service["provenance_class"] != "CONTROLLED_STRESS":
        raise GeneratorError("v0.1 service model must be explicit CONTROLLED_STRESS")

    trace_payload = _load(ROOT / trace["trace_ref"])
    return {
        "task": task,
        "capability": capability,
        "site": site,
        "trace": trace,
        "payload": payload,
        "service": service,
        "trace_payload": trace_payload,
    }


def generate(config: Mapping[str, Any]) -> Iterable[dict[str, Any]]:
    ctx = _build_context(config)
    task = ctx["task"]
    trace_payload = ctx["trace_payload"]
    controlled = config["controlled_axes"]
    step_s = int(controlled["trace_step_s"])
    trace_horizon_s = int(trace_payload["hours"]) * 3600

    slot_cache = {
        int(mask): _trace_slots(trace_payload, int(mask))
        for mask in controlled["elevation_mask_deg"]
    }

    for grade in config["source_axes"]["monitoring_grades"]:
        for pre_state, post_state in config["source_axes"]["warning_transitions"]:
            pre_values = _cadence_values(task, grade=int(grade), warning_state=pre_state)
            post_values = _cadence_values(task, grade=int(grade), warning_state=post_state)
            for pre_s, post_s in product(pre_values, post_values):
                if post_s >= pre_s:
                    continue
                for frac, lag, budget, post_count, mask in product(
                    controlled["transition_fraction_of_pre_deadline"],
                    controlled["recovery_lag_post_intervals"],
                    controlled["satellite_tx_budget_count"],
                    controlled["post_obligation_count"],
                    controlled["elevation_mask_deg"],
                ):
                    transition_offset = int(round(float(frac) * pre_s / step_s)) * step_s
                    recovery_offset = (
                        transition_offset
                        + int(round(float(lag) * post_s / step_s)) * step_s
                    )
                    first_post_deadline = transition_offset + post_s
                    if not (first_post_deadline < recovery_offset < pre_s):
                        continue

                    span_s = max(
                        pre_s,
                        transition_offset + int(post_count) * post_s,
                        recovery_offset,
                    )
                    starts = _phase_bins(
                        trace_horizon_s - span_s,
                        bins=int(controlled["phase_bins"]),
                        step_s=step_s,
                    )
                    for phase_index, start_s in enumerate(starts):
                        transition_abs = start_s + transition_offset
                        recovery_abs = start_s + recovery_offset
                        obligations = _obligations(
                            scenario_start_s=start_s,
                            pre_interval_s=pre_s,
                            transition_offset_s=transition_offset,
                            post_interval_s=post_s,
                            post_count=int(post_count),
                        )
                        horizon_abs = max(o.deadline_s for o in obligations)
                        terr_slots = _terrestrial_slots(
                            recovery_s=recovery_abs,
                            horizon_s=horizon_abs,
                            step_s=step_s,
                            capacity_per_step=int(controlled["terrestrial_reports_per_step"]),
                        )
                        sat_slots = _satellite_slots(
                            slot_cache[int(mask)],
                            scenario_start_s=start_s,
                            horizon_s=horizon_abs,
                            capacity_per_step=int(
                                controlled["satellite_reports_per_visible_step"]
                            ),
                        )
                        oracle = _scenario_oracle(
                            obligations,
                            terrestrial_slots=terr_slots,
                            satellite_slots=sat_slots,
                            satellite_budget=int(budget),
                            transition_s=transition_abs,
                            scenario_start_s=start_s,
                        )
                        coords = {
                            "grade": int(grade),
                            "pre_warning_state": pre_state,
                            "post_warning_state": post_state,
                            "pre_interval_s": pre_s,
                            "post_interval_s": post_s,
                            "transition_fraction_of_pre_deadline": float(frac),
                            "recovery_lag_post_intervals": float(lag),
                            "satellite_tx_budget_count": int(budget),
                            "post_obligation_count": int(post_count),
                            "elevation_mask_deg": int(mask),
                            "phase_index": phase_index,
                            "scenario_start_s": start_s,
                        }
                        group_coords = {
                            k: v for k, v in coords.items()
                            if k not in {"phase_index", "scenario_start_s"}
                        }
                        disposition = _disposition(
                            oracle,
                            hard_filter=config["hard_case_filter"],
                        )
                        yield {
                            "generator_id": config["generator_id"],
                            "candidate_id": "genv01-" + _canonical_hash(coords),
                            "structural_group_id": "grp-" + _canonical_hash(group_coords),
                            "coordinates": coords,
                            "provenance": {
                                "monitoring_grade": "SOURCE_RANGE",
                                "pre_warning_state": "SOURCE_RANGE",
                                "post_warning_state": "SOURCE_RANGE",
                                "pre_interval_s": "SOURCE_RANGE",
                                "post_interval_s": "SOURCE_RANGE",
                                "site_geometry": "MODEL_DERIVED_TRACE",
                                "transition_fraction_of_pre_deadline": "CONTROLLED_STRESS",
                                "recovery_lag_post_intervals": "CONTROLLED_STRESS",
                                "satellite_tx_budget_count": "CONTROLLED_STRESS",
                                "post_obligation_count": "CONTROLLED_STRESS",
                                "elevation_mask_deg": "CONTROLLED_STRESS",
                                "scenario_start_s": "CONTROLLED_STRESS",
                                "service_success_semantics": "CONTROLLED_STRESS",
                            },
                            "task_profile_id": config["task_profile_id"],
                            "site_profile_id": config["site_profile_id"],
                            "capability_profile_id": config["capability_profile_id"],
                            "trace_profile_id": config["trace_profile_id"],
                            "payload_profile_id": config["payload_profile_id"],
                            "service_profile_id": config["service_profile_id"],
                            "obligations": [
                                {
                                    "obligation_id": o.obligation_id,
                                    "release_s": o.release_s,
                                    "deadline_s": o.deadline_s,
                                }
                                for o in obligations
                            ],
                            "terrestrial_recovery_s": recovery_abs,
                            "oracle": oracle,
                            "disposition": disposition,
                        }


def materialize(
    *,
    config_path: Path,
    out_dir: Path,
) -> dict[str, Any]:
    config_path = config_path.resolve()
    out_dir = out_dir.resolve()
    config = _load(config_path)
    bundle_manifest_path = BENCH / "PROFILE-BUNDLE-MANIFEST.v0.1.json"
    config_hash = _sha256_file(config_path)
    bundle_hash = _sha256_file(bundle_manifest_path)

    out_dir.mkdir(parents=True, exist_ok=True)
    candidates_path = out_dir / "candidates.jsonl.gz"
    hard_path = out_dir / "hard-candidates.jsonl"

    counts: Counter[str] = Counter()
    total = 0
    hard = 0
    groups: set[str] = set()

    # mtime=0 makes the gzip byte-for-byte reproducible.
    with candidates_path.open("wb") as raw, gzip.GzipFile(
        filename="", mode="wb", fileobj=raw, mtime=0
    ) as gz, hard_path.open("w", encoding="utf-8") as hard_f:
        for row in generate(config):
            line = json.dumps(
                row, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ) + "\n"
            gz.write(line.encode("utf-8"))
            total += 1
            counts[row["disposition"]] += 1
            groups.add(row["structural_group_id"])
            if row["disposition"] == "HARD_CANDIDATE":
                hard += 1
                hard_f.write(line)

    manifest = {
        "schema_version": "0.1",
        "generator_id": config["generator_id"],
        "generator_code": "code/evaluation/benchmark/scenario_generator_v0_1.py",
        "generator_config": str(config_path.relative_to(ROOT)),
        "generator_config_sha256": config_hash,
        "profile_bundle_manifest": str(bundle_manifest_path.relative_to(ROOT)),
        "profile_bundle_manifest_sha256": bundle_hash,
        "candidate_count": total,
        "hard_candidate_count": hard,
        "structural_group_count": len(groups),
        "disposition_counts": dict(sorted(counts.items())),
        "artifacts": {
            "candidates_jsonl_gz": {
                "path": str(candidates_path.relative_to(ROOT)),
                "sha256": _sha256_file(candidates_path),
                "bytes": candidates_path.stat().st_size,
            },
            "hard_candidates_jsonl": {
                "path": str(hard_path.relative_to(ROOT)),
                "sha256": _sha256_file(hard_path),
                "bytes": hard_path.stat().st_size,
            },
        },
        "claim_boundary": [
            "Hard-case mining uses exact oracle/validity properties only; no model score is read.",
            "Controlled axes are preregistered in GENERATOR-CONFIG.v0.1.json.",
            "Satellite budget and outage timing are stress variables, not field distributions.",
            "Model-derived geometry is not measured service reliability.",
            "HARD_CANDIDATE is not BENCHMARK_ADMIT.",
        ],
    }
    manifest_path = out_dir / "MANIFEST.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--config",
        type=Path,
        default=BENCH / "GENERATOR-CONFIG.v0.1.json",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT / "local_research/current/benchmark/generated/scenario-generator-v0.1",
    )
    args = ap.parse_args()
    manifest = materialize(config_path=args.config, out_dir=args.out)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
