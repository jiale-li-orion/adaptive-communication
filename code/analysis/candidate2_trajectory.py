"""§31 §七 交付 3 的第二条：**候选 2 的有量纲因果轨迹**。

要求（§31 第 109 行）：记录**为何中间配置可行**、它增加的是**哪条固定义务**的服务、
**付出多少资源**。**聚合量答不了"哪条义务"**，所以这里用 `obligation_ledger=True`
取逐义务台账，再两两做差。

> **限定（判别 B 已更正后）**：候选 2 已按预注册 R1 **关闭**——网格内部在业务口径下
> **没有任何一点超过既有 38 条臂**。所以本轨迹记录的对象**不是"网格内部的中间配置"**，
> 而是**既有端点 `aoi_const300`**：它相对同族的自适应臂 `aoi` 为何够用、增加哪条义务、代价多少。

    python3 code/analysis/candidate2_trajectory.py --seeds 3

写 `results/candidate2_trajectory.json`。
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
TAG = "instance_ccorral_iid_c0.05"        # 第二来源节奏（900 s 义务）——候选 2 唯一有差的一档
ARMS = ("local", "aoi", "aoi_const300")


def config_changes(events) -> list[dict]:
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--out", default="candidate2_trajectory")
    args = ap.parse_args()

    cfg = json.load(open(_os.path.join(RES, f"{TAG}.json"), encoding="utf-8"))["config"]
    kw = build_kwargs(dict(cfg))
    kw.pop("trace", None)
    kw.pop("cache_service", None)

    out = {"condition": TAG, "seeds": args.seeds, "arms": list(ARMS),
           "note": ("候选 2 已按 R1 关闭；本轨迹记录的是**既有端点 `aoi_const300`** 相对 `aoi` "
                    "为何够用、增加哪条义务、代价多少。逐义务台账来自 `collect_rows=True`。"),
           "per_arm": {}}
    ledgers: dict[str, list[dict]] = {}
    for arm in ARMS:
        runs = [one_seed(s, arm=arm, trace=True, obligation_ledger=True, **kw)
                for s in range(args.seeds)]
        rows = runs[0]["_obligations"]
        ledgers[arm] = rows
        # **资源列一律跨种子平均**（只报 seed 0 会与跨种子的服务均值不可比）。
        def _mean(f):
            v = [f(r) for r in runs]
            v = [x for x in v if x is not None]
            return (sum(v) / len(v)) if v else None

        def _en(r):
            return (r.get("energy") or {}).get("per_node") or {}

        out["per_arm"][arm] = {
            "denom": runs[0]["routine"]["n"],
            "service_mean": _mean(lambda r: r["routine"]["delivered"]),
            "service_per_seed": [r["routine"]["delivered"] for r in runs],
            "missing_collection": _mean(lambda r: r["routine"]["missing_collection"]),
            "aoi_mean_s": _mean(lambda r: r["routine"]["aoi_mean_s"]),
            "uplinks": _mean(lambda r: (r.get("communication") or {}).get("uplinks")),
            "downlink_attempts": _mean(lambda r: (r.get("communication") or {})
                                       .get("downlink_attempts")),
            "airtime_uplink_h": _mean(lambda r: (r.get("communication") or {})
                                      .get("airtime_uplink_h")),
            "energy_consumed_wh": _mean(lambda r: round(sum(
                (v.get("consumed_wh") or 0.0) for v in _en(r).values()), 8)),
            "nodes_dead": _mean(lambda r: sum(1 for v in _en(r).values()
                                              if v.get("dead_at_s") is not None)),
            "soc_final_min_wh": _mean(lambda r: min(
                ((v.get("soc_final_wh") or 0.0) for v in _en(r).values()), default=None)),
            "n_config_changes": _mean(lambda r: len(config_changes(r["_trace"]))),
            "config_changes": config_changes(runs[0]["_trace"])[:12],
            "config_choices": sorted({(c["sampling_interval_s"], c["report_period_s"])
                                      for c in config_changes(runs[0]["_trace"])}),
        }

    # **逐义务做差**：`aoi_const300` 相对 `aoi` 增加了哪条义务的交付、丢掉了哪条
    def _by_oid(rows):
        return {r["oid"]: r for r in rows}

    a, b = _by_oid(ledgers["aoi"]), _by_oid(ledgers["aoi_const300"])
    gained = [oid for oid in a if b[oid]["delivered"] and not a[oid]["delivered"]]
    lost = [oid for oid in a if a[oid]["delivered"] and not b[oid]["delivered"]]
    out["diff_aoi_const300_vs_aoi"] = {
        "gained": len(gained), "lost": len(lost),
        "gained_oids_sample": sorted(gained)[:12],
        "lost_oids_sample": sorted(lost)[:12],
        "gained_latency_mean_s": (round(sum(b[o]["latency_s"] for o in gained
                                            if b[o]["latency_s"] is not None)
                                        / max(1, len(gained)), 1) if gained else None),
        "lost_latency_mean_s": (round(sum(a[o]["latency_s"] for o in lost
                                          if a[o]["latency_s"] is not None)
                                      / max(1, len(lost)), 1) if lost else None),
        "gained_by_release_hour": _hist(b, gained),
    }

    path = _os.path.join(RES, f"{args.out}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"wrote {path}\n")
    print(f"=== {TAG}（900 s 义务，分母 {out['per_arm']['aoi']['denom']}，{args.seeds} 种子）")
    print(f"  {'臂':<15}{'服务':>7}{'缺采':>7}{'AoI s':>8}{'上行':>7}{'下行':>7}"
          f"{'空口h':>8}{'能耗Wh':>9}{'死节点':>7}{'末电量min':>10}{'配置变化':>7}")
    for arm in ARMS:
        r = out["per_arm"][arm]
        print(f"  {arm:<15}{r['service_mean']:>7.1f}{r['missing_collection']:>7.1f}"
              f"{(r['aoi_mean_s'] or 0):>8.0f}{(r['uplinks'] or 0):>7.0f}"
              f"{(r['downlink_attempts'] or 0):>7.1f}{(r['airtime_uplink_h'] or 0):>8.4f}"
              f"{r['energy_consumed_wh']:>9.4f}{r['nodes_dead']:>7}{r['soc_final_min_wh']:>10.5f}"
              f"{r['n_config_changes']:>7}")
    d = out["diff_aoi_const300_vs_aoi"]
    print(f"\n  逐义务做差（aoi_const300 − aoi，seed 0）：新增交付 **{d['gained']}** 条、"
          f"丢掉 **{d['lost']}** 条")
    print(f"    新增的按义务释放小时分布: {d['gained_by_release_hour']}")
    print(f"    两个放置实际用到的配置: aoi={out['per_arm']['aoi']['config_choices']} "
          f"aoi_const300={out['per_arm']['aoi_const300']['config_choices']}")


def _hist(rows: dict, oids: list[str]) -> dict:
    h: dict[str, int] = {}
    for oid in oids:
        k = str(int(rows[oid]["release_at"] // 3600))
        h[k] = h.get(k, 0) + 1
    return dict(sorted(h.items(), key=lambda kv: int(kv[0])))


if __name__ == "__main__":
    main()
