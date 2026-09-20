# -*- coding: utf-8 -*-
"""r49_retention_horizon.py — 记录释放视界：按预注册 v1 判决。

口径见 `spec/prereg-retention-horizon-v1.md`（形状、对照臂、受检格、确认种子、阈值、关闭条件
均在运行前写定）。本脚本只做两件事：跑出三臂 × 两格 × 十个确认种子的配对结果，然后按预注册的
判决规则给出结论并写进结果文件。规则不成立时退出非零，使"结论与阈值不符"无法静默通过。

机制（探索阶段的发现，见预注册 §1）：`generic_expiry` 的到期清理在 `Node.batch` 内每次上报机会
执行，读的是 `profile.obligation_period_s`；因此该视界决定每条记录能进入多少次上报批次，而在
丢包管道里次数就是按期交付的来源。实现把视界钉在业务期限上，本实验检验"视界跟随管道自身时延"。

Run: python3 code/v3joint/r49_retention_horizon.py [--out results/r49_retention_horizon.json]
"""
from __future__ import annotations

import argparse
import collections
import dataclasses
import json
import os
import statistics as st
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
for _d in ("v3joint", "instance", "physics", "runtime", "experiments", "analysis", "monitoring"):
    _p = os.path.join(REPO, "code", _d)
    if _p not in sys.path:
        sys.path.insert(0, _p)

import c5_common
import c5_gate

c5_gate.MODE = "task2"
c5_gate.install()
import network as net

H = lambda h: h * 3600
PHASE = dict(up=H(2), down=H(6), out_lo=H(4), out_hi=H(20))
SCHED = [(0, 600, "blue"), (PHASE["up"], 300, "yellow"), (PHASE["down"], 600, "blue")]
PEAKS = (0.012, 0.010)
SEEDS = tuple(range(100, 110))          # 预注册 §4：开发区间内、与探索集 0--9 不重叠
ARMS = ("current", "fixed2", "adaptive")
MIN_LAT_SAMPLES = 8                     # 预注册 §2：少于 8 条按 0 处理
LAT_CAP_MULT = 4

_ORIG_BATCH = net.Node.batch
MODE = {"arm": "current"}


def _median_latency(self) -> int:
    """节点自己观测到的投递时延中位数（只用自有收据）。

    采样时刻从 sample_id 末段解出：`_take` 用 `f"{node_id}:{measurand}:{t_s}"` 造 id，
    因此节点无需额外存储即可知道自己每条已到达记录被采于何时。
    """
    lat = []
    for sid, tr in getattr(self, "transit", {}).items():
        if tr.received_at is None:
            continue
        try:
            taken = int(sid.rsplit(":", 1)[1])
        except ValueError:
            continue
        lat.append(tr.received_at - taken)
    if len(lat) < MIN_LAT_SAMPLES:
        return 0
    return max(0, int(st.median(lat)))


def batch(self, t_s: int, max_slots: int = 32):
    arm = MODE["arm"]
    if arm == "current":
        return _ORIG_BATCH(self, t_s, max_slots)
    if arm == "fixed2":
        orig = self.p
        self.p = dataclasses.replace(orig, obligation_period_s=2 * orig.obligation_period_s)
        try:
            return _ORIG_BATCH(self, t_s, max_slots)
        finally:
            self.p = orig
    # adaptive：信念期限 + L̂，L̂ 为自有收据的时延中位数，夹在 [0, 4P]
    period = max(1, int(self.p.obligation_period_s))
    lat = min(_median_latency(self), LAT_CAP_MULT * period)
    keep, drop = [], []
    for s in self.cache:
        base = s.taken_at + ((period - s.taken_at % period) + period)
        (drop if base + lat <= t_s else keep).append(s)
    if drop:
        for old in drop:
            self.transit[old.sample_id].dropped_at = t_s
            self.dropped += 1
        self.cache = keep
    return self.cache[:max_slots]


net.Node.batch = batch
c5_common.install()
from joint_run import run_joint


def run(arm: str, peak: float, seed: int) -> dict:
    MODE["arm"] = arm
    c5_common.C5Config.mode = "ttl"
    c5_common.C5Config.ttl_delta_s = 8 * H(1)
    c5_common.C5Config.peak_wh_h = peak
    c5_common.C5Config.task_end_s = 49 * H(1)
    r, inst, _ = run_joint(seed=seed, local_floor=True, task_hours=48, tail_hours=1, arm="local",
                           groups=2, sample_interval_s=600, report_period_s=600,
                           routine_period_s=600, harvest_mode="solar",
                           harvest_peak_wh_per_hour=peak, capacity_wh=0.05, initial_soc=1.0,
                           outage_start_h=4, outage_hours=16, enable_backup=True,
                           backup_rate_s=1200, backup_bytes=78, backup_chooser="maxcov",
                           cache_service="generic_expiry", mission_schedule=SCHED,
                           mission_mode="dayfeed", collect_rows=True)
    rows = [x for x in r["rows"] if x["kind"] == "routine" and not x.get("censored")]
    yel = [x for x in rows if PHASE["up"] <= x["release_at"] < PHASE["down"]]
    socs = [getattr(n, "_c5_min_soc", n.soc_wh) for n in inst.nodes.values()]
    return {"svc": r["routine"]["delivered"] / r["routine"]["n"],
            "yellow": sum(1 for x in yel if x["delivered"]),
            "dead": len(r["survival"].get("dead", [])),
            "min_soc_wh": min(socs), "sampled": sum(n.sampled for n in inst.nodes.values())}


def ci95(xs):
    n = len(xs)
    m = st.mean(xs)
    if n < 2:
        return m, m, m
    h = 1.96 * st.stdev(xs) / (n ** 0.5)
    return m, m - h, m + h


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join("results", "r49_retention_horizon.json"))
    args = ap.parse_args()
    out = {"script": "code/v3joint/r49_retention_horizon.py",
           "contract": "spec/prereg-retention-horizon-v1.md",
           "peaks": list(PEAKS), "seeds": list(SEEDS), "arms": list(ARMS),
           "cells": {}}
    verdicts = {}
    for peak in PEAKS:
        per = {a: [] for a in ARMS}
        for s in SEEDS:
            for a in ARMS:
                per[a].append(run(a, peak, s))
            print(f"peak={peak} seed {s}: " + "  ".join(
                f"{a} svc {per[a][-1]['svc']:.4f} 黄级 {per[a][-1]['yellow']:4d} "
                f"死 {per[a][-1]['dead']}" for a in ARMS), flush=True)
        d_adapt = [100 * (b["svc"] - a["svc"]) for a, b in zip(per["current"], per["adaptive"])]
        d_fix = [100 * (b["svc"] - a["svc"]) for a, b in zip(per["current"], per["fixed2"])]
        m_a, lo_a, hi_a = ci95(d_adapt)
        m_f, lo_f, hi_f = ci95(d_fix)
        dead_c = sum(x["dead"] for x in per["current"])
        dead_a = sum(x["dead"] for x in per["adaptive"])
        min_a = min(x["min_soc_wh"] for x in per["adaptive"])
        crit1 = (m_a > 0) and (lo_a > 0) and (sum(1 for x in d_adapt if x > 0) >= 8)
        crit2 = (dead_a <= dead_c) and (min_a >= 4.7e-4)
        verdicts[str(peak)] = {"adaptive_minus_current_points": round(m_a, 4),
                               "ci95": [round(lo_a, 4), round(hi_a, 4)],
                               "positive_seeds": sum(1 for x in d_adapt if x > 0),
                               "fixed2_minus_current_points": round(m_f, 4),
                               "fixed2_ci95": [round(lo_f, 4), round(hi_f, 4)],
                               "criterion1_primary": bool(crit1), "criterion2_risk": bool(crit2),
                               "dead_current": dead_c, "dead_adaptive": dead_a,
                               "min_soc_adaptive_wh": min_a,
                               "adaptive_vs_fixed2_separable": not (lo_a <= m_f <= hi_a)}
        out["cells"][str(peak)] = {a: [{k: (round(v, 6) if isinstance(v, float) else v)
                                        for k, v in row.items()} for row in per[a]] for a in ARMS}
        print(f"  峰值 {peak}：adaptive−current {m_a:+.2f} 点 CI[{lo_a:+.2f},{hi_a:+.2f}] "
              f"正种子 {sum(1 for x in d_adapt if x > 0)}/10；fixed2−current {m_f:+.2f} 点 "
              f"CI[{lo_f:+.2f},{hi_f:+.2f}]；判定 {crit1=} {crit2=}", flush=True)
    out["verdict"] = verdicts
    adopted = all(v["criterion1_primary"] and v["criterion2_risk"] for v in verdicts.values())
    both_separable = all(v["adaptive_vs_fixed2_separable"] for v in verdicts.values())
    out["status"] = "supported" if adopted else "scoped-negative"
    out["statement"] = ("视界跟随管道自身时延的规则在两个受检格、十个确认种子上抬升全时域服务"
                        if adopted else "预注册两项判据未同时成立，按关闭条件记限定负结果")
    out["downgrade_note"] = ("adaptive 与 fixed2 的区间不可分 ⇒ 只支持“视界可调”，"
                             "不支持“视界应自校准”" if adopted and not both_separable else None)
    path = args.out if os.path.isabs(args.out) else os.path.join(REPO, args.out)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"\n状态：{out['status']}；{out['statement']}")
    print("saved", path)
    return 0 if adopted else 1


if __name__ == "__main__":
    raise SystemExit(main())
