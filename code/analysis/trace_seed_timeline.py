#!/usr/bin/env python3
"""把**一次运行**的逐事件时间线拉出来：中心看到什么 → 下了什么 → 何时真的生效 → 节点在跑什么。

**为什么需要它。** 结果文件只存聚合量（交付/缺采/缺送/下行/亏空），**存不下这条链**。
而"配置生效之后中心失去有效控制、加密持续耗电"这类问题**只有把链连起来才答得上**——
聚合量只能说明"损害发生了"，不能说明"损害是哪一次配置、在哪一刻、经由哪条路径造成的"。

它做三件事：
  1. 用**与登记完全相同的参数**重跑一个 seed，并**逐列核对聚合量没有因为开 trace 而改变**
     （`Instance.__init__(trace=...)` 关闭时一个字节都不记，所以这是必须成立的自检）；
  2. 打印该 seed 的关键时刻：第一次加密生效、最后一次有效电量反馈、第一次缺采；
  3. 按节点给出"生效配置段"——每一段是 (起始时刻, 采样间隔, 上报周期, 该段内的真实耗电)。

Run:
    export PYTHONPATH="$PWD/libs/pylibs"
    python3 code/analysis/trace_seed_timeline.py --tag soc2_bias3.0 --seed 7 --arm ea_nb
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
for _p in (os.path.join(ROOT, "code", "experiments"),
           os.path.join(ROOT, "code", "instance"),
           os.path.join(ROOT, "code", "monitoring"),
           os.path.join(ROOT, "code", "physics")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from instance_run import one_seed  # noqa: E402

#: `config` 里的键 → `one_seed` 的形参名。**只映射真的影响这一次运行的量**；
#: 输出标签之类的元数据不在此列（`tag`、`arms`、`exec_layers`、`seeds`）。
KEYS = ("task_hours", "tail_hours", "outage_start_h", "outage_hours",
        "hold_every", "hold_s", "harvest_wh_per_hour", "sample_interval_s",
        "report_period_s", "routine_period_s", "uplink_p_arrive", "backhaul_p_good",
        "event_spacing_s", "harvest_mode", "access_outage_h",
        "access_outage_start_h", "blackout_start_h", "blackout_frac",
        "soc_max_age_s", "soc_noise_wh", "soc_bias", "soc_loss_p", "hold_op",
        "capacity_wh", "low_frac", "low_wh_per_hour", "oracle_soc_bins",
        "solar_day_start_h", "solar_peak_wh_per_hour", "solar_cloud_p",
        "solar_cloud_atten", "solar_snow_frac", "solar_snow_start_h",
        "solar_shade_frac", "initial_soc", "irr_start_h", "irr_peak_wh_per_hour",
        "irr_shade_frac", "irr_snow_frac", "irr_snow_after_h", "irr_source_temp",
        "irr_year", "charge_min_c", "idle_wh_per_tick", "cache_service",
        "energy_scale")

#: 映射到 `one_seed` 形参名不同的几个键。
RENAME = {"soc_bias": "soc_bias"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True, help="已登记的结果文件 tag（不带 instance_ 前缀）")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--node", default="", help="只打印这台节点；空表示全部")
    ap.add_argument("--dump", default="", help="把完整时间线写到这个路径（jsonl）")
    args = ap.parse_args()

    path = os.path.join(ROOT, "results", f"instance_{args.tag}.json")
    doc = json.load(open(path, encoding="utf-8"))
    cfg = dict(doc["config"])

    kwargs = {}
    for k in KEYS:
        if k in cfg and cfg[k] is not None and cfg[k] != "":
            kwargs[RENAME.get(k, k)] = cfg[k]
    if kwargs.get("charge_min_c") == "off":
        kwargs["charge_min_c"] = None
    else:
        kwargs["charge_min_c"] = float(kwargs.get("charge_min_c", 5.0))
    for b in ("dynamic_oracle", "irr_no_source_temp"):
        kwargs.pop(b, None)

    # 1) 先用**登记时的参数**跑一次（不开 trace），作为逐列核对的基准。
    plain = one_seed(args.seed, arm=args.arm, contract=True, **kwargs)
    traced = one_seed(args.seed, arm=args.arm, contract=True, trace=True, **kwargs)

    same, diff = True, []
    for k, v in plain.items():
        w = traced.get(k)
        if isinstance(v, (int, float, str, bool)) or v is None:
            if v != w:
                same = False
                diff.append(f"{k}: {v} vs {w}")
    print(f"[自检] 开 trace 后聚合量逐列相同: {same}")
    if not same:
        print("   差异:", diff[:8])

    # 2) 与已登记的结果文件里同一 (arm, seed) 的那一行对齐。
    rows = [r for r in doc["runs"] if r["arm"] == args.arm and r["seed"] == args.seed]
    if rows:
        r0 = rows[0]
        for label, got, want in (
                ("周期交付", traced["routine"]["delivered"], r0["routine"]["delivered"]),
                ("缺采", traced["routine"]["missing_collection"],
                 r0["routine"]["missing_collection"]),
                ("缺送", traced["routine"]["missing_delivery"],
                 r0["routine"]["missing_delivery"])):
            flag = "✓" if abs(got - want) < 1e-9 else "✗"
            print(f"[自检] {label}: 重跑 {got} vs 登记 {want} {flag}")

    ev = traced.get("_trace") or []
    if args.dump:
        with open(args.dump, "w", encoding="utf-8") as fh:
            for e in ev:
                fh.write(json.dumps(e, ensure_ascii=False) + "\n")
        print(f"时间线已写 {args.dump}（{len(ev)} 条事件）")

    nodes = sorted({e[1] for e in ev})
    if args.node:
        nodes = [n for n in nodes if n == args.node]
    for nid in nodes:
        mine = [e for e in ev if e[1] == nid]
        states = [e for e in mine if e[2] == "state"]
        if not states:
            continue
        # 生效配置段：两个字段**同时**不变的一段算一段。
        segs, cur = [], None
        for e in states:
            key = (e[3], e[4])
            if cur is None or key != cur[0]:
                if cur is not None:
                    segs.append(cur)
                cur = [key, e[0], e[0], e[5], e[5]]
            else:
                cur[2] = e[0]
                cur[4] = e[5]
        if cur is not None:
            segs.append(cur)
        acts = [e for e in mine if e[2] in ("plan", "applied")]
        obs = [e for e in mine if e[2] == "plan"]
        print(f"\n=== {nid} ===")
        print(f"  中心为它生成的意图 {len(obs)} 条、节点侧生效写入 {len([e for e in acts if e[2]=='applied'])} 次")
        print("  生效配置段（起始 h, 采样 s, 上报 s, 段内 SoC 起→止）:")
        for k, t0, t1, s0, s1 in segs:
            print(f"     {t0//3600:>3}h–{t1//3600:>3}h  采样 {k[0]:>5}s  上报 {k[1]:>5}s  "
                  f"SoC {s0:.4f} → {s1:.4f}")
        last_plan = obs[-1][0] // 3600 if obs else None
        print(f"  最后一次生成意图: {last_plan}h;  节点最后存活: "
              f"{'是' if states[-1][6] else '否'}（末状态 {states[-1][3]}s/{states[-1][4]}s）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
