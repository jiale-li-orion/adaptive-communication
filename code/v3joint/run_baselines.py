#!/usr/bin/env python3
"""run_baselines.py — Task v1.2-B：三个**现成**上游组合 × 自动备用腿对照（交付—代价前沿）。

不造新策略（Astra 07 §6-B）：
  B1 local（现场自治，不下发）；B2 最强**固定**上报（训练种子选档、评测种子独立）；
  B3 ea_aoi（v1.1 "最强传统基线"：能量+AoI 反馈成对下发）。

关键认识（doc09/quick）：地灾常态数据率极低，网关级备用**带宽不构成瓶颈**，联合的真实空间是
**时序匹配**——让数据在稀疏备用机会前就绪、其余时间不白加密。因此矩阵在 full 14 台上报"稀疏
备用/长中断/紧接入"档，并同时报**交付与真实代价**（接入空口、下行命令、备用包数=资费代理），
输出 Pareto 而非单点均值。选档种子与评测种子分离。
"""
from __future__ import annotations
import argparse, json, os, sys, statistics as st
_HERE = os.path.dirname(os.path.abspath(__file__))
_CODE = os.path.dirname(_HERE)
_DIRS = [os.path.join(_CODE, d) for d in ("physics", "runtime", "experiments", "analysis",
                                          "monitoring", "instance")]
for _p in [_HERE, *_DIRS]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from center import FixedPeriodPolicy, ARMS                 # noqa: E402
from joint_run import run_joint                            # noqa: E402

for _v in (1800, 3600):
    ARMS[f"fixed{_v}"] = (lambda v=_v: FixedPeriodPolicy(v))
FIXED_CANDIDATES = ["fixed300", "fixed900", "fixed1800", "fixed3600"]

# 中断态：常态 / 回传中断4h / 回传中断8h / 接入中断4h
STATES = {"none": {},
          "bh4": dict(outage_start_h=4.0, outage_hours=4.0),
          "bh8": dict(outage_start_h=4.0, outage_hours=8.0),
          "acc4": dict(access_outage_hours=4.0, access_outage_start_h=4.0)}
# 备用档：关 / 200B·120s / 78B·120s / 78B·300s(稀疏) / 78B·600s(很稀疏)
BACKUP = {"off": dict(enable_backup=False),
          "b200": dict(enable_backup=True, backup_rate_s=120, backup_bytes=200),
          "b78": dict(enable_backup=True, backup_rate_s=120, backup_bytes=78),
          "t300": dict(enable_backup=True, backup_rate_s=300, backup_bytes=78),
          "t600": dict(enable_backup=True, backup_rate_s=600, backup_bytes=78)}


def one(arm, state, bk, scale, seed, uplink_p=0.74):
    kw = dict(seed=seed, arm=arm, uplink_p_arrive=uplink_p, **STATES[state], **BACKUP[bk])
    kw.update(groups=1, per_group=4) if scale == "s1" else kw.update(groups=2)
    r, _, _ = run_joint(task_hours=12, tail_hours=1, **kw)
    return r


def agg(rs):
    rr = [r["routine"]["delivered"] / r["routine"]["n"] for r in rs]
    def m(path):
        vals = []
        for r in rs:
            v = r
            for k in path.split("."):
                v = v[k]
            vals.append(v)
        return round(st.mean(vals), 4)
    out = {"n": len(rs), "routine": round(st.mean(rr), 4), "routine_sd": round(st.pstdev(rr), 4),
           "event": m("event.deliver_rate"),
           "air_s": round(m("communication.airtime_uplink_h") * 3600, 2),
           "down_cmd": m("communication.downlink_attempts")}
    bks = [r["backup"] for r in rs]
    if bks and bks[0] and bks[0]["backup_packets"] >= 0:
        out["bk_pkt"] = round(st.mean(b["backup_packets"] for b in bks), 2)
        out["bk_rec"] = round(st.mean(b["backup_records"] for b in bks), 2)
        out["bk_byte"] = round(st.mean(b["backup_bytes_sent"] for b in bks), 1)
    return out


def pick_best_fixed(seeds, scale, state="bh8"):
    score = {}
    for arm in FIXED_CANDIDATES:
        rs = [one(arm, state, "off", scale, s) for s in seeds]
        score[arm] = st.mean(r["routine"]["delivered"] / r["routine"]["n"] for r in rs)
    best = max(FIXED_CANDIDATES, key=lambda a: (score[a], int(a[5:])))
    return best, {a: round(v, 4) for a, v in score.items()}


def run(select_seeds, eval_seeds, scales):
    res = {"select_seeds": select_seeds, "eval_seeds": eval_seeds, "cells": {}}
    for scale in scales:
        C = res["cells"][scale] = {}
        best, grid = pick_best_fixed(select_seeds, scale)
        C["_fixed_grid_bh8_off"] = grid
        C["_best_fixed"] = best
        arms = {"B1local": "local", "B2fixed": best, "B3eaoi": "ea_aoi"}
        # 主矩阵：常态/接入只看 off+b200；回传两档看全部备用稀缺档
        plan = []
        for state in ("none", "acc4"):
            for bk in ("off", "b200"):
                plan.append((state, bk, 0.74))
        for state in ("bh4", "bh8"):
            for bk in BACKUP:
                plan.append((state, bk, 0.74))
        # 紧接入只在长中断 + 三档备用，放大时序错配
        for bk in ("off", "b78", "t300", "t600"):
            plan.append(("bh8", bk, 0.50))
        for aname, arm in arms.items():
            for state, bk, up in plan:
                tag = f"{aname}|{state}|{bk}|u{int(up*100)}"
                rs = [one(arm, state, bk, scale, s, uplink_p=up) for s in eval_seeds]
                C[tag] = agg(rs)
                print(f"[{scale}] {tag:28s} {C[tag]}", flush=True)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    if args.quick:
        sel, evl, scales = [0, 1], [2, 3], ["s1"]
        outp = "results/v3joint_baselines_quick.json"
    else:
        sel, evl, scales = [0, 1, 2, 3], list(range(4, 12)), ["s1", "full"]
        outp = "results/v3joint_baselines.json"
    r = run(sel, evl, scales)
    os.makedirs("results", exist_ok=True)
    with open(outp, "w", encoding="utf-8") as fh:
        json.dump(r, fh, ensure_ascii=False, indent=1)
    print("\nWROTE", outp)
