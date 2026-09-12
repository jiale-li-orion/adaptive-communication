"""Seven diagnostic trajectories against every business-layer arm.

This is the experiment the P1 round should have run and did not: the arms it compared were three
baselines and a policy upper bound, and the runtime the paper is about was not among them. The
fix is not a bigger table, it is putting the arm that exists into the table.

One row per (trajectory, arm). Every arm sees the same deployment, the same exogenous demand, the
same injected faults, the same gateway and backhaul, and the same opportunity budget; only the
policy and the contract fields it chooses to put on the wire differ.

Run:  python3 code/experiments/monitoring_trajectories.py --days 3 --seeds 1
"""

from __future__ import annotations

import os as _os, sys as _sys

_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, *(_os.path.join(_CODE, d) for d in ("physics", "runtime", "experiments",
                                                      "analysis", "monitoring"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)
# -----------------------------------------------------------------------------

import argparse
import json
import os
import sys

import numpy as np

from faults import KIND_DEFAULTS, FaultInjector, FaultSpec, KINDS
from policies import BUSINESS_ARMS, build_arm
from runner import build_deployment, run_episode
from scorer import score
from supply import SupplyFleet

OUT = os.path.join(_CODE, "..", "results", "monitoring_trajectories.json")

# The no-fault trajectory plus one per fault kind, in the order the contract lists them. Reporting
# them together is the point: a fault that moves no arm is a fault that reached nothing, and the
# table is what makes that visible instead of arguable.
TRAJECTORIES = ("none",) + tuple(KINDS)

# The columns that answer a question rather than restating a count. `observation_gap` is the one
# the local-rules arm cannot answer at all, and `false_success` is the one the oracle cannot.
COLUMNS = (
    ("coverage", lambda r, a, p: 100.0 * r.coverage),
    ("observation_gap", lambda r, a, p: 100.0 * a["observation_gap_ratio"]),
    ("false_success", lambda r, a, p: float(a["false_successes"])),
    ("time_to_know_s", lambda r, a, p: float(a["knowledge_latency_s"])),
    ("downlink_attempts", lambda r, a, p: float(p.downlink_attempts)),
    ("airtime_h", lambda r, a, p: a["airtime_ms"] / 3.6e6),
    ("stale_overwrites", lambda r, a, p: float(a["stale_overwrites"])),
    ("fenced", lambda r, a, p: float(a["fenced"])),
    ("deduplicated", lambda r, a, p: float(a["reaccepted"])),
)


def one_run(arm: str, trajectory: str, days: float, seed: int, use_energy: bool) -> dict:
    hours = int(round(days * 24))
    fault = None if trajectory == "none" else FaultInjector(
        FaultSpec(kind=trajectory, seed=seed, hours=hours))
    deployment = build_deployment(seed)
    # One supply fleet per run, seeded from the same seed as the deployment, so the energy arm of
    # an arm comparison is not a second source of variation between arms.
    supply = SupplyFleet(deployment.nodes, seed) if use_energy else None
    policy = build_arm(arm)
    record, _state, plane = run_episode(policy, hours=hours, seed=seed, fault=fault,
                                        supply=supply)
    plane.check_opportunity_bound()
    result = score(record)
    row = {"arm": arm, "trajectory": trajectory, "seed": seed, "hours": hours}
    for name, read in COLUMNS:
        row[name] = read(result, result.aux, plane)
    row["demands"] = result.demands
    row["covered"] = result.covered
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=float, default=3.0)
    ap.add_argument("--seeds", type=int, default=1,
                    help="seeds are drawn from the development split, 0..999")
    ap.add_argument("--arms", default=",".join(BUSINESS_ARMS))
    ap.add_argument("--trajectories", default=",".join(TRAJECTORIES))
    ap.add_argument("--no-energy", dest="energy", action="store_false")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    arms = [a for a in args.arms.split(",") if a]
    trajectories = [t for t in args.trajectories.split(",") if t]
    unknown = [a for a in arms if a not in BUSINESS_ARMS]
    if unknown:
        raise SystemExit(f"unknown arms {unknown}; have {sorted(BUSINESS_ARMS)}")

    print(f"业务层七条诊断轨迹：{args.days:g} 天 × {args.seeds} 个种子，"
          f"能量模型 {'开' if args.energy else '关'}")
    rows = []
    for trajectory in trajectories:
        # Per-trajectory means over seeds, plus the per-seed values the paired comparison needs.
        # Averaging first and printing once is what keeps the table readable at seven trajectories.
        per_arm: dict[str, list[dict]] = {}
        for arm in arms:
            for seed in range(args.seeds):
                per_arm.setdefault(arm, []).append(
                    one_run(arm, trajectory, args.days, seed, args.energy))
        print(f"\n===== {trajectory} =====")
        hdr = (f"{'arm':18s}" + "".join(f"{n:>16s}" for n, _ in COLUMNS))
        print(hdr)
        print("-" * len(hdr))
        for arm in arms:
            runs = per_arm[arm]
            mean = {n: float(np.mean([r[n] for r in runs])) for n, _ in COLUMNS}
            row = {"arm": arm, "trajectory": trajectory,
                   "per_seed": {n: [r[n] for r in runs] for n, _ in COLUMNS}, **mean}
            rows.append(row)
            print(f"{arm:18s}" + "".join(f"{mean[n]:16.1f}" for n, _ in COLUMNS))

    tag = f"_{args.tag}" if args.tag else ""
    path = OUT.replace(".json", f"{tag}.json")
    with open(path, "w") as f:
        json.dump({"config": vars(args), "columns": [n for n, _ in COLUMNS], "results": rows},
                  f, indent=2, ensure_ascii=False)
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
