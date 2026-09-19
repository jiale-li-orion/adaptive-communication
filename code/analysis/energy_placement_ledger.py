"""交付 1：位置结果的**可追溯补件**（原条件重放，保存逐种子台账与前言）。
本模块引用的 `docs/…` 路径为作者本地过程文档，不随仓库发布。

依据 `docs/s7-method/instance-v1/48-review-energy-placement-and-pacing-decision-2026-09-14.md`
§2、§5.1。**只重放原条件**（同一脚本、同一三档、同一种子数），不扩大实验。

补四件事：

1. **逐种子台账落盘**——原脚本虽开了 `trace=`/`obligation_ledger=`，输出 JSON 只存了聚合量，
   所以 doc 47「逐义务台账已按种子落盘」**不成立**。这里把逐义务台账、配置变化链、意图摘要写进文件。
2. **原聚合列对齐**——同一条件重放后重算聚合，与 `energy_limited_placement.json` 逐项核对。
3. **严格降档计数**——原筛选是"新采样间隔 `>= 3600`"，**没有要求新值大于旧值**，
   于是"已经稀疏、只改了上报周期"的事件也被计入。这里以**采样间隔严格增大**识别降档，
   分开报告**节点数 / 转换次数 / 首次生效时刻**。**不预判更正后的数字。**
4. **前缀检查**——doc 48 §1：O0 是**整个任务**无中断的结果，**不是 `t < 3 h` 的快照**，
   所以它差异小**不能**证明两位置在中断前一致。这里从时间线取出 `t = 3 h` 时两台位置的
   节点真实配置，直接比对。

    python3 code/analysis/energy_placement_ledger.py --seeds 10
"""
from __future__ import annotations

import argparse
import json
import os as _os
import random
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
from energy_limited_placement import (ARMS, CONDITIONS, PLACEMENTS,      # noqa: E402
                                      BASE_TAG, OUT_START_S)

RES = _os.path.normpath(_os.path.join(_CODE, "..", "results"))
PREFIX_S = OUT_START_S                    # = 3 h，中断开始时刻


def _state_series(events):
    """逐 (t_s, 节点) 的真实配置与电量（trace 的 `state` 事件）。"""
    return [(ev[0], ev[1], ev[3], ev[4], ev[5]) for ev in events if ev[2] == "state"]


def _plan_events(events):
    return [ev for ev in events if ev[2] == "plan"]


def per_seed(run: dict) -> dict:
    """把一次运行整理成**可追溯摘要**（逐义务台账 + 配置链 + 前缀 + 意图摘要）。"""
    ev = run.get("_trace") or []
    st_series = _state_series(ev)
    plans = _plan_events(ev)

    # 配置变化链：**同时记旧值与新值**，并标出是否为"严格降档"（采样间隔严格增大）。
    last: dict[str, tuple] = {}
    changes, strict = [], {"n_transitions": 0, "nodes": set(), "first_t_s": None}
    for t_s, nid, i, r, _soc in st_series:
        prev = last.get(nid)
        last[nid] = (i, r)
        if prev is None or prev == (i, r):
            continue
        is_down = (i > prev[0])            # **严格增大**才算降档
        changes.append({"t_s": t_s, "node": nid,
                        "from": list(prev), "to": [i, r],
                        "sampling_changed": i != prev[0],
                        "period_changed": r != prev[1],
                        "strict_downgrade": is_down})
        if is_down:
            strict["n_transitions"] += 1
            strict["nodes"].add(nid)
            if strict["first_t_s"] is None:
                strict["first_t_s"] = t_s
    strict["n_nodes"] = len(strict.pop("nodes"))

    # 原筛选口径（弱）：新采样间隔 >= 3600，**不要求变大**——用于对比更正前后的数字。
    loose = [c for c in changes if c["t_s"] >= OUT_START_S and c["to"][0] >= 3600]
    loose_strict = [c for c in loose if c["strict_downgrade"]]

    # 前缀：中断开始时刻（t = 3h）前最后一次 state 的配置与电量，逐节点。
    prefix = {}
    for t_s, nid, i, r, soc in st_series:
        if t_s <= PREFIX_S:
            prefix[nid] = {"t_s": t_s, "sampling_interval_s": i,
                           "report_period_s": r, "soc_wh": soc}
    pre_plans = [p for p in plans if p[0] <= PREFIX_S]
    post_plans = [p for p in plans if p[0] > PREFIX_S]

    ages = [p[6] for p in plans if len(p) > 6 and p[6] is not None]
    reasons: dict[str, int] = {}
    for p in plans:
        if len(p) > 7 and p[7] is not None:
            reasons[p[7]] = reasons.get(p[7], 0) + 1

    return {
        "config_changes": changes,
        "downgrade_strict": strict,
        "downgrade_loose_original_filter": {
            "n": len(loose), "n_strict_within_loose": len(loose_strict)},
        "prefix_at_3h": prefix,
        "n_plan_events": len(plans),
        "n_plan_before_3h": len(pre_plans),
        "plan_reasons": reasons,
        "plan_evidence_age_median_s": (st.median(ages) if ages else None),
        "first_plan_after_3h": ([{"t_s": p[0], "node": p[1], "evidence_age_s": p[6]}
                                 for p in post_plans[:3]] or None),
        "obligations": [{"oid": o["oid"], "release_at": o["release_at"],
                         "collected": o["collected"], "delivered": o["delivered"],
                         "censored": o["censored"]}
                        for o in (run.get("_obligations") or [])],
    }


def _mean(xs):
    v = [x for x in xs if x is not None]
    return (round(sum(v) / len(v), 6) if v else None)


def _boot(diffs, n=2000, seed=0):
    if not diffs:
        return None
    rnd = random.Random(seed)
    k = len(diffs)
    m = sorted(_mean([diffs[rnd.randrange(k)] for _ in range(k)]) for _ in range(n))
    return [round(m[int(0.025 * n)], 4), round(m[int(0.975 * n) - 1], 4)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--out", default="energy_limited_placement_ledger")
    args = ap.parse_args()

    cfg = json.load(open(_os.path.join(RES, f"{BASE_TAG}.json"), encoding="utf-8"))["config"]
    base = build_kwargs(dict(cfg))
    base.pop("trace", None)
    base.pop("cache_service", None)

    out = {"base": BASE_TAG, "seeds": args.seeds, "prefix_s": PREFIX_S,
           "note": ("**只重放原条件**。严格降档＝采样间隔**严格增大**；原口径是"
                    "新采样间隔 >= 3600（不要求变大），两者都报以便对账。"),
           "per_seed": {}, "aggregate": {}, "paired": {}, "interaction": {}}
    agg_per_seed: dict[tuple, list] = {}
    for cond, over in CONDITIONS.items():
        kw = {**base, **over}
        for arm in ARMS:
            for pl in PLACEMENTS:
                key = f"{cond}|{arm}|{pl}"
                runs = [one_seed(s, arm=arm, placement=pl, trace=True,
                                 obligation_ledger=True, **kw)
                        for s in range(args.seeds)]
                out["per_seed"][key] = [{"seed": s, **per_seed(r)} for s, r in enumerate(runs)]
                agg_per_seed[(cond, arm, pl)] = runs

    # 聚合（与原结果对账）
    from energy_limited_placement import extract as _extract
    for cond in CONDITIONS:
        for arm in ARMS:
            for pl in PLACEMENTS:
                runs = agg_per_seed[(cond, arm, pl)]
                keys = list(_extract(runs[0]))
                out["aggregate"][f"{cond}|{arm}|{pl}"] = {
                    k: _mean([_extract(r)[k] for r in runs]) for k in keys}

    # 与已登记结果逐项核对
    reg_path = _os.path.join(RES, "energy_limited_placement.json")
    recon = {"checked": 0, "mismatch": []}
    if _os.path.exists(reg_path):
        reg = json.load(open(reg_path, encoding="utf-8"))
        for key, row in out["aggregate"].items():
            cond, arm, pl = key.split("|")
            old = reg["rows"].get(cond, {}).get(f"{arm}|{pl}")
            if not old:
                continue
            for k, v in row.items():
                recon["checked"] += 1
                ov = old.get(k)
                if ov is None or v is None:
                    if (ov is None) != (v is None):
                        recon["mismatch"].append([key, k, ov, v])
                    continue
                if abs(float(v) - float(ov)) > 1e-6:
                    recon["mismatch"].append([key, k, ov, v])
    out["reconciliation"] = recon

    # 配对差 + **交互差（相对 O0）** + 自助区间
    for arm in ARMS:
        for cond in CONDITIONS:
            c = agg_per_seed[(cond, arm, "center")]
            g = agg_per_seed[(cond, arm, "gateway")]
            d = [(_extract(gi)["missing_collection"] - _extract(ci)["missing_collection"],
                  _extract(gi)["service"] - _extract(ci)["service"])
                 for ci, gi in zip(c, g)]
            out["paired"][f"{cond}|{arm}"] = {
                "d_missing_collection": {"mean": _mean([x[0] for x in d]),
                                         "ci95": _boot([x[0] for x in d])},
                "d_service": {"mean": _mean([x[1] for x in d]),
                              "ci95": _boot([x[1] for x in d])}}
        # 交互差：O2 − O1 / O2 − O0（同种子）
        for cond in ("O1_access_outage", "O2_backhaul_outage"):
            a = agg_per_seed[(cond, arm, "center")]
            b = agg_per_seed[(cond, arm, "gateway")]
            c0 = agg_per_seed[("O0_no_outage", arm, "center")]
            g0 = agg_per_seed[("O0_no_outage", arm, "gateway")]
            x = [((_extract(bi)["missing_collection"] - _extract(ai)["missing_collection"])
                  - (_extract(gi)["missing_collection"] - _extract(ci)["missing_collection"]),
                  (_extract(bi)["service"] - _extract(ai)["service"])
                  - (_extract(gi)["service"] - _extract(ci)["service"]))
                 for ai, bi, ci, gi in zip(a, b, c0, g0)]
            out["interaction"][f"{cond}|{arm}|minus_O0"] = {
                "d_missing_collection": {"mean": _mean([v[0] for v in x]),
                                         "ci95": _boot([v[0] for v in x])},
                "d_service": {"mean": _mean([v[1] for v in x]),
                              "ci95": _boot([v[1] for v in x])}}

    path = _os.path.join(RES, f"{args.out}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"wrote {path}\n")
    print(f"原聚合列对账：核对了 {recon['checked']} 项，不一致 {len(recon['mismatch'])} 项"
          + (f" {recon['mismatch'][:4]}" if recon["mismatch"] else " ⇒ **逐项一致**"))
    print()
    for cond in CONDITIONS:
        for arm in ("ea_nb",):
            k = f"{cond}|{arm}"
            p = out["paired"][k]
            print(f"=== {k}  Δ缺采 {p['d_missing_collection']['mean']} "
                  f"CI{p['d_missing_collection']['ci95']}  Δ服务 {p['d_service']['mean']} "
                  f"CI{p['d_service']['ci95']}")
        for arm in ("ea_nb",):
            for c in ("O1_access_outage", "O2_backhaul_outage"):
                ik = f"{c}|{arm}|minus_O0"
                if ik in out["interaction"]:
                    v = out["interaction"][ik]
                    print(f"    {c} 扣 O0 后：Δ缺采 {v['d_missing_collection']['mean']} "
                          f"CI{v['d_missing_collection']['ci95']}  "
                          f"Δ服务 {v['d_service']['mean']} CI{v['d_service']['ci95']}")
    print()
    print("=== 严格降档计数（采样间隔**严格增大**）vs 原口径（新值 >= 3600）===")
    for cond in CONDITIONS:
        for arm in ("ea_nb",):
            for pl in PLACEMENTS:
                rows = out["per_seed"][f"{cond}|{arm}|{pl}"]
                s_tr = _mean([r["downgrade_strict"]["n_transitions"] for r in rows])
                s_nd = _mean([r["downgrade_strict"]["n_nodes"] for r in rows])
                s_ft = [r["downgrade_strict"]["first_t_s"] for r in rows
                        if r["downgrade_strict"]["first_t_s"] is not None]
                lo = _mean([r["downgrade_loose_original_filter"]["n"] for r in rows])
                print(f"  {cond:<22}{arm:<7}{pl:<8} 严格 次数 {s_tr:.2f} 节点 {s_nd:.2f} "
                      f"首次生效 {min(s_ft) if s_ft else None} | 原口径 {lo:.2f}")
    print()
    print("=== 前缀检查：t = 3 h 时两个位置的节点真实配置是否一致 ===")
    for arm in ("ea_nb",):
        for pl in PLACEMENTS:
            rows = out["per_seed"][f"O2_backhaul_outage|{arm}|{pl}"]
            cfg3 = rows[0]["prefix_at_3h"]
            print(f"  {arm}|{pl} seed0 @3h: "
                  f"{ {n: (v['sampling_interval_s'], v['report_period_s']) for n, v in list(cfg3.items())[:4]} }")
        same = 0
        for ci, gi in zip(out["per_seed"][f"O2_backhaul_outage|{arm}|center"],
                          out["per_seed"][f"O2_backhaul_outage|{arm}|gateway"]):
            a = {k: (v["sampling_interval_s"], v["report_period_s"]) for k, v in ci["prefix_at_3h"].items()}
            b = {k: (v["sampling_interval_s"], v["report_period_s"]) for k, v in gi["prefix_at_3h"].items()}
            same += int(a == b)
        print(f"  ⇒ {arm}: 10 个种子里，两位置在 t=3h 的**配置完全相同**的有 **{same}/10** 个")


if __name__ == "__main__":
    main()
