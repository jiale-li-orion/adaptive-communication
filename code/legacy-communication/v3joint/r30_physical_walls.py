# -*- coding: utf-8 -*-
"""r30 — 物理墙三段分解（零 LLM，主口径 UP_ONLY h6 升 300，seed0）。
四个反事实，逐义务(oid)集合对齐：
  base   : dayfeed 采样 + 稀缺备份(r1200/78B,maxcov)        =.4001 现状
  O_bh   : dayfeed 采样 + 无限回传(每tick巨包必达)           放宽回传段,隔离缺采/接入墙
  O_en   : comply 全程300 + 无限采能(peak=1) + 稀缺回传       放宽能量/采样段,隔离回传墙
  O_bo   : comply 全程300 + 无限采能 + 无限回传              双放宽,义务结构上界
集合分解:
  回传墙可救 = S_bh-S0 ; 能量墙可救 = S_en-S0 ;
  双墙耦合   = S_bo-(S_bh∪S_en) (单放宽任一段都救不了, 必须同时) -> 潜在联合套利;
  结构不可行 = 全集-S_bo。
"""
import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__)); _CODE = os.path.dirname(_HERE)
for p in [_HERE, _CODE] + [os.path.join(_CODE, d) for d in
        ("physics", "runtime", "experiments", "analysis", "monitoring", "instance")]:
    if p not in sys.path:
        sys.path.insert(0, p)
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


def run(tag, mode, peak, bk_rate, bk_bytes, p_succ):
    r, _i, _o = run_joint(collect_rows=True, mission_mode=mode,
        harvest_mode="solar", harvest_peak_wh_per_hour=peak,
        backup_rate_s=bk_rate, backup_bytes=bk_bytes, backup_chooser="maxcov",
        backup_p_succ=p_succ, **COMMON)
    rows = [x for x in r["rows"] if x["kind"] == "routine"]
    from collections import Counter
    c = Counter(cls(x) for x in rows)
    dlv = {x["oid"] for x in rows if x["delivered"]}
    n = r["routine"]["n"]
    print(f"{tag:6s} svc={len(dlv)/n:.4f} deliv={len(dlv)} n={n} {dict(c)}")
    return dlv, rows, n


print("== 主口径物理墙分解 (UP_ONLY, seed0, 48h) ==")
S0, R0, N = run("base", "dayfeed", 0.03, 1200, 78, 1.0)
Sbh, Rbh, _ = run("O_bh", "dayfeed", 0.03, 60, 100000, 1.0)
Sen, Ren, _ = run("O_en", "comply", 1.0, 1200, 78, 1.0)
Sbo, Rbo, _ = run("O_bo", "comply", 1.0, 60, 100000, 1.0)

allids = {x["oid"] for x in R0}
only_bh = Sbh - S0
only_en = Sen - S0
union = Sbh | Sen
coupled = Sbo - union
struct = allids - Sbo
print("\n== 逐义务集合分解（相对 base 多交付的义务数）==")
print(f"base 已交付                         : {len(S0)}  ({len(S0)/N:.3f})")
print(f"仅放宽回传可救 (回传/容量墙)         : {len(only_bh)}")
print(f"仅放宽能量可救 (能量/采样墙)         : {len(only_en)}")
print(f"双墙耦合 (单放宽都不行,需同时)       : {len(coupled)}  <- 潜在联合套利上界")
print(f"结构不可行 (双放宽仍失约)            : {len(struct)}")
# base 失约义务在 O_bh 下仍失约 = 缺采/接入墙（放宽回传无用）
base_fail = allids - S0
print(f"\nbase 失约总数                       : {len(base_fail)}")
print(f"  其中放宽回传仍失约(缺采/接入墙)    : {len(base_fail - Sbh)}")
print(f"  其中放宽能量仍失约(回传墙)         : {len(base_fail - Sen)}")
print(f"  双放宽仍失约(结构)                 : {len(base_fail & struct)}")
# 双墙耦合义务的时间分布（按 release 小时）与节点，判断是否可合法择时
if coupled:
    relh = {}
    for x in Rbo:
        if x["oid"] in coupled:
            relh[x["release_at"] // 3600] = relh.get(x["release_at"] // 3600, 0) + 1
    print(f"\n双墙耦合义务按 release 小时分布: {dict(sorted(relh.items()))}")
