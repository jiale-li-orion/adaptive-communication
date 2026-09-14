"""P1：**逐义务首次到达账本**（doc 58 §P1）。

回答 doc 58 §P1 的四个问题，并把 doc 55 §1.1 指出的时限归因真正闭合：

1. 加快上报**能否**改变「截止前到网关」时刻；
2. 命令当时**是否来得及生效**（记录义务关键阶段当时生效的上报档位）；
3. 样本若已在网关，节点重传**是否还有边际作用**；
4. **节省端**：哪些节点/周期已有合格样本，继续快报是否仍能增加中心**及时**交付。

三级定义（全部带**固定截止期**，`heard_on_time` 是 doc 55 §1.1 要求的新量）：

* `never_heard`  —— 运行结束前**从未**有匹配样本到网关；
* `late_heard`   —— 到了网关，但**第一次**到网关时刻 **晚于** `deadline`；
* `on_time_heard` —— 第一次到网关时刻 **不晚于** `deadline`；
* `delivered`    —— 第一次到中心时刻不晚于 `deadline`（与评分器 `delivered` 逐位等价，本脚本会断言）。

    python3 code/analysis/obligation_arrival_ledger.py --seeds 20

写 `results/obligation_arrival_ledger.json`。
"""
from __future__ import annotations

import argparse
import bisect
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

import center as C                                                       # noqa: E402
from instance_run import one_seed                                        # noqa: E402
from trace_seed_timeline import build_kwargs                             # noqa: E402
# 臂与条件**从 doc 53 的脚本里 import**，避免两处定义漂移
from pacing_fair import CONDITIONS, DWELL, BASE_TAG, PLACEMENT           # noqa: E402

RES = _os.path.normpath(_os.path.join(_CODE, "..", "results"))
#: **只取这两条**（doc 58 §P1 明列）：参照 `fixed300` 与上一轮的赢家。
ARMS = {"fixed300": lambda: C.FixedPeriodPolicy(300, dwell_s=DWELL),
        "pacing_backlog900_300": lambda: C.ReportPacingPolicy(
            slow_s=900, fast_s=300, mode="pending_backlog", dwell_s=DWELL)}


def _period_series(events):
    """从 trace 的 `state` 事件建「节点 → (时刻列表, 上报档位列表)」，用于查**当时生效的档位**。"""
    per: dict[str, list] = {}
    for ev in events:
        if ev[2] != "state":
            continue
        per.setdefault(ev[1], []).append((ev[0], ev[4]))
    return {n: ([t for t, _r in v], [r for _t, r in v]) for n, v in per.items()}


def _period_at(series, node, t_s):
    if node not in series:
        return None
    ts, rs = series[node]
    i = bisect.bisect_right(ts, t_s) - 1
    return rs[i] if i >= 0 else None


def per_seed(run: dict) -> dict:
    rows = run["_obligations"]
    series = _period_series(run.get("_trace") or [])
    # 评分器 `delivered` 与新量 `received_on_time` 必须逐位一致（不一致就是仪器错）
    conflict = sum(1 for r in rows if bool(r["delivered"]) != bool(r["received_on_time"]))
    on_time = [r for r in rows if r["heard_on_time"]]
    late = [r for r in rows if r["heard"] and not r["heard_on_time"]]
    never = [r for r in rows if not r["heard"]]
    # **第 3 问的判据**：准时到网关、却仍未准时到中心 ⇒ 损失发生在网关→中心那一跳
    stuck = [r for r in on_time if not r["delivered"]]
    return {
        "n": len(rows), "conflict": conflict,
        "on_time_heard": len(on_time), "late_heard": len(late), "never_heard": len(never),
        "delivered": sum(1 for r in rows if r["delivered"]),
        "stuck_at_gateway_hop": len(stuck),
        # **第 2 问**：义务在「释放时刻」当时生效的上报档位分布
        "period_at_release": _hist([_period_at(series, r["node_id"], r["release_at"])
                                    for r in rows]),
        # 该义务**首次到网关**时刻生效的档位（只对有到达的）
        "period_at_first_heard": _hist([_period_at(series, r["node_id"], r["first_heard_at"])
                                        for r in on_time + late
                                        if r["first_heard_at"] is not None]),
        # **第 4 问**：慢报（>=900）覆盖的那些义务里，有多少已经准时到达
        "slow_cover_on_time": sum(
            1 for r in on_time
            if (_period_at(series, r["node_id"], r["release_at"]) or 0) >= 900),
    }


def _hist(xs):
    h: dict[str, int] = {}
    for x in xs:
        if x is None:
            continue
        h[str(x)] = h.get(str(x), 0) + 1
    return dict(sorted(h.items(), key=lambda kv: int(kv[0])))


def _mean(xs):
    v = [x for x in xs if x is not None]
    return (round(sum(v) / len(v), 4) if v else None)


def _boot(d, n=2000, seed=0):
    if not d:
        return None
    rnd = random.Random(seed)
    k = len(d)
    m = sorted(_mean([d[rnd.randrange(k)] for _ in range(k)]) for _ in range(n))
    return [round(m[int(0.025 * n)], 3), round(m[int(0.975 * n) - 1], 3)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--out", default="obligation_arrival_ledger")
    args = ap.parse_args()
    for nm, f in ARMS.items():
        C.ARMS[nm] = f

    cfg = json.load(open(_os.path.join(RES, f"{BASE_TAG}.json"), encoding="utf-8"))["config"]
    base = build_kwargs(dict(cfg))
    base.pop("trace", None)
    base.pop("cache_service", None)

    out = {"base": BASE_TAG, "placement": PLACEMENT, "seeds": args.seeds,
           "arms": list(ARMS), "conditions": dict(CONDITIONS),
           "definitions": {
               "on_time_heard": "第一次到网关时刻 <= deadline",
               "late_heard": "到了网关但第一次到网关时刻 > deadline",
               "never_heard": "运行结束前从未有匹配样本到网关",
               "delivered": "第一次到中心时刻 <= deadline（与评分器 delivered 等价）",
               "stuck_at_gateway_hop": "准时到网关却未准时到中心 ⇒ 损失在网关→中心那一跳"},
           "per_seed": {}, "summary": {}, "paired": {}}

    for cond, over in CONDITIONS.items():
        want = (over["access_outage_h"], over["access_outage_start_h"],
                over["outage_hours"], over["outage_start_h"])
        kw = {**base, **over}
        got = (kw["access_outage_h"], kw["access_outage_start_h"],
               kw["outage_hours"], kw["outage_start_h"])
        assert got == want, f"{cond}: 中断设置与声明不符 {got} != {want}"
        per: dict[str, list] = {}
        for arm in ARMS:
            runs = [one_seed(s, arm=arm, placement=PLACEMENT, trace=True,
                             obligation_ledger=True, **kw) for s in range(args.seeds)]
            per[arm] = [{"seed": s, **per_seed(r)} for s, r in enumerate(runs)]
            keys = [k for k in per[arm][0] if k not in ("seed", "period_at_release",
                                                        "period_at_first_heard")]
            out["summary"].setdefault(cond, {})[arm] = {
                k: _mean([x[k] for x in per[arm]]) for k in keys}
        out["per_seed"][cond] = per
        # 配对差（候选 − 参照），含自助区间
        a, b = per["fixed300"], per["pacing_backlog900_300"]
        d = {}
        for k in ("on_time_heard", "late_heard", "never_heard", "delivered",
                  "stuck_at_gateway_hop"):
            v = [y[k] - x[k] for x, y in zip(a, b)]
            d[k] = {"mean": _mean(v), "ci95": _boot(v),
                    "n_gt0": sum(1 for x in v if x > 0), "n_lt0": sum(1 for x in v if x < 0)}
        out["paired"][cond] = d

    path = _os.path.join(RES, f"{args.out}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"wrote {path}\n")
    for cond, blk in out["summary"].items():
        print(f"=== {cond}（分母 {blk['fixed300']['n']:.0f}，{args.seeds} 种子）")
        print(f"  {'臂':<24}{'准时到网关':>10}{'晚到网关':>10}{'从未到网关':>11}"
              f"{'送达':>7}{'**卡在网关→中心**':>17}{'一致性冲突':>11}")
        for arm in ARMS:
            r = blk[arm]
            print(f"  {arm:<24}{r['on_time_heard']:>10.1f}{r['late_heard']:>10.1f}"
                  f"{r['never_heard']:>11.1f}{r['delivered']:>7.1f}"
                  f"{r['stuck_at_gateway_hop']:>17.1f}{r['conflict']:>11.1f}")
        p = out["paired"][cond]
        print(f"  配对差（候选 − 参照）：准时到网关 {p['on_time_heard']['mean']:+.2f} "
              f"CI{p['on_time_heard']['ci95']}｜晚到网关 {p['late_heard']['mean']:+.2f}"
              f"｜**卡在网关→中心** {p['stuck_at_gateway_hop']['mean']:+.2f} "
              f"CI{p['stuck_at_gateway_hop']['ci95']}")
        print(f"    前者更好/更差 {p['on_time_heard']['n_gt0']}/{p['on_time_heard']['n_lt0']}；"
              f"后者更好/更差 {p['stuck_at_gateway_hop']['n_gt0']}/{p['stuck_at_gateway_hop']['n_lt0']}")
        for arm in ARMS:
            print(f"    {arm:<24} 释放时生效档位 {out['per_seed'][cond][arm][0]['period_at_release']}"
                  f" | 首次到网关时档位 {out['per_seed'][cond][arm][0]['period_at_first_heard']}")
        print()


if __name__ == "__main__":
    main()
