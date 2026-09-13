#!/usr/bin/env python3
"""从结果文件里读出四目标的 Pareto 集。

四个目标（README §6.12）：**周期交付 ↑、上行 ↓、下行尝试 ↓、中心 AoI ↓**。
**不做加权**——加权会把"哪个目标更重要"这个研究选择偷偷塞进结论里，而支配关系不需要它。

判据（严格支配）：A 支配 B ⟺ A 在每个目标上都不差于 B，且至少一个目标严格更好。
浮点噪声用 `--eps` 处理：差值小于 eps 视为相等。

Run:
    export PYTHONPATH="$PWD/libs/pylibs"
    python3 code/analysis/pareto_front.py results/instance_frontfit_c0.05.json
    python3 code/analysis/pareto_front.py results/instance_burst_*.json --eps 0.05
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

#: 目标名 → (结果字段, 方向)；方向 `+1` 表示越大越好、`-1` 表示越小越好。
OBJECTIVES = (("交付", "routine_delivered", +1),
              ("上行", "uplinks", -1),
              ("下行", "downlink_attempts", -1),
              ("AoI", "routine_aoi_mean_s", -1))


def load(path: str) -> tuple[str, dict]:
    doc = json.load(open(path, encoding="utf-8"))
    return os.path.basename(path), doc


def points(doc: dict) -> dict[str, tuple[float, ...]]:
    out = {}
    for arm, a in (doc.get("aggregate") or {}).get("arms", {}).items():
        vals = []
        for _label, key, _sign in OBJECTIVES:
            v = a.get(key)
            if v is None:
                break
            vals.append(float(v))
        else:
            out[arm] = tuple(vals)
    return out


def dominates(a: tuple[float, ...], b: tuple[float, ...], eps: float) -> bool:
    not_worse = True
    strictly_better = False
    for (x, y), (_l, _k, sign) in zip(zip(a, b), OBJECTIVES):
        if sign * (y - x) > eps:
            not_worse = False
            break
        if sign * (x - y) > eps:
            strictly_better = True
    return not_worse and strictly_better


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--eps", type=float, default=1e-9)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    files = []
    for f in args.files:
        files.extend(sorted(glob.glob(f)) if any(c in f for c in "*?[") else [f])

    for path in files:
        name, doc = load(path)
        pts = points(doc)
        if not pts:
            print(f"{name}: 没有可比较的臂")
            continue
        arms = sorted(pts)
        nd = [a for a in arms
              if not any(dominates(pts[b], pts[a], args.eps) for b in arms if b != a)]
        print(f"\n{name}  非支配 {len(nd)}/{len(arms)}: {', '.join(nd)}")
        if args.quiet:
            continue
        print("  " + "  ".join(f"{l}" for l, _k, _s in OBJECTIVES))
        for a in arms:
            mark = "  *" if a in nd else "   "
            vals = "  ".join(f"{v:10.2f}" for v in pts[a])
            print(f"{mark} {a:<14} {vals}")
        for a in arms:
            if a in nd:
                continue
            who = [b for b in nd if dominates(pts[b], pts[a], args.eps)]
            print(f"    {a} 被 {', '.join(who)} 支配")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
