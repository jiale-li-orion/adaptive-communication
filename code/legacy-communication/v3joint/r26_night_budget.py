# -*- coding: utf-8 -*-
"""r26 — 夜间能量预算前馈强规则(night_budget) vs r24 五模式；含分时段损失分解与多种子配对。

零 LLM、确定性。night_budget 与 dayfeed 同信息(标称昼夜+当前SoC+center合法视图)，只多一个
"到日出的能量预算前馈 + 主路可达才夜密 + 夜内一次前密后疏锁存"。判定候选 C 是否存在
dayfeed/maxcov 拿不到的可改变损失。
"""
import os, sys, statistics as st
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


def one(seed=0, mode=None, obj=None, rows=False):
    kw = dict(BASE); kw["seed"] = seed; kw["collect_rows"] = rows
    if obj is not None:
        kw.update(mission_schedule=UP, mission_policy_obj=obj)
    else:
        kw.update(mission_schedule=UP, mission_mode=mode)
    return run_joint(**kw)[:2]


def line(tag, r):
    rr = r["routine"]; sv = r["survival"]
    print(f"{tag:14s} svc={rr['delivered']/rr['n']:.4f} n={rr['n']} "
          f"mC={rr.get('missing_collection')} mD={rr.get('missing_delivery')} "
          f"dead={len(sv['dead'])} SoC={sv['mean_final_soc']:.4f} "
          f"refus={len(r.get('mission_refusals', []))}")


print("== seed0 主点 ==")
res = {}
for m in ("ignore", "comply", "sustain", "dayfeed"):
    r, _ = one(mode=m); res[m] = r; line(m, r)
r_nb, inst_nb = one(obj=NightBudgetPolicy(UP)); res["nb"] = r_nb; line("night_budget", r_nb)


def buckets(r):
    B = {}
    for x in r["rows"]:
        if x["kind"] != "routine":
            continue
        b = (x["release_at"] // 3600 // 6) * 6
        d = B.setdefault(b, {"n": 0, "del": 0, "coll": 0, "mC": 0, "mD": 0, "cens": 0})
        if x["censored"]:
            d["cens"] += 1; continue
        d["n"] += 1
        if x["collected"]:
            d["coll"] += 1
        if x["delivered"]:
            d["del"] += 1
        elif not x["collected"]:
            d["mC"] += 1
        else:
            d["mD"] += 1
    return B


r_df, _ = one(mode="dayfeed", rows=True)
r_nb2, _ = one(obj=NightBudgetPolicy(UP), rows=True)
bd, bn = buckets(r_df), buckets(r_nb2)
print("\n== 6h 段 routine 损失分解 (非右删失) ==")
print("段(钟点: t=0为6:00)        | dayfeed  n/del/mC/mD        | night_budget n/del/mC/mD")
for b in sorted(set(bd) | set(bn)):
    d = bd.get(b, {}); n = bn.get(b, {})
    print(f"h{b:02d}-{b+6:02d}            | {d.get('n',0):4d} {d.get('del',0):4d} "
          f"{d.get('mC',0):4d} {d.get('mD',0):4d}      | {n.get('n',0):4d} {n.get('del',0):4d} "
          f"{n.get('mC',0):4d} {n.get('mD',0):4d}")

print("\n== seeds 0-5 配对 ==")
summary = {}
for name, mk in [("dayfeed", lambda s: one(seed=s, mode="dayfeed")[0]),
                 ("night_budget", lambda s: one(seed=s, obj=NightBudgetPolicy(UP))[0])]:
    vals, deads, socs = [], [], []
    for s in range(6):
        r = mk(s)
        vals.append(r["routine"]["delivered"] / r["routine"]["n"])
        deads.append(len(r["survival"]["dead"])); socs.append(r["survival"]["mean_final_soc"])
    summary[name] = vals
    print(f"{name:14s} mean={st.mean(vals):.4f} vals={[round(v,4) for v in vals]} "
          f"dead={deads} SoC={[round(x,3) for x in socs]}")
diff = [summary["night_budget"][s] - summary["dayfeed"][s] for s in range(6)]
print(f"配对差(nb-df): {[round(x,4) for x in diff]}  mean={st.mean(diff):+.4f}")
