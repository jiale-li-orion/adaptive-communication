"""run_probe.py — K(路径数) × b(突发度) 扫描，三臂配对比较。

同一 (seed,K,b) 只生成一份外生 Trace，三臂共享，逐种子配对。
写 results/probe_results.json，并打印 go/no-go 主表。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from env import generate_trace, MultipathEnv           # noqa: E402
from controllers import OracleController, RuleMpcController, FixedController  # noqa: E402

T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
        8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145,
        15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086}


def t975(df):
    if df <= 0:
        return float("nan")
    for k in sorted(T975):
        if df <= k:
            return T975[k]
    return 1.96


def paired(diffs):
    n = len(diffs)
    m = sum(diffs) / n
    if n > 1:
        var = sum((x - m) ** 2 for x in diffs) / (n - 1)
        se = math.sqrt(var / n)
    else:
        se = float("nan")
    h = t975(n - 1) * se if se == se else float("nan")
    return {"n": n, "mean": m, "lo": m - h, "hi": m + h,
            "win": sum(1 for x in diffs if x > 1e-12),
            "tie": sum(1 for x in diffs if abs(x) <= 1e-12),
            "loss": sum(1 for x in diffs if x < -1e-12),
            "all_zero": all(abs(x) <= 1e-12 for x in diffs)}


def run_one(trace, cname):
    env = MultipathEnv(trace)
    ctrl = {"oracle": OracleController, "rule_mpc": RuleMpcController,
            "fixed": FixedController}[cname]()
    for _ in range(trace.T):
        view = env.view()
        alloc = ctrl.decide(view, env.true_good()) if cname == "oracle" else ctrl.decide(view)
        env.step(alloc)
    return env.finalize()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--hours", type=int, default=336)
    ap.add_argument("--out", default=os.path.join(HERE, "results", "probe_results.json"))
    args = ap.parse_args()

    Ks = [1, 2, 3]
    Bs = ["iid", "chirpbox", "heavy"]
    arms = ["oracle", "rule_mpc", "fixed"]
    cells = []

    for K in Ks:
        for b in Bs:
            per_arm = {a: [] for a in arms}
            for seed in range(args.seeds):
                trace = generate_trace(seed=seed, K=K, burst=b, T=args.hours)
                for a in arms:
                    per_arm[a].append(run_one(trace, a))
            def col(a, key):
                return [m[key] for m in per_arm[a]]
            cell = {"K": K, "burst": b, "seeds": args.seeds, "arms": {}}
            for a in arms:
                er = col(a, "event_rate")
                rr = col(a, "routine_rate")
                cell["arms"][a] = {
                    "event_rate_mean": sum(er) / len(er),
                    "routine_rate_mean": sum(rr) / len(rr),
                    "wasted_bad_path_mean": sum(col(a, "wasted_bad_path")) / len(er),
                    "sat_quota_wasted_mean": sum(col(a, "sat_quota_wasted")) / len(er),
                    "money_mean": sum(col(a, "money")) / len(er),
                    "energy_mean": sum(col(a, "energy")) / len(er),
                    "per_seed_event_rate": er,
                }
            # 配对差（百分点 = 率差 ×100）
            cell["pairwise"] = {
                "oracle-rule_event_pp": paired([(o - r) * 100 for o, r in zip(
                    col("oracle", "event_rate"), col("rule_mpc", "event_rate"))]),
                "rule-fixed_event_pp": paired([(r - f) * 100 for r, f in zip(
                    col("rule_mpc", "event_rate"), col("fixed", "event_rate"))]),
                "oracle-rule_routine_pp": paired([(o - r) * 100 for o, r in zip(
                    col("oracle", "routine_rate"), col("rule_mpc", "routine_rate"))]),
                "oracle-rule_wasted": paired([(r - o) for r, o in zip(
                    col("rule_mpc", "wasted_bad_path"), col("oracle", "wasted_bad_path"))]),
            }
            cells.append(cell)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"seeds": args.seeds, "hours": args.hours, "cells": cells}, f,
                  ensure_ascii=False, indent=2)

    # ---------- 打印主表 ----------
    print("=" * 104)
    print(f"多路径隐状态探针：{args.seeds} 配对种子 × {args.hours}h。交付率为均值，括号为配对差 95% 区间，单位百分点(pp)")
    print("=" * 104)
    hdr = f"{'K':>2} {'burst':>8} | {'oracle E/R':>13} | {'rule_mpc E/R':>13} | {'fixed E/R':>13} | " \
          f"{'oracle-rule ΔE [lo,hi] W/T/L':>30} | {'rule-fix ΔE':>10}"
    print(hdr)
    print("-" * 104)
    for c in cells:
        a = c["arms"]
        def er(x):
            return a[x]["event_rate_mean"] * 100
        def rr(x):
            return a[x]["routine_rate_mean"] * 100
        por = c["pairwise"]["oracle-rule_event_pp"]
        prf = c["pairwise"]["rule-fixed_event_pp"]
        print(f"{c['K']:>2} {c['burst']:>8} | {er('oracle'):6.1f}/{rr('oracle'):5.1f} | "
              f"{er('rule_mpc'):6.1f}/{rr('rule_mpc'):5.1f} | {er('fixed'):6.1f}/{rr('fixed'):5.1f} | "
              f"{por['mean']:6.2f} [{por['lo']:5.2f},{por['hi']:5.2f}] "
              f"{por['win']}/{por['tie']}/{por['loss']:>4} | {prf['mean']:6.2f}")
    print("-" * 104)
    print("浪费对照（rule_mpc 相对 oracle 在坏路径上多发的尝试数，均值/任务）：")
    for c in cells:
        w = c["pairwise"]["oracle-rule_wasted"]
        sw = c["arms"]["rule_mpc"]["sat_quota_wasted_mean"]
        print(f"  K={c['K']} {c['burst']:>8}: Δwasted={w['mean']:7.2f} [{w['lo']:6.2f},{w['hi']:6.2f}]"
              f"  rule_mpc 卫星配额浪费={sw:5.2f}")
    print(f"\n已写：{args.out}")


if __name__ == "__main__":
    main()
