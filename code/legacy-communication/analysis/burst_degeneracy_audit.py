"""突发条件的**跨种子退化审计**（为什么必须有它：我已经因为只跑一个种子下过一次错结论）。

**背景。** 仓库里所有 polar/突发档共用同一组两态马尔可夫参数
（回传 `(0.00846, 0.0138)`、接入 `(0.0079, 0.0158)`）⇒ **平均坏突发 72.5 h / 63.3 h**。
一旦某个种子从"坏"态起链，**整段任务可能落在同一次坏突发里**，于是**每条臂的服务都恰好为 0**，
单种子读数**什么都说明不了**（§7.113 就是这么错的）。

本脚本做两件事：
  1. **解析扫描**：所有带突发参数的已登记档，逐个算 `task_hours` 与平均坏突发，标出"任务短于坏突发"的档；
  2. **经验核实**（可指定档）：跑 `local` 逐种子，报**全臂可能恒零的种子**占比；
     并回答一个更要紧的问题——**"全臂恒零"的种子会不会把已登记的"极差很小"人为压小**。

    python3 code/analysis/burst_degeneracy_audit.py --seeds 20

写 `results/burst_degeneracy_audit.json`。
"""
from __future__ import annotations

import argparse
import glob
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
#: 经验核实的代表档（12/24/48/96 h 四个任务长度 + 第二来源）。
PROBE = ("instance_polar_c0.05", "instance_len24_polar", "instance_len48_polar",
         "instance_len96_polar", "instance_ccorral_polar_c0.05")


def _parse(raw):
    if not raw:
        return None
    gb, bg = (float(x) for x in str(raw).split(","))
    return gb, bg


def scan() -> list[dict]:
    out = []
    for f in sorted(glob.glob(_os.path.join(RES, "instance_*.json"))):
        try:
            c = json.load(open(f, encoding="utf-8"))["config"]
        except Exception:
            continue
        pb, pu = _parse(c.get("backhaul_burst")), _parse(c.get("uplink_burst"))
        if pb is None and pu is None:
            continue
        bads = [1.0 / p[1] for p in (pb, pu) if p]
        st = [p[1] / (p[0] + p[1]) for p in (pb, pu) if p]
        task = float(c.get("task_hours") or 0.0)
        out.append({"file": _os.path.basename(f), "task_hours": task,
                    "seeds": c.get("seeds"), "backhaul_burst": c.get("backhaul_burst"),
                    "uplink_burst": c.get("uplink_burst"),
                    "mean_bad_burst_h": round(min(bads), 4),
                    "stationary_good": round(min(st), 4),
                    "risk": task < min(bads)})
    out.sort(key=lambda r: (not r["risk"], r["task_hours"], r["file"]))
    return out


def probe(tag: str, seeds: int) -> dict:
    cfg = json.load(open(_os.path.join(RES, f"{tag}.json"), encoding="utf-8"))["config"]
    kw = build_kwargs(dict(cfg))
    kw.pop("trace", None)
    kw.pop("cache_service", None)
    vals, den = [], None
    for s in range(seeds):
        r = one_seed(s, arm="local", **kw)["routine"]
        vals.append(r["delivered"])
        den = r["n"]
    # 与**已登记**结果对账：那份里每条臂逐种子的服务都在 `runs` 里
    reg = json.load(open(_os.path.join(RES, f"{tag}.json"), encoding="utf-8"))
    arms = [a.strip() for a in str(reg["config"]["arms"]).split(",") if a.strip()]
    byarm: dict[str, dict] = {a: {} for a in arms}
    for r in reg.get("runs", []):
        if r["arm"] in byarm:
            byarm[r["arm"]][r["seed"]] = r["routine"]["delivered"]
    allzero = [s for s in range(seeds)
               if byarm and all(byarm[a].get(s) == 0 for a in arms)]
    top8 = sorted(arms, key=lambda a: -sum(byarm[a].values()))[:8] if byarm else []

    def spread(sel):
        if not top8 or not sel:
            return None
        means = [sum(byarm[a][s] for s in sel) / len(sel) for a in top8]
        return round((max(means) - min(means)) / den * 100, 4)

    live = [s for s in range(seeds) if s not in allzero]
    return {"task_hours": kw["task_hours"], "denom": den, "seeds": seeds,
            "local_per_seed": vals,
            "local_zero_seeds": sum(1 for v in vals if v == 0),
            "all_arms_zero_seeds": allzero,
            "all_arms_zero_count": len(allzero),
            # **关键问题**：剔除全臂恒零的种子之后，已登记的"极差"会不会变大？
            "top8_spread_points_all_seeds": spread(list(range(seeds))),
            "top8_spread_points_live_seeds_only": spread(live),
            "n_top8": len(top8)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--out", default="burst_degeneracy_audit")
    args = ap.parse_args()

    out = {"scanned": scan(), "probes": {}}
    for tag in PROBE:
        if _os.path.exists(_os.path.join(RES, f"{tag}.json")):
            out["probes"][tag] = probe(tag, args.seeds)
    risky = [r for r in out["scanned"] if r["risk"]]
    out["summary"] = {
        "n_burst_conditions": len(out["scanned"]),
        "n_risk_task_shorter_than_bad_burst": len(risky),
        "min_task_hours": min((r["task_hours"] for r in out["scanned"]), default=None),
        "max_task_hours": max((r["task_hours"] for r in out["scanned"]), default=None),
        "all_share_same_burst_params": len({(r["backhaul_burst"], r["uplink_burst"])
                                            for r in out["scanned"]}) == 1,
    }
    path = _os.path.join(RES, f"{args.out}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"wrote {path}\n")
    s = out["summary"]
    print(f"扫描 {s['n_burst_conditions']} 个带突发参数的已登记档；"
          f"**{s['n_risk_task_shorter_than_bad_burst']} 个 task < 平均坏突发**（单种子可能整段退化）；"
          f"任务 {s['min_task_hours']:.0f}–{s['max_task_hours']:.0f} h；"
          f"全部共用同一组突发参数={s['all_share_same_burst_params']}\n")
    print(f"{'档':<34}{'task':>5}{'为0种子(local)':>14}{'全臂恒零':>9}"
          f"{'极差(全部种子)':>15}{'极差(剔除零种子)':>17}")
    for tag, p in out["probes"].items():
        print(f"{tag:<34}{p['task_hours']:>5.0f}{p['local_zero_seeds']:>10}/{p['seeds']}"
              f"{p['all_arms_zero_count']:>6}/{p['seeds']}"
              f"{str(p['top8_spread_points_all_seeds']):>15}"
              f"{str(p['top8_spread_points_live_seeds_only']):>17}")


if __name__ == "__main__":
    main()
