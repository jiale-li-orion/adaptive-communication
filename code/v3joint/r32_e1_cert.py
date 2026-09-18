# -*- coding: utf-8 -*-
"""r32 — E1 可行性投影器声明质量(第一版, 确定性证书, 零 LLM), 干净重写。
场景 UP_ONLY(h6 升300), 任务表随主回传 h20 才到网关; 备份 r1200/78; 主路中断 h4-20。
严格按 t 截断现场网关合法可见(taken/heard/received<=t); 义务在 mission gate 到达(ka)后可知。
两类确定性证书(只读):
  C_nosample 窗已过(hi<t)仍无合格 taken 样本 -> S_energy(采不到, 不可逆);
  C_time     ka 后、deadline 前, 剩余 [t,deadline] 全在中断且无 r1200 槽 -> S_time(乐观也无回传时刻)。
任务表延迟到达(ka>=deadline)的义务: 到达当刻用确定性规则做段归因(S_time/S_cap/S_energy/S_access)。
对照 r31 ground-truth 段, 报告精度/召回/段准确率/提前量/假阳/即到归因准确率。
S_cap 容量竞争预测与夜间能量概率预测留第二版(给大提前量)。
"""
import os, sys, math, statistics
_HERE = os.path.dirname(os.path.abspath(__file__)); _CODE = os.path.dirname(_HERE)
for p in [_HERE, _CODE] + [os.path.join(_CODE, d) for d in
        ("physics", "runtime", "experiments", "analysis", "monitoring", "instance")]:
    if p not in sys.path:
        sys.path.insert(0, p)
from collections import defaultdict, Counter
from exogenous import KIND_ROUTINE
from joint_run import run_joint

UP_ONLY = [(0, 600, "blue"), (6 * 3600, 300, "yellow")]
RATE = 1200
OUT_LO, OUT_HI = 4 * 3600, 20 * 3600
STEP = 600


def optimistic_slot(o, ready):
    """[ready,deadline] 内最早乐观回传时刻: 主路开 tick 或中断期 r1200 槽; None=乐观也不可行。"""
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
        backup_rate_s=RATE, backup_bytes=78, backup_chooser="maxcov",
        mission_schedule=UP_ONLY, mission_mode="dayfeed", collect_rows=True)
    seg_gw = {s["level"]: s["gateway_received_at"] for s in r.get("mission_timing", [])}
    upgrade_gw = seg_gw.get("yellow", 0)

    by_nm = defaultdict(list)
    for s in inst.log.samples.values():
        by_nm[(s.node_id, s.measurand)].append(s)
    for k in by_nm:
        by_nm[k].sort(key=lambda s: s.taken_at)
    heard_of = {sid: tr.heard_at for sid, tr in inst.log.transit.items()}
    recv_of = {sid: tr.received_at for sid, tr in inst.log.transit.items()}

    rows = {x["oid"]: x for x in r["rows"] if x["kind"] == "routine"}

    def gt_seg(o, x):
        if x["delivered"]:
            return "delivered"
        if optimistic_slot(o, o.window[0]) is None:
            return "S_time"
        if not x["collected"]:
            return "S_energy"
        if x["first_heard_at"] is None:
            return "S_access"
        return "S_cap"

    def visible(o, t):
        """<=t 可见的匹配样本: 返回 (delivered_at, heard_at, taken_at) 最早者。"""
        d = h = tk = None
        for s in by_nm.get((o.node_id, o.measurand), []):
            if s.taken_at > t + o.tolerance_s:
                break
            if not o.matches(s):
                continue
            if s.taken_at <= t:
                tk = s.taken_at if tk is None else min(tk, s.taken_at)
            hv = heard_of.get(s.sample_id)
            if hv is not None and hv <= t:
                h = hv if h is None else min(h, hv)
            rv = recv_of.get(s.sample_id)
            if rv is not None and rv <= t:
                d = rv if d is None else min(d, rv)
        return d, h, tk

    certs = {}          # oid -> (cert_t, seg, ka)
    gt, ka_of, dl_of = {}, {}, {}
    retro_truth = Counter(); retro_correct = 0; retro_total = 0
    for o in obligations.obligations:
        if o.kind != KIND_ROUTINE:
            continue
        x = rows.get(o.oid)
        if x is None or x["censored"]:
            continue
        g = gt_seg(o, x); gt[o.oid] = g
        ka = 0 if o.release_at < 6 * 3600 else upgrade_gw
        ka_of[o.oid] = ka; dl_of[o.oid] = o.deadline

        # --- 任务表延迟到达: deadline 已过, 用网关本地完整日志(heard/转发/节点报告)回溯段归因 ---
        if ka >= o.deadline:
            ms = [s for s in by_nm.get((o.node_id, o.measurand), [])
                  if s.taken_at <= ka and o.matches(s)]
            on_time = [s for s in ms if (recv_of.get(s.sample_id) is not None
                                         and recv_of[s.sample_id] <= o.deadline)]
            heard_any = [s for s in ms if heard_of.get(s.sample_id) is not None]
            if on_time:
                seg = "delivered"
            elif optimistic_slot(o, o.window[0]) is None:
                seg = "S_time"      # deadline 前乐观也无回传时刻(备份槽稀于交付窗)
            elif heard_any:
                seg = "S_cap"       # 到网关了, 容量/拥塞没按时送出
            elif ms:
                seg = "S_access"    # 采到但从未到网关
            else:
                seg = "S_energy"    # 窗内无采样(节点状态报告可佐证)
            certs[o.oid] = (ka, seg, ka)
            if g != "delivered":
                retro_total += 1; retro_truth[g] += 1
                if seg == g:
                    retro_correct += 1
            continue

        # --- deadline 前滚动, 找首个确定性提前证书 ---
        t = ((max(ka, 0) + STEP - 1) // STEP) * STEP
        while t < o.deadline:
            d, h, tk = visible(o, t)
            if d is not None:
                break                                  # 已交付
            if o.window[1] < t and tk is None:
                certs[o.oid] = (t, "S_energy", ka); break      # 窗过无样本, 不可逆
            # 最早就绪: 已有样本 heard->t; taken 未 heard->+600; 未采->乐观窗内采+600
            if h is not None:
                ready = t
            elif tk is not None:
                ready = t + 600
            else:
                ready = t + 600
            # 剩余到 deadline 全在中断且无槽 -> S_time
            if t >= OUT_LO and o.deadline <= OUT_HI and optimistic_slot(o, max(ready, t)) is None:
                certs[o.oid] = (t, "S_time", ka); break
            t += STEP

    # ===== 评估 =====
    fail = [oid for oid, g in gt.items() if g != "delivered"]
    print(f"== r32 E1 投影器声明质量 (n={len(gt)}, 失约 {len(fail)}) ==")
    print("ground-truth 段:", dict(Counter(gt.values())))
    print(f"\n[回溯归因] 任务表到达时 deadline 已过义务 n={retro_total}, "
          f"当刻段归因正确 {retro_correct} ({retro_correct/max(1,retro_total):.3f}); "
          f"真值段 {dict(retro_truth)}")

    # 提前证书(deadline 前)
    early = {oid: c for oid, c in certs.items() if c[0] < dl_of[oid] and c[1] != "delivered"}
    tp = [(oid, c) for oid, c in early.items() if gt[oid] != "delivered"]
    fp = [(oid, c) for oid, c in early.items() if gt[oid] == "delivered"]
    recalled = set(oid for oid, _ in tp)
    print(f"\n[提前证书] deadline 前发证 n={len(early)}; 真失约 {len(tp)}、假阳 {len(fp)}")
    seg_ok = Counter(); seg_bad = Counter(); leads = defaultdict(list)
    for oid, (ct, seg, ka) in tp:
        leads[seg].append(dl_of[oid] - ct)
        if seg == gt[oid]:
            seg_ok[seg] += 1
        else:
            seg_bad[seg] += 1
    for seg in ("S_time", "S_energy", "S_cap"):
        n = seg_ok[seg] + seg_bad[seg]
        if n:
            ls = leads[seg]
            print(f"  {seg}: 证 {n} 段正确 {seg_ok[seg]} 段错 {seg_bad[seg]}; "
                  f"提前量 min/中位/max={min(ls)}/{int(statistics.median(ls))}/{max(ls)}s")
    print(f"  提前证书覆盖失约义务 {len(recalled)}/{len(fail)} = {len(recalled)/len(fail):.3f}")
    print(f"  假阳(发失约证但最终交付) {len(fp)}")
    # 未被任何提前证书覆盖、也非回溯的失约 = 第二版要靠容量/能量预测的
    covered = set(recalled) | {oid for oid, c in certs.items()
                               if gt[oid] != "delivered" and c[0] >= dl_of[oid]}
    gap = [oid for oid in fail if oid not in covered]
    print(f"  尚未提前覆盖(待第二版容量/能量预测) n={len(gap)}, 段 {dict(Counter(gt[o] for o in gap))}")


if __name__ == "__main__":
    main()
