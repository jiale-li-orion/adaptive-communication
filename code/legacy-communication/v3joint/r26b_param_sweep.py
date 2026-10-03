# -*- coding: utf-8 -*-
"""r26b — night_budget 参数邻域扫描 + 预算轨迹诊断。
目的：证明稳健版退化为 dayfeed 是"物理无安全空间"还是"参数过保守"。
扫 L(命令延迟)/R(黎明缓冲)/hear(可达年龄)，记录 svc/dead/夜间密采触发数；并 dump n00 预算账。
"""
import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__)); _CODE = os.path.dirname(_HERE)
for p in [_HERE, _CODE] + [os.path.join(_CODE, d) for d in
        ("physics", "runtime", "experiments", "analysis", "monitoring", "instance")]:
    if p not in sys.path:
        sys.path.insert(0, p)
from joint_run import run_joint
from night_budget import NightBudgetPolicy

BASE = dict(seed=0, task_hours=48, tail_hours=1, arm="local", groups=2,
    sample_interval_s=600, report_period_s=600, routine_period_s=600,
    harvest_mode="solar", harvest_peak_wh_per_hour=0.03, initial_soc=1.0,
    outage_start_h=4, outage_hours=16, enable_backup=True,
    backup_rate_s=1200, backup_bytes=78, backup_chooser="maxcov")
UP = [(0, 600, "blue"), (6 * 3600, 300, "yellow")]


def run(pol):
    r, _i, _o = run_joint(mission_schedule=UP, mission_policy_obj=pol,
                          collect_rows=False, **BASE)
    return r, _i


def svc(r):
    return r["routine"]["delivered"] / r["routine"]["n"]


# ---------- 1) 预算轨迹诊断（默认参数，挑 n00） ----------
pol = NightBudgetPolicy(UP)
r, inst = run(pol)
tr = pol.budget_trace
print("== n00 夜间预算账 (t(h), soc, T_dawn(h), E_min, can_dense, heard, relaxed) ==")
for (t, nid, s, T, E, can, heard, rel) in tr:
    if nid != "n00":
        continue
    h = t / 3600
    if (12 <= h < 24) or (36 <= h < 48):
        print(f"h{h:5.1f} soc={s} T={T:5.2f} Emin={E} can={int(can)} heard={int(heard)} rel={int(rel)}")

# ---------- 2) 参数邻域扫描 ----------
print("\n== 参数扫描 seed0 (dayfeed 基准 .4001 / dead0) ==")
print(f"{'L':>5}{'R':>6}{'hear':>6} | {'svc':>7}{'dead':>5}{'SoC':>7}  night_dense_triggers")
for L in (0, 900, 1800, 3600):
    for R in (0, 1800, 3600, 7200):
        for hear in (1200, 2400):
            p = NightBudgetPolicy(UP, cmd_latency_s=L, dawn_ramp_s=R, hear_s=hear)
            rr, _ = run(p)
            ndense = sum(1 for x in p.budget_trace if x[5])
            print(f"{L:>5}{R:>6}{hear:>6} | {svc(rr):.4f}{len(rr['survival']['dead']):>5}"
                  f"{rr['survival']['mean_final_soc']:>7.3f}  {ndense}")
