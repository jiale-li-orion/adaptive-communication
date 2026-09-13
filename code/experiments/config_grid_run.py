"""§31 候选 2 第一项判别：**合法配置网格 + 普通滚动搜索**。

判定规则**先写定**在
`docs/s7-method/instance-v1/34-pre-registration-config-grid-2026-09-14.md`；
本脚本只负责执行与读数，**不得**按结果回头改规则。

条件**不新造**：三档直接重放已登记的 `results/instance_<tag>.json` 的 `config`，
并用与 `llm_naive_baseline.py` 同一个 `build_kwargs`，因此跑的是**同一个实例**。

    python3 code/experiments/config_grid_run.py --seeds 4      # 冒烟
    python3 code/experiments/config_grid_run.py                # 用登记种子数
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

import center as C                                                       # noqa: E402
from instance_run import one_seed                                        # noqa: E402
from trace_seed_timeline import build_kwargs                             # noqa: E402

RES = _os.path.normpath(_os.path.join(_CODE, "..", "results"))

#: 三档条件全部复用已登记实例（§31 第 108 行：优先复用现有条件和开发区间）。
CONDITIONS = {
    "N1_no_outage": "instance_arms",
    "N2_access_outage": "instance_adm_out3",
    "N3_second_source": "instance_ccorral_iid_c0.05",
}
#: 现有前沿：`local`（零中心控制）/ `aoi`（AoI 反馈）/ `ea_nb`（电能反馈）/ `eh_aoi`（文献二维门限）。
FRONTIER = ("local", "aoi", "ea_nb", "eh_aoi")
#: **所有 30 个合法点**（§31 第 77 行要求"所有合法配置的静态前沿"）。其中 10 个点本来就有臂
#: 覆盖，这里**显式重述**成 `gridIxR`，使"所有合法配置"与实际跑过的集合逐项对齐。
GRID_ARMS = [f"grid{i}x{r}" for i in C.GRID_SAMPLING for r in C.GRID_REPORT]

#: 目标：前四项越小越好，服务越大越好。
OBJECTIVES = (("service", +1), ("uplinks", -1), ("downlink_attempts", -1),
              ("missing_collection", -1), ("aoi_mean_s", -1))
EPS = 1e-9

_LAST: dict = {}


def extract(run: dict) -> dict:
    rt, en = run["routine"], (run.get("energy") or {}).get("per_node") or {}
    cm, cc = run.get("communication") or {}, run.get("command_counters") or {}
    return {
        "service": rt["delivered"], "service_denom": rt["n"],
        "missing_collection": rt["missing_collection"],
        "missing_delivery": rt["missing_delivery"], "aoi_mean_s": rt["aoi_mean_s"],
        "energy_consumed_wh": round(sum((v.get("consumed_wh") or 0.0) for v in en.values()), 8),
        "nodes_dead": sum(1 for v in en.values() if v.get("dead_at_s") is not None),
        "uplinks": cm.get("uplinks"), "uplinks_heard": cm.get("uplinks_heard"),
        "downlink_attempts": cm.get("downlink_attempts"),
        "commands_sent": cc.get("commands_sent"), "commands_refused": cc.get("commands_refused"),
        "mixed_config_s": run.get("mixed_config_s"),
    }


def mean_of(runs, key):
    vals = [extract(r)[key] for r in runs]
    vals = [v for v in vals if v is not None]
    return (sum(vals) / len(vals)) if vals else None


def dominates(a: dict, b: dict) -> bool:
    """`a` 是否在多目标上**支配** `b`（严格优于至少一项）。"""
    strict = False
    for key, sign in OBJECTIVES:
        x, y = a.get(key), b.get(key)
        if x is None or y is None:
            return False
        if sign * x < sign * y - EPS:
            return False
        if sign * x > sign * y + EPS:
            strict = True
    return strict


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=0, help="0 = 用登记条件里的种子数")
    ap.add_argument("--out", default="config_grid")
    args = ap.parse_args()

    result: dict = {"conditions": {}, "grid": {"sampling": list(C.GRID_SAMPLING),
                                               "report": list(C.GRID_REPORT)},
                    "grid_arms": GRID_ARMS, "frontier": list(FRONTIER),
                    "raw": {}}
    # 手算可核的两个点（预注册 §2 已登记）：采样占 94.0%、内部点只降 4.5%。
    _p = C.RollingConfigSearchPolicy()
    result["grid"]["load_h"] = {"(600,900)": _p._load_h(600, 900),
                                "(600,3600)": _p._load_h(600, 3600)}

    for cond, tag in CONDITIONS.items():
        cfg = json.load(open(_os.path.join(RES, f"{tag}.json"), encoding="utf-8"))["config"]
        kw = build_kwargs(dict(cfg))
        kw.pop("trace", None)
        seeds = args.seeds or int(cfg.get("seeds") or 20)

        # **普通滚动搜索按场景声明的参数构造**（同预测、同观测）。**不改任何已提交文件**：
        # 与 `llm_naive_baseline.py` 同法，运行时把臂注册进 `C.ARMS`。
        params = dict(routine_period_s=int(kw.get("routine_period_s") or 3600),
                      horizon_end_s=int(float(kw["task_hours"]) * 3600),
                      uplink_p=float(kw.get("uplink_p_arrive") or 0.74),
                      backhaul_p=float(kw.get("backhaul_p_good") or 0.62),
                      harvest_wh_per_hour=float(kw.get("harvest_wh_per_hour") or 0.0),
                      capacity_wh=float(kw["capacity_wh"]))

        def _mk(_p=params):
            pol = C.RollingConfigSearchPolicy(**_p)
            _LAST["pol"] = pol
            return pol

        C.ARMS["rolling_search"] = _mk
        arms = list(FRONTIER) + GRID_ARMS + ["rolling_search"]
        rows, search_reasons = {}, {}
        for arm in arms:
            runs = [one_seed(s, arm=arm, **kw) for s in range(seeds)]
            rows[arm] = {k: mean_of(runs, k) for k, _s in OBJECTIVES}
            rows[arm]["energy_consumed_wh"] = mean_of(runs, "energy_consumed_wh")
            rows[arm]["nodes_dead"] = mean_of(runs, "nodes_dead")
            rows[arm]["commands_sent"] = mean_of(runs, "commands_sent")
            rows[arm]["mixed_config_s"] = mean_of(runs, "mixed_config_s")
            result["raw"].setdefault(cond, {})[arm] = [extract(r) for r in runs]
            if arm == "rolling_search" and "pol" in _LAST:
                search_reasons = _LAST["pol"].search_report()
        result["conditions"][cond] = {"source": f"results/{tag}.json", "seeds": seeds,
                                      "params": params, "rows": rows,
                                      "rolling_search": search_reasons}
        _analyse(result["conditions"][cond], cond)

    path = _os.path.join(RES, f"{args.out}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)
    print(f"\nwrote {path}")
    _print(result)


def _analyse(blk: dict, cond: str) -> None:
    """按预注册 R1/R2 判定：网格点是否全被现有前沿支配。"""
    rows = blk["rows"]
    front = {a: rows[a] for a in FRONTIER if a in rows}
    grid = {a: rows[a] for a in GRID_ARMS if a in rows}
    non_dom, dom_by = [], {}
    for ga, gv in grid.items():
        killers = [fa for fa, fv in front.items() if dominates(fv, gv)]
        if killers:
            dom_by[ga] = killers
        else:
            non_dom.append(ga)
    # 网格内部两两之间也标出非支配点（读者要看的是一条前沿，不是一个布尔值）
    inner = [ga for ga in grid if not any(dominates(grid[gb], grid[ga])
                                          for gb in grid if gb != ga)]
    # 全臂（含前沿与滚动搜索）的非支配集
    allrows = dict(rows)
    allfrontier = [a for a in allrows
                   if not any(dominates(allrows[b], allrows[a])
                              for b in allrows if b != a)]
    blk["verdict"] = {
        "grid_non_dominated_vs_frontier": sorted(non_dom),
        "grid_dominated_by": dom_by,
        "grid_inner_non_dominated": sorted(inner),
        "non_dominated_all_arms": sorted(allfrontier),
        "R1_all_grid_points_dominated": len(non_dom) == 0,
        "rolling_search_dominated_by": sorted(
            fa for fa, fv in front.items() if dominates(fv, rows["rolling_search"])),
        "rolling_search_dominates": sorted(
            a for a in allrows
            if a != "rolling_search" and dominates(rows["rolling_search"], allrows[a])),
    }


def _print(result: dict) -> None:
    print()
    for cond, blk in result["conditions"].items():
        v = blk["verdict"]
        print(f"=== {cond}  （{blk['source']}，种子 {blk['seeds']}）")
        print(f"{'arm':<18}{'服务':>7}{'缺采':>6}{'AoI s':>8}{'上行':>7}{'下行':>7}{'能耗Wh':>10}")
        print("-" * 66)
        for arm in list(FRONTIER) + GRID_ARMS + ["rolling_search"]:
            r = blk["rows"][arm]
            flag = "  ←网格非支配" if arm in v["grid_non_dominated_vs_frontier"] else ""
            flag = "  ←全臂非支配" if arm in v["non_dominated_all_arms"] else flag
            print(f"{arm:<18}{(r['service'] or 0):>7.1f}{(r['missing_collection'] or 0):>6.1f}"
                  f"{(r['aoi_mean_s'] or 0):>8.0f}{(r['uplinks'] or 0):>7.0f}"
                  f"{(r['downlink_attempts'] or 0):>7.1f}{(r['energy_consumed_wh'] or 0):>10.4f}"
                  f"{flag}")
        print(f"  **R1 全部网格点被现有前沿支配？ {v['R1_all_grid_points_dominated']}**"
              f"  非支配网格点={v['grid_non_dominated_vs_frontier']}")
        print(f"  滚动搜索被这些前沿臂支配：{v['rolling_search_dominated_by']}"
              f"；它支配：{v['rolling_search_dominates']}")
        print(f"  选择原因：{blk['rolling_search'].get('reasons')}")
        print()


if __name__ == "__main__":
    main()
