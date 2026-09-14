#!/usr/bin/env python3
"""run_baselines.py — Task v1.2-B：三个**现成**上游组合 × 自动备用腿，在三中断态/两规模下对照。

不造新策略（Astra 07 §6-B）：
  B1 local（现场自治，中心不下发）
  B2 最强**固定**上报配置（先用训练种子在"无备用+回传中断"下选档，再在独立评测种子报告）
  B3 ea_aoi（v1.1 注释里的"最强传统基线"：能量反馈采样 + AoI 反馈上报，成对下发）
每个上游臂配三档回传：off（无备用）/ b200（200B）/ b78（78B 紧容量），failover+EDF 自动备用。

输出 results/v3joint_baselines.json，并打印紧凑表。**选档种子与评测种子分离**，不挑测试种子。
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

# 注册固定上报档（只改 report_period，采样维持 3600）
for _p_ in (1800, 3600):
    ARMS[f"fixed{_p_}"] = (lambda v=_p_: FixedPeriodPolicy(v))

FIXED_CANDIDATES = ["fixed300", "fixed900", "fixed1800", "fixed3600"]
STATES = {"none": {}, "backhaul": dict(outage_start_h=4.0, outage_hours=4.0),
          "access": dict(access_outage_hours=4.0, access_outage_start_h=4.0)}
BACKUP = {"off": dict(enable_backup=False),
          "b200": dict(enable_backup=True, backup_bytes=200),
          "b78": dict(enable_backup=True, backup_bytes=78)}


def one(arm, state, bk, scale, seed):
    kw = dict(seed=seed, arm=arm, **STATES[state], **BACKUP[bk])
    if scale == "s1":
        kw.update(groups=1, per_group=4)
    else:
        kw.update(groups=2)
    r, _, _ = run_joint(task_hours=12, tail_hours=1, **kw)
    return r


def agg(rs):
    def m(key_path):
        vals = []
        for r in rs:
            v = r
            for k in key_path.split("."):
                v = v[k]
            vals.append(v)
        return round(st.mean(vals), 4)
    routine_rate = [r["routine"]["delivered"] / r["routine"]["n"] for r in rs]
    out = {
        "n_seeds": len(rs),
        "routine_rate_mean": round(st.mean(routine_rate), 4),
        "routine_rate_sd": round(st.pstdev(routine_rate), 4),
        "routine_delivered_mean": m("routine.delivered"),
        "event_deliver_mean": m("event.deliver_rate"),
        "airtime_uplink_h": m("communication.airtime_uplink_h"),
        "downlink_attempts": m("communication.downlink_attempts"),
    }
    bks = [r["backup"] for r in rs]
    if bks and bks[0]:
        out["backup_packets"] = round(st.mean(b["backup_packets"] for b in bks), 2)
        out["backup_records"] = round(st.mean(b["backup_records"] for b in bks), 2)
        out["backup_bytes"] = round(st.mean(b["backup_bytes_sent"] for b in bks), 1)
    return out


def pick_best_fixed(select_seeds, scale):
    """训练种子、无备用、回传中断下，选 routine 交付率最高的固定档（并列取更省=更大周期）。"""
    score = {}
    for arm in FIXED_CANDIDATES:
        rs = [one(arm, "backhaul", "off", scale, s) for s in select_seeds]
        score[arm] = st.mean(r["routine"]["delivered"] / r["routine"]["n"] for r in rs)
    best = max(FIXED_CANDIDATES, key=lambda a: (score[a], int(a[5:])))
    return best, {a: round(v, 4) for a, v in score.items()}


def run(select_seeds, eval_seeds, scales):
    result = {"select_seeds": select_seeds, "eval_seeds": eval_seeds, "cells": {}}
    for scale in scales:
        best_fixed, fixed_grid = pick_best_fixed(select_seeds, scale)
        result["cells"].setdefault(scale, {})["_fixed_selection"] = fixed_grid
        result["cells"][scale]["_best_fixed"] = best_fixed
        arms = {"B1_local": "local", "B2_fixed": best_fixed, "B3_ea_aoi": "ea_aoi"}
        for aname, arm in arms.items():
            for state in STATES:
                for bk in BACKUP:
                    rs = [one(arm, state, bk, scale, s) for s in eval_seeds]
                    result["cells"][scale][f"{aname}|{state}|{bk}"] = agg(rs)
                    print(f"[{scale}] {aname:9s} {state:9s} {bk:4s} "
                          f"{result['cells'][scale][f'{aname}|{state}|{bk}']}", flush=True)
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    if args.quick:
        sel, evl, scales = [0, 1], [2, 3], ["s1"]
        out_path = "results/v3joint_baselines_quick.json"
    else:
        sel, evl, scales = [0, 1, 2, 3], list(range(4, 12)), ["s1", "full"]
        out_path = "results/v3joint_baselines.json"
    res = run(sel, evl, scales)
    os.makedirs("results", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print("\nWROTE", out_path)
