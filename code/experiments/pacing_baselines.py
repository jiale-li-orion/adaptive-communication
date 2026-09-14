"""交付 2：**普通规则的节奏对照**（不实现候选）。

依据 `docs/s7-method/instance-v1/48-review-energy-placement-and-pacing-decision-2026-09-14.md`
§4、§5。规则先写定在
`docs/s7-method/instance-v1/50-pre-registration-pacing-baselines-2026-09-14.md`。

**固定**：N3（`instance_ccorral_iid_c0.05`，900 s 义务）的原始采样节奏、事件逻辑、
缓存与打包纪律、能源参数，**以及网关执行位置**（`placement="gateway"`，所有臂相同）。
**只变 `report_period` 策略。** 不把能源采样优化混进来。

三档：无强制中断 / 回传 [4h,7h) / 接入 [4h,7h)。

    python3 code/experiments/pacing_baselines.py --seeds 20

写 `results/pacing_baselines.json`。
"""
from __future__ import annotations

import argparse
import json
import os as _os
import random
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
BASE_TAG = "instance_ccorral_iid_c0.05"      # N3：900 s 义务
PLACEMENT = "gateway"                        # 所有臂共享同一执行位置

#: **冻结的合法上报周期全集**（仓库 `GRID_REPORT`，含保持原配置的那一档）。
FIXED_REPORTS = (300, 600, 900, 1800, 3600)
#: **冻结的既有 AoI 规则族代表**（开发区间内已登记前沿上的端点 + 常数臂）。
AOI_REPS = {"aoi": dict(), "aoi_const300": dict(fast_s=300, slow_s=300),
            "aoi_f600": dict(fast_s=600), "aoi_t7200": dict(stale_s=7200)}
#: 新增的**普通**节奏规则（不是候选）。**「慢档上限」不单选**——
#: 预先声明 `slow ∈ {1800, 3600}` 两档、含迟滞版，**全部报告**；
#: 理由见预注册 §4：避免用参数选择让普通基线显得差。
NEW_ORDINARY = {
    "pacing_bp1800": dict(slow_s=1800),
    "pacing_bp3600": dict(slow_s=3600),
    "pacing_bp1800_hyst": dict(slow_s=1800, hysteresis=True, confirm_n=2),
    "pacing_bp3600_hyst": dict(slow_s=3600, hysteresis=True, confirm_n=2),
}
#: **服务容差**：占固定分母的比例。主报告 0% 与 1%（doc 48 §5）。
TOLERANCES = (0.00, 0.01, 0.03, 0.05)
MAIN_TOLERANCES = ("0.00%", "1.00%")
#: **冻结的参照基线集合**（普通基线，不含新增节奏规则）——参照服务值只能来自它。
FROZEN_BASELINE = tuple(["local"] + [f"fixed{r}" for r in FIXED_REPORTS]
                        + list(AOI_REPS))
CONDITIONS = {
    "P0_no_outage": dict(access_outage_h=0.0, access_outage_start_h=4.0,
                         outage_hours=0.0, outage_start_h=0.0),
    "P1_backhaul_4h7h": dict(access_outage_h=0.0, access_outage_start_h=4.0,
                             outage_hours=3.0, outage_start_h=4.0),
    "P2_access_4h7h": dict(access_outage_h=3.0, access_outage_start_h=4.0,
                           outage_hours=0.0, outage_start_h=0.0),
}


def _register() -> list[str]:
    C.ARMS["local"] = C.LocalPolicy          # 已存在，保持
    for r in FIXED_REPORTS:
        # **只写上报周期**、dwell 与所有臂一致 ⇒ 差异只在规则本身。
        C.ARMS[f"fixed{r}"] = (lambda _r=r: C.FixedPeriodPolicy(_r, dwell_s=600))
    for nm, kw in AOI_REPS.items():
        C.ARMS[nm] = (lambda _kw=kw: C.AoiPolicy(dwell_s=600, **_kw))
    for nm, kw in NEW_ORDINARY.items():
        C.ARMS[nm] = (lambda _kw=kw: C.ReportPacingPolicy(dwell_s=600, **_kw))
    return list(FROZEN_BASELINE) + list(NEW_ORDINARY)


def extract(run: dict) -> dict:
    rt = run["routine"]
    en = (run.get("energy") or {}).get("per_node") or {}
    cm = run.get("communication") or {}
    return {
        "service": rt["delivered"], "service_denom": rt["n"],
        "missing_collection": rt["missing_collection"],
        "missing_delivery": rt["missing_delivery"], "aoi_mean_s": rt["aoi_mean_s"],
        "uplinks": cm.get("uplinks"), "downlink_attempts": cm.get("downlink_attempts"),
        "airtime_uplink_h": cm.get("airtime_uplink_h"),
        "energy_consumed_wh": round(sum((v.get("consumed_wh") or 0.0)
                                        for v in en.values()), 8),
        "nodes_dead": sum(1 for v in en.values() if v.get("dead_at_s") is not None),
        "commands_sent": (run.get("command_counters") or {}).get("commands_sent"),
    }


def _mean(xs):
    v = [x for x in xs if x is not None]
    return (round(sum(v) / len(v), 6) if v else None)


def _boot(d, n=2000, seed=0):
    if not d:
        return None
    rnd = random.Random(seed)
    k = len(d)
    m = sorted(_mean([d[rnd.randrange(k)] for _ in range(k)]) for _ in range(n))
    return [round(m[int(0.025 * n)], 4), round(m[int(0.975 * n) - 1], 4)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--out", default="pacing_baselines")
    args = ap.parse_args()
    arms = _register()

    cfg = json.load(open(_os.path.join(RES, f"{BASE_TAG}.json"), encoding="utf-8"))["config"]
    base = build_kwargs(dict(cfg))
    base.pop("trace", None)
    base.pop("cache_service", None)

    out = {"base": BASE_TAG, "placement": PLACEMENT, "seeds": args.seeds,
           "frozen_baseline": list(FROZEN_BASELINE),
           "new_ordinary": list(NEW_ORDINARY),
           "tolerances": list(TOLERANCES), "main_tolerances": list(MAIN_TOLERANCES),
           "note": ("只变 `report_period` 策略；采样/事件/缓存/打包/能源与执行位置全部固定。"
                    "参照服务值只来自**冻结的普通基线集合**。所有中断字段逐档写全并有断言。"),
           "rows": {}, "raw": {}, "envelope": {}}

    for cond, over in CONDITIONS.items():
        want = (over["access_outage_h"], over["access_outage_start_h"],
                over["outage_hours"], over["outage_start_h"])
        kw = {**base, **over}
        got = (kw["access_outage_h"], kw["access_outage_start_h"],
               kw["outage_hours"], kw["outage_start_h"])
        assert got == want, f"{cond}: 中断设置与声明不符 {got} != {want}"
        out["rows"][cond], out["raw"][cond] = {}, {}
        for arm in arms:
            runs = [one_seed(s, arm=arm, placement=PLACEMENT, **kw)
                    for s in range(args.seeds)]
            keys = list(extract(runs[0]))
            out["rows"][cond][arm] = {k: _mean([extract(r)[k] for r in runs]) for k in keys}
            out["raw"][cond][arm] = [extract(r) for r in runs]
        # 参照服务值：**只来自冻结的普通基线集合**
        den = out["rows"][cond]["local"]["service_denom"]
        ref_arm = max(FROZEN_BASELINE,
                      key=lambda a: out["rows"][cond][a]["service"])
        best = out["rows"][cond][ref_arm]["service"]
        env = {"denom": den, "reference_arm": ref_arm, "reference_service": best,
               "points": {}}
        for t in TOLERANCES:
            floor = best - t * den
            feas = [a for a in arms if out["rows"][cond][a]["service"] >= floor]
            cheapest = {}
            for key in ("uplinks", "airtime_uplink_h", "energy_consumed_wh",
                        "aoi_mean_s"):
                a = min(feas, key=lambda x: out["rows"][cond][x][key])
                cheapest[key] = {"arm": a, "value": out["rows"][cond][a][key],
                                 "service": round(out["rows"][cond][a]["service"], 4),
                                 "missing_collection":
                                     out["rows"][cond][a]["missing_collection"]}
            # **缺采约束（doc 48 §5）**：不得以新增缺采换成本收益
            ref_mc = out["rows"][cond][ref_arm]["missing_collection"]
            violate = [a for a in feas
                       if (out["rows"][cond][a]["missing_collection"] or 0) > ref_mc + 1e-9]
            env["points"][f"{t:.2%}"] = {
                "service_floor": round(floor, 4), "n_feasible": len(feas),
                "cheapest": cheapest,
                "arms_violating_missing_collection_constraint": violate,
                "new_ordinary_feasible": [a for a in NEW_ORDINARY if a in feas],
                "new_ordinary_is_cheapest_on": [
                    k for k, v in cheapest.items() if v["arm"] in NEW_ORDINARY],
            }
        out["envelope"][cond] = env

    path = _os.path.join(RES, f"{args.out}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"wrote {path}\n")
    for cond, env in out["envelope"].items():
        print(f"=== {cond}  分母 {env['denom']}  参照（冻结普通基线）{env['reference_arm']} "
              f"= {env['reference_service']:.2f}")
        for t, pt in env["points"].items():
            c = pt["cheapest"]
            main = "  ← 主报告" if t in MAIN_TOLERANCES else ""
            print(f"  容差 {t:>5} 可行 {pt['n_feasible']:>2}{main} | "
                  f"最省上行 {c['uplinks']['arm']}({c['uplinks']['value']:.0f}) | "
                  f"最省空口 {c['airtime_uplink_h']['arm']}({c['airtime_uplink_h']['value']:.4f}) | "
                  f"最省能耗 {c['energy_consumed_wh']['arm']}({c['energy_consumed_wh']['value']:.4f})")
            print(f"        新增普通规则在可行集: {pt['new_ordinary_feasible']}；"
                  f"在最低成本位上: {pt['new_ordinary_is_cheapest_on']}")
            if pt["arms_violating_missing_collection_constraint"]:
                print(f"        ⚠ 违反缺采约束的可行臂: "
                      f"{pt['arms_violating_missing_collection_constraint']}")
        print()


if __name__ == "__main__":
    main()
