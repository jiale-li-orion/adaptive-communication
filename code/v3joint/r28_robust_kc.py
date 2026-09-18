# -*- coding: utf-8 -*-
"""r28 — night_mpc 对采能模型失配的鲁棒性：扫保守云系数 kc × 6 种子。
dayfeed dead=[0,12,0,0,0,0] mean=.3729 为基准。找"不新增死亡且配对差均值>=0"的稳健工作点。"""
import os, sys, statistics as st
_HERE = os.path.dirname(os.path.abspath(__file__)); _CODE = os.path.dirname(_HERE)
for p in [_HERE, _CODE] + [os.path.join(_CODE, d) for d in
        ("physics", "runtime", "experiments", "analysis", "monitoring", "instance")]:
    if p not in sys.path:
        sys.path.insert(0, p)
from joint_run import run_joint
from night_mpc import NightMpcPolicy

BASE = dict(task_hours=48, tail_hours=1, arm="local", groups=2,
    sample_interval_s=600, report_period_s=600, routine_period_s=600,
    harvest_mode="solar", harvest_peak_wh_per_hour=0.03, initial_soc=1.0,
    outage_start_h=4, outage_hours=16, enable_backup=True,
    backup_rate_s=1200, backup_bytes=78, backup_chooser="maxcov")
UP = [(0, 600, "blue"), (6 * 3600, 300, "yellow")]
SEEDS = (0, 1, 2, 3, 4, 5)


def svc(r):
    return r["routine"]["delivered"] / r["routine"]["n"]


df = []
for s in SEEDS:
    r, _i, _o = run_joint(seed=s, mission_schedule=UP, mission_mode="dayfeed",
                          collect_rows=False, **BASE)
    df.append((svc(r), len(r["survival"]["dead"])))
print("dayfeed   " + " ".join(f"s{s}:{v:.4f}/d{d}" for s, (v, d) in zip(SEEDS, df))
      + f" | mean={st.mean(v for v,_ in df):.4f}")

for kc in (0.25, 0.4, 0.5, 0.7375):
    rows = []
    for s in SEEDS:
        pol = NightMpcPolicy(UP, cloud_mode=f"kc:{kc}", cmd_latency_s=1800)
        r, _i, _o = run_joint(seed=s, mission_schedule=UP, mission_policy_obj=pol,
                              collect_rows=False, **BASE)
        rows.append((svc(r), len(r["survival"]["dead"])))
    diffs = [rows[i][0] - df[i][0] for i in range(len(SEEDS))]
    print(f"kc={kc:<6} " + " ".join(f"s{s}:{v:.4f}/d{d}" for s, (v, d) in zip(SEEDS, rows))
          + f" | mean={st.mean(v for v,_ in rows):.4f} diff={st.mean(diffs):+.4f} "
          f"worst={min(diffs):+.4f} newdead={sum(max(0,rows[i][1]-df[i][1]) for i in range(len(SEEDS)))}")
