#!/usr/bin/env python3
"""闭环分解：把 `T_loop` 拆成 `T_evidence + T_return`，并算条件概率 `A(a)`。
本模块引用的 `docs/…` 路径为作者本地过程文档，不随仓库发布。

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


def pairs(trace: list) -> tuple[list[dict], dict]:
    """按**逻辑身份**把 `plan → sent → applied` 串起来，算两条腿。

    为什么要身份。按「同节点 + 同值」配对时，`aoi` 的 67% 重发（§6.24）会让多条 plan
    **认领同一次 `applied`**，既污染 `T_return` 也把"哪条 intent 从未落地"搞错。
    身份由 `network.py` 写进 trace 的三个事件：`plan`（决策）→ `sent`（带 `logical`）→
    `applied`（带 `logical`）。`logical = f"{node}:{op}:{generation}"`，与节点侧
    `applied_logicals` 去重用的是同一个串。

    **三种结局在逐 intent 级就分开了**（这正是四层归因要的）：
    - **没找到 `sent`** ⇒ 这条意图**被第一层拒了**（`center_send` 时回传路径不可用）；
    - 有 `sent` 但没有同身份的 `applied` ⇒ **发出去了但没落地**（第二/三层）；
    - 有 `applied` ⇒ 落地，`T_return = t_applied − t_plan`。

    向后兼容：trace 里没有 `sent` 事件（旧 dump）时退回**贪心一对一**，并报出用了哪种。
    """
    has_identity = any(e[2] == "sent" for e in trace)
    applied_by_logical: dict = {}
    for e in trace:
        if e[2] == "applied" and len(e) > 5 and e[5]:
            applied_by_logical.setdefault(e[5], [e, False])
    sent_pool: dict = {}
    for e in trace:
        if e[2] == "sent":
            sent_pool.setdefault(e[1], []).append([e, False])
    out = []
    for e in trace:
        if e[2] != "plan":
            continue
        t_s, nid, _k, soc_seen, op, value, age = (list(e) + [None] * 7)[:7]
        t_ret, refused, logical, found_sent = None, False, None, False
        if has_identity:
            for slot in sent_pool.get(nid, ()):
                se = slot[0]
                if (not slot[1]) and se[0] == t_s and se[4] == op and se[5] == value:
                    slot[1] = True
                    logical = se[3]
                    found_sent = True
                    break
            if not found_sent:
                refused = True                      # 第一层：根本没发出去
            elif logical is not None:
                hit = applied_by_logical.get(logical)
                if hit and not hit[1]:
                    hit[1] = True
                    t_ret = hit[0][0] - t_s
            else:
                # ⚠ `send_contract_fields=False`（如 naive 执行层）时报文里**根本没有** `logical`，
                # 这时身份不存在，只能退回**贪心一对一**。**"没有身份"与"没找到 sent"是两件事**，
                # 第一版把两者都写成 `logical is None`，于是所有落地都被判成"从未落地"（落地 0）。
                t_ret = _greedy_one(trace, nid, t_s, value)
        else:                                        # 旧 trace：贪心一对一（按值）
            t_ret = _greedy_one(trace, nid, t_s, value)
        out.append({"t": t_s, "node": nid, "soc_seen": soc_seen,
                    "t_evidence_s": age, "t_return_s": t_ret,
                    "refused": refused, "logical": logical})
    stats = {"t_end": max((e[0] for e in trace), default=0), "plans": len(out),
             "has_identity": has_identity,
             "refused": sum(1 for r in out if r["refused"]),
             "sent_no_apply": sum(1 for r in out
                                  if (not r["refused"]) and r["t_return_s"] is None),
             "applied": sum(1 for r in out if r["t_return_s"] is not None),
             "applied_unclaimed": sum(1 for v in applied_by_logical.values() if not v[1])}
    return out, stats


def _greedy_one(trace: list, nid: str, t_s: int, value):
    """按值的一对一贪心：同节点、同值、`t_s` 之后**最早未被认领**的 `applied`。"""
    for slot in _legacy_applied(trace, nid):
        if (not slot[1]) and slot[0][0] > t_s and slot[0][4] == value:
            slot[1] = True
            return slot[0][0] - t_s
    return None


_LEGACY: dict = {}


def _legacy_applied(trace: list, nid: str) -> list:
    """旧 trace 的 applied 池（按 `(节点, 值)` 贪心一对一）。只在没有 `sent` 事件时用。"""
    key = id(trace)
    if key not in _LEGACY:
        pool: dict = {}
        for e in trace:
            if e[2] == "applied":
                pool.setdefault(e[1], []).append([e, False])
        _LEGACY[key] = pool
    return _LEGACY[key].get(nid, ())


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
    all_rows, stats_by_tag = [], {}
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
            _pairs, st_ = pairs(d["_trace"])
            t_end = st_["t_end"]
            # **累加而不是覆盖**：`st_` 是**单种子**的，而下面报的 `决策 n` 是跨种子汇总的。
            # 覆盖会让印出的"落地/被拒"只反映最后一个种子，与 n 不同口径（踩过）。
            acc = stats_by_tag.setdefault(tag, {})
            for k, v in st_.items():
                if isinstance(v, bool):
                    acc[k] = v
                elif k == "t_end":
                    acc[k] = max(acc.get(k, 0), v)
                else:
                    acc[k] = acc.get(k, 0) + v
            for p in _pairs:
                st_ev = [e for e in d["_trace"]
                         if e[2] == "state" and e[1] == p["node"] and e[0] == p["t"]]
                pair_cfg = (st_ev[0][3], st_ev[0][4]) if st_ev else (3600, 3600)
                # **两个口径都要算**：`soc_seen` 是中心**相信**的电量，`state` 是**真实**电量。
                # `out3` 的机制恰恰是"相信 0.0185 而真实接近死亡"——用信念算 `T_harm` 会偏大、
                # 从而把 `A` 往 0 压。**主口径用真实 SoC**；信念口径同时报出来，让偏置量可见。
                # 决策时**在跑的上报周期**：`T_return` 若由"上报周期 + 一次回传"量化决定，
                # 那么按它分箱就该看到 `T_return` 随上报周期成比例变化。
                p["report_s"] = st_ev[0][4] if st_ev else None
                p["_t_end"] = t_end
                p["t_harm_true_s"] = t_harm_at(st_ev[0][5] if st_ev else None, pair_cfg) * 3600.0
                p["t_harm_belief_s"] = t_harm_at(p["soc_seen"], pair_cfg) * 3600.0
                rows.append(p)
        all_rows.extend((tag, r) for r in rows)
        n = len(rows)
        matched = [r for r in rows if r["t_return_s"] is not None]
        ev = [r["t_evidence_s"] for r in rows if r["t_evidence_s"] is not None]
        rt = [r["t_return_s"] for r in matched]
        print(f"== {tag} ==")
        st_ = stats_by_tag.get(tag, {})
        mode = "**真身份**" if st_.get("has_identity") else "贪心一对一（旧 trace）"
        print(f"   决策 n={n}｜{mode}｜落地 {st_.get('applied')}"
              f"｜**被第一层拒 {st_.get('refused')}**"
              f"｜**发出但未落地 {st_.get('sent_no_apply')}**"
              f"｜未被认领的 applied {st_.get('applied_unclaimed')}")
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
        # ⚠ **未落地的意图不能丢。** `T_return = None` 意味着"这条纠正到任务结束都没生效"，
        # 那**本身就是闭环未闭合**——正是要找的 authority failure。原先只在 `matched` 里取条件样本，
        # 等于把分子和分母同时剔掉了最该算的那些行，**系统性把 A 压向 0**。
        # 现在：未落地按 `T_return = ∞` 计入（记作 `never`），单列出来。
        cond = [r for r in rows
                if r["t_evidence_s"] is not None
                and r["t_evidence_s"] <= args.deadline_s]
        for r in cond:
            r["loop_s"] = (None if r["t_return_s"] is None
                           else r["t_evidence_s"] + r["t_return_s"])
        if cond:
            def is_fail(r, horizon_key):
                """**主口径**：`T_return` 对 `T_harm^now`（从现在起）；`T_evidence` 只作条件。
                未落地（`T_return=None`）**只在** `t_plan + T_harm^now <= t_end` 时才无争议记 failure；
                否则是**右删失**，单列。
                """
                hr = r[horizon_key]
                if r["t_return_s"] is None:
                    return (r["t"] + hr) <= r["_t_end"], True      # (是否 failure, 是否删失)
                return r["t_return_s"] > hr, False
            fails, cens = 0, 0
            for r in cond:
                f, c = is_fail(r, "t_harm_true_s")
                fails += bool(f)
                cens += bool(c)
            # 旧口径（**口径不一致，仅作对照，不作结论**）：`T_loop > T_harm^now`，
            # 把发生在决策之前的 `T_evidence` 也从当前生存预算里扣了一遍。
            old_f = sum(1 for r in cond
                        if r["loop_s"] is None or r["loop_s"] > r["t_harm_true_s"])
            print(f"   **条件样本**（T_evidence ≤ deadline）n={len(cond)}")
            print(f"     ★ A（主口径 T_return vs T_harm^now）= {fails/len(cond):.3f}"
                  f"  (n_fail={fails}, 其中右删失 {cens})")
            print(f"       A（旧口径 T_loop vs T_harm^now，**口径不一致**) = {old_f/len(cond):.3f}")
        else:
            print("   **条件样本 n=0 ⇒ 不许下结论**")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
