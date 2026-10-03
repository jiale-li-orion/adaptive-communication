# -*- coding: utf-8 -*-
"""r29 — H2 降级/解除片段最便宜诊断（零 LLM）。
schedule: h6 升 600->300, h30 降 300->600。对照 UP_ONLY(不降级)。
聚焦降级点附近、已采但尚未到网关/中心、deadline 跨降级点的升级密义务，定位可改变损失。
"""
import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__)); _CODE = os.path.dirname(_HERE)
for p in [_HERE, _CODE] + [os.path.join(_CODE, d) for d in
        ("physics", "runtime", "experiments", "analysis", "monitoring", "instance")]:
    if p not in sys.path:
        sys.path.insert(0, p)
from joint_run import run_joint

BASE = dict(seed=0, task_hours=48, tail_hours=1, arm="local", groups=2,
    sample_interval_s=600, report_period_s=600, routine_period_s=600,
    harvest_mode="solar", harvest_peak_wh_per_hour=0.03, initial_soc=1.0,
    outage_start_h=4, outage_hours=16, enable_backup=True,
    backup_rate_s=1200, backup_bytes=78, backup_chooser="maxcov")
UP_ONLY = [(0, 600, "blue"), (6 * 3600, 300, "yellow")]
UP_DOWN = [(0, 600, "blue"), (6 * 3600, 300, "yellow"), (30 * 3600, 600, "blue")]
H6, H30 = 6 * 3600, 30 * 3600


def run(sched, mode="dayfeed"):
    r, inst, obs = run_joint(mission_schedule=sched, mission_mode=mode,
                             collect_rows=True, **BASE)
    return r, inst, obs


def summ(tag, r):
    rr = r["routine"]; sv = r["survival"]
    print(f"{tag:16s} svc={rr['delivered']/rr['n']:.4f} n={rr['n']} "
          f"mC={rr.get('missing_collection')} mD={rr.get('missing_delivery')} "
          f"dead={len(sv['dead'])} SoC={sv['mean_final_soc']:.4f}")


def analyze_edge(tag, r):
    rows = [x for x in r["rows"] if x["kind"] == "routine"]
    # 升级段密义务中，release 在降级点前 30min 内（deadline=release+600 可能跨 h30）
    edge = [x for x in rows if H30 - 1800 <= x["release_at"] < H30]
    # 以及降级点后 30min 内（应为疏义务，作对照）
    after = [x for x in rows if H30 <= x["release_at"] < H30 + 1800]

    def cls(x):
        if x["censored"]:
            return "cens"
        if x["delivered"]:
            return "deliv"
        if not x["collected"]:
            return "missColl"
        if x["first_heard_at"] is None:
            return "stuck_node"      # 采到但从未到网关
        if not x["received_on_time"]:
            return "stuck_gw"        # 到网关但未按时到中心
        return "other"
    from collections import Counter
    ce = Counter(cls(x) for x in edge)
    ca = Counter(cls(x) for x in after)
    print(f"\n[{tag}] 降级前最后30min密义务 n={len(edge)}: {dict(ce)}")
    print(f"[{tag}] 降级后首30min义务     n={len(after)}: {dict(ca)}")
    # 卡在节点的明细
    stuck = [x for x in edge if cls(x) == "stuck_node"]
    for x in stuck[:8]:
        print(f"   node={x['node_id']} rel={x['release_at']} dl={x['deadline']} "
              f"heard={x['first_heard_at']} recv={x['first_received_at']} "
              f"nMatch={x['n_matching']} nHeard={x['n_heard']}")
    # 整个升级段按"卡点"统计
    up = [x for x in rows if H6 <= x["release_at"] < H30 and not x["censored"]]
    cu = Counter(cls(x) for x in up)
    print(f"[{tag}] 整个升级段(h6-30) n={len(up)}: {dict(cu)}")


for sched, tag in [(UP_DOWN, "UP_DOWN"), (UP_ONLY, "UP_ONLY")]:
    r, inst, obs = run(sched)
    summ(tag, r)
    analyze_edge(tag, r)
    # 降级后节点实际上报/采样周期（取一个普通节点 n00 的 trace state 末段）
    states = [(t, iv, rp, soc, alive) for (t, nid, k, iv, rp, soc, alive)
              in inst.trace_events if k == "state" and nid == "n00"]
    late = [s for s in states if s[0] >= H30 - 1800]
    if late:
        seq = sorted(set((iv, rp) for (_t, iv, rp, _s, _a) in late))
        print(f"[{tag}] n00 降级点后(采样,上报)档位集合: {seq}")
    print("")
