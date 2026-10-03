#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v2gate runner。顺序纪律（04 §6）：先 `--rules-only` 验证规则能力阶梯，再接 LLM。
档：R 纯随机负对照；S seen（规则树覆盖）；H held（含规则树未写的组合变体）。"""
from __future__ import annotations
import argparse, json, os, random, statistics, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [_HERE, os.path.join(_HERE, "..", "v2probe"), os.path.join(_HERE, "..", "analysis")]

from world_gen import gen_instance, RHO_MAIN, B_BUDGET, ALPHA_MAIN, ALPHA_GRID  # noqa: E402
from arms import run_rule_arms, RULE_ARMS                                       # noqa: E402
from stats_util import paired_compare                                           # noqa: E402

REGIMES = ["R", "S", "H"]
REG_OFFSET = {"R": 0, "S": 50000, "H": 90000}


def instance_rng(regime, seed, k):
    return random.Random(seed * 1000 + k + REG_OFFSET[regime])


def evaluate_rules(seeds, per_seed, n, rho, B, alpha):
    data = {g: {a: [] for a in RULE_ARMS} for g in REGIMES}
    n_unbal = {g: 0 for g in REGIMES}
    total = {g: 0 for g in REGIMES}
    for g in REGIMES:
        for s in seeds:
            for k in range(per_seed):
                cands = gen_instance(instance_rng(g, s, k), regime=g, n=n, alpha=alpha)
                total[g] += 1
                if any("UNBAL" in c.ptype for c in cands):
                    n_unbal[g] += 1
                res = run_rule_arms(cands, rho=rho, B=B)
                ov = res["oracle"].true_value
                for a in RULE_ARMS:
                    data[g][a].append(res[a].true_value / ov if ov > 0 else 0.0)
    return data, total, n_unbal


def dose_response(seeds, per_seed, n, rho, B):
    out = {}
    for al in ALPHA_GRID:
        caps = {a: [] for a in RULE_ARMS}
        for s in seeds:
            for k in range(per_seed):
                cands = gen_instance(instance_rng("H", s, k), regime="H", n=n, alpha=al)
                res = run_rule_arms(cands, rho=rho, B=B)
                ov = res["oracle"].true_value
                for a in RULE_ARMS:
                    caps[a].append(res[a].true_value / ov if ov > 0 else 0.0)
        out[f"{al:.2f}"] = {a: round(statistics.mean(caps[a]), 4) for a in RULE_ARMS}
    return out


def summarize(data):
    out = {}
    for g in REGIMES:
        d = data[g]
        out[g] = {
            "arms": {a: {"mean": round(statistics.mean(d[a]), 4),
                         "median": round(statistics.median(d[a]), 4)} for a in RULE_ARMS},
            "comparisons": {
                "oracle-rule_linear": paired_compare(d["oracle"], d["rule_linear"]),
                "oracle-rule_keyword": paired_compare(d["oracle"], d["rule_keyword"]),
                "oracle-rule_tree": paired_compare(d["oracle"], d["rule_tree"]),
                "rule_tree-rule_keyword": paired_compare(d["rule_tree"], d["rule_keyword"]),
                "rule_linear-edf": paired_compare(d["rule_linear"], d["edf"])},
            "n": len(d["oracle"])}
    return out


def gates(summ):
    R, S, H = summ["R"], summ["S"], summ["H"]
    return {
        "F1_R_all_rules_to_ceiling": R["arms"]["rule_linear"]["median"] >= 0.98
        and R["arms"]["rule_tree"]["median"] >= 0.98,
        "F3_edf_worse_in_H": H["comparisons"]["rule_linear-edf"]["both_exclude_zero"],
        "seen_tree_to_ceiling(gap<=0.04)": S["comparisons"]["oracle-rule_tree"]["mean_diff"] <= 0.04,
        "seen_linear_headroom": round(S["comparisons"]["oracle-rule_linear"]["mean_diff"], 4),
        "held_tree_residual": round(H["comparisons"]["oracle-rule_tree"]["mean_diff"], 4),
        "held_tree_residual_in_0.05_0.25": 0.05 <= H["comparisons"]["oracle-rule_tree"]["mean_diff"] <= 0.25}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rules-only", action="store_true")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--seeds", type=int, default=12)
    ap.add_argument("--per-seed", type=int, default=18)
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--rho", type=float, default=RHO_MAIN)
    ap.add_argument("--alpha", type=float, default=ALPHA_MAIN)
    ap.add_argument("--out", default=os.path.join(_HERE, "..", "..", "results", "v2gate_rules.json"))
    args = ap.parse_args()
    seeds = list(range(3 if args.quick else args.seeds))
    per = 4 if args.quick else args.per_seed

    data, total, unbal = evaluate_rules(seeds, per, args.n, args.rho, B_BUDGET, args.alpha)
    summ = summarize(data)
    dose = dose_response(seeds, per, args.n, args.rho, B_BUDGET)
    gt = gates(summ)
    json.dump({"meta": {"seeds": seeds, "per_seed": per, "n": args.n, "rho": args.rho,
                        "alpha": args.alpha, "B": B_BUDGET},
               "summary": summ, "dose_response_H": dose, "gates": gt,
               "unbalanced": {g: f"{unbal[g]}/{total[g]}" for g in REGIMES}},
              open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"n_per_regime={total['R']} (n={args.n},rho={args.rho},alpha={args.alpha})  "
          f"UNBAL={unbal}")
    for g in REGIMES:
        s = summ[g]
        print(f"\n[档 {g}] " + "  ".join(f"{a}={s['arms'][a]['mean']:.3f}" for a in RULE_ARMS))
        for name, c in s["comparisons"].items():
            print(f"    Δ {name:22s} {c['mean_diff']:+.4f} "
                  f"boot[{c['bootstrap_lo']:+.4f},{c['bootstrap_hi']:+.4f}] sig={c['both_exclude_zero']}")
    print("\n=== 档H 剂量反应 (capture by α) ===")
    print(" alpha  " + "  ".join(f"{a:>12s}" for a in RULE_ARMS))
    for al, row in dose.items():
        print(f"  {al} " + "  ".join(f"{row[a]:>12.4f}" for a in RULE_ARMS))
    print("\n=== gates ===")
    for k, v in gt.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
