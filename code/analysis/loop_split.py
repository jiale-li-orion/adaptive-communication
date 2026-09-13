#!/usr/bin/env python3
"""闭环分解：把 `T_loop` 拆成 `T_evidence + T_return`，并算条件概率 `A(a)`。

要回答什么
----------
repo 之前把 `T_ctrl` 近似成「一条**已经准备好**的命令什么时候能落地」。但 G5 关心的是
**reactive** agent：节点产生新证据 → 网关听到 → 回传到中心 → Agent 依这条新证据决策 →
命令回到网关 → 再等一次接收窗口 → 生效。所以真正的量是**闭环**：

    T_loop = T_evidence + T_return

而真正能分开两种失败的，是**条件概率**：

    A(a) = P(T_loop > T_harm(a) | T_evidence ≤ T_deadline)

- `T_evidence > T_deadline` ⇒ **业务/观测已经失败**（数据根本没按时到）；
- `T_evidence ≤ T_deadline ∧ T_loop > T_harm` ⇒ **authority failure**（数据到了，闭环来不及救）。

无条件那个 `P(T_ctrl > T_harm)` 把两者混成一个数，所以上一轮卡在"A 与 B 混杂"上。

两条腿怎么测（**都在已有 trace 上，不加条件、不加策略**）
--------------------------------------------------------
- `T_return = t_applied − t_plan`：trace 的 `plan` 与 `applied` 两种事件都在，按 **节点 + 值** 配对。
- `T_evidence = soc_age_s`：`plan` 事件里带的诊断字段（按**源时刻**算的证据年龄）。
  这个字段是为测量而加的，见 `docs/s8-report/progress-log.md` §7.76。

**样本量必须一起报。** polar 下 `T_evidence ≤ T_deadline` 会筛掉大部分决策，
条件样本可能只剩几个——那时候不许下结论。

Run:
    export PYTHONPATH="$PWD/libs/pylibs"
    python3 code/analysis/loop_split.py --tags adm_noout,adm_out3 --arm ea_nb --seeds 3
"""
from __future__ import annotations

import argparse
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "instance"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "experiments"))

from instance_run import one_seed                      # noqa: E402
from trace_seed_timeline import build_kwargs           # noqa: E402
import regime_map as RM                                # noqa: E402

#: 常规义务周期（秒）。业务最晚多久必须得到结果 ⇒ 用**已登记**的 `routine_period_s`。
DEFAULT_DEADLINE_S = 3600


def pairs(trace: list) -> list[dict]:
    """从一条时间线里抽出每个 `plan` 及其配对 `applied`，算两条腿。

    配对规则：同一节点、**同一字段值**、时间严格在 `plan` 之后的**第一个** `applied`。
    配不上的 `plan` 单独记（它们是"意图没有落地"，本身也是信息，不能悄悄丢掉）。
    """
    by_node: dict[str, list] = {}
    for e in trace:
        if e[2] == "applied":
            by_node.setdefault(e[1], []).append(e)
    out = []
    for e in trace:
        if e[2] != "plan":
            continue
        t_s, nid, _k, soc_seen, op, value, age = (list(e) + [None] * 7)[:7]
        hit = None
        for a in by_node.get(nid, ()):
            if a[0] > t_s and a[4] == value:
                hit = a
                break
        out.append({"t": t_s, "node": nid, "soc_seen": soc_seen,
                    "t_evidence_s": age,
                    "t_return_s": None if hit is None else hit[0] - t_s})
    return out


def t_harm_at(soc: float, cfg_pair: tuple[int, int]) -> float:
    """此刻在跑的配置把节点推到归零还要多久（零采能上界，手算可核）。"""
    if soc is None or soc <= 0:
        return 0.0
    return soc / RM.hourly_load(*cfg_pair)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags", default="adm_noout,adm_out3")
    ap.add_argument("--arm", default="ea_nb")
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--deadline-s", type=int, default=DEFAULT_DEADLINE_S)
    args = ap.parse_args()

    print(f"闭环分解：arm = {args.arm}，{args.seeds} 个种子，"
          f"T_deadline = {args.deadline_s} s（已登记的常规义务周期）\n")
    all_rows = []
    for tag in [t.strip() for t in args.tags.split(",") if t.strip()]:
        cfg = json.load(open(f"results/instance_{tag}.json", encoding="utf-8"))["config"]
        kw = build_kwargs(dict(cfg))
        kw.pop("trace", None)
        rows = []
        for seed in range(args.seeds):
            try:
                d = one_seed(seed, arm=args.arm, trace=True, **kw)
            except Exception as exc:                        # noqa: BLE001
                print(f"  {tag} seed {seed}: 跑不动 —— {type(exc).__name__}: {exc}")
                continue
            # 节点侧真实配置（用最后一条 state 事件推此刻在跑什么）
            for p in pairs(d["_trace"]):
                st_ev = [e for e in d["_trace"]
                         if e[2] == "state" and e[1] == p["node"] and e[0] == p["t"]]
                pair_cfg = (st_ev[0][3], st_ev[0][4]) if st_ev else (3600, 3600)
                # **两个口径都要算**：`soc_seen` 是中心**相信**的电量，`state` 是**真实**电量。
                # `out3` 的机制恰恰是"相信 0.0185 而真实接近死亡"——用信念算 `T_harm` 会偏大、
                # 从而把 `A` 往 0 压。**主口径用真实 SoC**；信念口径同时报出来，让偏置量可见。
                # 决策时**在跑的上报周期**：`T_return` 若由"上报周期 + 一次回传"量化决定，
                # 那么按它分箱就该看到 `T_return` 随上报周期成比例变化。
                p["report_s"] = st_ev[0][4] if st_ev else None
                p["t_harm_true_s"] = t_harm_at(st_ev[0][5] if st_ev else None, pair_cfg) * 3600.0
                p["t_harm_belief_s"] = t_harm_at(p["soc_seen"], pair_cfg) * 3600.0
                rows.append(p)
        all_rows.extend((tag, r) for r in rows)
        n = len(rows)
        matched = [r for r in rows if r["t_return_s"] is not None]
        ev = [r["t_evidence_s"] for r in rows if r["t_evidence_s"] is not None]
        rt = [r["t_return_s"] for r in matched]
        print(f"== {tag} ==")
        print(f"   决策数 n={n}；配到 applied 的 n={len(matched)}"
              f"（**配不上的 {n - len(matched)} 个是意图没落地，单独计**）")
        if ev:
            print(f"   T_evidence 秒：中位 {st.median(ev):.0f}  最大 {max(ev):.0f}  n={len(ev)}")
        if rt:
            print(f"   T_return  秒：中位 {st.median(rt):.0f}  最大 {max(rt):.0f}  n={len(rt)}")
        # **按上报周期分箱**：检验 `T_return` 是不是"上报周期 + 一次回传"的确定性量化。
        bins: dict = {}
        for r in matched:
            bins.setdefault(r.get("report_s"), []).append(r["t_return_s"])
        print("   T_return 按在跑的上报周期分箱（中位 / n）：")
        for rep in sorted(b for b in bins if b is not None):
            v = bins[rep]
            print(f"     上报周期 {rep:>5} s ⇒ T_return 中位 {st.median(v):>7.0f} s  n={len(v)}")
        cond = [r for r in matched
                if r["t_evidence_s"] is not None
                and r["t_evidence_s"] <= args.deadline_s]
        if cond:
            ft = [r for r in cond
                  if (r["t_evidence_s"] + r["t_return_s"]) > r["t_harm_true_s"]]
            fb = [r for r in cond
                  if (r["t_evidence_s"] + r["t_return_s"]) > r["t_harm_belief_s"]]
            print(f"   **条件样本**（T_evidence ≤ deadline）n={len(cond)}")
            print(f"     A（真实 SoC 算 T_harm，主口径）= {len(ft)/len(cond):.3f}  (n_fail={len(ft)})")
            print(f"     A（信念 SoC 算 T_harm，旧口径） = {len(fb)/len(cond):.3f}  (n_fail={len(fb)})")
        else:
            print("   **条件样本 n=0 ⇒ 不许下结论**")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
