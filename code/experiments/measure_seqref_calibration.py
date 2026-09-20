#!/usr/bin/env python3
"""measure_seqref_calibration.py — 实测 `c5_seqref` 模型所需的两件事，并冻结成参考结果。

`c5_seqref.py` 的能量台账与环境逐拍同序，但它的**负载是声明常数**，不是从代码推出来的：
  * 稀疏档 3.000 mWh/h、密集档 6.000 mWh/h。
本脚本把这两个常数**测出来**并冻结，同时留下一段可以逐小时比对的轨迹，使抽象台账能被核对，
而不是自称与环境一致。

测什么（单节点、一个相位、一个种子，全程确定性可复现）：

  1. 每小时的**意向采能** `truth.harvest_at` 与**小时末电量**（环境自己积出来的）；
  2. 同一小时的**采样次数**与**射频次数**，用来分解负载来源；
  3. 由相邻小时末电量反推的每小时负载，区分白天/夜间与密集/稀疏。

不判真假，只出数据；判定在 `code/experiments/audit_seqref.py` 里，用这份文件复算抽象轨迹。

输出写 `results/c5_seqref_calibration.json`（活文件）。**冻结快照**按本仓库惯例另存
`results/reference/c5_seqref_calibration.json`，判定读的是冻结份；两者出现差异是信号不是噪声。

Run: python3 code/experiments/measure_seqref_calibration.py [--out results/reference/c5_seqref_calibration.json]
"""
from __future__ import annotations

import argparse
import collections
import inspect
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
for _d in ("v3joint", "instance", "physics", "runtime", "experiments", "analysis", "monitoring"):
    _p = os.path.join(ROOT, "code", _d)
    if _p not in sys.path:
        sys.path.insert(0, _p)

PEAK = 0.012
SEED = 0
NODE = "n00"
PHASE = "A"
UP_H, DOWN_H = 2, 6
TTL_H = 8


def sun_frac(t_s: float) -> float:
    hod = (6.0 + t_s / 3600.0) % 24.0
    rel = (hod - 6.0) % 24.0
    if rel > 12.0:
        return 0.0
    return max(0.0, float(np.sin(np.pi * rel / 12.0)))


def clear_hour_wh(hour: int, peak: float = PEAK) -> float:
    return float(sum(peak * sun_frac(hour * 3600 + k * 60) / 60.0 for k in range(60)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join("results", "c5_seqref_calibration.json"))
    args = ap.parse_args()

    import c5_common as C
    C.C5Config.mode = "ttl"
    C.C5Config.ttl_delta_s = TTL_H * 3600
    C.C5Config.peak_wh_h = PEAK
    C.C5Config.task_end_s = 49 * 3600
    C.install()
    import c5_gate
    c5_gate.MODE = "task2"
    c5_gate.install()

    import network as net

    trace: dict[str, list] = collections.defaultdict(list)
    allhour: dict[tuple[str, int], float] = collections.defaultdict(float)
    _orig_step = net.Node._step_power
    _orig_spend = net.Node.spend

    def step_power(self, t_s, truth):
        _orig_step(self, t_s, truth)
        allhour[(self.node_id, t_s // 3600)] += truth.harvest_at(self.node_id, t_s)
        if self.node_id == NODE:
            trace["step"].append((t_s, truth.harvest_at(self.node_id, t_s), self.soc_wh,
                                  self.sample_interval_s, self.alive))

    _tick = {"t": 0}

    def step_power2(self, t_s, truth):
        _tick["t"] = t_s
        step_power(self, t_s, truth)

    def spend(self, wh):
        _orig_spend(self, wh)
        if self.node_id == NODE:
            fr = inspect.stack()[1]
            trace["spend"].append((_tick["t"], fr.function, wh))

    net.Node._step_power = step_power2
    net.Node.spend = spend

    from joint_run import run_joint
    H = lambda h: h * 3600
    sched = [(0, 600, "blue"), (H(UP_H), 300, "yellow"), (H(DOWN_H), 600, "blue")]
    r, inst, _ = run_joint(seed=SEED, local_floor=True, task_hours=48, tail_hours=1, arm="local",
                           groups=2, sample_interval_s=600, report_period_s=600,
                           routine_period_s=600, harvest_mode="solar",
                           harvest_peak_wh_per_hour=PEAK, capacity_wh=0.05, initial_soc=1.0,
                           outage_start_h=4, outage_hours=16, enable_backup=True,
                           backup_rate_s=1200, backup_bytes=78, backup_chooser="maxcov",
                           cache_service="generic_expiry", mission_schedule=sched,
                           mission_mode="dayfeed", collect_rows=True)
    node = inst.nodes[NODE]
    by_hour: dict[int, list] = collections.defaultdict(list)
    for t, h, soc, iv, alive in trace["step"]:
        by_hour[t // 3600].append((t, h, soc, iv))
    spends = collections.Counter(k for _t, k, _w in trace["spend"])
    spend_wh = collections.Counter()
    for _t, k, w in trace["spend"]:
        spend_wh[k] += w
    # 逐小时负载直接由花费账本给出：与溢出无关，比"采能减电量差"可靠
    load_by_hour: dict[int, float] = collections.defaultdict(float)
    for t_s, _k, w in trace["spend"]:
        load_by_hour[t_s // 3600] += w

    hourly = []
    prev_end = None
    for hour in sorted(by_hour):
        recs = sorted(by_hour[hour])
        harvest = sum(h for _, h, _, _ in recs)
        soc_end = recs[-1][2]
        iv = collections.Counter(iv for _, _, _, iv in recs).most_common(1)[0][0]
        load = None if prev_end is None else round((prev_end - soc_end) + harvest, 9)
        load_spend = round(load_by_hour.get(hour, 0.0), 9)
        hourly.append({"hour": hour, "interval_s": iv,
                       "intended_harvest_wh": round(harvest, 9),
                       "clear_hour_wh": round(clear_hour_wh(hour), 9),
                       "factor": (None if clear_hour_wh(hour) <= 0
                                  else round(harvest / clear_hour_wh(hour), 6)),
                       "soc_end_wh": round(soc_end, 9),
                       "load_from_soc_delta_wh": load,
                       "load_from_spend_wh": load_spend,
                       "n_samples": int(sum(1 for _t, k, _w in trace["spend"]
                                            if k == "_take" and _t // 3600 == hour))})
        prev_end = soc_end

    dense_hours = [h for h in hourly if h["interval_s"] == 300]
    sparse_hours = [h for h in hourly if h["interval_s"] == 600 and h["load_from_soc_delta_wh"]]
    # 只在**未触及容量上限**的小时上反推负载；碰到上限的小时反推值会把溢出算进负载
    cap_hit = {h["hour"] for h in hourly if h["soc_end_wh"] >= 0.05 - 1e-9}
    night = [h for h in sparse_hours if h["hour"] >= 12 and h["hour"] < 24]
    load_sparse = float(np.median([h["load_from_spend_wh"] for h in night]))
    day_sparse_unspilled = [h for h in sparse_hours
                            if h["hour"] not in cap_hit and h["clear_hour_wh"] > 0]
    load_day_sparse = (float(np.median([h["load_from_spend_wh"] for h in day_sparse_unspilled]))
                       if day_sparse_unspilled else None)
    dense_unspilled = [h for h in dense_hours if h["hour"] not in cap_hit]
    load_dense = float(np.median([h["load_from_spend_wh"] for h in dense_hours]))

    # 云遮因子：全部节点 × 全部白天小时，只保留晴空基准足够大的小时（基准过小时比值噪声主导）
    MIN_CLEAR_WH = 3.0e-3
    factors_all = []
    for (nid, hour), harv in sorted(allhour.items()):
        c = clear_hour_wh(hour)
        if c >= MIN_CLEAR_WH:
            factors_all.append((nid, hour, harv / c))
    fv = [f for _n, _h, f in factors_all]
    p_cloud, atten = 0.35, 0.25
    sigma_theory = (1 - atten) * float(np.sqrt(p_cloud * (1 - p_cloud) / 60.0))
    cloud_stats = {
        "min_clear_wh_for_ratio": MIN_CLEAR_WH,
        "n_samples": len(fv),
        "n_nodes": len({n for n, _h, _f in factors_all}),
        "mean_factor": float(np.mean(fv)) if fv else None,
        "std_factor": float(np.std(fv, ddof=1)) if len(fv) > 1 else None,
        "theoretical_mean": (1 - p_cloud) + p_cloud * atten,
        "theoretical_std": sigma_theory,
        "note": ("逐拍 Bernoulli(p=.35, atten=.25) 的每小时均值：理论 std=(1-atten)*sqrt(p(1-p)/60)。"
                 "这里给出实测值作为声明 sigma 的依据。"),
    }

    out = {
        "provenance": {
            "script": "code/experiments/measure_seqref_calibration.py",
            "command": "python3 code/experiments/measure_seqref_calibration.py",
            "environment": {"phase": PHASE, "arm": "ttl8", "seed": SEED, "node": NODE,
                            "peak_wh_per_h": PEAK, "sched": sched,
                            "mission_mode": "dayfeed", "local_floor": True},
            "determinism": "stable_uniform 按 seed 取键；同 seed 同参数逐位可复现",
        },
        # **声明值**：与 `code/v3joint/c5_seqref.py` 用同一组字面量与同一表达式，逐位可比。
        "declared_constants": {
            # C10 将 generic_expiry 改为保留 deadline tick 后，实际上传批次内容会改变；
            # 空口能耗按 payload airtime 计，因此这里的等效每报告能耗也必须随当前语义重标定。
            "radio_wh_per_report": 3.1867792516129184e-5,
            "sample_wh": 4.7e-4,
            "load_sparse_wh_per_h": 6 * (4.7e-4 + 3.1867792516129184e-5),
            "load_dense_wh_per_h": 12 * (4.7e-4 + 3.1867792516129184e-5),
            "note": "模型的物理常数；结构 = 每小时采样数 × (sample_wh + 单次射频)。",
        },
        # **实测值**：全精度，作为声明值的来源与旁证。
        "measured_constants": {
            "radio_wh_per_report": spend_wh["_charge_radio"] / max(1, spends["_charge_radio"]),
            "sample_wh_from_code": 4.7e-4,
            "sample_wh_from_spend": spend_wh["_take"] / max(1, spends["_take"]),
            "load_sparse_wh_per_h": 6 * (4.7e-4 + spend_wh["_charge_radio"]
                                         / max(1, spends["_charge_radio"])),
            "load_dense_wh_per_h": 12 * (4.7e-4 + spend_wh["_charge_radio"]
                                         / max(1, spends["_charge_radio"])),
        },
        "measured": {
            "load_sparse_wh_per_h": round(load_sparse, 9),
            "load_dense_wh_per_h": round(load_dense, 9),
            "load_day_sparse_wh_per_h": None if load_day_sparse is None else round(load_day_sparse, 9),
            "load_dense_wh_per_h_all_dense_hours": [h["load_from_spend_wh"] for h in dense_hours],
            "dense_hours_used_for_load": [h["hour"] for h in dense_hours],
            "dense_hours_unspilled_crosscheck": [h["hour"] for h in dense_unspilled],
            "night_hours_used_for_load": [h["hour"] for h in night],
            "cap_hit_hours_excluded": sorted(cap_hit),
        },
        "node_totals": {
            "sampled": int(node.sampled),
            "harvested_wh": round(node.power.harvested_wh, 9),
            "consumed_wh": round(node.power.consumed_wh, 9),
            "final_soc_wh": round(node.soc_wh, 9),
            "min_soc_wh": round(min(s for *_, s, _a in
                                    [(x[0], x[1], x[2], x[4]) for x in trace["step"]]), 9),
            "dead": r["survival"].get("dead", []),
        },
        "spend_counts": dict(spends),
        "spend_wh_by_site": {k: round(v, 9) for k, v in spend_wh.items()},
        "hourly": hourly,
        "cloud_discretisation": cloud_stats,
        "cross_check": {
            "declared_vs_measured_sparse": 6 * (4.7e-4 + 3.1867792516129184e-5) - 6 * (
                4.7e-4 + spend_wh["_charge_radio"] / max(1, spends["_charge_radio"])),
            "declared_vs_measured_dense": 12 * (4.7e-4 + 3.1867792516129184e-5) - 12 * (
                4.7e-4 + spend_wh["_charge_radio"] / max(1, spends["_charge_radio"])),
            "hourly_sparse_median_vs_declared": load_sparse - 6 * (4.7e-4 + 3.1867792516129184e-5),
            "hourly_dense_median_vs_declared": load_dense - 12 * (4.7e-4 + 3.1867792516129184e-5),
        },
        "note": ("逐小时负载由**花费账本**给出（与容量溢出无关）；`load_from_soc_delta_wh` 只在"
                 "未触顶的可信小时上作旁证，触顶小时的差值含溢出。"
                 "本文件只出实测数据，判定见 code/experiments/audit_seqref.py。"),
    }
    path = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps(out["measured"], ensure_ascii=False, indent=1))
    print(json.dumps(out["node_totals"], ensure_ascii=False, indent=1))
    print("saved", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
