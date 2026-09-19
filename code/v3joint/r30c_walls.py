# -*- coding: utf-8 -*-
"""r30c — 物理墙三段分解(正确松弛电池容量), 主口径 UP_ONLY h6 升300, seed0。
  base  : dayfeed cap.05 peak.03 备份r1200/78            现状
  O_bh  : dayfeed cap.05 peak.03 备份无限(60/100000)      隔离回传墙(采到送不出)
  O_en  : comply 全程300 cap.50 peak.03 备份r1200/78      正确放宽能量(大电池跨夜密采),隔离回传容量上限
  O_bo  : comply cap.50 peak.03 备份无限                  双放宽=结构上界
逐义务 oid 集合: 回传墙/能量墙/双墙耦合(需同时增电池+增回传)/结构不可行。"""
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
    mission_schedule=UP_ONLY, harvest_mode="solar")


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


def run(tag, mode, cap, peak, bk_rate, bk_bytes):
    r, _i, _o = run_joint(collect_rows=True, mission_mode=mode,
        capacity_wh=cap, harvest_peak_wh_per_hour=peak,
        backup_rate_s=bk_rate, backup_bytes=bk_bytes, backup_chooser="maxcov",
        backup_p_succ=1.0, **COMMON)
    rows = [x for x in r["rows"] if x["kind"] == "routine"]
    c = Counter(cls(x) for x in rows)
    dlv = {x["oid"] for x in rows if x["delivered"]}
    n = r["routine"]["n"]; nd = len(r["survival"]["dead"])
    print(f"{tag:6s} svc={len(dlv)/n:.4f} deliv={len(dlv)} dead={nd} n={n} {dict(c)}")
    return dlv, rows, n


print("== 物理墙分解(正确容量松弛) UP_ONLY seed0 ==")
S0, R0, N = run("base", "dayfeed", 0.05, 0.03, 1200, 78)
Sbh, Rbh, _ = run("O_bh", "dayfeed", 0.05, 0.03, 60, 100000)
Sen, Ren, _ = run("O_en", "comply", 0.50, 0.03, 1200, 78)
Sbo, Rbo, _ = run("O_bo", "comply", 0.50, 0.03, 60, 100000)

allids = {x["oid"] for x in R0}
base_fail = allids - S0
wall_bh_dayfeed = Sbh - S0                       # dayfeed 采到、仅需增回传容量
wall_en_only = (Sen - S0) - Sbh                  # 需大电池才采到、现有回传即可送? (近似)
coupled = Sbo - (Sbh | Sen)                      # 需同时增电池+增回传
struct = allids - Sbo                            # 双放宽仍不可行
print("\n== 集合分解 ==")
print(f"base 交付                                         : {len(S0)} ({len(S0)/N:.3f})")
print(f"dayfeed已采到、仅卡回传容量 (Sbh-S0)              : {len(wall_bh_dayfeed)}")
print(f"只需更大电池即可(在Sbh外但Sen内)                  : {len((Sen-S0)-Sbh)}")
print(f"双墙耦合: 需同时增电池与回传 (Sbo-(Sbh∪Sen))      : {len(coupled)}")
print(f"结构不可行: 双放宽仍失约 (全集-Sbo)               : {len(struct)}")
print(f"\n校验: base失约={len(base_fail)}  "
      f"放宽回传仍失约(采不到/接入)={len(base_fail-Sbh)}  "
      f"放宽能量仍失约(回传墙)={len(base_fail-Sen)}")
# 结构不可行义务的时间分布(应集中在中断窗 h4-20: 采到也无任何回传)
if struct:
    hh = Counter(x["release_at"]//3600 for x in R0 if x["oid"] in struct)
    print(f"\n结构不可行按 release 小时: {dict(sorted(hh.items()))}")
if coupled:
    hh = Counter(x["release_at"]//3600 for x in Rbo if x["oid"] in coupled)
    print(f"双墙耦合按 release 小时: {dict(sorted(hh.items()))}")

# --- 机器可读结果：论文表格直接从这份 json 生成，不再靠人抄 print 输出 ---
import json as _json
_out = {
    "run": "r30c_walls",
    "seed": COMMON.get("seed"),
    "task_hours": COMMON.get("task_hours"),
    "outage_h": [COMMON.get("outage_start_h"),
                 COMMON.get("outage_start_h", 0) + COMMON.get("outage_hours", 0)],
    "runs": {
        "base": {"config": "dayfeed,0.05Wh,1200s/78B", "delivered": len(S0), "n": N,
                 "svc": round(len(S0) / N, 4)},
        "O_bh": {"config": "dayfeed,0.05Wh,unlimited", "delivered": len(Sbh), "n": N,
                 "svc": round(len(Sbh) / N, 4)},
        "O_en": {"config": "always-300,0.50Wh,1200s/78B", "delivered": len(Sen), "n": N,
                 "svc": round(len(Sen) / N, 4)},
        "O_bo": {"config": "always-300,0.50Wh,unlimited", "delivered": len(Sbo), "n": N,
                 "svc": round(len(Sbo) / N, 4)},
    },
    "decomposition": {
        "backhaul_only": len(wall_bh_dayfeed),
        "energy_only": len((Sen - S0) - Sbh),
        "coupled": len(coupled),
        "structurally_infeasible": len(struct),
        "base_failures": len(base_fail),
    },
}
_p = os.path.join(_CODE, "..", "results", "r30c_walls.json")
_json.dump(_out, open(_p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"\n写出 {_p}")
