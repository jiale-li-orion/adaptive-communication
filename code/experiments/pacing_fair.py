"""公平版节奏对照（交付：把上一轮被先验排除的那一格补上）。

规则与臂集合先写定在
`docs/s7-method/instance-v1/53-pre-registration-fair-pacing-2026-09-14.md`。

与上一轮（`pacing_baselines.py`，**保持不动**）的差别只有两处：

1. **臂集合给动态节奏公平机会**：加 `fast_s = 300` 配 `slow_s ∈ {900, 1800}`
   （`slow = 900` 即「按义务节奏封顶」），并加**第二条普通规则族**
   （按网关缓存里最老待转发记录的年龄判受阻）；
2. **补逐条解剖**：每条义务定位到 **采到 / 已到网关 / 已到中心** 三级（`heard`），
   保存位图以便精确算与参照臂的翻转集，并记录**恢复后的时间链**。

    python3 code/experiments/pacing_fair.py --seeds 20

写 `results/pacing_fair.json`。
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
BASE_TAG = "instance_ccorral_iid_c0.05"
PLACEMENT = "gateway"
DWELL = 600

FIXED_REPORTS = (300, 600, 900, 1800, 3600)
AOI_REPS = {"aoi": dict(), "aoi_const300": dict(fast_s=300, slow_s=300),
            "aoi_f600": dict(fast_s=600), "aoi_t7200": dict(stale_s=7200)}
#: **快慢档组合（冻结，全部报告）**：`(slow, fast)`。
#: `slow = 900` 是上一轮**完全缺失**的那一格——「按义务节奏封顶 + 未受阻时全力」。
PAIRS = ((900, 300), (1800, 300), (1800, 900), (3600, 900))
NEW_ORDINARY: dict[str, dict] = {}
for _s, _f in PAIRS:
    NEW_ORDINARY[f"pacing_bp{_s}_{_f}"] = dict(slow_s=_s, fast_s=_f)
    NEW_ORDINARY[f"pacing_backlog{_s}_{_f}"] = dict(slow_s=_s, fast_s=_f,
                                                    mode="pending_backlog")
NEW_ORDINARY["pacing_bp900_300_hyst"] = dict(slow_s=900, fast_s=300,
                                             hysteresis=True, confirm_n=2)
NEW_ORDINARY["pacing_backlog900_300_hyst"] = dict(slow_s=900, fast_s=300,
                                                  mode="pending_backlog",
                                                  hysteresis=True, confirm_n=2)

TOLERANCES = (0.00, 0.01, 0.03, 0.05)
MAIN_TOLERANCES = ("0.00%", "1.00%")
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
COST_AXES = ("uplinks", "downlink_attempts", "airtime_uplink_h",
             "energy_consumed_wh", "aoi_mean_s")


def _register() -> list[str]:
    for r in FIXED_REPORTS:
        C.ARMS[f"fixed{r}"] = (lambda _r=r: C.FixedPeriodPolicy(_r, dwell_s=DWELL))
    for nm, kw in AOI_REPS.items():
        C.ARMS[nm] = (lambda _kw=kw: C.AoiPolicy(dwell_s=DWELL, **_kw))
    for nm, kw in NEW_ORDINARY.items():
        C.ARMS[nm] = (lambda _kw=kw: C.ReportPacingPolicy(dwell_s=DWELL, **_kw))
    return list(FROZEN_BASELINE) + list(NEW_ORDINARY)


def _changes(events):
    last, out = {}, []
    for ev in events:
        if ev[2] != "state":
            continue
        t_s, nid, i, r = ev[0], ev[1], ev[3], ev[4]
        if nid not in last:
            last[nid] = (i, r)
        elif last[nid] != (i, r):
            prev, last[nid] = last[nid], (i, r)
            out.append({"t_s": t_s, "node": nid, "from": prev, "to": (i, r),
                        "strict_downgrade": i > prev[0]})
    return out


def extract(run: dict) -> dict:
    rt = run["routine"]
    en = (run.get("energy") or {}).get("per_node") or {}
    cm = run.get("communication") or {}
    ch = _changes(run.get("_trace") or [])
    down = [c for c in ch if c["strict_downgrade"]]
    rows = sorted(run.get("_obligations") or [], key=lambda r: r["oid"])
    po = run.get("post_outage") or {}
    return {
        "service": rt["delivered"], "service_denom": rt["n"],
        "missing_collection": rt["missing_collection"],
        "missing_delivery": rt["missing_delivery"], "aoi_mean_s": rt["aoi_mean_s"],
        "uplinks": cm.get("uplinks"), "downlink_attempts": cm.get("downlink_attempts"),
        "airtime_uplink_h": cm.get("airtime_uplink_h"),
        "energy_consumed_wh": round(sum((v.get("consumed_wh") or 0.0)
                                        for v in en.values()), 8),
        "nodes_dead": sum(1 for v in en.values() if v.get("dead_at_s") is not None),
        # —— 三级解剖
        "n_collected": sum(1 for r in rows if r["collected"]),
        "n_heard": sum(1 for r in rows if r["heard"]),
        "n_delivered": sum(1 for r in rows if r["delivered"]),
        # 已到网关但未到中心 = 回传侧的损失；未到网关 = 节点上行侧的损失
        "n_lost_backhaul_side": sum(1 for r in rows if r["heard"] and not r["delivered"]),
        "n_lost_uplink_side": sum(1 for r in rows if not r["heard"]),
        "first_downgrade_t_s": (min((c["t_s"] for c in down), default=None)),
        "n_strict_downgrades": len(down),
        "heard_delay_s": po.get("heard_delay_s"), "received_delay_s": po.get("received_delay_s"),
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
    ap.add_argument("--out", default="pacing_fair")
    args = ap.parse_args()
    arms = _register()

    cfg = json.load(open(_os.path.join(RES, f"{BASE_TAG}.json"), encoding="utf-8"))["config"]
    base = build_kwargs(dict(cfg))
    base.pop("trace", None)
    base.pop("cache_service", None)

    out = {"base": BASE_TAG, "placement": PLACEMENT, "seeds": args.seeds,
           "frozen_baseline": list(FROZEN_BASELINE), "new_ordinary": list(NEW_ORDINARY),
           "pairs": [list(p) for p in PAIRS], "tolerances": list(TOLERANCES),
           "main_tolerances": list(MAIN_TOLERANCES), "rows": {}, "per_seed": {},
           "envelope": {}, "anatomy": {}, "paired": {}}

    for cond, over in CONDITIONS.items():
        want = (over["access_outage_h"], over["access_outage_start_h"],
                over["outage_hours"], over["outage_start_h"])
        kw = {**base, **over}
        got = (kw["access_outage_h"], kw["access_outage_start_h"],
               kw["outage_hours"], kw["outage_start_h"])
        assert got == want, f"{cond}: 中断设置与声明不符 {got} != {want}"
        out["rows"][cond], out["per_seed"][cond] = {}, {}
        for arm in arms:
            runs = [one_seed(s, arm=arm, placement=PLACEMENT, trace=True,
                             obligation_ledger=True, **kw) for s in range(args.seeds)]
            keys = list(extract(runs[0]))
            out["rows"][cond][arm] = {k: _mean([extract(r)[k] for r in runs]) for k in keys}
            out["per_seed"][cond][arm] = [
                {"seed": s, **extract(r),
                 # 位图：义务按 `oid` 定序 ⇒ 可跨臂精确求翻转集
                 "delivered_bitmap": "".join(
                     "1" if x["delivered"] else "0"
                     for x in sorted(r["_obligations"], key=lambda y: y["oid"])),
                 "heard_bitmap": "".join(
                     "1" if x["heard"] else "0"
                     for x in sorted(r["_obligations"], key=lambda y: y["oid"])),
                 "release_hours": [x["release_at"] // 3600
                                   for x in sorted(r["_obligations"], key=lambda y: y["oid"])]}
                for s, r in enumerate(runs)]

        den = out["rows"][cond]["local"]["service_denom"]
        ref_arm = max(FROZEN_BASELINE, key=lambda a: out["rows"][cond][a]["service"])
        best = out["rows"][cond][ref_arm]["service"]
        ref_mc = out["rows"][cond][ref_arm]["missing_collection"]
        env = {"denom": den, "reference_arm": ref_arm, "reference_service": best,
               "reference_missing_collection": ref_mc, "points": {}}
        for t in TOLERANCES:
            floor = best - t * den
            feas = [a for a in arms if out["rows"][cond][a]["service"] >= floor]
            cheapest = {}
            for k in COST_AXES:
                a = min(feas, key=lambda x: out["rows"][cond][x][k])
                cheapest[k] = {"arm": a, "value": out["rows"][cond][a][k],
                               "service": round(out["rows"][cond][a]["service"], 4),
                               "missing_collection": out["rows"][cond][a]["missing_collection"]}
            violate = [a for a in feas
                       if (out["rows"][cond][a]["missing_collection"] or 0) > ref_mc + 1e-9]
            env["points"][f"{t:.2%}"] = {
                "service_floor": round(floor, 4), "n_feasible": len(feas),
                "cheapest": cheapest, "violating_missing_collection": violate,
                "new_ordinary_feasible": [a for a in NEW_ORDINARY if a in feas],
                "new_ordinary_cheapest_on": [k for k, v in cheapest.items()
                                             if v["arm"] in NEW_ORDINARY]}
        out["envelope"][cond] = env

        # **解剖**：与参照臂逐义务求翻转集（位图差），并把损失分到三级
        r0 = out["per_seed"][cond][ref_arm]
        for arm in arms:
            if arm == ref_arm:
                continue
            ga, lo_, hu, lb_ = [], [], [], []
            for ci, gi in zip(r0, out["per_seed"][cond][arm]):
                db = list(zip(ci["delivered_bitmap"], gi["delivered_bitmap"]))
                hb = list(zip(ci["heard_bitmap"], gi["heard_bitmap"]))
                ga.append(sum(1 for x, y in db if x == "0" and y == "1"))
                lo_.append(sum(1 for x, y in db if x == "1" and y == "0"))
                lb_.append(sum(1 for x, y in hb if x == "1" and y == "0"))
                hu.append(sum(1 for x, y in hb if x == "0" and y == "1"))
            out["anatomy"].setdefault(cond, {})[arm] = {
                "ref": ref_arm,
                "gained_obligations": _mean(ga), "lost_obligations": _mean(lo_),
                "lost_hearing": _mean(lb_), "gained_hearing": _mean(hu),
                "d_uplinks": _mean([g["uplinks"] - c["uplinks"] for c, g in
                                    zip(r0, out["per_seed"][cond][arm])]),
                "d_energy_wh": _mean([g["energy_consumed_wh"] - c["energy_consumed_wh"]
                                      for c, g in zip(r0, out["per_seed"][cond][arm])]),
                "d_lost_backhaul_side": _mean(
                    [g["n_lost_backhaul_side"] - c["n_lost_backhaul_side"]
                     for c, g in zip(r0, out["per_seed"][cond][arm])]),
                "d_lost_uplink_side": _mean(
                    [g["n_lost_uplink_side"] - c["n_lost_uplink_side"]
                     for c, g in zip(r0, out["per_seed"][cond][arm])]),
                "heard_delay_s": _mean([g["heard_delay_s"] for g in out["per_seed"][cond][arm]]),
                "received_delay_s": _mean([g["received_delay_s"]
                                           for g in out["per_seed"][cond][arm]]),
                "n_strict_downgrades": _mean([g["n_strict_downgrades"]
                                              for g in out["per_seed"][cond][arm]]),
            }

    path = _os.path.join(RES, f"{args.out}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"wrote {path}\n")
    for cond, env in out["envelope"].items():
        print(f"=== {cond}  参照（冻结普通基线）{env['reference_arm']} = "
              f"{env['reference_service']:.2f} / {env['denom']}")
        for t, pt in env["points"].items():
            c = pt["cheapest"]
            tag = "  ← 主报告" if t in MAIN_TOLERANCES else ""
            print(f"  容差 {t:>5} 可行 {pt['n_feasible']:>2}{tag} | "
                  f"上行 {c['uplinks']['arm']}({c['uplinks']['value']:.0f}) | "
                  f"能耗 {c['energy_consumed_wh']['arm']}({c['energy_consumed_wh']['value']:.4f}) | "
                  f"空口 {c['airtime_uplink_h']['arm']}({c['airtime_uplink_h']['value']:.4f})")
            print(f"        新增普通可行 {len(pt['new_ordinary_feasible'])} 条 "
                  f"{pt['new_ordinary_feasible'][:4]} | 占最低成本位 {pt['new_ordinary_cheapest_on']}")
            if pt["violating_missing_collection"]:
                print(f"        ⚠ 违反缺采约束 {pt['violating_missing_collection']}")
        print()


if __name__ == "__main__":
    main()
