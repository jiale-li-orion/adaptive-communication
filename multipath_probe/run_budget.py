"""run_budget.py — 第二版：固定 K=3，扫描能量硬预算松紧，检验"信息差→业务差"的相变。

动机（来自第一版结果）：无能量约束时 rule_mpc 靠在坏路径广撒网（多耗 25–50% 能量）追平 oracle。
本版给三臂相同的总能量预算（等预算公平），rule_mpc 已带能量水位节能模式。
事前预测：预算从松到紧，oracle-rule 交付率差从≈0 单调拉开；若任意紧档差距仍≈0，则为硬 no-go。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from env import generate_trace, MultipathEnv          # noqa: E402
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
    var = sum((x - m) ** 2 for x in diffs) / (n - 1) if n > 1 else float("nan")
    se = math.sqrt(var / n) if var == var else float("nan")
    h = t975(n - 1) * se if se == se else float("nan")
    return {"mean": m, "lo": m - h, "hi": m + h,
            "win": sum(1 for x in diffs if x > 1e-12),
            "tie": sum(1 for x in diffs if abs(x) <= 1e-12),
            "loss": sum(1 for x in diffs if x < -1e-12)}


def run_one(trace, cname, budget):
    env = MultipathEnv(trace, energy_budget_wh=budget)
    ctrl = {"oracle": OracleController, "rule_mpc": RuleMpcController,
            "fixed": FixedController}[cname]()
    for _ in range(trace.T):
        v = env.view()
        a = ctrl.decide(v, env.true_good()) if cname == "oracle" else ctrl.decide(v)
        env.step(a)
    return env.finalize()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--hours", type=int, default=336)
    ap.add_argument("--out", default=os.path.join(HERE, "results", "budget_sweep.json"))
    args = ap.parse_args()

    budgets = [None, 2300, 2100, 1950, 1800, 1650]
    blabel = {None: "loose"}
    Bs = ["iid", "chirpbox", "heavy"]
    arms = ["oracle", "rule_mpc", "fixed"]
    rows = []

    for b in Bs:
        for budget in budgets:
            per = {a: [] for a in arms}
            for seed in range(args.seeds):
                tr = generate_trace(seed=seed, K=3, burst=b, T=args.hours)
                for a in arms:
                    per[a].append(run_one(tr, a, budget))
            def col(a, k):
                return [m[k] for m in per[a]]
            row = {"burst": b, "budget": budget,
                   "oracle-rule_event_pp": paired([(o - r) * 100 for o, r in zip(
                       col("oracle", "event_rate"), col("rule_mpc", "event_rate"))]),
                   "oracle-rule_routine_pp": paired([(o - r) * 100 for o, r in zip(
                       col("oracle", "routine_rate"), col("rule_mpc", "routine_rate"))]),
                   "rule-fixed_event_pp": paired([(r - f) * 100 for r, f in zip(
                       col("rule_mpc", "event_rate"), col("fixed", "event_rate"))]),
                   "arm_event_rate": {a: sum(col(a, "event_rate")) / args.seeds for a in arms},
                   "arm_routine_rate": {a: sum(col(a, "routine_rate")) / args.seeds for a in arms},
                   "arm_energy": {a: sum(col(a, "energy")) / args.seeds for a in arms},
                   "rule_wasted": sum(col("rule_mpc", "wasted_bad_path")) / args.seeds}
            rows.append(row)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"seeds": args.seeds, "K": 3, "rows": rows}, f, ensure_ascii=False, indent=2)

    print("=" * 108)
    print(f"能量预算扫描 K=3，{args.seeds} 配对种子。ΔE=oracle-rule 事件交付率差(pp)，括号 95% 区间，W/T/L")
    print("=" * 108)
    for b in Bs:
        print(f"\n--- burst={b} ---")
        print(f"{'budget':>7} | {'oracle E%':>9} {'rule E%':>8} {'fixed E%':>9} | "
              f"{'ΔE [lo,hi] W/T/L':>26} | {'Δroutine':>9} | {'rule/oracle能量':>14}")
        for row in [r for r in rows if r["burst"] == b]:
            lab = blabel.get(row["budget"], str(row["budget"]))
            d = row["oracle-rule_event_pp"]
            dr = row["oracle-rule_routine_pp"]
            er = row["arm_event_rate"]
            en = row["arm_energy"]
            print(f"{lab:>7} | {er['oracle']*100:9.1f} {er['rule_mpc']*100:8.1f} {er['fixed']*100:9.1f} | "
                  f"{d['mean']:6.2f} [{d['lo']:5.2f},{d['hi']:5.2f}] {d['win']}/{d['tie']}/{d['loss']:>3} | "
                  f"{dr['mean']:8.2f} | {en['rule_mpc']:7.0f}/{en['oracle']:<7.0f}")
    print(f"\n已写：{args.out}")


if __name__ == "__main__":
    main()
