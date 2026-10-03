"""契约 §9 第②项：通信机会与断连的敏感性。

这一项问的是"收益在哪条轴上出现、哪条轴上消失"。两条轴，都直接来自契约而不是自选的扫描
范围：

- **每次上行给几个下行机会**（契约 §7 的待定参数，D6 定为场景参数，Class A 默认 1）。
  这是纯机会供给，把下行窗口从"一次上行换一次"放宽到"一次上行换 N 次"。
- **回传中断时长**。断连是这套部署的常态而不是异常，中断越长，积压越多，恢复期越挤。

两条轴上的读数必须分开看：机会供给增加帮助的是"命令能不能送到"，中断时长考验的是"送不到
之后怎么收场"。把它们合成一个"鲁棒性"分数会把这两件事混掉。

Run:  python3 code/experiments/sensitivity.py --days 3 --seeds 3
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

import numpy as np

from faults import FaultInjector, FaultSpec
from policies import BUSINESS_ARMS, COMPOSED_ARMS, build_arm
from runner import run_episode
from scorer import score

OUT = os.path.join(_CODE, "..", "results", "sensitivity.json")

# The columns that move on these axes. Coverage answers "did the demand get served"; the
# observation gap and the unknown interval answer "was the center's picture right"; the downlink
# count is what the opportunity axis is spent on; the late-delivery count says whether the residual
# failure is delivery or sampling.
# `downlink_attempts` is read from the channel rather than from the score, because how many
# opportunities an arm spent is a property of the run and not of the demands it served.
COLUMNS = (
    ("coverage", lambda r, a: 100.0 * r.coverage),
    ("observation_gap", lambda r, a: 100.0 * a["observation_gap_ratio"]),
    ("unknown_h", lambda r, a: a["unknown_s"] / 3600.0),
    ("aoi_mean_s", lambda r, a: a["aoi_mean_s"]),
    ("late_delivery", lambda r, a: a["residual_late_delivery"]),
    ("no_sample_in_window", lambda r, a: a["residual_no_sample_in_window"]),
)


def one_run(arm, hours, seed, opportunities, outage_h, use_energy=True):
    """One episode on one point of the grid.

    `opportunities` is downlinks per uplink, `outage_h` the length of a single backhaul outage
    placed in the second quarter of the run. Both are scenario parameters shared by every arm, so a
    difference between arms at a grid point is not a difference in the conditions.
    """
    fault = None
    if outage_h > 0:
        start = int(hours * 3600 * 0.25)
        fault = FaultInjector(FaultSpec(kind="backhaul_only", seed=seed, hours=hours,
                                        first_at_s=start, duration_s=int(outage_h * 3600),
                                        count=1))
    policy = build_arm(arm)
    record, _state, plane = run_episode(policy, hours=hours, seed=seed,
                                        downlink_per_uplink=opportunities, fault=fault,
                                        supply=_supply(seed) if use_energy else None)
    result = score(record)
    row = {"arm": arm, "opportunities": opportunities, "outage_h": outage_h, "seed": seed}
    for name, read in COLUMNS:
        row[name] = (float(plane.downlink_attempts) if name == "downlink_attempts"
                     else read(result, result.aux))
    row["demands"] = result.demands
    row["covered"] = result.covered
    return row


def _supply(seed):
    from supply import SupplyFleet
    from task_generator import build_deployment
    return SupplyFleet(build_deployment(seed).nodes, seed)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=float, default=3.0)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--arms", default="versioned_config,ours")
    ap.add_argument("--opportunities", default="1,2,4")
    ap.add_argument("--outages", default="0,2,6,12")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    hours = int(round(args.days * 24))
    arms = [a for a in args.arms.split(",") if a]
    unknown = [a for a in arms if a not in set(BUSINESS_ARMS) | set(COMPOSED_ARMS)]
    if unknown:
        raise SystemExit(f"unknown arms {unknown}")
    ops = [int(x) for x in args.opportunities.split(",")]
    outages = [float(x) for x in args.outages.split(",")]

    print(f"通信机会与断连敏感性：{args.days:g} 天 × {args.seeds} 种子，"
          f"机会额度 {ops}，回传中断 {outages} 小时")
    rows = []
    for axis, values in (("opportunities", ops), ("outage_h", outages)):
        other = outages if axis == "opportunities" else ops
        print(f"\n===== 轴: {axis} =====")
        hdr = f"{'臂':20s}{axis:>16s}" + "".join(f"{n:>14s}" for n, _ in COLUMNS)
        print(hdr, flush=True)
        print("-" * len(hdr), flush=True)
        for value in values:
            for arm in arms:
                runs = [one_run(arm, hours, seed,
                                value if axis == "opportunities" else other[0],
                                other[0] if axis == "opportunities" else value)
                        for seed in range(args.seeds)]
                mean = {n: float(np.mean([r[n] for r in runs])) for n, _ in COLUMNS}
                row = {"arm": arm, "axis": axis, "value": value,
                       "per_seed": {n: [r[n] for r in runs] for n, _ in COLUMNS}, **mean}
                rows.append(row)
                print(f"{arm:20s}{value:>16g}"
                      + "".join(f"{mean[n]:>14.1f}" for n, _ in COLUMNS), flush=True)
        print(flush=True)

    tag = f"_{args.tag}" if args.tag else ""
    path = OUT.replace(".json", f"{tag}.json")
    with open(path, "w") as f:
        json.dump({"config": vars(args), "results": rows}, f, indent=2, ensure_ascii=False)
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
