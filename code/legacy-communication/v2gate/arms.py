#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v2gate 决策者。所有 arm 的得分统一用真值 v* 计（full=v*, digest=ρv*）；
oracle 与所有规则共用同一最优背包器，差别只在价值估计（公平性）。"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Dict, List, Sequence

from knapsack import grouped_knapsack, options_from_values
from world_gen import (Candidate, B_BUDGET, S_FULL, S_DIGEST, rule_linear_value,
                       rule_keyword_value, rule_tree_value)


@dataclass
class ArmResult:
    arm: str
    true_value: float
    choices: List[str | None]
    over_budget: bool = False


def score_choices(cands, choices, rho):
    tot = 0.0
    for c, ch in zip(cands, choices):
        tot += c.v_star if ch == "full" else rho * c.v_star if ch == "digest" else 0.0
    return tot


def _knapsack_arm(cands, value_fn, rho, B, arm):
    opts = options_from_values(list(range(len(cands))), S_FULL, S_DIGEST, rho,
                               lambda i, _f: value_fn(cands[i]))
    _, choices = grouped_knapsack(opts, B)
    return ArmResult(arm, score_choices(cands, choices, rho), choices)


def arm_oracle(cands, rho=0.7, B=B_BUDGET):
    return _knapsack_arm(cands, lambda c: c.v_star, rho, B, "oracle")


def arm_rule_linear(cands, rho=0.7, B=B_BUDGET):
    return _knapsack_arm(cands, rule_linear_value, rho, B, "rule_linear")


def arm_rule_keyword(cands, rho=0.7, B=B_BUDGET):
    return _knapsack_arm(cands, rule_keyword_value, rho, B, "rule_keyword")


def arm_rule_tree(cands, rho=0.7, B=B_BUDGET):
    return _knapsack_arm(cands, rule_tree_value, rho, B, "rule_tree")


def arm_edf(cands, rho=0.7, B=B_BUDGET):
    """只认 slack（紧迫优先），不用价值；顺序塞 full，塞不下退 digest。"""
    order = sorted(range(len(cands)), key=lambda i: cands[i].x["slack"])
    choices: List[str | None] = [None] * len(cands)
    rem = B
    for i in order:
        if rem >= S_FULL:
            choices[i] = "full"; rem -= S_FULL
        elif rem >= S_DIGEST:
            choices[i] = "digest"; rem -= S_DIGEST
    return ArmResult("edf", score_choices(cands, choices, rho), choices)


def arm_from_llm(cands, pick, rho=0.7, B=B_BUDGET):
    """pick: cid->full/digest/drop；按 LLM 选择用真值评分，超预算按 cid 序确定性截断（不替它优化）。"""
    choices: List[str | None] = [None] * len(cands)
    for c in cands:
        ch = pick.get(c.cid) or pick.get(str(c.cid))
        if ch in ("full", "digest"):
            choices[c.cid] = ch
    cost = sum(S_FULL if ch == "full" else S_DIGEST if ch == "digest" else 0 for ch in choices)
    if cost > B:
        for i in range(len(choices)):
            if cost <= B:
                break
            if choices[i] == "full" and cost - S_FULL + S_DIGEST <= B:
                choices[i] = "digest"; cost = cost - S_FULL + S_DIGEST
            elif choices[i] in ("full", "digest"):
                cost -= S_FULL if choices[i] == "full" else S_DIGEST; choices[i] = None
    return ArmResult("llm_flash", score_choices(cands, choices, rho), choices, cost > B)


def arm_from_llm_scores(cands, scores, rho=0.7, B=B_BUDGET):
    """公平版 LLM 臂：LLM 只给每条价值分，打包走与规则臂**同一个**最优背包器。
    scores: cid->0..100。LLM 与规则的唯一差别是价值来源，不手搓字节组合。"""
    opts = options_from_values(list(range(len(cands))), S_FULL, S_DIGEST, rho,
                               lambda i, _f: float(scores[cands[i].cid]))
    _, choices = grouped_knapsack(opts, B)
    return ArmResult("llm_flash", score_choices(cands, choices, rho), choices)


RULE_ARMS = ["edf", "rule_linear", "rule_keyword", "rule_tree", "oracle"]


def run_rule_arms(cands, rho=0.7, B=B_BUDGET):
    return {"edf": arm_edf(cands, rho, B),
            "rule_linear": arm_rule_linear(cands, rho, B),
            "rule_keyword": arm_rule_keyword(cands, rho, B),
            "rule_tree": arm_rule_tree(cands, rho, B),
            "oracle": arm_oracle(cands, rho, B)}
