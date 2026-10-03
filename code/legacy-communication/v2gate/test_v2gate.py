#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v2gate 确定性自检（不调 LLM、快）。运行：python3 code/v2gate/test_v2gate.py"""
import itertools, os, random, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [_HERE, os.path.join(_HERE, "..", "v2probe")]

from knapsack import grouped_knapsack, options_from_values          # noqa: E402
from world_gen import (gen_instance, linear_base, combo_base, _make_text,  # noqa: E402
                       S_FULL, S_DIGEST, B_BUDGET, rule_linear_value,
                       rule_keyword_value, rule_tree_value, _TARGET)
from arms import run_rule_arms, arm_from_llm                          # noqa: E402

PASS, FAIL = 0, 0


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"  FAIL: {name}  {extra}")


def brute_force_best(opts_by_item, B):
    best = 0.0
    for combo in itertools.product(*opts_by_item):
        cost = sum(o[0] for o in combo); val = sum(o[1] for o in combo)
        if cost <= B and val > best:
            best = val
    return best


def test_knapsack_optimal():
    rng = random.Random(0)
    for n in range(1, 7):
        for _ in range(60):
            vals = [rng.uniform(1, 90) for _ in range(n)]
            rho = 0.7
            opts = options_from_values(list(range(n)), S_FULL, S_DIGEST, rho,
                                       lambda i, _f: vals[i])
            dp, choices = grouped_knapsack(opts, B_BUDGET)
            bf = brute_force_best(opts, B_BUDGET)
            check(f"knapsack DP==bruteforce n={n}", abs(dp - bf) < 1e-6, f"{dp} vs {bf}")


def test_budget_respected():
    rng = random.Random(1)
    for g in ["R", "S", "H"]:
        for _ in range(30):
            cands = gen_instance(rng, g, n=8)
            res = run_rule_arms(cands)
            for a, r in res.items():
                cost = sum(S_FULL if ch == "full" else S_DIGEST if ch == "digest" else 0
                           for ch in r.choices)
                check(f"{g}/{a} within budget", cost <= B_BUDGET, f"cost={cost}")


def test_R_negative_control():
    # 档 R：rule_linear 拥有正确价值函数，必须逐实例等于 oracle
    rng = random.Random(2)
    gaps = []
    for _ in range(60):
        cands = gen_instance(rng, "R", n=8)
        res = run_rule_arms(cands)
        gaps.append(1 - res["rule_linear"].true_value / res["oracle"].true_value)
    check("R: rule_linear == oracle (median gap 0)", max(gaps) < 1e-9, f"maxgap={max(gaps)}")


def test_rule_ladder():
    # S：tree ≥ keyword ≥ linear（均值，阶梯）；tree 到顶
    rng = random.Random(3)
    cap = {a: [] for a in ["rule_linear", "rule_keyword", "rule_tree"]}
    balanced = 0; tot = 0
    for _ in range(120):
        cands = gen_instance(rng, "S", n=8)
        tot += 1
        if not any("UNBAL" in c.ptype for c in cands):
            balanced += 1
        res = run_rule_arms(cands); ov = res["oracle"].true_value
        for a in cap:
            cap[a].append(res[a].true_value / ov)
    m = {a: sum(v) / len(v) for a, v in cap.items()}
    check("S ladder linear<=keyword<=tree",
          m["rule_linear"] + 1e-6 <= m["rule_keyword"] <= m["rule_tree"] + 1e-6, str(m))
    check("S tree near ceiling (>=0.985)", m["rule_tree"] >= 0.985, str(m))
    check("S balanced rate >=0.9", balanced / tot >= 0.9, f"{balanced}/{tot}")


def test_held_tree_residual():
    # H：rule_tree 仍有明确残差（漏 residual），balanced 率高
    rng = random.Random(4)
    tg, balanced, tot = [], 0, 0
    for _ in range(120):
        cands = gen_instance(rng, "H", n=8)
        tot += 1
        if not any("UNBAL" in c.ptype for c in cands):
            balanced += 1
        res = run_rule_arms(cands); ov = res["oracle"].true_value
        tg.append(1 - res["rule_tree"].true_value / ov)
    check("H tree residual mean in [0.04,0.22]",
          0.04 <= sum(tg) / len(tg) <= 0.22, f"mean={sum(tg)/len(tg):.3f}")
    check("H balanced rate >=0.85", balanced / tot >= 0.85, f"{balanced}/{tot}")


def test_rules_dont_peek_vstar():
    # 保持 x 不变、只改 v_star，三个规则的选择/价值估计必须不变（它们不读真值）
    rng = random.Random(5)
    cands = gen_instance(rng, "H", n=8)
    est1 = [(rule_linear_value(c), rule_keyword_value(c), rule_tree_value(c)) for c in cands]
    for c in cands:
        c.v_star *= 0.13
    est2 = [(rule_linear_value(c), rule_keyword_value(c), rule_tree_value(c)) for c in cands]
    check("rules ignore v_star", est1 == est2)


def test_text_from_x_only():
    rng = random.Random(6)
    cands = gen_instance(rng, "S", n=8)
    for c in cands:
        t1, t2 = _make_text(c.cid, c.x), _make_text(c.cid, c.x)
        check("text deterministic from x", t1 == t2)
        check("text never leaks v_star", str(round(c.v_star, 1)) not in c.text)


def test_llm_overbudget_clip():
    rng = random.Random(7)
    cands = gen_instance(rng, "S", n=8)
    pick = {i: "full" for i in range(8)}          # 全 full 必然超 200
    r = arm_from_llm(cands, pick)
    cost = sum(S_FULL if ch == "full" else S_DIGEST if ch == "digest" else 0 for ch in r.choices)
    check("LLM over-budget clipped to B", cost <= B_BUDGET, f"cost={cost}")


def test_edf_ignores_value():
    rng = random.Random(8)
    cands = gen_instance(rng, "H", n=8)
    r1 = run_rule_arms(cands)["edf"].choices
    for c in cands:
        c.v_star += 500
    cands2 = cands
    from arms import arm_edf
    r2 = arm_edf(cands2).choices
    check("edf choices independent of value", r1 == r2)


if __name__ == "__main__":
    for fn in [test_knapsack_optimal, test_budget_respected, test_R_negative_control,
               test_rule_ladder, test_held_tree_residual, test_rules_dont_peek_vstar,
               test_text_from_x_only, test_llm_overbudget_clip, test_edf_ignores_value]:
        fn()
    print(f"\n{'='*50}\n  v2gate self-test: {PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)
