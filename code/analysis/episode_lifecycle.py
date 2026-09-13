#!/usr/bin/env python3
"""逐 **episode** 的语义控制回路聚合。

回答的问题
----------
`intent` 层的失败率**不能**直接翻译成系统失败：同一个节点为了同一个目标重试 20 次、前 19 次被
layer 1 拒、第 20 次成功，intent 层看起来是 95% failure，**控制回路层其实是 100% closed**。
所以真正要问的是：

> **Agent 是真的失去了控制，还是只是为了完成同一个控制动作喊了太多遍？**

episode 的定义（**冻结，不得事后改**）
-----------------------------------
一次**语义上的远端状态改变需求**：对节点 `i` 的某个 effect，当 planner **第一次产生一个与当前目标
不同的 target** 时 episode 开始；随后所有为实现**同一个 target** 的重试都属同一 episode
（复用 `plan` 事件里的 `intent_reason`：`target_change` 开新 episode，`resend` 留在旧 episode，
`unknown_state` **看 target 变没变**——没变就仍是同一 episode）。

结束于五种之一：**closed**（真正 applied）/ **superseded**（被后续新 target 取代）/
**deadline**（超过该动作的有效 deadline 仍未生效）/ **node_dead**（节点先死）/ **censored**（trace 结束）。

**冻结的判定细节**：
- **superseded 不算 failure**（它已失去业务意义），单列。
- **censored 不算 failure**，单列。
- 真正危险的是**supersede 之后才 applied 的 obsolete effect** ⇒ 记为 `obsolete_apply`，
  只有它才让 contract/version/atomic 那条线有承重意义。

四个量 + 两个放大率：closure rate、time-to-settle、attempts/closed、terminal layer；
`planning amplification = #intents / #episodes`、`wasted per closed = (#attempts − #closed)/#closed`。

Run:
    export PYTHONPATH="$PWD/libs/pylibs"
    python3 code/analysis/episode_lifecycle.py --tags adm_noout,adm_out3 --arm aoi --seeds 3
"""
from __future__ import annotations

import argparse
import json
import os
import statistics as st
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [_HERE, os.path.join(_HERE, "..", "instance"),
                os.path.join(_HERE, "..", "experiments")]

from instance_run import one_seed                      # noqa: E402
from trace_seed_timeline import build_kwargs           # noqa: E402

#: 该动作的**有效 deadline**（秒）。取已登记的常规义务周期——目标若在这么久内没生效，
#: 它对这一段业务就已经没有意义了。**这是声明，不是拟合。**
DEADLINE_S = 3600


def episodes(trace: list, deadline_s: int = DEADLINE_S) -> dict:
    """把一条时间线切成 episode，并给每个 episode 一个终局。"""
    t_end = max((e[0] for e in trace), default=0)
    # 节点存活区间（`state` 事件里 alive=False 的最早时刻）
    dead_at: dict = {}
    for e in trace:
        if e[2] == "state" and len(e) > 6 and e[6] is False:
            dead_at[e[1]] = min(dead_at.get(e[1], e[0]), e[0])
    applied: dict = {}          # (node, op) -> [(t, value)]
    for e in trace:
        if e[2] == "applied":
            applied.setdefault((e[1], e[3]), []).append((e[0], e[4]))
    plans: dict = {}            # (node, op) -> [(t, value, reason)]
    for e in trace:
        if e[2] == "plan":
            plans.setdefault((e[1], e[4]), []).append(
                (e[0], e[5], e[7] if len(e) > 7 else None))

    out = []
    for (nid, op), ps in plans.items():
        ps.sort()
        segs = []               # 按 target 变化切段
        for t, val, reason in ps:
            if not segs or segs[-1]["target"] != val:
                segs.append({"target": val, "start": t, "attempts": [], "reason": reason})
            segs[-1]["attempts"].append(t)
        for k, sg in enumerate(segs):
            next_start = segs[k + 1]["start"] if k + 1 < len(segs) else t_end + 1
            ap = [a for a in applied.get((nid, op), ())
                  if sg["start"] <= a[0] <= next_start and a[1] == sg["target"]]
            rec = {"node": nid, "op": op, "target": sg["target"],
                   "start": sg["start"], "n_attempts": len(sg["attempts"]),
                   "opens": sg["reason"]}
            if ap:
                rec.update(terminal="closed", settle_s=ap[0][0] - sg["start"])
            elif k + 1 < len(segs):
                rec.update(terminal="superseded", settle_s=None)
            elif t_end < sg["start"] + deadline_s:
                rec.update(terminal="censored", settle_s=None)
            elif nid in dead_at and dead_at[nid] <= sg["start"] + deadline_s:
                rec.update(terminal="node_dead", settle_s=None)
            else:
                rec.update(terminal="deadline", settle_s=None)
            out.append(rec)
    # **obsolete apply**：supersede 之后才生效的旧 target
    obsolete = 0
    for (nid, op), ps in plans.items():
        for i in range(len(ps)):
            for a in applied.get((nid, op), ()):
                if a[0] > ps[i][0] and a[1] == ps[i][1]:
                    later = [p for p in ps if p[0] > ps[i][0] and p[1] != ps[i][1]]
                    if later and a[0] > later[0][0]:
                        obsolete += 1
                    break
    return {"rows": out, "t_end": t_end, "obsolete_apply": obsolete}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags", default="adm_noout,adm_out3")
    ap.add_argument("--arm", default="aoi")
    ap.add_argument("--seeds", type=int, default=3)
    args = ap.parse_args()

    print(f"episode 聚合：arm={args.arm}，{args.seeds} 种子，deadline={DEADLINE_S} s\n")
    for tag in [t.strip() for t in args.tags.split(",") if t.strip()]:
        cfg = json.load(open(f"results/instance_{tag}.json", encoding="utf-8"))["config"]
        kw = build_kwargs(dict(cfg))
        kw.pop("trace", None)
        rows, intent_n, obsolete = [], 0, 0
        for seed in range(args.seeds):
            try:
                d = one_seed(seed, arm=args.arm, trace=True, **kw)
            except Exception as exc:                        # noqa: BLE001
                print(f"  {tag} seed {seed}: {type(exc).__name__}: {exc}")
                continue
            ep = episodes(d["_trace"])
            rows.extend(ep["rows"])
            obsolete += ep["obsolete_apply"]
            intent_n += sum(1 for e in d["_trace"] if e[2] == "plan")
        if not rows:
            print(f"== {tag} == 无 episode\n")
            continue
        term: dict = {}
        for r in rows:
            term[r["terminal"]] = term.get(r["terminal"], 0) + 1
        closed = term.get("closed", 0)
        n = len(rows)
        settle = [r["settle_s"] for r in rows if r["settle_s"] is not None]
        # closure rate 的两种分母都报：含/不含 superseded 与 censored（**口径必须写明**）
        denom_strict = n - term.get("superseded", 0) - term.get("censored", 0)
        print(f"== {tag} ==")
        print(f"   intent n={intent_n}；**episode n={n}**；"
              f"planning amplification = {intent_n/n:.2f}×")
        print(f"   终局：{term}")
        if denom_strict > 0:
            print(f"   **closure rate = {closed}/{denom_strict} = {closed/denom_strict:.1%}**"
                  f"（分母剔除 superseded 与 censored）")
        print(f"   closure rate（含全部 episode 作分母）= {closed/n:.1%}")
        if settle:
            print(f"   time-to-settle：中位 {st.median(settle):.0f} s  最大 {max(settle):.0f} s")
        if closed:
            print(f"   attempts per closed episode = "
                  f"{sum(r['n_attempts'] for r in rows if r['terminal']=='closed')/closed:.1f}")
            print(f"   wasted reasoning per closed effect = "
                  f"{(sum(r['n_attempts'] for r in rows)-closed)/closed:.1f}")
        print(f"   **obsolete apply（supersede 之后才生效）= {obsolete}**")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
