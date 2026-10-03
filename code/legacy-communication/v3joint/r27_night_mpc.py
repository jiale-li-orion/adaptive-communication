# -*- coding: utf-8 -*-
"""r27 — 标称能量前馈 MPC(night_mpc) vs dayfeed；含云系数/命令延迟敏感性、分时段、多种子。"""
import os, sys, statistics as st
_HERE = os.path.dirname(os.path.abspath(__file__)); _CODE = os.path.dirname(_HERE)
for p in [_HERE, _CODE] + [os.path.join(_CODE, d) for d in
        ("physics", "runtime", "experiments", "analysis", "monitoring", "instance")]:
    if p not in sys.path:
        sys.path.insert(0, p)
from joint_run import run_joint
from night_mpc import NightMpcPolicy
from night_budget import NightBudgetPolicy

BASE = dict(seed=0, task_hours=48, tail_hours=1, arm="local", groups=2,
    sample_interval_s=600, report_period_s=600, routine_period_s=600,
    harvest_mode="solar", harvest_peak_wh_per_hour=0.03, initial_soc=1.0,
    outage_start_h=4, outage_hours=16, enable_backup=True,
    backup_rate_s=1200, backup_bytes=78, backup_chooser="maxcov")
UP = [(0, 600, "blue"), (6 * 3600, 300, "yellow")]


def one(seed=0, mode=None, obj=None, rows=False):
    kw = dict(BASE); kw["seed"] = seed; kw["collect_rows"] = rows
    if obj is not None:
        kw.update(mission_schedule=UP, mission_policy_obj=obj)
    else:
        kw.update(mission_schedule=UP, mission_mode=mode)
    return run_joint(**kw)[:2]


def line(tag, r):
    rr = r["routine"]; sv = r["survival"]
    print(f"{tag:22s} svc={rr['delivered']/rr['n']:.4f} mC={rr.get('missing_collection')} "
          f"mD={rr.get('missing_delivery')} dead={len(sv['dead'])} SoC={sv['mean_final_soc']:.4f}")


print("== seed0 主点 ==")
r_df, _ = one(mode="dayfeed"); line("dayfeed", r_df)
for tag, pol in [
    ("mpc_mean_L1800", NightMpcPolicy(UP, cloud_mode="mean", cmd_latency_s=1800)),
    ("mpc_mean_L3600", NightMpcPolicy(UP, cloud_mode="mean", cmd_latency_s=3600)),
    ("mpc_mean_L900", NightMpcPolicy(UP, cloud_mode="mean", cmd_latency_s=900)),
    ("mpc_sunny_L1800", NightMpcPolicy(UP, cloud_mode="sunny", cmd_latency_s=1800)),
    ("budget_R3600_L0", NightBudgetPolicy(UP, cmd_latency_s=0, dawn_ramp_s=3600)),
]:
    r, _ = one(obj=pol); line(tag, r)


def buckets(r):
    B = {}
    for x in r["rows"]:
        if x["kind"] != "routine":
            continue
        b = (x["release_at"] // 3600 // 6) * 6
        d = B.setdefault(b, {"n": 0, "del": 0, "mC": 0, "mD": 0})
        if x["censored"]:
            continue
        d["n"] += 1
        if x["delivered"]:
            d["del"] += 1
        elif not x["collected"]:
            d["mC"] += 1
        else:
            d["mD"] += 1
    return B


r_df2, _ = one(mode="dayfeed", rows=True)
r_mp, _ = one(obj=NightMpcPolicy(UP, cloud_mode="mean", cmd_latency_s=1800), rows=True)
bd, bm = buckets(r_df2), buckets(r_mp)
print("\n== 6h 段 routine (非删失) dayfeed vs mpc_mean ==")
for b in sorted(set(bd) | set(bm)):
    d = bd.get(b, {}); m = bm.get(b, {})
    print(f"h{b:02d}-{b+6:02d} | df {d.get('n',0):4d}/{d.get('del',0):4d}/"
          f"{d.get('mC',0):4d}/{d.get('mD',0):4d} | mp {m.get('n',0):4d}/"
          f"{m.get('del',0):4d}/{m.get('mC',0):4d}/{m.get('mD',0):4d}")

print("\n== seeds 0-5 ==")
summ = {}
for name, mk in [("dayfeed", lambda s: one(seed=s, mode="dayfeed")[0]),
                 ("mpc_mean_L1800", lambda s: one(seed=s, obj=NightMpcPolicy(UP, cmd_latency_s=1800))[0])]:
    vals, dead, socs = [], [], []
    for s in range(6):
        r = mk(s); vals.append(r["routine"]["delivered"] / r["routine"]["n"])
        dead.append(len(r["survival"]["dead"])); socs.append(r["survival"]["mean_final_soc"])
    summ[name] = vals
    print(f"{name:18s} mean={st.mean(vals):.4f} vals={[round(v,4) for v in vals]} dead={dead}")
diff = [summ["mpc_mean_L1800"][s] - summ["dayfeed"][s] for s in range(6)]
print(f"配对差(mpc-df): {[round(x,4) for x in diff]} mean={st.mean(diff):+.4f}")
