#!/usr/bin/env python3
"""Cross-year full-sim smoke for source-period-separated benchmark coordinates."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
ROOT = CODE.parent
for p in (
    CODE,
    CODE / "substrate" / "joint",
    CODE / "substrate" / "instance",
    CODE / "substrate" / "monitoring",
    CODE / "substrate" / "physics",
    CODE / "substrate" / "runtime",
    CODE / "evaluation" / "agentic",
    CODE / "legacy-communication" / "analysis",
):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from agentic_communication.benchmark_split import YEAR_SPLIT, nasa_power_path  # noqa: E402
from agentic_communication.episodes import o4_energy_constrained_monitoring_task  # noqa: E402
from agentic_communication.metrics import physical_signature  # noqa: E402
from agentic_communication.planner import DeterministicComplyPlannerConsumer  # noqa: E402
from agentic_communication.run import run_agentic_episode, run_reference_comply  # noqa: E402


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    # A-layer smoke coordinate: use the same seasonal day across years but start
    # in a daylight interval so irradiance differences reach the battery model.
    ap.add_argument("--window", type=int, default=151 * 24 + 8)
    ap.add_argument(
        "--out",
        default=str(ROOT / "results" / "agentic" / "source-period-smoke-v1.json"),
    )
    args = ap.parse_args()

    task = o4_energy_constrained_monitoring_task(task_hours=4)
    rows = []
    all_equal = True
    for year in sorted(YEAR_SPLIT):
        sim = {
            "task_hours": 4,
            "tail_hours": 1,
            "harvest_mode": "irradiance",
            "irradiance_year": year,
            "irradiance_start_hour": args.window,
            "harvest_peak_wh_per_hour": 0.003,
            "capacity_wh": 0.03,
            "initial_soc": 0.1,
            "outage_hours": 0.0,
            "backhaul_p_good": 1.0,
            "execution_feedback": True,
        }
        reference, _, _ = run_reference_comply(
            seed=args.seed,
            operational_task=task,
            simulator_kwargs=sim,
        )
        current, policy, _, _ = run_agentic_episode(
            seed=args.seed,
            operational_task=task,
            planner_consumer=DeterministicComplyPlannerConsumer(),
            simulator_kwargs=sim,
        )
        equal = physical_signature(reference) == physical_signature(current)
        all_equal = all_equal and equal
        source = nasa_power_path(ROOT, year)
        cm = current["agentic"]["communication_metrics"]
        rows.append(
            {
                "split": YEAR_SPLIT[year].value,
                "year": year,
                "source_path": str(source.relative_to(ROOT)),
                "source_sha256": sha256(source),
                "irradiance_start_hour": args.window,
                "seed": args.seed,
                "physical_equal_legacy_comply": equal,
                "total_harvested_wh": cm["total_harvested_wh"],
                "total_consumed_wh": cm["total_consumed_wh"],
                "timely_delivery_rate": cm["timely_delivery_rate"],
                "collection_rate": cm["collection_rate"],
                "model_requests": current["agentic"]["agent_metrics"]["model_requests"],
                "runtime_events": current["agentic"]["agent_metrics"]["events"],
            }
        )

    distinct_hashes = len({row["source_sha256"] for row in rows}) == len(rows)
    distinct_harvest = len({round(float(row["total_harvested_wh"]), 12) for row in rows}) == len(rows)
    passed = all_equal and distinct_hashes and distinct_harvest
    payload = {
        "experiment_id": "source-period-smoke-v1",
        "status": "PASS" if passed else "FAIL",
        "claim_ceiling": (
            "Infrastructure/robustness-coordinate validation only: source-year split reaches the "
            "full simulator and produces distinct source-driven harvest traces while the typed "
            "runtime remains physically equivalent to its paired deterministic reference."
        ),
        "task": task.model_dump(mode="json"),
        "source_year_precedes_seed": True,
        "distinct_source_hashes": distinct_hashes,
        "distinct_harvest_outcomes": distinct_harvest,
        "all_physical_equivalent": all_equal,
        "rows": rows,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
