#!/usr/bin/env python3
"""
paired_ci.py — paired comparisons with a 95% interval, and zero-checks that do not average.

Two things this file exists for.

PAIRED, NOT TWO MEANS. Every arm in a run sees the same node set, the same environment trace and
the same decision trajectory for a given seed. The arms are therefore paired, and the quantity
worth testing is the per-seed DIFFERENCE, not the gap between two independent means. Pairing
removes the between-seed variance that dominates a link this lossy, which is most of it.

ZERO IS A CLAIM. "duplicate = 0" and "stale overwrite = 0" are reported as counts, and a mean of
0.0 is not the same statement as "no seed produced one". A metric that is zero in 18 of 20 seeds
and 40 in the other two has a mean of 4.0 and is not zero. Every zero-valued metric is checked
per seed and the check is reported explicitly.

Usage:
    python3 code/analysis/paired_ci.py results/method_comparison_main.json ours verified_tool_calls
    python3 code/analysis/paired_ci.py results/method_comparison_p2.json ours ablate_fencing --metric stale_overwrites
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

# 97.5% quantiles of Student's t, by degrees of freedom. Above 60 the normal value is used.
T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306,
        9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131,
        16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086, 22: 2.074, 24: 2.064,
        26: 2.056, 28: 2.048, 30: 2.042, 35: 2.030, 40: 2.021, 50: 2.009, 60: 2.000}


def t975(df: int) -> float:
    if df <= 0:
        return float("nan")
    if df in T975:
        return T975[df]
    keys = sorted(T975)
    for k in keys:
        if df <= k:
            return T975[k]
    return 1.960


def load(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def find(doc: dict, arm: str, workload: str | None = None) -> dict | None:
    for r in doc["results"]:
        if r["arm"] == arm and (workload is None or r.get("workload") == workload):
            return r
    return None


def paired(a: list[float], b: list[float]) -> dict:
    n = min(len(a), len(b))
    d = [a[i] - b[i] for i in range(n)]
    mean = sum(d) / n
    if n > 1:
        var = sum((x - mean) ** 2 for x in d) / (n - 1)
        se = math.sqrt(var / n)
    else:
        se = float("nan")
    half = t975(n - 1) * se if se == se else float("nan")
    return {"n": n, "mean": mean, "lo": mean - half, "hi": mean + half, "se": se,
            "all_zero": all(x == 0 for x in d),
            "signs": (sum(1 for x in d if x > 0), sum(1 for x in d if x < 0),
                      sum(1 for x in d if x == 0))}


def report(path: str, arm_a: str, arm_b: str, metrics: list[str],
           workload: str | None) -> None:
    doc = load(path)
    ra, rb = find(doc, arm_a, workload), find(doc, arm_b, workload)
    if ra is None or rb is None:
        print(f"  {arm_a if ra is None else arm_b} 不在 {os.path.basename(path)} 里"
              + (f"（workload={workload}）" if workload else ""))
        return
    wl = ra.get("workload", "")
    print(f"\n{os.path.basename(path)}  workload={wl}  seeds={len(ra['per_seed'][metrics[0]])}")
    print(f"  {arm_a} − {arm_b}，配对差值的 95% 置信区间")
    print(f"  {'指标':22s} {'差值':>12s} {'95% CI':>26s} {'区间含 0':>9s} {'正/负/平':>10s}")
    for m in metrics:
        if m not in ra["per_seed"] or m not in rb["per_seed"]:
            continue
        st = paired(ra["per_seed"][m], rb["per_seed"][m])
        crosses = st["lo"] <= 0 <= st["hi"]
        print(f"  {m:22s} {st['mean']:12.4f} "
              f"[{st['lo']:11.4f}, {st['hi']:11.4f}] "
              f"{'是' if crosses else '否':>9s} "
              f"{st['signs'][0]:3d}/{st['signs'][1]:3d}/{st['signs'][2]:3d}")


def zero_check(path: str, arms: list[str], metrics: list[str]) -> None:
    doc = load(path)
    print(f"\n零值检查：{os.path.basename(path)}")
    print(f"  {'arm':24s} {'workload':14s} {'指标':20s} {'全 seed 为 0':>12s} {'非零 seed':>9s} {'最大':>10s}")
    for r in doc["results"]:
        if arms and r["arm"] not in arms:
            continue
        for m in metrics:
            vals = r["per_seed"].get(m)
            if vals is None:
                continue
            nz = [v for v in vals if v != 0]
            print(f"  {r['arm']:24s} {r.get('workload', ''):14s} {m:20s} "
                  f"{'是' if not nz else '否':>12s} {len(nz):9d} "
                  f"{(max(vals) if vals else 0):10.3f}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--arm-a", default="ours")
    ap.add_argument("--arm-b", default="verified_tool_calls")
    ap.add_argument("--workload", default=None)
    ap.add_argument("--metrics", default="exactly_once_rate,duplicate_applications,"
                                        "stale_reorders,stale_overwrites,airtime_s,normalized_cost")
    ap.add_argument("--zero-check", action="store_true")
    args = ap.parse_args()

    metrics = args.metrics.split(",")
    for p in args.paths:
        if not os.path.exists(p):
            print(f"跳过不存在的 {p}")
            continue
        report(p, args.arm_a, args.arm_b, metrics, args.workload)
    if args.zero_check:
        for p in args.paths:
            if os.path.exists(p):
                zero_check(p, [], ["duplicate_applications", "stale_overwrites", "stale_reorders"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
