"""备选 3 补充判别：**一窗多条记录**（采样周期细于义务周期）。
本模块引用的 `docs/…` 路径为作者本地过程文档，不随仓库发布。

预注册先写定在
`docs/s7-method/instance-v1/40-pre-registration-multirecord-2026-09-14.md`。

**为什么补这一档**：doc 36 的五档里采样周期**恰好等于**义务周期 ⇒ 每窗只有一条记录
⇒ 到达顺序就是截止期顺序（FIFO ≡ EDF）、去重**无对象可去**。
那五档测的是「匹配规则在它没有对象时」，**不是**「匹配规则没用」。本档补上那个对象。

    python3 code/experiments/cache_packing_multirecord.py --seeds 10

写 `results/cache_packing_multirecord.json`。
"""
from __future__ import annotations

import argparse
import json
import os as _os
import sys as _sys

_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, _CODE,
           *(_os.path.join(_CODE, d) for d in
             ("physics", "runtime", "experiments", "analysis", "monitoring", "instance"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

from instance_run import one_seed                                        # noqa: E402
from trace_seed_timeline import build_kwargs                             # noqa: E402

RES = _os.path.normpath(_os.path.join(_CODE, "..", "results"))
DISCIPLINES = ("fifo", "lifo", "latest_only", "edf", "obligation_greedy")
PURE = ("fifo", "lifo", "edf", "obligation_greedy")     # 纯打包次序（不含会丢弃的 latest_only）
#: `(来源 tag, 覆盖项, 每窗记录数, 用途)`
CONDITIONS = {
    "E1_multirecord_no_outage": ("instance_arms", {"sample_interval_s": 600}, 6,
                                 "一窗 6 条 · 无中断"),
    "E2_multirecord_long_outage": ("instance_accout40_fifo", {"sample_interval_s": 600}, 6,
                                   "一窗 6 条 · 接入中断 40 h（**预期激活**）"),
    "E3_negative_one_per_window": ("instance_accout40_fifo", {}, 1,
                                   "**负对照**：一窗 1 条（匹配规则必须为空操作）"),
}


def extract(run: dict) -> dict:
    rt, en = run["routine"], (run.get("energy") or {}).get("per_node") or {}
    cm, cb = run.get("communication") or {}, run.get("cache_backlog") or {}
    return {
        "service": rt["delivered"], "denom": rt["n"],
        "missing_collection": rt["missing_collection"],
        "missing_delivery": rt["missing_delivery"], "aoi_mean_s": rt["aoi_mean_s"],
        "energy_consumed_wh": round(sum((v.get("consumed_wh") or 0.0) for v in en.values()), 8),
        "uplinks": cm.get("uplinks"), "downlink_attempts": cm.get("downlink_attempts"),
        "airtime_uplink_h": cm.get("airtime_uplink_h"),
        "over_payload_ticks": cb.get("over_payload_ticks"),
        "over_payload_peak": cb.get("over_payload_peak"),
        "cache_len_mean": cb.get("cache_len_mean"),
        "dropped_total": cb.get("dropped_total"),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--out", default="cache_packing_multirecord")
    args = ap.parse_args()

    out: dict = {"disciplines": list(DISCIPLINES), "seeds": args.seeds, "conditions": {}}
    for cond, (tag, over, per_window, note) in CONDITIONS.items():
        cfg = json.load(open(_os.path.join(RES, f"{tag}.json"), encoding="utf-8"))["config"]
        kw = build_kwargs(dict(cfg))
        kw.pop("trace", None)
        kw.pop("cache_service", None)
        kw.update(over)
        arm = "local"                      # 零中心控制 ⇒ 差异只来自设备侧打包纪律
        rows, peaks = {}, {}
        for disc in DISCIPLINES:
            runs = [one_seed(s, arm=arm, cache_service=disc, **kw) for s in range(args.seeds)]
            keys = list(extract(runs[0]))
            rows[disc] = {k: _mean([extract(r)[k] for r in runs]) for k in keys}
            peaks[disc] = max(int(extract(r)["over_payload_peak"] or 0) for r in runs)

        base = rows["fifo"]
        effect = {d: {
            "d_service": round((rows[d]["service"] or 0) - (base["service"] or 0), 4),
            "d_airtime_uplink_h": round((rows[d]["airtime_uplink_h"] or 0)
                                        - (base["airtime_uplink_h"] or 0), 6),
            "d_energy_wh": round((rows[d]["energy_consumed_wh"] or 0)
                                 - (base["energy_consumed_wh"] or 0), 6),
            "d_missing_collection": round((rows[d]["missing_collection"] or 0)
                                          - (base["missing_collection"] or 0), 4),
            "d_dropped": round((rows[d]["dropped_total"] or 0)
                               - (base["dropped_total"] or 0), 2),
        } for d in DISCIPLINES}
        activated = bool((base["over_payload_ticks"] or 0) > 0)
        out["conditions"][cond] = {
            "source": f"results/{tag}.json", "overrides": over, "note": note,
            "records_per_window": per_window, "arm": arm,
            "rows": rows, "effect_vs_fifo": effect,
            "activation": {"over_payload_ticks": base["over_payload_ticks"],
                           "over_payload_peak_max_across_seeds": max(peaks.values()),
                           "cache_len_mean": base["cache_len_mean"], "payload_slots": 32},
            "verdict": {
                "activated": activated,
                "max_abs_d_service_pure": round(max(abs(effect[d]["d_service"])
                                                    for d in PURE), 4),
                "R1_negative_control_ok": (per_window == 1
                                           and all(abs(effect[d]["d_service"]) < 1e-9
                                                   for d in PURE)),
                "best_by_service": max(DISCIPLINES,
                                       key=lambda d: rows[d]["service"] or 0),
                "best_by_airtime": min(DISCIPLINES,
                                       key=lambda d: rows[d]["airtime_uplink_h"] or 9e9),
            },
        }

    path = _os.path.join(RES, f"{args.out}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"wrote {path}\n")
    for cond, blk in out["conditions"].items():
        a = blk["activation"]
        print(f"=== {cond}  {blk['note']}（一窗 {blk['records_per_window']} 条，臂={blk['arm']}）")
        print(f"  激活: tick={a['over_payload_ticks']} 峰值(max)={a['over_payload_peak_max_across_seeds']} "
              f"平均缓存深度={a['cache_len_mean']}（容量 {a['payload_slots']}）")
        print(f"  {'纪律':<19}{'服务':>8}{'缺采':>7}{'缺送':>7}{'AoI s':>8}{'上行':>7}"
              f"{'空口h':>9}{'能耗Wh':>9}{'丢弃':>7}{'Δ服务':>8}")
        for d in DISCIPLINES:
            r, e = blk["rows"][d], blk["effect_vs_fifo"][d]
            print(f"  {d:<19}{(r['service'] or 0):>8.1f}{(r['missing_collection'] or 0):>7.1f}"
                  f"{(r['missing_delivery'] or 0):>7.1f}{(r['aoi_mean_s'] or 0):>8.0f}"
                  f"{(r['uplinks'] or 0):>7.0f}{(r['airtime_uplink_h'] or 0):>9.4f}"
                  f"{(r['energy_consumed_wh'] or 0):>9.4f}{(r['dropped_total'] or 0):>7.1f}"
                  f"{e['d_service']:>8.2f}")
        v = blk["verdict"]
        print(f"  ⇒ 激活={v['activated']} 纯打包最大|Δ服务|={v['max_abs_d_service_pure']} "
              f"R1={v['R1_negative_control_ok']} 服务最高={v['best_by_service']} "
              f"空口最省={v['best_by_airtime']}")
        print()


def _mean(xs):
    v = [x for x in xs if x is not None]
    return (sum(v) / len(v)) if v else None


if __name__ == "__main__":
    main()
