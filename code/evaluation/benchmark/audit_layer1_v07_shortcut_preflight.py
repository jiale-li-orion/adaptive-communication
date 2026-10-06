#!/usr/bin/env python3
"""Cheap construction-validity attack for frozen Layer-1 v0.7.

This audit deliberately runs *before* exact policy search.  It checks whether
the process-support correction actually removes the v0.6 construction-level
blind-satellite shortcut without changing any other axis.

It never edits generation axes and never reads Layer-2/Layer-3 results.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import argparse
import json
from typing import Any

import generate_layer1_v07_cases as gen


ROOT = Path(__file__).resolve().parents[3]


def _satellite_only_feasible(obligations: list[gen.Obligation], sat: list[dict[str, Any]]) -> bool:
    return gen._edf_feasible(
        obligations,
        tuple(range(len(obligations))),
        sat,
    )


def audit() -> dict[str, Any]:
    axes = gen._read_json(gen.AXES_PATH)
    trace_path = ROOT / axes["model_derived"]["satellite_geometry"]["trace_path"]
    trace = gen._read_json(trace_path)
    cs = axes["controlled_stress"]

    candidate_families = {
        row["id"] for row in cs["terrestrial_service_process"]["support_families"]
        if row["role"] == "CANDIDATE"
    }
    control_families = {
        row["id"] for row in cs["terrestrial_service_process"]["support_families"]
        if row["role"] != "CANDIDATE"
    }
    min_stages = int(cs["obligation_composition"]["minimum_dynamic_release_stages"])

    counts = Counter()
    by_family: dict[str, Counter[str]] = defaultdict(Counter)
    saturation_examples: list[dict[str, Any]] = []
    satellite_only_examples: list[dict[str, Any]] = []
    geometry_cache: dict[int, list[dict[str, Any]]] = {}

    for cell in gen._task_cells():
        interval = int(cell["report_interval_s"])
        for per_stream in cs["obligation_composition"]["obligations_per_stream"]:
            for phase_mode in cs["obligation_composition"]["stream_phase_modes"]:
                obs = gen._obligations(interval, int(per_stream), str(phase_mode))
                stages = gen._release_stages(obs)
                if len(stages) < min_stages:
                    counts["EXCLUDED_LT_MIN_STAGES"] += 1
                    continue
                horizon = max(o.deadline_s for o in obs)
                if horizon > int(trace["hours"]) * 3600:
                    counts["EXCLUDED_GEOMETRY_HORIZON"] += 1
                    continue
                if horizon not in geometry_cache:
                    geometry_cache[horizon] = gen._geometry_catalog(trace, axes, horizon)[0]

                for geo in geometry_cache[horizon]:
                    sat = [
                        {
                            "opportunity_id": f"sat@{int(start)}",
                            "time_s": int(start),
                            "window_end_s": int(end),
                            "capacity_units": int(cs["satellite_window_capacity_units"]),
                        }
                        for start, end in geo["relative_windows_s"]
                    ]
                    sat_only = _satellite_only_feasible(obs, sat)

                    for family in cs["terrestrial_service_process"]["support_families"]:
                        family_id = str(family["id"])
                        support = gen._service_support(len(stages), family_id)
                        all_down = tuple(False for _ in stages)
                        all_up = tuple(True for _ in stages)
                        role = str(family["role"])

                        counts[f"ROLE::{role}::SUPPORT_CHECKS"] += 1
                        if all_down in support:
                            counts[f"ROLE::{role}::CONTAINS_ALL_DOWN"] += 1
                        if all_up in support:
                            counts[f"ROLE::{role}::CONTAINS_ALL_UP"] += 1

                        for terr_capacity in cs["terrestrial_opportunities"]["capacity_units"]:
                            terr = gen._terr_opportunities(
                                obs,
                                interval,
                                cs["terrestrial_opportunities"]["phase_ratios"],
                                int(terr_capacity),
                            )
                            worlds, physical_status, tight = gen._world_rows(obs, terr, sat, support)
                            key_prefix = f"ROLE::{role}"
                            counts[f"{key_prefix}::BASES"] += 1
                            counts[f"{key_prefix}::{physical_status}"] += 1
                            by_family[family_id][physical_status] += 1

                            if physical_status != "ALL_WORLD_PHYSICAL":
                                continue

                            n = len(obs)
                            assert tight is not None
                            balanced = min(int(tight) + 1, n)
                            slack = n
                            for mode, budget in (
                                ("TIGHT", int(tight)),
                                ("BALANCED", balanced),
                                ("SLACK_CONTROL", slack),
                            ):
                                counts[f"{key_prefix}::{mode}::CASES"] += 1
                                if budget == n:
                                    counts[f"{key_prefix}::{mode}::BUDGET_EQ_N"] += 1
                                if sat_only and budget >= n:
                                    counts[f"{key_prefix}::{mode}::PUBLIC_SAT_ONLY_COMMON_SAFE"] += 1
                                    if len(satellite_only_examples) < 24:
                                        satellite_only_examples.append(
                                            {
                                                "role": role,
                                                "family": family_id,
                                                "task_case_id": cell["task_case_id"],
                                                "per_stream": int(per_stream),
                                                "phase_mode": str(phase_mode),
                                                "geometry_signature_id": geo["geometry_signature_id"],
                                                "terr_capacity": int(terr_capacity),
                                                "fallback_mode": mode,
                                                "fallback_budget": budget,
                                                "obligation_count": n,
                                            }
                                        )

                            if int(tight) == n and len(saturation_examples) < 24:
                                saturation_examples.append(
                                    {
                                        "role": role,
                                        "family": family_id,
                                        "task_case_id": cell["task_case_id"],
                                        "per_stream": int(per_stream),
                                        "phase_mode": str(phase_mode),
                                        "geometry_signature_id": geo["geometry_signature_id"],
                                        "terr_capacity": int(terr_capacity),
                                        "tight_budget": int(tight),
                                        "obligation_count": n,
                                        "world_count": len(worlds),
                                    }
                                )

    candidate_all_down = counts["ROLE::CANDIDATE::CONTAINS_ALL_DOWN"]
    candidate_tight_sat_shortcut = counts[
        "ROLE::CANDIDATE::TIGHT::PUBLIC_SAT_ONLY_COMMON_SAFE"
    ]
    candidate_balanced_sat_shortcut = counts[
        "ROLE::CANDIDATE::BALANCED::PUBLIC_SAT_ONLY_COMMON_SAFE"
    ]

    if candidate_all_down:
        disposition = "FAIL_CANDIDATE_SUPPORT_STILL_CONTAINS_ALL_DOWN"
    elif candidate_tight_sat_shortcut:
        disposition = "FAIL_CANDIDATE_TIGHT_GLOBAL_OR_PARTIAL_SATELLITE_SHORTCUT"
    else:
        disposition = "PASS_NO_V06_STYLE_TIGHT_SATELLITE_SHORTCUT"

    return {
        "schema_version": "0.1",
        "stage": "V07_PREORACLE_SHORTCUT_PREFLIGHT",
        "disposition": disposition,
        "candidate_families": sorted(candidate_families),
        "control_families": sorted(control_families),
        "counts": dict(sorted(counts.items())),
        "by_family": {k: dict(sorted(v.items())) for k, v in sorted(by_family.items())},
        "saturation_examples": saturation_examples,
        "satellite_only_examples": satellite_only_examples,
        "interpretation": {
            "pass_condition": "candidate supports exclude ALL_DOWN and no ALL_WORLD_PHYSICAL candidate TIGHT case is guaranteed blind-satellite-only by public geometry + full backup budget",
            "balanced_note": "BALANCED may intentionally collapse to n when tight=n-1; those cells are shortcut controls/candidates for downstream filtering, not a generator failure unless the collapse is global",
            "slack_note": "SLACK_CONTROL intentionally permits n backup units and is expected to contain satellite-only controls where geometry allows",
            "next_gate": "exact blind-open-loop pilot on frozen generated cases; this preflight does not prove absence of mixed-path open-loop shortcuts",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    payload = audit()
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
