# -*- coding: utf-8 -*-
"""r30b — 诊断 O_en(comply+无限能量+稀缺回传) 为何 missColl 反增。"""
import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__)); _CODE = os.path.dirname(_HERE)
for p in [_HERE, _CODE] + [os.path.join(_CODE, d) for d in
        ("physics", "runtime", "experiments", "analysis", "monitoring", "instance")]:
    if p not in sys.path:
        sys.path.insert(0, p)
from collections import Counter
from joint_run import run_joint

UP_ONLY = [(0, 600, "blue"), (6 * 3600, 300, "yellow")]
COMMON = dict(seed=0, task_hours=48, tail_hours=1, arm="local", groups=2,
    sample_interval_s=600, report_period_s=600, routine_period_s=600,
    initial_soc=1.0, outage_start_h=4, outage_hours=16, enable_backup=True,
    mission_schedule=UP_ONLY)


def cls(x):
    if x["censored"]:
        return "cens"
    if x["delivered"]:
        return "deliv"
    if not x["collected"]:
        return "missColl"
    if x["first_heard_at"] is None:
        return "stuck_node"
    if not x["received_on_time"]:
        return "stuck_gw"
    return "other"


for tag, mode, peak, br, bb in [
    ("Oen_comply", "comply", 1.0, 1200, 78),
    ("Oen_day_energy", "dayfeed", 1.0, 1200, 78),
    ("Obo_comply_inf", "comply", 1.0, 60, 100000)]:
    r, inst, obs = run_joint(collect_rows=True, mission_mode=mode,
        harvest_mode="solar", harvest_peak_wh_per_hour=peak,
        backup_rate_s=br, backup_bytes=bb, backup_chooser="maxcov",
        backup_p_succ=1.0, **COMMON)
    rows = [x for x in r["rows"] if x["kind"] == "routine"]
    c = Counter(cls(x) for x in rows)
    sv = r["survival"]
    print(f"\n=== {tag} svc={r['routine']['delivered']/r['routine']['n']:.4f} dead={len(sv['dead'])} "
          f"finalSoC_mean={sv.get('mean_final_soc', float('nan')):.3f} {dict(c)}")
    # missColl 按 h6 前/后 与小时
    mc = [x for x in rows if cls(x) == "missColl"]
    pre = sum(1 for x in mc if x["release_at"] < 6*3600)
    post = len(mc) - pre
    print(f"  missColl h6前={pre} h6后={post}")
    hh = Counter(x["release_at"]//3600 for x in mc)
    print(f"  missColl 按小时: {dict(sorted(hh.items()))}")
    sn = [x for x in rows if cls(x) == "stuck_node"]
    print(f"  stuck_node n={len(sn)}: " + ", ".join(
        f"{x['node_id']}@h{x['release_at']//3600}" for x in sn[:10]))
    # 节点实际采样档位轨迹（n00 若干时刻）
    states = [(t, iv, rp) for (t, nid, k, iv, rp, soc, al)
              in inst.trace_events if k == "state" and nid == "n00"]
    states.sort()
    sample_iv = [(t//3600, iv, rp) for (t, iv, rp) in states[::60]]
    print(f"  n00 (hour, sampleIV, reportP) 每60采样: {sample_iv[:30]}")
