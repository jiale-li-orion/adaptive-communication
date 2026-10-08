#!/usr/bin/env python3
"""Bounded S7 future-choice smoke over predeclared NASA POWER dev windows.

This is a task-discovery audit, not benchmark admission.  It compares three
existing execution choices on the existing O6/S7 compound task:

* no early preparation;
* one-hour early densification preparation;
* the same preparation guarded by the existing persistent-energy ResourceGate.

The environment coordinates come from the already-declared benchmark split.
No generator, capability or task surface is added here.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
CODE = ROOT / "code"
for _p in (
    CODE,
    CODE / "substrate" / "joint",
    CODE / "substrate" / "instance",
    CODE / "substrate" / "monitoring",
    CODE / "substrate" / "physics",
    CODE / "substrate" / "runtime",
):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from agentic_communication.benchmark_split import WINDOW_START_HOURS  # noqa: E402
from agentic_communication.episodes import (  # noqa: E402
    benchmark_episode_catalog,
    o6_compound_long_horizon_task,
)
from joint_run import run_joint  # noqa: E402


def run(seed: int = 0, year: int = 2023, capacity_wh: float = 0.05) -> dict:
    task = o6_compound_long_horizon_task(task_hours=12)
    template = benchmark_episode_catalog()["O6"]
    base = dict(template.simulator_overrides)
    base.update(
        {
            "seed": seed,
            "task_hours": 12,
            "tail_hours": 1,
            "arm": "local",
            "groups": 2,
            "sample_interval_s": 3600,
            "report_period_s": 3600,
            "routine_period_s": 3600,
            "harvest_mode": "irradiance",
            "irradiance_year": year,
            "capacity_wh": float(capacity_wh),
            "initial_soc": 1.0,
            "backup_rate_s": 120,
            "backup_bytes": 200,
            "execution_feedback": True,
            "mission_schedule": task.mission_schedule(),
            "mission_mode": "comply",
            "mission_gateway_delegate": True,
            # Controlled task-revision timing coordinate: the yellow revision
            # becomes visible two hours before its effective time, before the
            # frozen O6 backhaul outage begins.  This is not a field-frequency
            # claim and is held fixed across all three arms/windows.
            "mission_notice_lead_s": 7200,
            "mission_record_trace": True,
        }
    )
    arms = {
        "no_prepare": {
            "mission_preparation_lead_s": 0,
            "mission_preparation_resource_guard": False,
        },
        "prepare": {
            "mission_preparation_lead_s": 3600,
            "mission_preparation_resource_guard": False,
        },
        "prepare_guard": {
            "mission_preparation_lead_s": 3600,
            "mission_preparation_resource_guard": True,
        },
    }

    rows = []
    for window_id, start_hour in WINDOW_START_HOURS.items():
        for arm, extra in arms.items():
            kwargs = dict(base)
            kwargs.update(extra)
            kwargs["irradiance_start_hour"] = start_hour
            result, _instance, _obligations = run_joint(**kwargs, collect_rows=True)
            gate = result.get("preparation_gate") or {}
            phase_bounds = (
                ("pre_warning", 0, 5 * 3600),
                ("warning", 5 * 3600, 10 * 3600),
                ("post_warning", 10 * 3600, 12 * 3600),
            )
            phase_metrics = {}
            routine_rows = [row for row in result.get("rows", []) if row.get("kind") == "routine"]
            for phase, lo, hi in phase_bounds:
                subset = [row for row in routine_rows if lo <= int(row["release_at"]) < hi]
                phase_metrics[phase] = {
                    "n": len(subset),
                    "delivered": sum(bool(row["delivered"]) for row in subset),
                    "collected": sum(bool(row["collected"]) for row in subset),
                    "missing_collection": sum(not bool(row["collected"]) for row in subset),
                    "missing_delivery": sum(
                        bool(row["collected"]) and not bool(row["delivered"]) for row in subset
                    ),
                }
            rows.append(
                {
                    "window_id": window_id,
                    "irradiance_start_hour": start_hour,
                    "arm": arm,
                    "routine_obligations": result["routine"]["n"],
                    "routine_delivered": result["routine"]["delivered"],
                    "missing_collection": result["routine"]["missing_collection"],
                    "missing_delivery": result["routine"]["missing_delivery"],
                    "recovery_delivered": result["recovery"]["delivered"],
                    "mean_final_soc": result["survival"]["mean_final_soc"],
                    "dead_nodes": list(result["survival"]["dead"]),
                    "backup_packets": result["backup"]["backup_packets"],
                    "backup_records": result["backup"]["backup_records"],
                    "preparation_gate_denied": gate.get("denied_total"),
                    "preparation_gate": gate or None,
                    "phase_metrics": phase_metrics,
                }
            )

    by_window = {}
    for window_id in WINDOW_START_HOURS:
        subset = {row["arm"]: row for row in rows if row["window_id"] == window_id}
        no_prepare = subset["no_prepare"]
        prepare = subset["prepare"]
        guard = subset["prepare_guard"]
        by_window[window_id] = {
            "prepare_minus_no_prepare_delivered": (
                prepare["routine_delivered"] - no_prepare["routine_delivered"]
            ),
            "guard_minus_prepare_delivered": (
                guard["routine_delivered"] - prepare["routine_delivered"]
            ),
            "prepare_minus_no_prepare_soc": round(
                prepare["mean_final_soc"] - no_prepare["mean_final_soc"], 6
            ),
            "prepare_dead_nodes": prepare["dead_nodes"],
            "guard_dead_nodes": guard["dead_nodes"],
            "guard_denied": guard["preparation_gate_denied"],
            "phase_delivery_delta_prepare_minus_no_prepare": {
                phase: (
                    prepare["phase_metrics"][phase]["delivered"]
                    - no_prepare["phase_metrics"][phase]["delivered"]
                )
                for phase in ("pre_warning", "warning", "post_warning")
            },
            "phase_missing_collection_delta_prepare_minus_no_prepare": {
                phase: (
                    prepare["phase_metrics"][phase]["missing_collection"]
                    - no_prepare["phase_metrics"][phase]["missing_collection"]
                )
                for phase in ("pre_warning", "warning", "post_warning")
            },
        }

    return {
        "stage": "T1_S7_FUTURE_CHOICE_WEATHER_SMOKE",
        "task_surface": "T1.S7_COMPOUND_CONTINUITY",
        "task_template": "O6",
        "year": year,
        "seed": seed,
        "capacity_wh": capacity_wh,
        "windows": list(WINDOW_START_HOURS),
        "rows": rows,
        "by_window": by_window,
        "claim_boundary": [
            "Task discovery only; this is not benchmark admission or a method result.",
            "NASA POWER year/window coordinates are inherited from the existing benchmark split.",
            "The two-hour notice lead and one-hour preparation lead are fixed controlled coordinates shared by all arms.",
            "A useful future-choice witness requires early preparation to be beneficial in some lawful states and harmful in others because of persistent resource consequences; otherwise this task is rejected for the method claim.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--year", type=int, default=2023)
    parser.add_argument("--capacity-wh", type=float, default=0.05)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    payload = run(seed=args.seed, year=args.year, capacity_wh=args.capacity_wh)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
