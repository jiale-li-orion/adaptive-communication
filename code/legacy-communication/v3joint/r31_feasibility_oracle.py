# -*- coding: utf-8 -*-
"""r31 — 义务级乐观可行性检验器（doc33 §7.2 乐观模型，零 LLM）。
对每条 routine 义务，沿 合格样本(采样)->到网关(接入)->截止前回传 求乐观可行解:
  采样段: 用 base 实际是否采到(collected)；另给"大电池必采到"的乐观标记。
  接入段: 乐观假设窗口内样本可即时到网关(单独用实测 first_heard 是否 null 监控接入墙)。
  回传段(纯时间结构, 乐观忽略包间竞争/随机丢包):
     [window_lo, deadline] 内是否存在
       主路 gate 开的 tick, 或 中断期 t%%rate==0 的备份槽(failover: 主路 down 才发备份)。
交叉表给出每条失约义务的段归因 ground truth(不可行证书应输出的标签):
  S_time  : 乐观也无回传时刻(备份频率 r1200 慢于义务交付窗; 需增频率/主路恢复)
  S_cap   : 有回传时刻、采到、到网关, 仍未交付(包容量/竞争, maxcov 已在固定容量最优)
  S_energy: 有回传时刻但没采到(能量/采样墙)
  S_access: 采到但从未到网关(接入墙)
"""
import os, sys, math
_HERE = os.path.dirname(os.path.abspath(__file__)); _CODE = os.path.dirname(_HERE)
for p in [_HERE, _CODE] + [os.path.join(_CODE, d) for d in
        ("physics", "runtime", "experiments", "analysis", "monitoring", "instance")]:
    if p not in sys.path:
        sys.path.insert(0, p)
from collections import Counter
from exogenous import KIND_ROUTINE
from joint_run import run_joint

UP_ONLY = [(0, 600, "blue"), (6 * 3600, 300, "yellow")]
RATE = 1200
OUT_LO, OUT_HI = 4, 20          # 主回传中断小时
TICK = 60


def gate_open(hour):
    return not (OUT_LO <= hour < OUT_HI)


def earliest_backhaul(o, rate=RATE):
    """乐观: 采样于 window 起点、即时接入; 返回 (window_lo,deadline] 内最早回传 (kind,t) 或 None。"""
    lo, hi = o.window[0], o.deadline
    t = lo
    # 先看是否落入主路开的小时
    tt = lo
    while tt <= hi:
        h = tt // 3600
        if gate_open(h):
            return ("primary", tt)
        # 该小时主路关: 找该小时内/之后第一个 rate 槽
        slot = math.ceil(tt / rate) * rate
        if slot <= hi and slot // 3600 == h:
            return ("backup", slot)
        # 跳到下一小时边界
        tt = (h + 1) * 3600
    return None


def main():
    r, inst, obligations = run_joint(
        seed=0, task_hours=48, tail_hours=1, arm="local", groups=2,
        sample_interval_s=600, report_period_s=600, routine_period_s=600,
        harvest_mode="solar", harvest_peak_wh_per_hour=0.03, capacity_wh=0.05,
        initial_soc=1.0, outage_start_h=4, outage_hours=16, enable_backup=True,
        backup_rate_s=RATE, backup_bytes=78, backup_chooser="maxcov",
        mission_schedule=UP_ONLY, mission_mode="dayfeed", collect_rows=True)
    rows = {x["oid"]: x for x in r["rows"] if x["kind"] == "routine"}
    seg = Counter()
    seg_by_hour = {}
    feasible_delivered = feasible_failed = 0
    for o in obligations.obligations:
        if o.kind != KIND_ROUTINE:
            continue
        x = rows.get(o.oid)
        if x is None:
            continue
        if x["censored"]:
            continue
        eb = earliest_backhaul(o)
        if x["delivered"]:
            seg["delivered"] += 1
            continue
        # 失约义务分段归因
        if eb is None:
            label = "S_time"          # 乐观也无回传时刻
        elif not x["collected"]:
            label = "S_energy"        # 有回传时刻但没采到
        elif x["first_heard_at"] is None:
            label = "S_access"        # 采到没到网关
        else:
            label = "S_cap"           # 时刻有、样本在网关, 仍未按时送(容量/竞争)
        seg[label] += 1
        h = o.release_at // 3600
        seg_by_hour.setdefault(h, Counter())[label] += 1
    n = sum(seg.values())
    print(f"== r31 义务级段归因 (UP_ONLY dayfeed r{RATE}/78, n={n}) ==")
    for k in ("delivered", "S_time", "S_cap", "S_energy", "S_access"):
        print(f"  {k:9s}: {seg.get(k,0):5d}  ({seg.get(k,0)/n:.3f})")
    print("\n失约段按 release 小时:")
    for h in sorted(seg_by_hour):
        print(f"  h{h:02d}: {dict(seg_by_hour[h])}")
    # 备份频率墙的纯量化: 中断窗内密义务(window/deadline=600) 中 [rel,dl] 无 r1200 槽的比例
    tot = no_slot = 0
    for o in obligations.obligations:
        if o.kind != KIND_ROUTINE:
            continue
        h = o.release_at // 3600
        if not (OUT_LO <= h < OUT_HI):
            continue
        tot += 1
        if earliest_backhaul(o) is None:
            no_slot += 1
    print(f"\n中断窗(h{OUT_LO}-{OUT_HI})义务 n={tot}, 乐观无回传时刻={no_slot} ({no_slot/tot:.3f})")


if __name__ == "__main__":
    main()
