#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分组 0-1 背包：每条候选有 drop/digest/full 三种形态，字节预算 B。

oracle 与所有规则**共用同一个最优背包器**，差别只在喂进去的价值：
  - oracle 喂真值 v*；- rule_* 喂各自估计 v_hat。
这样"规则不够好"只能来自价值估计，不可能来自背包求解器更弱（公平性）。
cost 为整数字节，B=200，n<=10，直接 DP + 回溯，返回全局最优（非贪心近似）。
"""
from __future__ import annotations
from typing import Callable, List, Sequence, Tuple

NEG = -1e18

# (cost_bytes, value, form_tag)
Option = Tuple[int, float, str]


def grouped_knapsack(options_by_item: Sequence[Sequence[Option]], B: int):
    """返回 (best_value, choices_list)，choices_list[i] in {'full','digest',None}。"""
    n = len(options_by_item)
    dp = [NEG] * (B + 1)
    dp[0] = 0.0
    parents: List[dict] = []
    for opts in options_by_item:
        ndp = [NEG] * (B + 1)
        par: dict = {}
        for b in range(B + 1):
            if dp[b] <= NEG / 2:
                continue
            for cost, val, tag in opts:
                nb = b + cost
                if nb <= B and dp[b] + val > ndp[nb] + 1e-12:
                    ndp[nb] = dp[b] + val
                    par[nb] = (b, tag)
        parents.append(par)
        dp = ndp
    best_b = max(range(B + 1), key=lambda b: dp[b])
    best = dp[best_b]
    choices: List[str | None] = [None] * n
    b = best_b
    for i in range(n - 1, -1, -1):
        # 该候选可能整体 drop（par 里没有以某形态到达的记录），回溯到等价值的 drop
        if b in parents[i]:
            pb, tag = parents[i][b]
            choices[i] = None if tag == "drop" else tag
            b = pb
        else:  # 走的是 drop（cost 0、value 0），容量不变
            choices[i] = None
    return best, choices


def options_from_values(ids: Sequence[int], s_full: int, s_digest: int, rho: float,
                        value_of: Callable[[int, str], float]) -> List[List[Option]]:
    """给定每条 full/digest 价值函数，构造三选项。digest 价值 = rho * full 价值。"""
    out: List[List[Option]] = []
    for i in ids:
        vf = float(value_of(i, "full"))
        out.append([(0, 0.0, "drop"),
                    (s_digest, rho * vf, "digest"),
                    (s_full, vf, "full")])
    return out
