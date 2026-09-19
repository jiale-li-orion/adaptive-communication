"""交付 3：**能源受限上下文中的中心/网关位置对照**。
本模块引用的 `docs/…` 路径为作者本地过程文档，不随仓库发布。

预注册先写定在
`docs/s7-method/instance-v1/46-pre-registration-energy-placement-2026-09-14.md`。

三档条件（共用中断前外生过程，由同一个种子决定）：
`O0 无中断` / `O1 接入中断 [3h,12h)` / `O2 回传中断 [3h,12h)`。
**O0 是配对基准**——两位置在中断前就可能已经不同，O1/O2 的差必须相对它报告。

    python3 code/experiments/energy_limited_placement.py --seeds 10

写 `results/energy_limited_placement.json`。
"""
from __future__ import annotations

import argparse
import json
import os as _os
import statistics as st
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
BASE_TAG = "instance_adm_out3"        # capacity 0.02 / hetero / low 0 / 接入 [3h,12h)
ARMS = ("local", "ea_nb")
PLACEMENTS = ("center", "gateway")
OUT_START_S, OUT_END_S = 3 * 3600, 12 * 3600
# **每一档都必须把两个中断字段写全。** 第一版 O0 写成 `{}`，而基底
# `instance_adm_out3.json` 的 config **本身就带 `access_outage_h=9.0`** ⇒ O0 与 O1 都带着接入中断、
# 数字**完全相同**（这就是发现它的方式），**O0 根本不是无中断基准**。
# 教训与 `build_kwargs` 文档里那句一样：**静默继承一个字段会让"重放"跑成另一个实例。**
CONDITIONS = {
    "O0_no_outage": {"access_outage_h": 0.0, "access_outage_start_h": 3.0,
                     "outage_hours": 0.0, "outage_start_h": 0.0},
    "O1_access_outage": {"access_outage_h": 9.0, "access_outage_start_h": 3.0,
                         "outage_hours": 0.0, "outage_start_h": 0.0},
    "O2_backhaul_outage": {"access_outage_h": 0.0, "access_outage_start_h": 3.0,
                           "outage_hours": 9.0, "outage_start_h": 3.0},
}


def _config_changes(events) -> list[dict]:
    """节点**真实**配置的变化点（trace 的 `state` 事件）。"""
    last, out = {}, []
    for ev in events:
        if ev[2] != "state":
            continue
        t_s, nid, i, r = ev[0], ev[1], ev[3], ev[4]
        if nid not in last:
            last[nid] = (i, r)
        elif last[nid] != (i, r):
            last[nid] = (i, r)
            out.append({"t_s": t_s, "node": nid, "sampling_interval_s": i,
                        "report_period_s": r})
    return out


def _evidence_ages(events) -> list[int]:
    return [ev[6] for ev in events
            if ev[2] == "plan" and len(ev) > 6 and ev[6] is not None]


def extract(run: dict) -> dict:
    rt = run["routine"]
    en = (run.get("energy") or {}).get("per_node") or {}
    cm = run.get("communication") or {}
    cb = run.get("cache_backlog") or {}
    ch = _config_changes(run.get("_trace") or [])
    ages = _evidence_ages(run.get("_trace") or [])
    # **降档生效时刻**：中断开始后第一次把采样间隔**改稀**（数值变大）的时刻。
    down = [(c["t_s"], c["node"], c["sampling_interval_s"]) for c in ch
            if c["t_s"] >= OUT_START_S and c["sampling_interval_s"] >= 3600]
    return {
        "service": rt["delivered"], "denom": rt["n"],
        "missing_collection": rt["missing_collection"],
        "missing_delivery": rt["missing_delivery"], "aoi_mean_s": rt["aoi_mean_s"],
        "energy_consumed_wh": round(sum((v.get("consumed_wh") or 0.0) for v in en.values()), 8),
        "nodes_dead": sum(1 for v in en.values() if v.get("dead_at_s") is not None),
        "soc_final_min_wh": min(((v.get("soc_final_wh") or 0.0) for v in en.values()),
                                default=None),
        "deficit_s_total": sum((v.get("deficit_s") or 0) for v in en.values()),
        "uplinks": cm.get("uplinks"), "downlink_attempts": cm.get("downlink_attempts"),
        "airtime_uplink_h": cm.get("airtime_uplink_h"),
        "over_payload_ticks": cb.get("over_payload_ticks"),
        "n_config_changes": len(ch),
        "n_downgrades_after_outage": len(down),
        "first_downgrade_t_s": (min((d[0] for d in down)) if down else None),
        "evidence_age_median_s": (st.median(ages) if ages else None),
        "evidence_age_max_s": (max(ages) if ages else None),
    }


def _mean(xs):
    v = [x for x in xs if x is not None]
    return (round(sum(v) / len(v), 6) if v else None)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--out", default="energy_limited_placement")
    args = ap.parse_args()

    cfg = json.load(open(_os.path.join(RES, f"{BASE_TAG}.json"), encoding="utf-8"))["config"]
    base = build_kwargs(dict(cfg))
    base.pop("trace", None)
    base.pop("cache_service", None)

    out = {"base": BASE_TAG, "base_config_used": {k: base.get(k) for k in
           ("task_hours", "capacity_wh", "harvest_mode", "low_wh_per_hour",
            "sample_interval_s", "report_period_s", "routine_period_s", "seeds")},
           "conditions": CONDITIONS, "arms": list(ARMS), "placements": list(PLACEMENTS),
           "note": ("O0 是**配对基准**：两位置在中断前就可能不同，O1/O2 的差必须相对它报告。"
                    "O2（回传中断 [3h,12h)）是**新声明的因子组合**，不是已登记结果的重放。"),
           "rows": {}, "paired": {}}

    for cond, over in CONDITIONS.items():
        kw = {**base, **over}
        # **响亮检查**：三档的中断设置必须真的不同，且与本档声明一致。
        # 少写一个字段就会静默继承基底的接入中断（第一版就是这么错的）。
        want = (over["access_outage_h"], over["access_outage_start_h"],
                over["outage_hours"], over["outage_start_h"])
        got = (kw["access_outage_h"], kw["access_outage_start_h"],
               kw["outage_hours"], kw["outage_start_h"])
        assert got == want, f"{cond}: 中断设置与声明不符：{got} != {want}"
        out["rows"][cond] = {}
        per_seed: dict[tuple, list] = {}
        for arm in ARMS:
            for pl in PLACEMENTS:
                runs = [one_seed(s, arm=arm, placement=pl, trace=True,
                                 obligation_ledger=True, **kw)
                        for s in range(args.seeds)]
                per_seed[(arm, pl)] = runs
                keys = list(extract(runs[0]))
                out["rows"][cond][f"{arm}|{pl}"] = {
                    k: _mean([extract(r)[k] for r in runs]) for k in keys}
                out["rows"][cond][f"{arm}|{pl}"]["seeds"] = args.seeds
        # **配对差（网关 − 中心）**：同种子
        out["paired"][cond] = {}
        for arm in ARMS:
            c, g = per_seed[(arm, "center")], per_seed[(arm, "gateway")]
            d = {}
            for k in ("service", "missing_collection", "missing_delivery",
                      "energy_consumed_wh", "nodes_dead", "soc_final_min_wh",
                      "uplinks", "downlink_attempts", "airtime_uplink_h",
                      "evidence_age_median_s", "n_downgrades_after_outage",
                      "first_downgrade_t_s"):
                v = [extract(gi)[k] - extract(ci)[k]
                     for ci, gi in zip(c, g)
                     if extract(gi)[k] is not None and extract(ci)[k] is not None]
                d[k] = {"mean": _mean(v), "n_gt0": sum(1 for x in v if x > 1e-9),
                        "n_lt0": sum(1 for x in v if x < -1e-9), "n": len(v)}
            out["paired"][cond][arm] = d

    sigs = {c: tuple(sorted({**base, **o}.items())) for c, o in CONDITIONS.items()}
    assert len(set(sigs.values())) == len(sigs), "三档条件有重复（中断字段没写全）"
    path = _os.path.join(RES, f"{args.out}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"wrote {path}\n")
    for cond in CONDITIONS:
        print(f"=== {cond}  {CONDITIONS[cond]}")
        print(f"  {'arm|placement':<18}{'服务':>7}{'缺采':>7}{'缺送':>7}{'死节点':>7}"
              f"{'末电量min':>10}{'能耗Wh':>9}{'证据年龄中位':>13}{'中断后降档':>11}")
        for k, r in out["rows"][cond].items():
            print(f"  {k:<18}{(r['service'] or 0):>7.1f}{(r['missing_collection'] or 0):>7.1f}"
                  f"{(r['missing_delivery'] or 0):>7.1f}{(r['nodes_dead'] or 0):>7.1f}"
                  f"{(r['soc_final_min_wh'] or 0):>10.5f}{(r['energy_consumed_wh'] or 0):>9.4f}"
                  f"{(r['evidence_age_median_s'] or 0):>13.0f}"
                  f"{(r['n_downgrades_after_outage'] or 0):>11.1f}")
        print(f"  配对差（网关−中心）：")
        for arm in ARMS:
            d = out["paired"][cond][arm]
            print(f"    {arm:<8} 服务 {d['service']['mean']:+.2f} "
                  f"缺采 {d['missing_collection']['mean']:+.2f} "
                  f"死节点 {d['nodes_dead']['mean']:+.2f} "
                  f"末电量 {d['soc_final_min_wh']['mean'] if d['soc_final_min_wh']['mean'] is not None else 0:+.5f} "
                  f"能耗 {d['energy_consumed_wh']['mean']:+.5f} "
                  f"| 缺采 更好{d['missing_collection']['n_lt0']}/更差{d['missing_collection']['n_gt0']}")
        print()


if __name__ == "__main__":
    main()
