"""服务—成本包络：在**公开声明的服务容差 × 资源工作点**下报告可行臂与最低成本。
本模块引用的 `docs/…` 路径为作者本地过程文档，不随仓库发布。

依据 `docs/s7-method/instance-v1/43-review-service-cost-and-plan-semantics-2026-09-14.md`
§二、§八.2、§八.3。**只用已有结果文件，不重跑仿真、不调用 LLM。**

四条必须守的规矩（都来自 doc 43）：

1. **主口径保留固定业务分母**（N1/N2 = 168、N3 = 672），**分列缺采、AoI、空口、能源**；
2. **容差与预算是公开声明的研究参数**，**不为任何候选单选有利阈值**；
   未有现场依据前**不得称 SLA**；
3. **区分空口下降与总站点能耗下降**（§40 E1 空口 −30.7% 而总能耗只降约 0.3%），**不得混读**；
4. **均值前沿之外报告配对差及其不确定性**（同种子配对 + 自助百分位区间）。

    python3 code/analysis/service_cost_envelope.py

写 `results/service_cost_envelope.json`。
"""
from __future__ import annotations

import argparse
import json
import os as _os
import random
import statistics as st

_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
RES = _os.path.normpath(_os.path.join(_CODE, "..", "results"))

#: **公开声明的服务容差**：允许比该条件的最优臂**少交付**的固定分母比例。
#: 它是**研究参数**，不是现场 SLA（现场无依据）。
TOLERANCES = (0.00, 0.01, 0.03, 0.05)
#: **四条成本轴**：空口与总能耗**分开**（doc 43 §八.3）。
COST_AXES = (
    ("uplinks", "上行次数"),
    ("downlink_attempts", "下行尝试"),
    ("airtime_uplink_h", "上行空口 h"),
    ("energy_consumed_wh", "总站点能耗 Wh"),
)
BOOT = 2000


def _mean(xs):
    v = [x for x in xs if x is not None]
    return (sum(v) / len(v)) if v else None


def _boot_ci(diffs, n=BOOT, alpha=0.05, seed=0):
    """自助百分位区间（同种子配对差）。样本量小，**只作不确定性提示，不作显著性判决**。"""
    if not diffs:
        return None
    rnd = random.Random(seed)
    k = len(diffs)
    means = sorted(_mean([diffs[rnd.randrange(k)] for _ in range(k)]) for _ in range(n))
    lo = means[int(alpha / 2 * n)]
    hi = means[int((1 - alpha / 2) * n) - 1]
    return [round(lo, 4), round(hi, 4)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", default="config_grid.json")
    ap.add_argument("--out", default="service_cost_envelope")
    args = ap.parse_args()

    src = json.load(open(_os.path.join(RES, args.grid), encoding="utf-8"))
    raw = src["raw"]
    arms = list(src["frontier"]) + list(src["grid_arms"])
    out = {"source": src.get("grid_arms") and args.grid,
           "declared": {"tolerances_frac_of_fixed_denominator": list(TOLERANCES),
                        "cost_axes": [k for k, _ in COST_AXES],
                        "note": ("容差与预算点是**公开声明的研究参数**，"
                                 "**未有现场依据前不得称 SLA**；主口径保留固定业务分母，"
                                 "空口与总能耗**分列**。")},
           "conditions": {}}

    for cond, byarm in raw.items():
        rows = {a: {k: _mean([r[k] for r in byarm[a]]) for k in byarm[a][0]}
                for a in arms if a in byarm}
        den = rows[arms[0]]["service_denom"]
        best_arm = max(arms, key=lambda a: rows[a]["service"])
        best = rows[best_arm]["service"]
        blk = {"denom": den, "seeds": len(byarm[best_arm]),
               "best_arm": best_arm, "best_service": best,
               "tolerance_points": {}}

        for t in TOLERANCES:
            floor = best - t * den
            feas = [a for a in arms if rows[a]["service"] >= floor]
            cheapest = {}
            for key, _label in COST_AXES:
                a = min(feas, key=lambda x: rows[x][key])
                cheapest[key] = {"arm": a, "value": round(rows[a][key], 6),
                                 "service": round(rows[a]["service"], 4),
                                 "service_gap_to_best": round(best - rows[a]["service"], 4)}
            blk["tolerance_points"][f"{t:.2%}"] = {
                "service_floor": round(floor, 4), "n_feasible_arms": len(feas),
                "feasible_sample": sorted(feas, key=lambda a: -rows[a]["service"])[:8],
                "cheapest_per_axis": cheapest,
            }

        # **配对差及不确定性**：最优服务臂 vs 各成本轴上的最低成本可行臂（容差 1%）。
        t_ref = 0.01
        floor = best - t_ref * den
        feas = [a for a in arms if rows[a]["service"] >= floor]
        pair_blk = {}
        for key, label in COST_AXES:
            low = min(feas, key=lambda x: rows[x][key])
            if low == best_arm:
                pair_blk[key] = {"arm": low, "note": "与该轴最低成本臂相同，无配对差"}
                continue
            d = {k: [] for k in ("service", "missing_collection", "aoi_mean_s",
                                 "uplinks", "downlink_attempts", "airtime_uplink_h",
                                 "energy_consumed_wh")}
            seeds = min(len(byarm[best_arm]), len(byarm[low]))
            for s in range(seeds):
                for k in d:
                    x, y = byarm[best_arm][s][k], byarm[low][s][k]
                    d[k].append(None if x is None or y is None else y - x)
            pair_blk[key] = {
                "axis_label": label, "low_cost_arm": low, "reference_arm": best_arm,
                "seeds": seeds,
                "mean_delta": {k: (round(_mean(v), 6) if _mean(v) is not None else None)
                               for k, v in d.items()},
                "ci95_bootstrap": {k: _boot_ci([x for x in v if x is not None])
                                   for k, v in d.items()},
            }
        blk["paired_vs_best_service_arm"] = pair_blk
        out["conditions"][cond] = blk

    path = _os.path.join(RES, f"{args.out}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"wrote {path}\n")

    for cond, b in out["conditions"].items():
        print(f"=== {cond}  分母 {b['denom']}  种子 {b['seeds']}  最优服务臂 {b['best_arm']} "
              f"= {b['best_service']:.2f}")
        for t, pt in b["tolerance_points"].items():
            c = pt["cheapest_per_axis"]
            print(f"  容差 {t:>5}  可行 {pt['n_feasible_arms']:>2} 条 | "
                  f"最省上行 {c['uplinks']['arm']}({c['uplinks']['value']:.0f}) | "
                  f"最省下行 {c['downlink_attempts']['arm']}({c['downlink_attempts']['value']:.1f}) | "
                  f"最省空口 {c['airtime_uplink_h']['arm']}({c['airtime_uplink_h']['value']:.4f}h) | "
                  f"最省能耗 {c['energy_consumed_wh']['arm']}({c['energy_consumed_wh']['value']:.4f}Wh)")
        print("  配对差（相对最优服务臂，正=更省/更多）：")
        for key, p in b["paired_vs_best_service_arm"].items():
            if "mean_delta" not in p:
                continue
            md, ci = p["mean_delta"], p["ci95_bootstrap"]
            print(f"    [{key:<19}] {p['low_cost_arm']:<18} 服务 {md['service']:+.3f} "
                  f"缺采 {md['missing_collection']:+.2f} AoI {md['aoi_mean_s'] or 0:+.0f}s "
                  f"上行 {md['uplinks']:+.1f} 空口 {md['airtime_uplink_h']:+.4f}h "
                  f"能耗 {md['energy_consumed_wh']:+.5f}Wh")
            print(f"       服务 CI95 {ci['service']}  能耗 CI95 {ci['energy_consumed_wh']}")
        print()


if __name__ == "__main__":
    main()
