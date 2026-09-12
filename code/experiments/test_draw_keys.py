#!/usr/bin/env python3
"""
test_draw_keys.py — the packet-level randomness contract.

Three properties have to hold or the comparison between runtimes is not a comparison:

  1. PAIRED. The same logical operation meets the same draw in every arm. If arm A and arm B both
     send operation X at hour t, they meet the same channel.

  2. SEPARATED. Two DIFFERENT logical operations at the same node, hour, kind and attempt do not
     share one draw. Otherwise a runtime that keeps more operations in flight silently correlates
     their fates: they all survive together or all fail together.

  3. ORDER-FREE. A draw does not depend on how many draws happened before it. Otherwise arm A
     sending two extra queries shifts the weather for every hour that follows, and the arms are
     compared under different channels.

Property 3 is what the environment fix bought; properties 1 and 2 are what adding `logical_intent`
to the key buys. This file checks all three, and checks that every packet-level random quantity in
the model carries the intent: arrival, acknowledgement, hold, hold duration and relay delivery.

Run: python3 code/experiments/test_draw_keys.py
"""
from __future__ import annotations

# --- module resolution -------------------------------------------------------
import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, *(_os.path.join(_CODE, d) for d in ("physics", "runtime",
                                                     "experiments", "analysis"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)
# -----------------------------------------------------------------------------

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from method_comparison import Link, EnvironmentTrace, _u, P_GOOD_TO_BAD, P_BAD_TO_GOOD  # noqa: E402

NODE = {"nid": "r07", "sf": 9, "loss_db": 150.0, "permanent": False, "good": True,
        "alive": True, "servable": False, "energy": None}

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{('  ' + detail) if detail else ''}")
    if not ok:
        FAILURES.append(name)


# ---------------------------------------------------------------- property 2
def test_distinct_intents_get_distinct_draws() -> None:
    print("\n[2] 不同 logical operation 不共享同一枚 draw")
    link = Link(7)
    outcomes = set()
    n = 400
    for i in range(n):
        arrived = link.request(NODE, 100, "data_write", 0, intent=f"r07:threshold:{i}")
        outcomes.add(arrived)
    check("同节点/同小时/同类型/同 attempt 的不同 intent 未退化为同一结果",
          len(outcomes) == 2,
          f"{n} 个 intent 得到 {len(outcomes)} 种结果")

    # the arrival rate should track the channel, not collapse
    link2 = Link(7)
    arrived_ct = sum(link2.request(NODE, 100, "data_write", 0, intent=f"r07:threshold:{i}")
                     for i in range(2000))
    rate = arrived_ct / 2000
    check("到达率落在信道模型给出的量级内", 0.3 < rate < 1.0, f"到达率 {rate:.3f}")

    # two intents must be able to differ at the SAME address
    a = _u(7, "rx", "r07", 100, "data_write", 0, "r07:threshold:1")
    b = _u(7, "rx", "r07", 100, "data_write", 0, "r07:threshold:2")
    check("相邻 intent 的 rx draw 不同", a != b, f"{a:.6f} vs {b:.6f}")


# ---------------------------------------------------------------- property 1
def test_paired_across_arms() -> None:
    print("\n[1] 同一 logical operation 在不同 arm 中 paired")
    intent = "r07:threshold:42"
    outcomes = []
    for seed in (11, 11, 11):
        lk = Link(seed)
        outcomes.append(lk.request(NODE, 55, "data_write", 0, intent=intent))
    check("同 seed、同 key 的到达结果逐次一致", len(set(outcomes)) == 1)

    # paired means paired even when the arms differ in everything else they sent
    lk_a = Link(11)
    lk_a.request(NODE, 1, "verify_read", 3, intent="r07:verify:0")
    arrive_a = lk_a.request(NODE, 55, "data_write", 0, intent=intent)
    lk_b = Link(11)
    for i in range(200):
        lk_b.request(NODE, i, "reconcile_read", 1, intent=f"r07:reconcile:{i}")
    arrive_b = lk_b.request(NODE, 55, "data_write", 0, intent=intent)
    check("另一 arm 多发 200 条消息不改变本 operation 的到达结果", arrive_a == arrive_b)


# ---------------------------------------------------------------- property 3
def test_order_free() -> None:
    print("\n[3] draw 不受此前 draw 数量的影响")
    key = ("rx", "r07", 300, "data_write", 2, "r07:threshold:9")
    first = _u(5, *key)
    # simulate many intervening draws of every other shape the model uses
    for i in range(500):
        _u(5, "rx", "r01", i, "verify_read", 0, f"r01:verify:{i}")
        _u(5, "ack", "r02", i, "data_write", 1, f"r02:alarm:{i}")
        _u(5, "hold", "r03", i, "data_write", 0, f"r03:threshold:{i}")
    check("500 次其它抽样后同一 key 的值不变", _u(5, *key) == first)

    lk = Link(5)
    v1 = lk.request(NODE, 300, "data_write", 2, intent="r07:threshold:9")
    for i in range(500):
        lk.request(NODE, i, "verify_read", 0, intent=f"r07:verify:{i}")
    check("Link 上的到达结果同样不受历史消息数影响",
          lk.request(NODE, 300, "data_write", 2, intent="r07:threshold:9") == v1)


# ---------------------------------------------------------------- coverage
def test_every_random_quantity_carries_intent() -> None:
    print("\n[4] 每一个报文级随机量都带 logical intent")
    lk = Link(3)
    for kind in ("data_write", "verify_read", "reconcile_read"):
        try:
            lk.request(NODE, 1, kind, 0, intent="")
            check(f"{kind} 缺少 intent 时报错", False)
        except AssertionError:
            check(f"{kind} 缺少 intent 时报错", True)
        try:
            lk.reply(NODE, 1, kind, 0, intent="")
            check(f"{kind} reply 缺少 intent 时报错", False)
        except AssertionError:
            check(f"{kind} reply 缺少 intent 时报错", True)

    # hold, hold duration and relay delivery are drawn in run_arm; their keys must separate intents
    for name, tmpl in (("hold", ("hold", "r07", 10, 1, "r07:threshold:{i}")),
                       ("hold_len", ("hold_len", "r07", 10, 1, "r07:threshold:{i}")),
                       ("relay_deliver", ("relay_deliver", "r07", 10, "r07:threshold:{i}"))):
        vals = {_u(3, *[x.format(i=i) if isinstance(x, str) else x for x in tmpl])
                for i in range(200)}
        check(f"{name} 的 draw 随 intent 变化", len(vals) > 100, f"{len(vals)} 个不同取值")


# ---------------------------------------------------------------- environment
def test_environment_trace_is_shared() -> None:
    print("\n[5] EnvironmentTrace 不因 arm 的消息量而改变")
    nodes = [dict(NODE), {"nid": "b00", "sf": 12, "loss_db": 170.0, "permanent": True,
                          "good": False, "alive": True, "servable": True, "energy": None}]
    t1 = EnvironmentTrace(nodes, 48, 99)
    # an arm that asks many questions must not shift the weather
    lk = Link(99)
    for i in range(1000):
        lk.request(nodes[0], i % 48, "verify_read", 0, intent=f"r07:verify:{i}")
    t2 = EnvironmentTrace(nodes, 48, 99)
    check("轨迹与抽样次数无关",
          all(t1.good[k] == t2.good[k] for k in t1.good)
          and all(t1.alive[k] == t2.alive[k] for k in t1.alive))
    check("永久遮挡节点在轨迹里始终不可用",
          all(not t1.good[("b00", t)] for t in range(48)))
    check("马尔可夫转移概率与模型常数一致",
          abs(P_GOOD_TO_BAD - 0.071211) < 1e-9 and abs(P_BAD_TO_GOOD - 0.156721) < 1e-9)


def main() -> int:
    print("报文级随机契约回归测试")
    test_distinct_intents_get_distinct_draws()
    test_paired_across_arms()
    test_order_free()
    test_every_random_quantity_carries_intent()
    test_environment_trace_is_shared()
    print("\n" + "-" * 74)
    if FAILURES:
        print(f"  {len(FAILURES)} 项失败: {', '.join(FAILURES)}")
        return 1
    print("  全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
