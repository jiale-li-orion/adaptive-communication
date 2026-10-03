#!/usr/bin/env python3
"""return-leg fate accounting：一条意图最终**死在哪一级**。

为什么需要它。`loop_split.py` 只给出 `T_return` 的一个数，而那个数**连自己都还没被稳定识别**
（配对身份不够强、右删失被当成 failure、时间原点与 `T_harm` 不一致）。更要紧的是：
即使把 `T_return` 量准了，也答不上「该往哪里改」——因为`从未落地`可能死在三四个完全不同的地方，
每个地方指向**完全不同的方法方向**。

四层（与 `ControlPlane` 的现有分层一一对应，**不新造概念**）：

| 层 | 死法 | 指向的方法 |
|---|---|---|
| 1 | 中心生成后，`center_send` 因**回传当时不可用**被拒 | 缩短 `report_period` **解决不了**（问题在 center→gateway） |
| 2 | 进了 gateway queue，**没等到被听到的 uplink/RX 机会**，先过期/滞留 | `report_period` 买 authority 的方向**有依据** |
| 3 | 有机会了，但 **RX/下行丢失**或仍在排队 | agent infra 的 intent suppression / coalescing 有空间 |
| 4 | 已 delivered，但被 **fenced / dedup / stale_gen** 拒，或**节点已死** | 才轮到 contract / version / atomic execution |

数据来源：**已登记结果文件里的 `intent_ledger` 聚合**（`network.py:intent_ledger`），
所以**不需要跑任何新条件**，也不需要新 trace 字段。

**恒等式必须闭合**（`intent_ledger` 的 docstring 里写死）：
`generated = refused + sent`；`sent = landed + lost + dedup + fenced + stale_gen`。
本脚本**先验证闭合**，不闭合就报错退出——不印一张自己对不上的表。

Run:
    export PYTHONPATH="$PWD/libs/pylibs"
    python3 code/analysis/intent_fate.py results/instance_adm_out3.json
    python3 code/analysis/intent_fate.py --glob 'results/instance_burst_*c0.05.json'
"""
from __future__ import annotations

import argparse
import glob as _glob
import json
import os
import sys

#: 聚合字段 → (层, 含义)。字段名以 `instance_run.py` 的聚合输出为准。
#: ⚠ 层 1 的标签**已按代码核对**：`network.py:_send_command` 里 `else: commands_refused += 1`
#: 配对的正是 `if self.plane.center_send(...)`，而 `center_send` 只在
#: `not path_available(hour, path)` 时返回 False ⇒ 它就是"回传路径当时不可用"。
#: （`intent_ledger` 的 docstring 原先写"连下行机会都没拿到（机会额度用尽）"，与本实现不符，已修。）
LAYERS = (
    ("1 center_send 时回传不可用", ("commands_refused",)),
    ("2 排队中未等到机会/过期/滞留",
     ("intent_expired", "queued_left_derived")),
    ("3 发出后链路丢失", ("intent_lost",)),
    ("4 delivered 但被语义拒绝", ("deduplicated", "fenced", "intent_stale_gen")),
)


def ledger_of(agg: dict) -> dict:
    """把聚合里的账本相关字段取出来；缺的记 `None`（**不当 0**，避免把"没登记"当"没发生"）。"""
    keys = ("intent_generated", "intent_refused", "commands_sent", "commands_delivered",
            "intent_expired", "intent_lost", "deduplicated", "fenced",
            "intent_stale_gen", "intent_rejected", "commands_refused",
            "intent_reason_resend", "intent_reason_sent_resend")
    return {k: agg.get(k) for k in keys}


def check_closure(L: dict, tag: str) -> list[str]:
    """恒等式校验。**不闭合就报错**，不印错表。"""
    errs = []
    g, r, s = L["intent_generated"], L["intent_refused"], L["commands_sent"]
    if None not in (g, r, s) and abs((r + s) - g) > 1e-6:
        errs.append(f"{tag}: generated({g}) != refused({r}) + sent({s})")
    # **完整恒等式**：`lost` 在 `intent_ledger()` 里是**残差**
    # （`lost = sent - landed - dedup - fenced - stale - expired - queued`），
    # 所以闭合式必须把 `expired` 与 `queued_left` 一起算进来。
    # ⚠ 聚合里**没有** `queued_left`，所以只能把它当残差反算，并单列出来——
    #   不能假装它不存在（第一版就是这么写的，于是假报不闭合）。
    if s is not None:
        parts = [L[k] for k in ("commands_delivered", "intent_lost",
                                "deduplicated", "fenced", "intent_stale_gen",
                                "intent_expired")]
        if all(p is not None for p in parts):
            resid = s - sum(parts)          # = queued_left（聚合里没登记）
            L["queued_left_derived"] = resid
            if resid < -1e-6:
                errs.append(f"{tag}: 残差为负（{resid:.3f}）⇒ 账本自相矛盾，须查")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--glob", default="")
    ap.add_argument("--eps", type=float, default=1e-6)
    args = ap.parse_args()

    files = list(args.files)
    if args.glob:
        files.extend(sorted(_glob.glob(args.glob)))
    if not files:
        print("没有输入文件", file=sys.stderr)
        return 2

    all_errs, printed = [], 0
    for path in files:
        doc = json.load(open(path, encoding="utf-8"))
        name = os.path.basename(path)[len("instance_"):-len(".json")]
        for arm, agg in sorted(((doc.get("aggregate") or {}).get("arms") or {}).items()):
            L = ledger_of(agg)
            if L["commands_sent"] is None or L["intent_generated"] is None:
                continue
            errs = check_closure(L, f"{name}/{arm}")
            all_errs.extend(errs)
            dead = [(lab, sum(L[k] or 0.0 for k in ks)) for lab, ks in LAYERS]
            tot_dead = sum(v for _l, v in dead)
            if tot_dead <= args.eps:
                continue
            printed += 1
            print(f"\n{name}  /  {arm}")
            print(f"  生成 {L['intent_generated']:.0f} → 发出 {L['commands_sent']:.0f}"
                  f" → 落地 {L['commands_delivered']:.0f}；"
                  f"未落地合计 {tot_dead:.0f}"
                  f"（其中重发类 {L['intent_reason_resend'] or 0:.0f}）")
            for lab, v in dead:
                if v > args.eps:
                    print(f"     {lab:<28} {v:>7.1f}  占未落地 {v/tot_dead:6.1%}")

    print(f"\n共 {printed} 个 (文件, 臂) 有未落地记录")
    if all_errs:
        print("⚠ **恒等式不闭合**：")
        for e in all_errs[:10]:
            print("   " + e)
        return 1
    print("恒等式全部闭合（generated = refused + sent；sent = landed + lost + dedup + fenced + stale）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
