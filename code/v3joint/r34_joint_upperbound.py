# -*- coding: utf-8 -*-
"""r34 — 固定资源联合最优上界收尾对表(中断期 h6-20 升级义务), 回应 doc38 "完整联合 MPC 未做"。
r33 离线 h6 全知 EDF 回传装填给 guaranteed=420(乐观假设窗起点即供样、忽略能量), 实测 dayfeed 仅交付 9。
本脚本对同一中断期义务集(release>=h6, deadline<=h20)比较:
  base : dayfeed cap.05 r1200/78                      现状(持续配置+能量墙+备份容量)
  O_en : comply cap.50 r1200/78  (移除能量墙, 全程300密采不死亡, 备份容量不变) -> 回传+供样实际上界
  O_bo : comply cap.50 备份无限(60/1e5)               双放宽结构上界(只剩 S_time 无槽)
  EDF  : r33 离线 h6 全知回传装填 guaranteed 数(乐观供样, 无能量约束)
判读:
  * O_en 中断期交付 ≈ EDF(420) -> r33 回传装填真实, dayfeed 的 420->9 差距全在能量/持续配置(doc41 已关闭);
  * O_en << EDF               -> r33 离线装填过乐观(接入/打包时机), S_cap 证书须按 O_en 收紧;
  * O_bo 交付 ≈ 有槽义务数      -> S_time 无槽是唯一结构性硬墙(588 确定性证书坐实)。
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
RATE, CAP, HDR = 1200, 78, 20
PAYLOAD = CAP - HDR
SBYTES = {"displacement": 6, "rainfall": 4}
OUT_LO, OUT_HI, H6 = 4 * 3600, 20 * 3600, 6 * 3600
COMMON = dict(seed=0, task_hours=48, tail_hours=1, arm="local", groups=2,
              sample_interval_s=600, report_period_s=600, routine_period_s=600,
              initial_soc=1.0, outage_start_h=4, outage_hours=16, enable_backup=True,
              mission_schedule=UP_ONLY, harvest_mode="solar")


def interrupt_rows(r, obligations):
    """中断期 h6-20 升级 routine 义务的 rows(按 oid), 及义务对象。"""
    omap = {o.oid: o for o in obligations.obligations
            if o.kind == KIND_ROUTINE and o.release_at >= H6 and o.deadline <= OUT_HI}
    out = {x["oid"]: x for x in r["rows"]
           if x["kind"] == "routine" and x["oid"] in omap and not x["censored"]}
    return omap, out


def run(tag, mode, cap, bk_rate, bk_bytes):
    r, _i, ob = run_joint(collect_rows=True, mission_mode=mode, capacity_wh=cap,
                          harvest_peak_wh_per_hour=0.03, backup_rate_s=bk_rate,
                          backup_bytes=bk_bytes, backup_chooser="maxcov",
                          backup_p_succ=1.0, **COMMON)
    omap, rows = interrupt_rows(r, ob)
    dlv = {oid for oid, x in rows.items() if x["delivered"]}
    heard = {oid for oid, x in rows.items() if x["first_heard_at"] is not None}
    coll = {oid for oid, x in rows.items() if x["collected"]}
    print(f"{tag:5s} 中断期义务 n={len(rows)} delivered={len(dlv)} "
          f"heard={len(heard)} collected={len(coll)} dead={len(r['survival']['dead'])}")
    return omap, rows, dlv


# 三组
om0, R0, D0 = run("base", "dayfeed", 0.05, RATE, CAP)
_, Re, De = run("O_en", "comply", 0.50, RATE, CAP)
_, Rbo, Dbo = run("O_bo", "comply", 0.50, 60, 100000)

# r33 离线 EDF 回传装填(乐观供样, 无能量)
slots = [c for c in range(0, OUT_HI, RATE) if OUT_LO <= c < OUT_HI]
rem = {c: PAYLOAD for c in slots}
edf_guar, no_slot = set(), 0
for o in sorted(om0.values(), key=lambda o: (o.deadline, o.window[0])):
    b = SBYTES.get(o.measurand, 6)
    cand = [c for c in slots if o.window[0] <= c <= o.deadline]
    if not cand:
        no_slot += 1; continue
    tgt = next((c for c in cand if rem[c] >= b), None)
    if tgt is None:
        continue
    rem[tgt] -= b
    edf_guar.add(o.oid)

n = len(om0)
print(f"\n== 中断期联合上界对表 (n={n}) ==")
print(f"结构性无槽 S_time(确定性, r33): {no_slot}")
print(f"r33 离线 h6 全知 EDF 回传装填 guaranteed(乐观供样/无能量): {len(edf_guar)}")
print(f"base dayfeed 实际交付: {len(D0)}")
print(f"O_en 移除能量墙(cap.50 全程密采)、备份容量不变 实际交付: {len(De)}")
print(f"O_bo 双放宽(能量+回传) 实际交付: {len(Dbo)}")
print(f"\n解读:")
print(f"  EDF 装填中移除能量墙后能兑现: {len(edf_guar & De)}/{len(edf_guar)} "
      f"({len(edf_guar & De)/max(1,len(edf_guar)):.3f})")
print(f"  base->O_en 移除能量墙的增量(能量墙可改变空间): {len(De-D0)}")
print(f"  O_en->O_bo 增回传的增量(回传容量墙): {len(Dbo-De)}")
print(f"  双放宽仍未交付(结构性 S_time/接入): {n-len(Dbo)}")
# EDF 装填但 O_en 仍送不出 = 离线装填过乐观(接入/打包时机)
over = edf_guar - De
print(f"  EDF 说可装但 O_en 仍未交付(离线装填过乐观): {len(over)}")
