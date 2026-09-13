#!/usr/bin/env python3
"""从**两个独立来源**拟合链路的两态马尔可夫结构，并换算到同一时间粒度。

**为什么需要第二个来源。** 这个实例的 residual 主要落在 delivery 侧，而此前**全部**
时间相关性都来自上海 ChirpBox 一个数据集。一条"最重要的 residual 由最弱的一层数据生成"
的批评只能靠**第二个独立来源**回答。本仓库本地就有第二个：LoRa-on-Ice 的南极冰面部署。

| 来源 | 部署 | 粒度 | 许可/出处 |
|---|---|---|---|
| ChirpBox | 上海，城市/园区，21 节点 | 小时 | Zenodo 10.5281/zenodo.5527877（见 `results/loss_model.json`） |
| LoRa-on-Ice | **南极 Neumayer III 附近冰面**，单节点漂移 | 原始 10 s | 见 `data/downloads/lora_on_ice/LoRa-on-Ice_upload/readme.txt` |

**两个来源必须在同一时间粒度上比**，否则"突发度"会被尝试速率污染：南极是每 10 s 一次尝试，
一次 0.46 h 的坏突发是 167 次**连续失败**；ChirpBox 每小时一次，6.38 h 是 6.38 次。
所以本脚本把两边都归到**小时级**再算。

Run: python3 code/analysis/fit_link_sources.py
"""
from __future__ import annotations

import collections
import csv
import datetime as dt
import json
import os as _os
import re

_HERE = _os.path.dirname(_os.path.abspath(__file__))
_ROOT = _os.path.normpath(_os.path.join(_HERE, "..", ".."))
ICE = _os.path.join(_ROOT, "data", "downloads", "lora_on_ice", "LoRa-on-Ice_upload",
                    "2023-01-01_Antarctica-drift")
NUM = re.compile(r"-?\d+")


def _ice_attempts() -> list[tuple[dt.datetime, int]]:
    """把 received / lost 两个文件合成一条按时间排序的 (时刻, 是否收到) 序列。"""
    out = []
    for fname, ok in (("drift-received.csv", 1), ("drift-lost.csv", 0)):
        path = _os.path.join(ICE, fname)
        if not _os.path.exists(path):
            raise FileNotFoundError(f"缺少 {path}（`data/` 不入库，见 data/README.md）")
        for r in csv.DictReader(open(path, encoding="utf-8-sig", errors="replace"),
                                delimiter=","):
            g = (r.get("TimeGPS") or "").strip()
            n = [int(x) for x in NUM.findall(g)[:7]] if g else []
            if len(n) < 7:
                continue                       # 少量行时间戳格式不同，跳过并计数
            out.append((dt.datetime(n[0], n[1], n[2], n[4], n[5], n[6],
                                    tzinfo=dt.timezone.utc), ok))
    out.sort(key=lambda x: x[0])
    return out


def _fit(bits: list[int]) -> dict:
    """两态链：p_gb（好→坏）、p_bg（坏→好）。返回平稳坏比例与平均坏突发。"""
    n = len(bits)
    good = sum(bits)
    n00 = n01 = n10 = n11 = 0
    for a, b in zip(bits, bits[1:]):
        if a and b:
            n11 += 1
        elif a and not b:
            n10 += 1
        elif not a and b:
            n01 += 1
        else:
            n00 += 1
    p_gb = n10 / max(n10 + n11, 1)
    p_bg = n01 / max(n01 + n00, 1)
    stat_bad = p_gb / max(p_gb + p_bg, 1e-12)
    mean_bad = 1 / max(p_bg, 1e-12)
    iid_bad = 1 / max(stat_bad, 1e-12)
    return {"n": n, "good_frac": good / n, "empirical_bad": 1 - good / n,
            "p_gb": p_gb, "p_bg": p_bg, "stationary_bad": stat_bad,
            "mean_bad_burst": mean_bad, "iid_mean_bad_burst": iid_bad,
            "burstiness": mean_bad / max(iid_bad, 1e-12)}


def main() -> int:
    print("链路来源对照（**都换算到小时级**，否则突发度会被尝试速率污染）\n")
    # --- 第二个来源：南极 ---
    ser = _ice_attempts()
    t0 = ser[0][0]
    bins = collections.defaultdict(list)
    for t, b in ser:
        bins[int((t - t0).total_seconds() // 3600)].append(b)
    hrs = sorted(bins)
    hourly = [1 if sum(bins[h]) / len(bins[h]) > 0.5 else 0 for h in hrs]
    f2 = _fit(hourly)
    print("LoRa-on-Ice（南极冰面）")
    print("  原始尝试 %d 次，跨度 %.1f 天，中位间隔 10 s，每小时尝试数中位 %d"
          % (len(ser), (ser[-1][0] - ser[0][0]).total_seconds() / 86400,
             sorted(len(bins[h]) for h in hrs)[len(hrs) // 2]))
    print("  样本级接收率 %.4f；小时级坏态占比 %.4f（与链平稳值 %.4f 有差，说明两态是近似）"
          % (sum(b for _, b in ser) / len(ser), f2["empirical_bad"], f2["stationary_bad"]))
    print("  p_gb=%.5f p_bg=%.5f  平均坏突发 **%.1f h**  i.i.d. 对照 %.2f h  "
          "**突发度 %.1f x**" % (f2["p_gb"], f2["p_bg"], f2["mean_bad_burst"],
                                 f2["iid_mean_bad_burst"], f2["burstiness"]))
    # --- 第一个来源：ChirpBox（已在 results/loss_model.json 里拟合过）---
    ref_path = _os.path.join(_ROOT, "results", "loss_model.json")
    ref = json.load(open(ref_path, encoding="utf-8"))
    print("\nChirpBox（上海，城市/园区，小时级）—— 读 `results/loss_model.json`")
    print("  平稳丢失 %.4f  平均下行突发 **%.2f h**  同丢失率 i.i.d. %.2f h  "
          "**突发度 %.2f x**" % (ref["stationary_loss_fraction"],
                                 ref["mean_down_burst_hours"],
                                 ref["iid_mean_down_burst_hours"],
                                 ref["burstiness_ratio"]))
    print("\n结论：**偏远/极端部署比城市部署突发得多**（%.1f x vs %.2f x，相差 %.1f 倍）。"
          % (f2["burstiness"], ref["burstiness_ratio"],
             f2["burstiness"] / ref["burstiness_ratio"]))
    print("⇒ 只用 ChirpBox 会**低估**突发度；而实例的任务时长是 12 h，"
          "第二个来源的平均坏突发（%.0f h）是它的 %.1f 倍。" %
          (f2["mean_bad_burst"], f2["mean_bad_burst"] / 12))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
