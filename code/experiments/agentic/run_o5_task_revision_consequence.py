#!/usr/bin/env python3
"""O5 deterministic consequence probe for Task-revision timing errors.

The benchmark Task/scorer remains O5.  Only the controller's Task schedule is
perturbed.  All arms run at gateway placement so the probe isolates Task/context
revision semantics from center-backhaul command reachability.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import sys


HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
ROOT = CODE.parent
for p in (
    CODE,
    CODE / "v3joint",
    CODE / "instance",
    CODE / "monitoring",
    CODE / "physics",
    CODE / "runtime",
    CODE / "experiments",
    CODE / "analysis",
):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from agentic_communication.episodes import benchmark_episode_catalog  # noqa: E402
from agentic_communication.metrics import communication_metrics  # noqa: E402
from agentic_communication.run import DEFAULT_FULLSIM  # noqa: E402
from joint_run import run_joint  # noqa: E402
from mission_policy import MissionChangePolicy  # noqa: E402


DEFAULT_OUT = ROOT / "results" / "agentic" / "o5-task-revision-consequence-v1"


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def mean(rows: list[dict], key: str) -> float:
    return statistics.fmean(float(row[key]) for row in rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default=",".join(str(i) for i in range(20)))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    seeds = [int(x) for x in args.seeds.split(",") if x.strip()]
    out = Path(args.out)

    ep = benchmark_episode_catalog()["O5"]
    original = ep.task.mission_schedule()
    arms = {
        "correct": list(original),
        "stale_yellow_after_recovery": [original[0], original[1]],
        "premature_blue_at_h8": [original[0], original[1], (8 * 3600, 3600, "blue")],
        "late_blue_at_h10": [original[0], original[1], (10 * 3600, 3600, "blue")],
    }
    result = {
        "experiment": "o5-task-revision-consequence-v1",
        "seeds": seeds,
        "task": ep.task.model_dump(mode="json"),
        "simulator_overrides": ep.simulator_overrides,
        "placement": "gateway",
        "arms": {},
        "claim_ceiling": (
            "Deterministic consequence of stale/premature Task revision under fixed gateway placement. "
            "This quantifies physical stakes for Context-transition evaluation; it is not a model result."
        ),
    }

    for name, policy_schedule in arms.items():
        rows = []
        for seed in seeds:
            sim = dict(DEFAULT_FULLSIM)
            sim.update(ep.simulator_overrides)
            raw, _, _ = run_joint(
                seed=seed,
                arm="local",
                mission_schedule=original,
                mission_scope=(ep.task.target_node_ids or None),
                mission_policy_obj=MissionChangePolicy(policy_schedule, mode="comply"),
                mission_policy_placement="gateway",
                backup_chooser="edf",
                **sim,
            )
            m = communication_metrics(raw)
            rows.append(
                {
                    "seed": seed,
                    "tdr": m["timely_delivery_rate"],
                    "collection": m["collection_rate"],
                    "energy_wh": m["total_consumed_wh"],
                    "backup_bytes": m["backup_bytes"],
                    "commands_sent": m["commands_sent"],
                    "mean_final_soc": m["mean_final_soc"],
                }
            )
        result["arms"][name] = {
            "policy_schedule": policy_schedule,
            "aggregate": {
                key: mean(rows, key)
                for key in (
                    "tdr",
                    "collection",
                    "energy_wh",
                    "backup_bytes",
                    "commands_sent",
                    "mean_final_soc",
                )
            },
            "per_seed": rows,
        }

    base = result["arms"]["correct"]["aggregate"]
    result["deltas_vs_correct"] = {}
    for name, arm in result["arms"].items():
        if name == "correct":
            continue
        agg = arm["aggregate"]
        result["deltas_vs_correct"][name] = {
            "tdr": agg["tdr"] - base["tdr"],
            "collection": agg["collection"] - base["collection"],
            "energy_wh": agg["energy_wh"] - base["energy_wh"],
            "backup_bytes": agg["backup_bytes"] - base["backup_bytes"],
            "commands_sent": agg["commands_sent"] - base["commands_sent"],
        }

    dump(out / "aggregate.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
