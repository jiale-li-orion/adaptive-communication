# -*- coding: utf-8 -*-
"""retention_deadline_audit.py — 截止边界一致性审计与 C10 的公平对照。

问题
----
评分接受 `received_at <= deadline`（`scoring.py`），而源端在每次上报/转发**之前**按
`expires_at <= t_s` 删除记录（`network.py:440-450`）。当周期公式给出的到期时刻恰等于业务期限时，
基线会先删掉本可在该拍交付的记录。C10（`r49_retention_horizon.json`）的增益是否主要来自这个
边界不一致，必须先用**普通 expiry 的边界一致版本**作对照来判定。

臂
--
`current`   现行：`expires_at <= t_s` 删除，周期 = 节点已知业务周期
`boundary`  普通 expiry，只把边界改成 `expires_at < t_s`（保留截止当拍），周期不变
`fixed2`    周期 2 倍，`<=` 删除（r49 的探索最优点）
`adaptive`  r49 预注册规则（信念期限 + 自有收据时延中位数）

本脚本只做诊断，不改 `code/` 或已登记结果的语义；旧 r49 结果保留不覆盖。

Run: python3 code/analysis/retention_deadline_audit.py [--seeds 100 101 ...]
"""
from __future__ import annotations

import argparse
import collections
import dataclasses
import json
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
for _d in ("v3joint", "instance", "physics", "runtime", "experiments", "analysis", "monitoring"):
    _p = os.path.join(ROOT, "code", _d)
    if _p not in sys.path:
        sys.path.insert(0, _p)

import c5_common
import c5_gate

c5_gate.MODE = "task2"
c5_gate.install()
import network as net

H = lambda h: h * 3600
SCHED = [(0, 600, "blue"), (H(2), 300, "yellow"), (H(6), 600, "blue")]
PEAK = 0.012
ARMS = ("current", "boundary", "fixed2", "adaptive")
MODE = {"arm": "current"}

_ORIG_BATCH = net.Node.batch
WITNESS: dict = collections.defaultdict(collections.Counter)


def _expected_expiry(taken: int, period: int) -> int:
    return taken + ((period - taken % period) + period)


def _true_deadline(taken: int) -> int:
    """该采集时刻所属义务的**真业务期限**：按公开任务表取档位周期，期限 = 窗口末端 + 一个周期。"""
    for i, (start, period, _lv) in enumerate(SCHED):
        nxt = SCHED[i + 1][0] if i + 1 < len(SCHED) else 10 ** 12
        if start <= taken < nxt:
            rel = (taken // period) * period
            return rel + 2 * period
    return taken + 2 * SCHED[-1][1]


def batch(self, t_s: int, max_slots: int = 32):
    arm = MODE["arm"]
    if arm == "current":
        return _ORIG_BATCH(self, t_s, max_slots)
    period = max(1, int(self.p.obligation_period_s))
    if arm == "boundary":
        keep, drop = [], []
        for s in self.cache:
            (drop if _expected_expiry(s.taken_at, period) < t_s else keep).append(s)
        if drop:
            for old in drop:
                self.transit[old.sample_id].dropped_at = t_s
                self.dropped += 1
            self.cache = keep
        return self.cache[:max_slots]
    if arm == "fixed2":
        period = 2 * period
        keep, drop = [], []
        for s in self.cache:
            (drop if _expected_expiry(s.taken_at, period) <= t_s else keep).append(s)
        if drop:
            for old in drop:
                self.transit[old.sample_id].dropped_at = t_s
                self.dropped += 1
            self.cache = keep
        return self.cache[:max_slots]
    # adaptive：信念期限 + L̂（自有收据时延中位数，夹 [0,4P]）
    lat = []
    for sid, tr in getattr(self, "transit", {}).items():
        if tr.received_at is None:
            continue
        try:
            lat.append(tr.received_at - int(sid.rsplit(":", 1)[1]))
        except ValueError:
            continue
    lhat = 0 if len(lat) < 8 else min(max(0, int(st.median(lat))), 4 * period)
    keep, drop = [], []
    for s in self.cache:
        (drop if _expected_expiry(s.taken_at, period) + lhat <= t_s else keep).append(s)
    if drop:
        for old in drop:
            self.transit[old.sample_id].dropped_at = t_s
            self.dropped += 1
        self.cache = keep
    return self.cache[:max_slots]


net.Node.batch = batch
c5_common.install()
from joint_run import run_joint


def run(arm: str, seed: int) -> dict:
    MODE["arm"] = arm
    WITNESS.clear()
    c5_common.C5Config.mode = "ttl"
    c5_common.C5Config.ttl_delta_s = 8 * H(1)
    c5_common.C5Config.peak_wh_h = PEAK
    c5_common.C5Config.task_end_s = 49 * H(1)
    r, inst, _ = run_joint(seed=seed, local_floor=True, task_hours=48, tail_hours=1, arm="local",
                           groups=2, sample_interval_s=600, report_period_s=600,
                           routine_period_s=600, harvest_mode="solar",
                           harvest_peak_wh_per_hour=PEAK, capacity_wh=0.05, initial_soc=1.0,
                           outage_start_h=4, outage_hours=16, enable_backup=True,
                           backup_rate_s=1200, backup_bytes=78, backup_chooser="maxcov",
                           cache_service="generic_expiry", mission_schedule=SCHED,
                           mission_mode="dayfeed", collect_rows=True)
    rows = [x for x in r["rows"] if x["kind"] == "routine" and not x.get("censored")]
    yel = [x for x in rows if H(2) <= x["release_at"] < H(6)]
    delivered = {x["oid"] for x in rows if x["delivered"]}
    # 逐样本口径：到期当拍被听到、以及到期当拍被删除
    heard_at_expiry = dropped_at_expiry = 0
    heard_at_expiry_is_deadline = 0      # 恰好等于真业务期限：这是被边界缺陷丢掉的那一类
    heard_at_expiry_after_deadline = 0   # 听到时已过期：不构成获救
    wit_heard: list[dict] = []
    wit_dropped: list[dict] = []
    period_seen = collections.Counter()
    for _nid, node in inst.nodes.items():
        p = max(1, int(node.p.obligation_period_s))
        period_seen[p] += 1
        for sid, tr in getattr(node, "transit", {}).items():
            try:
                taken = int(sid.rsplit(":", 1)[1])
            except ValueError:
                continue
            exp = _expected_expiry(taken, p)
            if tr.heard_at is not None and tr.heard_at == exp:
                heard_at_expiry += 1
                td = _true_deadline(taken)
                if exp == td:
                    heard_at_expiry_is_deadline += 1
                elif exp > td:
                    heard_at_expiry_after_deadline += 1
                if len(wit_heard) < 5:
                    wit_heard.append({"sample_id": sid, "taken": taken, "expiry": exp,
                                      "heard": tr.heard_at, "received": tr.received_at,
                                      "dropped": tr.dropped_at})
            if tr.dropped_at is not None and tr.dropped_at == exp:
                dropped_at_expiry += 1
                if len(wit_dropped) < 5:
                    wit_dropped.append({"sample_id": sid, "taken": taken, "expiry": exp,
                                        "dropped": tr.dropped_at, "heard": tr.heard_at,
                                        "received": tr.received_at})
    socs = [getattr(n, "_c5_min_soc", n.soc_wh) for n in inst.nodes.values()]
    return {"n_obligations": len(rows), "n_yellow": len(yel),
            "svc": r["routine"]["delivered"] / r["routine"]["n"],
            "delivered": len(delivered),
            "yellow": sum(1 for x in yel if x["delivered"]),
            "dead": len(r["survival"].get("dead", [])),
            "min_soc_wh": min(socs),
            "heard_exactly_at_expiry": heard_at_expiry,
            "heard_at_expiry_is_true_deadline": heard_at_expiry_is_deadline,
            "heard_at_expiry_after_deadline": heard_at_expiry_after_deadline,
            "dropped_exactly_at_expiry": dropped_at_expiry,
            "periods_seen": dict(period_seen),
            "witness_heard_at_expiry": wit_heard,
            "witness_dropped_at_expiry": wit_dropped,
            "sampled": sum(n.sampled for n in inst.nodes.values()),
            "_delivered_oids": delivered}


def ci95(xs):
    n = len(xs)
    m = st.mean(xs)
    if n < 2:
        return m, m, m
    h = 1.96 * st.stdev(xs) / (n ** 0.5)
    return m, m - h, m + h


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="*", default=list(range(100, 110)))
    ap.add_argument("--out", default=os.path.join("results", "retention_deadline_audit.json"))
    args = ap.parse_args()
    out = {"script": "code/analysis/retention_deadline_audit.py",
           "purpose": "截止边界一致性审计：C10 增益是否由 '评分允许当拍交付、源端当拍前已删' 造成",
           "phase": "A", "peak": PEAK, "seeds": args.seeds, "arms": list(ARMS), "runs": {}}
    per = {a: [] for a in ARMS}
    for s in args.seeds:
        for a in ARMS:
            row = run(a, s)
            per[a].append(row)
            print(f"seed {s} {a:9s} 服务 {row['svc']:.4f}  交付 {row['delivered']:5}/{row['n_obligations']}"
                  f"  黄级 {row['yellow']:4}  死亡 {row['dead']:2}  minSoC {row['min_soc_wh']*1000:7.3f} mWh"
                  f"  到期当拍听到 {row['heard_exactly_at_expiry']:4}"
                  f"  到期当拍删除 {row['dropped_exactly_at_expiry']:4}", flush=True)
        out["runs"][str(s)] = {a: {k: v for k, v in per[a][-1].items() if k != "_delivered_oids"}
                               for a in ARMS}
    print()
    summary = {}
    for a in ARMS:
        sv = [100 * x["svc"] for x in per[a]]
        summary[a] = {"svc_mean_pct": round(st.mean(sv), 4),
                      "delivered_total": sum(x["delivered"] for x in per[a]),
                      "n_obligations_total": sum(x["n_obligations"] for x in per[a]),
                      "yellow_total": sum(x["yellow"] for x in per[a]),
                      "dead_total": sum(x["dead"] for x in per[a]),
                      "min_soc_wh": min(x["min_soc_wh"] for x in per[a]),
                      "heard_exactly_at_expiry_total": sum(x["heard_exactly_at_expiry"] for x in per[a]),
                      "heard_at_expiry_is_true_deadline_total":
                          sum(x["heard_at_expiry_is_true_deadline"] for x in per[a]),
                      "heard_at_expiry_after_deadline_total":
                          sum(x["heard_at_expiry_after_deadline"] for x in per[a]),
                      "dropped_exactly_at_expiry_total": sum(x["dropped_exactly_at_expiry"] for x in per[a]),
                      "sampled_total": sum(x["sampled"] for x in per[a])}
    for a in ("boundary", "fixed2", "adaptive"):
        d = [100 * (b["svc"] - c["svc"]) for b, c in zip(per[a], per["current"])]
        m, lo, hi = ci95(d)
        summary[a]["vs_current_points"] = round(m, 4)
        summary[a]["vs_current_ci95"] = [round(lo, 4), round(hi, 4)]
        summary[a]["vs_current_positive_seeds"] = sum(1 for x in d if x > 0)
    for a in ("fixed2", "adaptive"):
        d = [100 * (b["svc"] - c["svc"]) for b, c in zip(per[a], per["boundary"])]
        m, lo, hi = ci95(d)
        summary[a]["vs_boundary_points"] = round(m, 4)
        summary[a]["vs_boundary_ci95"] = [round(lo, 4), round(hi, 4)]
    out["summary"] = summary
    print("十种子合计（相位 A，peak .012，ttl8）：")
    for a in ARMS:
        s = summary[a]
        extra = (f"  vs current {s.get('vs_current_points'):+.2f} 点 CI{s.get('vs_current_ci95')}"
                 f" 正种子 {s.get('vs_current_positive_seeds')}/10" if a != "current" else "")
        print(f"  {a:9s} 服务 {s['svc_mean_pct']:.4f}%  交付 {s['delivered_total']}/{s['n_obligations_total']}"
              f"  黄级 {s['yellow_total']}  死亡 {s['dead_total']}  minSoC {s['min_soc_wh']*1000:.3f} mWh"
              f"  到期当拍听到 {s['heard_exactly_at_expiry_total']}"
              f"（其中恰等于真期限 {s['heard_at_expiry_is_true_deadline_total']}，"
              f"听到已过期 {s['heard_at_expiry_after_deadline_total']}）"
              f"  vs boundary {s.get('vs_boundary_points')}{extra}")
    path = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("\nsaved", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
