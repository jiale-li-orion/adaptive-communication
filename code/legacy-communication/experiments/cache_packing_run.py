"""§31 备选 3 第一项判别：**按监测义务使用一次已有上报机会**（设备缓存/打包纪律）。
本模块引用的 `docs/…` 路径为作者本地过程文档，不随仓库发布。

判定规则**先写定**在
`docs/s7-method/instance-v1/36-pre-registration-cache-packing-2026-09-14.md`。
本脚本只执行与读数，**不得**按结果回头改规则。**先不做 agent**（§31 第 93 行）。

    python3 code/experiments/cache_packing_run.py --seeds 10

写 `results/cache_packing.json`。
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

#: 五条纪律。**前三条是仓库既有成果，不得当新贡献**（`lifo` 见 `11-aoi-defect-and-cache-service`）。
DISCIPLINES = ("fifo", "lifo", "latest_only", "edf", "obligation_greedy")
#: 条件：`(来源 tag, 覆盖项, 用途)`。**全部复用已登记条件**，只在负对照上改任务长度与中断。
CONDITIONS = {
    "C1_long_outage": ("instance_accout40_fifo", {}, "已登记 48 h / 接入中断 40 h，**预期激活**"),
    "C2_short_negative": ("instance_accout40_fifo",
                          {"task_hours": 12.0, "tail_hours": 1.0, "access_outage_h": 0.0},
                          "**负对照**：12 h、无中断，**预期不激活**"),
    "C3a_normal_cadence": ("instance_arms", {}, "现有常态节奏（12 h、i.i.d. 回传）"),
    "C3b_second_source": ("instance_ccorral_iid_c0.05", {}, "现有第二来源节奏（900 s 义务）"),
    "C3c_burst_link": ("instance_polar_c0.05", {}, "现有**长突发链路**片段"),
}


def extract(run: dict) -> dict:
    rt, en = run["routine"], (run.get("energy") or {}).get("per_node") or {}
    cm, cb = run.get("communication") or {}, run.get("cache_backlog") or {}
    return {
        "service": rt["delivered"], "denom": rt["n"],
        "missing_collection": rt["missing_collection"],
        "missing_delivery": rt["missing_delivery"], "aoi_mean_s": rt["aoi_mean_s"],
        "energy_consumed_wh": round(sum((v.get("consumed_wh") or 0.0) for v in en.values()), 8),
        "uplinks": cm.get("uplinks"), "uplinks_heard": cm.get("uplinks_heard"),
        "downlink_attempts": cm.get("downlink_attempts"),
        "airtime_uplink_h": cm.get("airtime_uplink_h"),
        # 激活量
        "over_payload_ticks": cb.get("over_payload_ticks"),
        "over_payload_peak": cb.get("over_payload_peak"),
        "cache_len_mean": cb.get("cache_len_mean"),
        "dropped_total": cb.get("dropped_total"),
    }


def mean_of(runs, key):
    vals = [extract(r)[key] for r in runs]
    vals = [v for v in vals if v is not None]
    return (sum(vals) / len(vals)) if vals else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--out", default="cache_packing")
    args = ap.parse_args()

    out: dict = {"disciplines": list(DISCIPLINES), "conditions": {},
                 "policy": ("fifo 后端既有自动补发＝基线；lifo 是**仓库既有成果**；"
                            "edf 与 obligation_greedy 是教科书式/普通贪心——都不是本文机制")}
    for cond, (tag, over, note) in CONDITIONS.items():
        src = _os.path.join(RES, f"{tag}.json")
        if not _os.path.exists(src):
            print(f"  [skip] {cond}: 缺少 {tag}.json")
            continue
        cfg = json.load(open(src, encoding="utf-8"))["config"]
        kw = build_kwargs(dict(cfg))
        kw.pop("trace", None)
        # `build_kwargs` 会把登记条件里的 `cache_service` 一起搬过来；本轮要**逐纪律扫**它，
        # 所以先摘掉，再按纪律显式传。
        kw.pop("cache_service", None)
        kw.update(over)
        arms = [a.strip() for a in str(kw.get("arms") or "local").split(",") if a.strip()]
        rows: dict = {}
        peaks: dict = {}          # 跨种子**最大**积压深度（不是均值）
        for disc in DISCIPLINES:
            per_arm = {}
            for arm in arms:
                runs = [one_seed(s, arm=arm, cache_service=disc, **kw)
                        for s in range(args.seeds)]
                per_arm[arm] = {k: mean_of(runs, k) for k in extract(runs[0])}
                if arm == arms[0]:
                    peaks[disc] = max(int(extract(r)["over_payload_peak"] or 0)
                                      for r in runs)
            rows[disc] = per_arm
        # 主臂：条件里声明的第一条（C1 是 local）。**业务读数按"相对 fifo 的变化"看**。
        main_arm = arms[0]
        effect = {}
        for disc in DISCIPLINES:
            a, b = rows[disc][main_arm], rows["fifo"][main_arm]
            effect[disc] = {
                "d_service": round((a["service"] or 0) - (b["service"] or 0), 4),
                "d_missing_collection": round((a["missing_collection"] or 0)
                                              - (b["missing_collection"] or 0), 4),
                "d_aoi_s": (round((a["aoi_mean_s"] or 0) - (b["aoi_mean_s"] or 0), 1)
                            if a["aoi_mean_s"] is not None and b["aoi_mean_s"] is not None else None),
                "d_airtime_uplink_h": round((a["airtime_uplink_h"] or 0)
                                            - (b["airtime_uplink_h"] or 0), 6),
                "d_dropped": round((a["dropped_total"] or 0) - (b["dropped_total"] or 0), 2),
            }
        act = rows["fifo"][main_arm]
        # 激活量的峰值必须取**跨种子最大**——取平均会把"只有一个种子激活"摊成一个小数字，
        # 看上去像"没激活"（第一版就踩了这个：40 次激活的档平均峰值只有 11.3）。
        peak_max = max(peaks.values()) if peaks else 0
        # **事后诊断（不改 R1）**：四条"纯打包次序"纪律 vs `latest_only`。
        # `latest_only` 不是"在包内容量内挑哪些记录"，它是**主动丢弃**旧记录——
        # 因此它**注定在没有激活时也改变读数**，不该拿它去检验 R1 的"无激活即无差别"。
        PURE = ("fifo", "lifo", "edf", "obligation_greedy")
        spread_pure = max(abs(effect[d]["d_service"]) for d in PURE)
        out["conditions"][cond] = {
            "source": f"results/{tag}.json", "note": note, "overrides": over,
            "seeds": args.seeds, "arms": arms, "main_arm": main_arm,
            "rows": rows, "effect_vs_fifo_on_main_arm": effect,
            "activation": {"over_payload_ticks": act["over_payload_ticks"],
                           "over_payload_peak": act["over_payload_peak"],
                           "over_payload_peak_max_across_seeds": peak_max,
                           "cache_len_mean": act["cache_len_mean"],
                           "payload_slots": 32},
        }
        # R1 / R2 / R4 的机械判定（只报数值，不替读者下结论）
        spread = max(abs(effect[d]["d_service"]) for d in DISCIPLINES)
        out["conditions"][cond]["verdict"] = {
            "activated": bool((act["over_payload_ticks"] or 0) > 0),
            "max_abs_d_service_across_disciplines": round(spread, 4),
            "R1_negative_control_ok": (bool((act["over_payload_ticks"] or 0) == 0)
                                       and spread < 1.0),
            "max_abs_d_service_pure_packing": round(spread_pure, 4),
            "R1_pure_packing_only": (bool((act["over_payload_ticks"] or 0) == 0)
                                     and spread_pure < 1.0),
            "best_by_service": max(DISCIPLINES,
                                   key=lambda d: rows[d][main_arm]["service"] or 0),
        }

    path = _os.path.join(RES, f"{args.out}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"wrote {path}\n")
    for cond, blk in out["conditions"].items():
        a = blk["activation"]
        print(f"=== {cond}  主臂={blk['main_arm']}  {blk['note']}")
        print(f"  激活量: 超载荷容量 tick 数={a['over_payload_ticks']} "
              f"峰值(跨种子最大)={a['over_payload_peak_max_across_seeds']} "
              f"平均缓存深度={a['cache_len_mean']}（容量 {a['payload_slots']}）")
        print(f"  {'纪律':<19}{'服务':>7}{'缺采':>7}{'缺送':>7}{'AoI s':>8}{'上行':>7}{'空口h':>8}{'丢弃':>7}{'Δ服务':>8}")
        for d in DISCIPLINES:
            r = blk["rows"][d][blk["main_arm"]]
            e = blk["effect_vs_fifo_on_main_arm"][d]
            print(f"  {d:<19}{(r['service'] or 0):>7.1f}{(r['missing_collection'] or 0):>7.1f}"
                  f"{(r['missing_delivery'] or 0):>7.1f}{(r['aoi_mean_s'] or 0):>8.0f}"
                  f"{(r['uplinks'] or 0):>7.0f}{(r['airtime_uplink_h'] or 0):>8.4f}"
                  f"{(r['dropped_total'] or 0):>7.1f}{e['d_service']:>8.2f}")
        v = blk["verdict"]
        print(f"  ⇒ 激活={v['activated']}  五条纪律最大|Δ服务|={v['max_abs_d_service_across_disciplines']}"
              f"  四条纯打包纪律最大|Δ服务|={v['max_abs_d_service_pure_packing']}"
              f"  R1(全部)={v['R1_negative_control_ok']}  R1(仅纯打包)={v['R1_pure_packing_only']}"
              f"  服务最高={v['best_by_service']}")
        print()


if __name__ == "__main__":
    main()
