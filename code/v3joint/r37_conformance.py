# -*- coding: utf-8 -*-
"""r37 — E2 承诺-兑现一致性(conformance)端到端记账, 零 LLM, 只读(不改控制/默认值)。

问题(doc43 §6 开放项): 物理吞吐增量已被对称上界关闭, 论文主张是"承诺-执行一致"。
此前只有侧证(r35 45.6% 过期备份、r36 命令风暴停止), 缺一条完整 promise-vs-fulfillment 数字。

本脚本在同一主口径(seed0/14节点/cap.05/中断h4-20/备份r1200-78/UP_ONLY h6升300/任务表h20到网关)下:
  编制侧(中心 h6, 中断期升级义务 n≈2338):
    P0 naive 编制: 无证书, 默认承诺全部升级义务可按黄级完成 -> 承诺 precision = 终局on-time/承诺数;
    P1 结构证书 : 仅对"窗内无任何备份槽"的义务发确定性不可行证(S_time), 其余标"不能保证"(不正向承诺)。
  现场侧(网关备份选包, 端到端真实 run 对照, 非离线循环):
    maxcov  : 现行强基线, 槽有空闲用积压(含已过期)样本补满 -> 它"隐式承诺"了每条发出的记录可按期交付;
    salvage : 证书感知的普通确定性打包器(已在 joint_plane): dl<=t 的过期样本不占包位、积压全过期则空包不发。
    两 chooser 同参数各跑一次 run_joint, 报: 全时段服务、中断期 delivered、备份包/记录/字节、
    中断期经备份 received 的 on-time/过期(同一上帝黄级 deadline 口径)、抑制数。
口径诚实: 中断期网关合法只知蓝级600节奏(任务表h20才到); r35/r37 的 on-time/过期用黄级300义务的
上帝 deadline 仅用于事后资费/承诺核算, 不假装现场当时可知。
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
RATE, CAP = 1200, 78
OUT_LO, OUT_HI = 4 * 3600, 20 * 3600
H6 = 6 * 3600
SBYTES = {"displacement": 6, "rainfall": 4}

COMMON = dict(seed=0, task_hours=48, tail_hours=1, arm="local", groups=2,
              sample_interval_s=600, report_period_s=600, routine_period_s=600,
              harvest_mode="solar", harvest_peak_wh_per_hour=0.03, capacity_wh=0.05,
              initial_soc=1.0, outage_start_h=4, outage_hours=16, enable_backup=True,
              backup_rate_s=RATE, backup_bytes=CAP,
              mission_schedule=UP_ONLY, mission_mode="dayfeed", collect_rows=True)


def deadline_of(taken):
    P = 300 if taken >= H6 else 600
    return (taken // P + 2) * P


def opt_slot(o, ready):
    """与 r33 同一乐观回传时刻判定(主路开 tick 或中断期 r1200 槽); None=乐观也不可行。"""
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


def run_one(chooser):
    return run_joint(backup_chooser=chooser, **COMMON)


def audit(tag, r, inst, obligations):
    rows = {x["oid"]: x for x in r["rows"] if x["kind"] == "routine"}
    # 全时段服务
    allr = [x for x in r["rows"] if x["kind"] == "routine" and not x["censored"]]
    svc = sum(1 for x in allr if x["delivered"]) / len(allr)
    dead = r.get("survival", {}).get("dead", 0)
    # 中断期升级义务
    jobs = [o for o in obligations.obligations
            if o.kind == KIND_ROUTINE and o.release_at >= H6 and o.deadline <= OUT_HI
            and o.oid in rows and not rows[o.oid]["censored"]]
    n = len(jobs)
    d = sum(1 for o in jobs if rows[o.oid]["delivered"])
    # 中断期经备份 received: on-time / 过期(上帝黄级 deadline 口径)
    on = late = 0; onb = lateb = 0
    for sid, sx in inst.log.samples.items():
        tr = inst.log.transit.get(sid)
        if tr is None or tr.received_at is None:
            continue
        if OUT_LO <= tr.received_at < OUT_HI:
            b = SBYTES.get(sx.measurand, 6)
            dl = deadline_of(sx.taken_at)
            if tr.received_at <= dl:
                on += 1; onb += b
            else:
                late += 1; lateb += b
    tot = on + late
    bk = r["backup"]
    print(f"\n----- [{tag}] chooser={bk['backup_chooser']} -----")
    print(f"全时段 svc={svc:.4f} (delivered {sum(1 for x in allr if x['delivered'])}/{len(allr)}), dead={dead}")
    print(f"中断期升级义务 n={n}, on-time delivered={d} ({d/max(1,n):.3f})")
    print(f"备份: packets={bk['backup_packets']} records={bk['backup_records']} "
          f"bytes={bk['backup_bytes_sent']} suppressed={bk['backup_suppressed']} "
          f"local_purge={bk.get('backup_local_purge', 0)}")
    print(f"中断期经备份 received={tot}: on-time={on}({onb}B) 过期={late}({lateb}B); "
          f"发送承诺precision(on-time/发出)={on/max(1,tot):.3f}, 过期率={late/max(1,tot):.3f}")
    return dict(svc=svc, dead=dead, n=n, d=d, on=on, late=late, onb=onb, lateb=lateb,
                packets=bk["backup_packets"], records=bk["backup_records"],
                bytes=bk["backup_bytes_sent"], suppressed=bk["backup_suppressed"],
                local_purge=bk.get("backup_local_purge", 0),
                rows=rows, jobs=jobs)


def main():
    print("== r37 E2 承诺-兑现 conformance (同主口径, maxcov vs salvage, 零 LLM) ==")
    rm, im, om = run_one("maxcov")
    A = audit("现场基线 maxcov", rm, im, om)
    rs, ins, os_ = run_one("salvage")
    B = audit("朴素抑制 salvage", rs, ins, os_)
    rc, ic, oc = run_one("maxcov_ontime")
    C = audit("证书感知 maxcov_ontime", rc, ic, oc)
    rp, ip, op2 = run_one("cert_purge")
    D = audit("完整证书 cert_purge(停发+本地核销)", rp, ip, op2)

    rows, jobs = A["rows"], A["jobs"]
    slots = [c for c in range(0, OUT_HI, RATE) if OUT_LO <= c < OUT_HI]

    def slots_in(o):
        return [c for c in slots if o.window[0] <= c <= o.deadline]

    n = len(jobs)
    delivered = {o.oid for o in jobs if rows[o.oid]["delivered"]}
    # P0 naive: 承诺全部
    p0_prec = len(delivered) / n
    # P1 结构 S_time 不可行证
    cert_st = [o for o in jobs if not slots_in(o)]
    cert_fail = [o for o in cert_st if o.oid not in delivered]
    true_st = [o for o in jobs if o.oid not in delivered and opt_slot(o, o.window[0]) is None]
    print("\n===== 编制侧(h6)承诺 conformance, 中断期升级义务 =====")
    print(f"义务 n={n}, 终局 on-time delivered={len(delivered)} ({len(delivered)/n:.3f}), 失约={n-len(delivered)}")
    print(f"P0 naive 全承诺: 承诺 {n}, 兑现 {len(delivered)}, 承诺 precision={p0_prec:.3f}, "
          f"过度承诺(声称会做却失约)={n-len(delivered)}")
    print(f"P1 结构不可行证 S_time: 发证 {len(cert_st)}, 终局全失约 {len(cert_fail)} "
          f"(precision={len(cert_fail)/max(1,len(cert_st)):.3f}); "
          f"真 S_time={len(true_st)}, 召回={len(set(o.oid for o in cert_st)&set(o.oid for o in true_st))/max(1,len(true_st)):.3f}, "
          f"假阳(发证却交付)={len(cert_st)-len(cert_fail)}; 其余 {n-len(cert_st)} 标'不能保证/best-effort'(不正向承诺)")

    def prec(Z):
        return Z["on"] / max(1, Z["on"] + Z["late"])

    print("\n===== 现场侧端到端对照 (四档, 同参数同 seed) =====")
    hdr = f"{'chooser':<16}{'svc':>8}{'中断deliv':>10}{'备份on':>8}{'过期':>6}{'包':>5}{'字节':>7}{'核销':>6}{'承诺prec':>9}"
    print(hdr)
    for tag, Z in (("maxcov", A), ("salvage", B), ("maxcov_ontime", C), ("cert_purge", D)):
        print(f"{tag:<16}{Z['svc']:>8.4f}{Z['d']:>10}{Z['on']:>8}{Z['late']:>6}"
              f"{Z['packets']:>5}{Z['bytes']:>7}{Z['local_purge']:>6}{prec(Z):>9.3f}")
    print("\n-- 关键对比: maxcov(强基线) -> maxcov_ontime(只停阶段2过期补满, 阶段1逐位相同) --")
    print(f"中断期 on-time delivered: {A['d']} -> {C['d']} (Δ={C['d']-A['d']}; 朴素抑制的接入段代价)")
    print(f"全时段 svc: {A['svc']:.4f} -> {C['svc']:.4f} (Δ={C['svc']-A['svc']:+.4f}), dead {A['dead']}->{C['dead']}")
    print(f"过期(无效)发送: {A['late']} -> {C['late']} (抑制 {A['late']-C['late']}, "
          f"过期字节 {A['lateb']}B -> {C['lateb']}B)")
    print(f"备份字节: {A['bytes']}B -> {C['bytes']}B (省 {A['bytes']-C['bytes']}B, "
          f"{(A['bytes']-C['bytes'])/max(1,A['bytes'])*100:.1f}%), 包 {A['packets']} -> {C['packets']}")
    print(f"发送承诺 precision: {prec(A):.3f} -> {prec(C):.3f}")
    print(f"[对照] 朴素 salvage: on-time {A['d']}->{B['d']} (Δ={B['d']-A['d']}), "
          f"说明任务表未到时激进冗余抑制/义务口径错位会误杀可交付样本; "
          f"maxcov_ontime 不动阶段1故无此损失")
    print("\n-- 完整证书 cert_purge(不发过期 + 网关本地核销确定失约样本, 释放节点 FIFO 重传) --")
    print(f"中断期 on-time delivered: {A['d']} -> {D['d']} (Δ={D['d']-A['d']}; 目标=0: 省资费且不损服务)")
    print(f"全时段 svc: {A['svc']:.4f} -> {D['svc']:.4f} (Δ={D['svc']-A['svc']:+.4f}), dead {A['dead']}->{D['dead']}")
    print(f"过期发送: {A['late']} -> {D['late']}; 备份字节 {A['bytes']}B -> {D['bytes']}B "
          f"(省 {(A['bytes']-D['bytes'])/max(1,A['bytes'])*100:.1f}%); 本地核销 {D['local_purge']} 条(不占资费)")
    print(f"发送承诺 precision: {prec(A):.3f} -> {prec(D):.3f}")


if __name__ == "__main__":
    main()
