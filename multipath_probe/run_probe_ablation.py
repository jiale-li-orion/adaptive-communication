"""run_probe_ablation.py — 探测成本消融：主动探测能否让强规则买回状态信息、追平 oracle？

关键反驳：网络领域标准手段是主动探测。若探测近乎免费（带外），强规则应能逼近 oracle；
但真实 LoRa/卫星是"观测=控制同通道"——探测与数据包抢同一份不可逆能量。
扫描 probe_energy：0=免费带外（理想上界）→ 1.0=与一个数据包同价（同通道真实情形）。
固定 K=3、紧能量预算。若 probe=1.0 时 rule+probe 仍显著低于 oracle，则信息差无法被同通道探测消除。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from env import generate_trace, MultipathEnv, PATH_SPECS          # noqa: E402
from controllers import OracleController, RuleMpcController, FixedController, _uav_scheduled  # noqa: E402

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
    return m, m - h, m + h


class RuleProbe(RuleMpcController):
    """强规则 + 聪明主动探测：仅在有积压、该路径可能被用到、信念落在不确定带、且距上次动作≥冷却时探 1 次。"""
    def __init__(self, cooldown=2):
        super().__init__()
        self.cooldown = cooldown

    def probe_decision(self, view):
        if view.backlog <= 0:
            return {}
        pr = {}
        for p in view.paths:
            if p == "uav" and not _uav_scheduled(view.t):
                continue
            b = self._belief(p, view)
            if not (self.lo <= b <= self.hi):
                continue
            hist = view.history.get(p, [])
            last = max((t for t, _, _ in hist), default=-99)
            if view.t - last >= self.cooldown:
                pr[p] = 1
        return pr


def run(trace, arm, budget, probe_cost):
    """arm: oracle/rule/rule_probe{cost}/fixed。返回 metrics。"""
    use_probe = arm.startswith("rule_probe")
    env = MultipathEnv(trace, energy_budget_wh=budget,
                       probe_energy=(probe_cost if use_probe else None))
    if arm == "oracle":
        ctrl = OracleController()
    elif arm == "rule":
        ctrl = RuleMpcController()
    elif use_probe:
        ctrl = RuleProbe()
    else:
        ctrl = FixedController()
    for _ in range(trace.T):
        v = env.view()
        probes = ctrl.probe_decision(v) if use_probe else {}
        if arm == "oracle":
            alloc = ctrl.decide(v, env.true_good())
        else:
            alloc = ctrl.decide(v)
        env.step(alloc, probes)
    return env.finalize()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--out", default=os.path.join(HERE, "results", "probe_ablation.json"))
    args = ap.parse_args()

    budgets = [2100, 1950, 1800]
    Bs = ["iid", "chirpbox", "heavy"]
    probe_costs = [0.0, 0.25, 0.5, 1.0]
    arms = ["oracle", "rule"] + [f"rule_probe{c}" for c in probe_costs] + ["fixed"]
    rows = []

    for b in Bs:
        for budget in budgets:
            acc = {a: [] for a in arms}
            for seed in range(args.seeds):
                tr = generate_trace(seed=seed, K=3, burst=b, T=336)
                for a in arms:
                    cost = float(a.replace("rule_probe", "")) if a.startswith("rule_probe") else 0.0
                    acc[a].append(run(tr, a, budget, cost))
            er = {a: sum(m["event_rate"] for m in acc[a]) / args.seeds for a in arms}
            row = {"burst": b, "budget": budget, "event_rate": er,
                   "oracle_minus": {a: paired([(o - x) * 100 for o, x in zip(
                       [m["event_rate"] for m in acc["oracle"]],
                       [m["event_rate"] for m in acc[a]])]) for a in arms if a != "oracle"}}
            rows.append(row)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"seeds": args.seeds, "rows": rows}, f, ensure_ascii=False, indent=2)

    print("=" * 116)
    print("探测成本消融 K=3。各臂事件交付率%；括号为 oracle−该臂(pp) 与95%区间。probe成本:0=免费带外,1=同数据包同价")
    print("=" * 116)
    for b in Bs:
        for budget in budgets:
            row = next(r for r in rows if r["burst"] == b and r["budget"] == budget)
            er = row["event_rate"]
            print(f"\n[{b}  budget={budget}]")
            print(f"  oracle={er['oracle']*100:5.1f}   rule(no probe)={er['rule']*100:5.1f}   fixed={er['fixed']*100:5.1f}")
            for c in probe_costs:
                a = f"rule_probe{c}"
                m, lo, hi = row["oracle_minus"][a]
                print(f"  rule+probe(cost={c:<4})={er[a]*100:5.1f}   oracle-gap={m:6.2f}pp [{lo:6.2f},{hi:6.2f}]")
    print(f"\n已写：{args.out}")


if __name__ == "__main__":
    main()
