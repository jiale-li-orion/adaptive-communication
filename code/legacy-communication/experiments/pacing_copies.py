"""副本覆盖率导向的上报节奏：冻结 9 臂对照（P2）。
本模块引用的 `docs/…` 路径为作者本地过程文档，不随仓库发布。

臂集合与判读规则**先写定**在
`docs/s7-method/instance-v1/60-pre-registration-copy-coverage-pacing-2026-09-14.md`，
本脚本只是它的执行器；**任何结果都不得导致臂集合或规则被改动**。

与 `pacing_fair.py`（**保持不动**）的差别：

1. 竞争臂换成 doc 60 §2 冻结的 9 条：`fixed300`、`pacing_backlog900_300`、
   `oblig_copies{1,2,3}`（**最可能竞争的普通规则**）、`oblig_slack`（候选）与 3 条消融；
2. **额外跑冻结普通基线**（`local` + `fixed{600,900,1800,3600}` + aoi 系）——
   它们**不参与竞争**，只用于确定服务容差的分位（参照服务）。这是**更严**的协议：
   分位越高 ⇒ R1/R2 越难过；
3. 记录量按 doc 60 §4 **分列**，并用 P1 到达台账把损失定位到「哪一跳」；
4. 逐义务**副本数**（`n_heard`）单独统计——它是 P1 定位出的机制变量。

    python3 code/experiments/pacing_copies.py --seeds 20

写 `results/pacing_copies.json`。
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
FAST_S, SLOW_S = 300, 900
OBLIGATION_PERIOD_S = 900
COMMAND_DELAY_S = 600          # 与 dwell 同值：中心点到网关到节点的生效延迟下界

#: **冻结的 9 条竞争臂**（doc 60 §2）
COMPETING = ("fixed300", "pacing_backlog900_300",
             "oblig_copies1", "oblig_copies2", "oblig_copies3",
             "oblig_slack", "oblig_slack_no_slack", "oblig_slack_no_delay",
             "oblig_slack_no_obligation")
ORDINARY_COPIES = ("oblig_copies1", "oblig_copies2", "oblig_copies3")
ABLATIONS = ("oblig_slack_no_slack", "oblig_slack_no_delay", "oblig_slack_no_obligation")
#: 候选必须打赢的**全部成员**（doc 60 §5 R2）
R2_RIVALS = ("fixed300", "pacing_backlog900_300") + ORDINARY_COPIES
#: **只**用来定容差分位的冻结普通基线，**不参与竞争**
REFERENCE_BASELINES = ("local", "fixed600", "fixed900", "fixed1800", "fixed3600",
                       "aoi", "aoi_const300", "aoi_f600", "aoi_t7200")

TOLERANCES = (0.00, 0.01)
MAIN_TOLERANCES = ("0.00%", "1.00%")
#: doc 60 §4 的分列成本轴
COST_AXES = ("uplinks", "downlink_attempts", "airtime_uplink_h",
             "energy_consumed_wh", "aoi_mean_s")
#: 到达台账的三级 + 卡住位置（doc 60 §4）
LEDGER_KEYS = ("n_collected", "on_time_heard", "late_heard", "never_heard",
               "stuck_at_gateway_hop", "delivered", "sum_copies_heard")

CONDITIONS = {
    "P0_no_outage": dict(access_outage_h=0.0, access_outage_start_h=4.0,
                         outage_hours=0.0, outage_start_h=0.0),
    "P1_backhaul_4h7h": dict(access_outage_h=0.0, access_outage_start_h=4.0,
                             outage_hours=3.0, outage_start_h=4.0),
    "P2_access_4h7h": dict(access_outage_h=3.0, access_outage_start_h=4.0,
                           outage_hours=0.0, outage_start_h=0.0),
}


def _register() -> None:
    C.ARMS["fixed300"] = lambda: C.FixedPeriodPolicy(FAST_S, dwell_s=DWELL)
    C.ARMS["pacing_backlog900_300"] = (
        lambda: C.ReportPacingPolicy(slow_s=SLOW_S, fast_s=FAST_S,
                                     dwell_s=DWELL, mode="pending_backlog"))
    for k in (1, 2, 3):
        C.ARMS[f"oblig_copies{k}"] = (
            lambda _k=k: C.ObligationCopiesPolicy(k=_k, fast_s=FAST_S, slow_s=SLOW_S,
                                                  dwell_s=DWELL))
    for nm, kw in (("oblig_slack", {}),
                   ("oblig_slack_no_slack", dict(use_slack=False)),
                   ("oblig_slack_no_delay", dict(use_delay=False)),
                   ("oblig_slack_no_obligation", dict(use_obligation=False))):
        C.ARMS[nm] = (lambda _kw=kw: C.ObligationSlackPolicy(
            fast_s=FAST_S, slow_s=SLOW_S, dwell_s=DWELL,
            obligation_period_s=OBLIGATION_PERIOD_S,
            command_delay_s=COMMAND_DELAY_S, **_kw))
    # 参照基线
    for r in (600, 900, 1800, 3600):
        C.ARMS[f"fixed{r}"] = (lambda _r=r: C.FixedPeriodPolicy(_r, dwell_s=DWELL))
    C.ARMS["aoi"] = lambda: C.AoiPolicy(dwell_s=DWELL)
    C.ARMS["aoi_const300"] = lambda: C.AoiPolicy(dwell_s=DWELL, fast_s=300, slow_s=300)
    C.ARMS["aoi_f600"] = lambda: C.AoiPolicy(dwell_s=DWELL, fast_s=600)
    C.ARMS["aoi_t7200"] = lambda: C.AoiPolicy(dwell_s=DWELL, stale_s=7200)


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
    """单次运行的**全部**记录量（doc 60 §4），不隐藏任何一列。"""
    rt = run["routine"]
    en = (run.get("energy") or {}).get("per_node") or {}
    cm = run.get("communication") or {}
    ch = _changes(run.get("_trace") or [])
    down = [c for c in ch if c["strict_downgrade"]]
    rows = sorted(run.get("_obligations") or [], key=lambda r: r["oid"])
    n = len(rows) or 1
    return {
        # —— 服务与损失（分列）
        "service": rt["delivered"], "service_denom": rt["n"],
        "missing_collection": rt["missing_collection"],
        "missing_delivery": rt["missing_delivery"], "aoi_mean_s": rt["aoi_mean_s"],
        # —— 成本分列
        "uplinks": cm.get("uplinks"), "downlink_attempts": cm.get("downlink_attempts"),
        "airtime_uplink_h": cm.get("airtime_uplink_h"),
        "energy_consumed_wh": round(sum((v.get("consumed_wh") or 0.0)
                                        for v in en.values()), 8),
        "nodes_dead": sum(1 for v in en.values() if v.get("dead_at_s") is not None),
        "n_config_changes": len(ch), "n_strict_downgrades": len(down),
        # —— 到达台账：把损失定位到**哪一跳**
        "n_collected": sum(1 for r in rows if r["collected"]),
        "on_time_heard": sum(1 for r in rows if r["heard_on_time"]),
        "late_heard": sum(1 for r in rows
                          if r["heard"] and not r["heard_on_time"]),
        "never_heard": sum(1 for r in rows if not r["heard"]),
        "stuck_at_gateway_hop": sum(1 for r in rows
                                    if r["heard"] and not r["delivered"]),
        "delivered": sum(1 for r in rows if r["delivered"]),
        # —— 机制变量：逐义务**副本数**（P1 定位出的那一跳的覆盖率）
        "sum_copies_heard": sum(r["n_heard"] for r in rows),
        "mean_copies_heard": round(sum(r["n_heard"] for r in rows) / n, 6),
        "mean_copies_received": round(sum(r["n_received"] for r in rows) / n, 6),
        "first_downgrade_t_s": (min((c["t_s"] for c in down), default=None)),
    }


def _mean(xs):
    v = [x for x in xs if x is not None]
    return (round(sum(v) / len(v), 6) if v else None)


def _boot(d, n=2000, seed=0, alpha=0.05):
    if not d:
        return None
    rnd = random.Random(seed)
    k = len(d)
    m = sorted(_mean([d[rnd.randrange(k)] for _ in range(k)]) for _ in range(n))
    lo = round(m[int(alpha / 2 * n)], 4)
    hi = round(m[int((1 - alpha / 2) * n) - 1], 4)
    return [lo, hi]


def paired(per_seed: dict, cond: str, arm: str, ref: str, keys) -> dict:
    """同种子配对差 + 自助区间；另给同向种子比（**单种子不得下结论**）。"""
    a = per_seed[cond][arm]
    b = per_seed[cond][ref]
    out = {}
    for k in keys:
        d = [(x[k] - y[k]) for x, y in zip(a, b)
             if x.get(k) is not None and y.get(k) is not None]
        if not d:
            continue
        ci = _boot(d, seed=abs(hash((cond, arm, ref, k))) % 10 ** 6)
        out[k] = {
            "mean_delta": _mean(d), "ci95": ci,
            "ci_excludes_0": bool(ci and (ci[0] > 0 or ci[1] < 0)),
            "n_pos": sum(1 for x in d if x > 0), "n_neg": sum(1 for x in d if x < 0),
            "n_seeds": len(d),
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--out", default="pacing_copies")
    args = ap.parse_args()
    _register()

    cfg = json.load(open(_os.path.join(RES, f"{BASE_TAG}.json"), encoding="utf-8"))["config"]
    base = build_kwargs(dict(cfg))
    base.pop("trace", None)
    base.pop("cache_service", None)

    arms = list(COMPETING) + list(REFERENCE_BASELINES)
    out = {"base": BASE_TAG, "placement": PLACEMENT, "seeds": args.seeds,
           "competing": list(COMPETING), "reference_baselines": list(REFERENCE_BASELINES),
           "r2_rivals": list(R2_RIVALS), "tolerances": list(TOLERANCES),
           "main_tolerances": list(MAIN_TOLERANCES),
           "obligation_period_s": OBLIGATION_PERIOD_S, "dwell_s": DWELL,
           "rows": {}, "per_seed": {}, "reference": {},
           "rules": {}, "paired": {}}

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
            ex = [extract(r) for r in runs]
            out["rows"][cond][arm] = {k: _mean([e[k] for e in ex]) for k in keys}
            out["per_seed"][cond][arm] = [
                {"seed": s, **e,
                 # 位图：义务按 `oid` 定序 ⇒ 可跨臂精确求翻转集
                 "delivered_bitmap": "".join(
                     "1" if x["delivered"] else "0"
                     for x in sorted(r["_obligations"], key=lambda y: y["oid"])),
                 "on_time_heard_bitmap": "".join(
                     "1" if x["heard_on_time"] else "0"
                     for x in sorted(r["_obligations"], key=lambda y: y["oid"])),
                 "stuck_bitmap": "".join(
                     "1" if (x["heard"] and not x["delivered"]) else "0"
                     for x in sorted(r["_obligations"], key=lambda y: y["oid"]))}
                for s, (r, e) in enumerate(zip(runs, ex))]
            print(f"  {cond} {arm:28s} 服务 {out['rows'][cond][arm]['service']:6.2f}"
                  f" 缺采 {out['rows'][cond][arm]['missing_collection']:6.2f}"
                  f" 上行 {out['rows'][cond][arm]['uplinks']:7.1f}"
                  f" 能耗 {out['rows'][cond][arm]['energy_consumed_wh']:8.4f}"
                  f" 卡住 {out['rows'][cond][arm]['stuck_at_gateway_hop']:6.2f}")

        # 参照服务：只取冻结普通基线的**最高**服务（更严）
        den = out["rows"][cond]["fixed300"]["service_denom"]
        ref_arm = max(REFERENCE_BASELINES, key=lambda a: out["rows"][cond][a]["service"])
        ref_srv = out["rows"][cond][ref_arm]["service"]
        ref_mc = out["rows"][cond][ref_arm]["missing_collection"]
        out["paired"][cond] = {}
        for arm in COMPETING:
            for ref in sorted(set(R2_RIVALS) | {ref_arm}):
                if arm == ref:
                    continue
                out["paired"][cond][f"{arm}|{ref}"] = paired(
                    out["per_seed"], cond, arm, ref,
                    ("service", "missing_collection", *COST_AXES, *LEDGER_KEYS))
        out["reference"][cond] = {
            "denom": den, "reference_arm": ref_arm, "reference_service": ref_srv,
            "reference_missing_collection": ref_mc,
            "floors": {f"{t:.2%}": round(ref_srv - t * den, 4) for t in TOLERANCES}}

    path = _os.path.join(RES, f"{args.out}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
