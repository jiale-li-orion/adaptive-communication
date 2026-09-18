# -*- coding: utf-8 -*-
"""r33 — E1 核心: 中心编制时刻(h6)乐观可行性分配, 小时级提前的确定性回传墙证书。
动机(r32): 任务表 h20 才穿过中断到网关, 现场对 h6-20 已死义务只能到达当刻回溯归因(100%段准确但提前量为负)。
小时级提前量只能在**编制侧**获得: 中心 h6 编制升级任务时掌握完整义务表 + 网络侧中断(h4-20) + 公开备份节拍。
方法(乐观模型, doc33 S7.2): 乐观假设采样/接入总能在窗起点 lo 把样本送到网关(隔离回传墙, 最有利于可行),
只对"连乐观也无法在 deadline 前装入备份容量"的义务发不可能证书:
  * 窗口 [lo,dl=lo+600] 内无 r1200 备份槽 -> S_time(槽稀于交付窗, 确定性);
  * 有槽但按字节 EDF 最早可行槽装填仍装不下(中断期跨节点共享 58B/槽) -> S_cap(容量竞争, 确定性)。
EDF 最早可行槽对单位作业是严格最优可行性判定; 变字节(6/4B)为乐观贪心, 装不下则在线 maxcov(信息更少)更装不下。
对照终局 r31 段: 证书精度/段准确/召回/假阳、提前量(dl-h6); guaranteed(乐观可装)中实际交付比例(暴露能量墙)。
零 LLM, 只读, 不改控制。
"""
import os, sys, math
_HERE = os.path.dirname(os.path.abspath(__file__)); _CODE = os.path.dirname(_HERE)
for p in [_HERE, _CODE] + [os.path.join(_CODE, d) for d in
        ("physics", "runtime", "experiments", "analysis", "monitoring", "instance")]:
    if p not in sys.path:
        sys.path.insert(0, p)
from collections import defaultdict, Counter
from exogenous import KIND_ROUTINE
from joint_run import run_joint

UP_ONLY = [(0, 600, "blue"), (6 * 3600, 300, "yellow")]
RATE, CAP, HDR = 1200, 78, 20
PAYLOAD = CAP - HDR                       # 58 B
SBYTES = {"displacement": 6, "rainfall": 4}
OUT_LO, OUT_HI = 4 * 3600, 20 * 3600
H6 = 6 * 3600


def opt_slot(o, ready):
    tt = ready
    while tt <= o.deadline:
        h = tt // 3600 * 3600
        if not (OUT_LO <= tt < OUT_HI):
            return ("primary", tt)
        c = math.ceil(tt / RATE) * RATE
        if c <= o.deadline and OUT_LO <= c < OUT_HI:
            return ("backup", c)
        tt = h + 3600
    return None


def main():
    r, inst, obligations = run_joint(
        seed=0, task_hours=48, tail_hours=1, arm="local", groups=2,
        sample_interval_s=600, report_period_s=600, routine_period_s=600,
        harvest_mode="solar", harvest_peak_wh_per_hour=0.03, capacity_wh=0.05,
        initial_soc=1.0, outage_start_h=4, outage_hours=16, enable_backup=True,
        backup_rate_s=RATE, backup_bytes=CAP, backup_chooser="maxcov",
        mission_schedule=UP_ONLY, mission_mode="dayfeed", collect_rows=True)
    rows = {x["oid"]: x for x in r["rows"] if x["kind"] == "routine"}

    def gt_seg(o, x):
        if x["delivered"]:
            return "delivered"
        if opt_slot(o, o.window[0]) is None:
            return "S_time"
        if not x["collected"]:
            return "S_energy"
        if x["first_heard_at"] is None:
            return "S_access"
        return "S_cap"

    # 中断期、deadline<20h 的升级(h6起) routine 义务 = h6 编译时回传墙证书对象
    jobs = []
    gt = {}
    for o in obligations.obligations:
        if o.kind != KIND_ROUTINE or o.release_at < H6 or o.deadline > OUT_HI:
            continue
        x = rows.get(o.oid)
        if x is None or x["censored"]:
            continue
        gt[o.oid] = gt_seg(o, x)
        jobs.append(o)

    # 中断期备份槽(从 epoch 对齐 r1200), 每槽 PAYLOAD 字节
    slots = [c for c in range(0, OUT_HI, RATE) if OUT_LO <= c < OUT_HI]
    rem = {c: PAYLOAD for c in slots}

    def slots_in(lo, dl):
        return [c for c in slots if lo <= c <= dl]

    cert, guaranteed = {}, {}
    for o in sorted(jobs, key=lambda o: (o.deadline, o.window[0])):
        b = SBYTES.get(o.measurand, 6)
        cand = slots_in(o.window[0], o.deadline)
        if not cand:
            cert[o.oid] = "S_time"; continue
        target = None
        for c in cand:                    # EDF 最早可行槽
            if rem[c] >= b:
                target = c; break
        if target is None:
            cert[o.oid] = "S_cap"
        else:
            rem[target] -= b
            guaranteed[o.oid] = target

    # ===== 评估 =====
    n = len(jobs)
    fail = [oid for oid, g in gt.items() if g != "delivered"]
    print(f"== r33 h6 编制时乐观可行性分配 (中断期升级义务 n={n}, 终局失约 {len(fail)}) ==")
    print("终局段:", dict(Counter(gt.values())))
    print(f"备份槽数 {len(slots)}, 每槽 {PAYLOAD}B; h6 乐观装填: guaranteed={len(guaranteed)}, "
          f"证书 S_time={sum(1 for v in cert.values() if v=='S_time')}, "
          f"S_cap={sum(1 for v in cert.values() if v=='S_cap')}")

    # 证书质量
    tp = [(oid, s) for oid, s in cert.items() if gt[oid] != "delivered"]
    fp = [(oid, s) for oid, s in cert.items() if gt[oid] == "delivered"]
    seg_ok = sum(1 for oid, s in tp if s == gt[oid])
    print(f"\n[证书] 发证 {len(cert)}: 真失约 {len(tp)}、假阳(发证却交付) {len(fp)}; "
          f"精度 {len(tp)/max(1,len(cert)):.3f}; 段定位准确 {seg_ok}/{len(tp)}="
          f"{seg_ok/max(1,len(tp)):.3f}")
    # 段混淆
    conf = Counter((s, gt[oid]) for oid, s in cert.items())
    print("  混淆(证->真值):", {f"{a}->{b}": k for (a, b), k in sorted(conf.items())})
    recalled = set(oid for oid, _ in tp)
    print(f"  召回(中断期失约被 h6 发证覆盖) {len(recalled)}/{len(fail)}="
          f"{len(recalled)/len(fail):.3f}")
    miss = Counter(gt[oid] for oid in fail if oid not in recalled)
    print(f"  未发证的失约(乐观能量假设隔离, 留现场/能量证书): {dict(miss)}")
    # 提前量
    dl_of = {o.oid: o.deadline for o in jobs}
    import statistics
    leads = [dl_of[oid] - H6 for oid in cert]
    print(f"  提前量(deadline-h6): min/中位/max = {min(leads)}/{int(statistics.median(leads))}/"
          f"{max(leads)} s = {min(leads)/3600:.1f}/{statistics.median(leads)/3600:.1f}/"
          f"{max(leads)/3600:.1f} h")
    # guaranteed 中实际交付比例(乐观回传可行, 但能量/接入可能仍失败)
    g_del = sum(1 for oid in guaranteed if gt[oid] == "delivered")
    g_fail = Counter(gt[oid] for oid in guaranteed if gt[oid] != "delivered")
    print(f"\n[guaranteed] 乐观可装 {len(guaranteed)}: 实际交付 {g_del} "
          f"({g_del/max(1,len(guaranteed)):.3f}); 仍失约段 {dict(g_fail)}")
    print("  -> guaranteed 回传可行但能量/接入失败的比例, 说明能量墙须由现场/保守证书兜底")


if __name__ == "__main__":
    main()
