# -*- coding: utf-8 -*-
"""r29b — H2 降级相位系统扫描（零 LLM）。升级固定 h6，降级时刻 dh 扫中断窗内/夜间/日出/白天。
核心 H2 指标：是否存在"已采、deadline 未到、因降级上报回疏而卡在节点(stuck_node)"的升级密义务。
另看降级段任务表何时真正到达网关（中断窗内须等主回传恢复）。"""
import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__)); _CODE = os.path.dirname(_HERE)
for p in [_HERE, _CODE] + [os.path.join(_CODE, d) for d in
        ("physics", "runtime", "experiments", "analysis", "monitoring", "instance")]:
    if p not in sys.path:
        sys.path.insert(0, p)
from collections import Counter
from joint_run import run_joint

BASE = dict(seed=0, task_hours=48, tail_hours=1, arm="local", groups=2,
    sample_interval_s=600, report_period_s=600, routine_period_s=600,
    harvest_mode="solar", harvest_peak_wh_per_hour=0.03, initial_soc=1.0,
    outage_start_h=4, outage_hours=16, enable_backup=True,
    backup_rate_s=1200, backup_bytes=78, backup_chooser="maxcov")
H6 = 6 * 3600


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


def run(sched):
    r, inst, obs = run_joint(mission_schedule=sched, mission_mode="dayfeed",
                             collect_rows=True, **BASE)
    return r, inst


def stats(tag, r, inst, dh):
    rr = r["routine"]; sv = r["survival"]
    rows = [x for x in r["rows"] if x["kind"] == "routine" and not x["censored"]]
    allc = Counter(cls(x) for x in rows)
    # 降级授权点前 30min 的升级密义务
    D = dh * 3600
    edge = [x for x in rows if D - 1800 <= x["release_at"] < D]
    ce = Counter(cls(x) for x in edge)
    # 任务表段实际到达网关时刻
    gw_times = [s.get("gateway_received_at") for s in r.get("mission_timing", [])]
    print(f"{tag:10s} svc={rr['delivered']/rr['n']:.4f} n={rr['n']} dead={len(sv['dead'])} "
          f"SoC={sv['mean_final_soc']:.3f} | 全任务卡点 {dict(allc)}")
    print(f"           降级授权 h{dh} 边界30min n={len(edge)} {dict(ce)} | 段到达网关时刻={gw_times}")


r0, i0 = run([(0, 600, "blue"), (H6, 300, "yellow")])
stats("UP_ONLY", r0, i0, 99)
for dh in [10, 14, 18, 22, 26, 30, 34]:
    sched = [(0, 600, "blue"), (H6, 300, "yellow"), (dh * 3600, 600, "blue")]
    r, inst = run(sched)
    stats(f"DOWN_h{dh}", r, inst, dh)
