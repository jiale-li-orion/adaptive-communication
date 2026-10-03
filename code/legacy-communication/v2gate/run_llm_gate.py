#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v2gate LLM 臂配对运行（顺序纪律：必须在 run_gate.py --rules-only 阶梯确认后运行）。

对同一批种子实例，规则臂与 deepseek-flash 零样本臂用**同一真值、同一背包口径**评分。
LLM 信息不多于规则（只收 cid+观测文本+打包规则）。结果写 results/v2gate_llm.json。
H1（04b 修正）：在 H 档，LLM 须显著优于**该档最强规则臂**（接 LLM 前依规则侧 mean 锁定），
且追回份额 capture 达到阈值；否则按预注册三向解释落结论，不反挑阈值。
"""
from __future__ import annotations
import argparse, json, os, statistics, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [_HERE, os.path.join(_HERE, "..", "v2probe"), os.path.join(_HERE, "..", "analysis")]

from world_gen import gen_instance, RHO_MAIN, B_BUDGET, ALPHA_MAIN      # noqa: E402
from arms import run_rule_arms, arm_from_llm_scores, RULE_ARMS                # noqa: E402
from stats_util import paired_compare                                  # noqa: E402
import ds_client                                                       # noqa: E402

REGIMES = ["R", "S", "H"]
REG_OFFSET = {"R": 0, "S": 50000, "H": 90000}
RULE_ONLY = ["rule_linear", "rule_keyword", "rule_tree"]


def instance_rng(regime, seed, k):
    import random
    return random.Random(seed * 1000 + k + REG_OFFSET[regime])


def run(seeds, per_seed, n, rho, B, alpha, regimes, use_cache, key, workers=8, temperature=0.0):
    from concurrent.futures import ThreadPoolExecutor
    series = {g: {a: [] for a in RULE_ARMS + ["llm_flash"]} for g in regimes}
    audit = {g: {"n": 0, "parse_fail": 0, "over_budget": 0, "uncached": 0,
                 "prompt_tokens": 0, "completion_tokens": 0} for g in regimes}
    for g in regimes:
        jobs = []
        for s in seeds:
            for k in range(per_seed):
                cands = gen_instance(instance_rng(g, s, k), regime=g, n=n, alpha=alpha)
                res = run_rule_arms(cands, rho=rho, B=B)
                ov = res["oracle"].true_value
                if ov <= 0:
                    continue
                for a in RULE_ARMS:
                    series[g][a].append(res[a].true_value / ov)
                jobs.append((len(jobs), cands, ov))

        def work(job):
            i, cands, ov = job
            scores, meta = ds_client.decide(cands, use_cache=use_cache, key=key,
                                            temperature=temperature)
            llm = arm_from_llm_scores(cands, scores, rho=rho, B=B)
            return i, llm.true_value / ov, meta

        llm_norm, metas = [None] * len(jobs), [None] * len(jobs)
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for i, val, meta in ex.map(work, jobs):
                llm_norm[i], metas[i] = val, meta
        series[g]["llm_flash"] = llm_norm

        au = audit[g]
        au["n"] = len(jobs)
        for meta in metas:
            au["parse_fail"] += int(meta["parse_fail"])
            u = meta.get("usage") or {}
            if not meta["cached"]:
                au["uncached"] += 1
                au["prompt_tokens"] += int(u.get("prompt_tokens", 0))
                au["completion_tokens"] += int(u.get("completion_tokens", 0))
        print(f"[{g}] n={au['n']} uncached={au['uncached']} parse_fail={au['parse_fail']} "
              f"tok(p/c)={au['prompt_tokens']}/{au['completion_tokens']}", flush=True)
    return series, audit


def summarize(series):
    out = {}
    for g, d in series.items():
        rule_means = {a: statistics.mean(d[a]) for a in RULE_ONLY}
        best_rule = max(rule_means, key=rule_means.get)
        n = len(d["llm_flash"])
        # 追回份额：(llm-best_rule)/(oracle-best_rule)，oracle 归一化=1
        cap = [(d["llm_flash"][i] - d[best_rule][i]) / (1.0 - d[best_rule][i])
               if 1.0 - d[best_rule][i] > 1e-9 else 0.0 for i in range(n)]
        out[g] = {
            "arms": {a: {"mean": round(statistics.mean(d[a]), 4),
                         "median": round(statistics.median(d[a]), 4)}
                     for a in RULE_ARMS + ["llm_flash"]},
            "best_rule_arm": best_rule,
            "best_rule_mean": round(rule_means[best_rule], 4),
            "llm_vs_best_rule": paired_compare(d["llm_flash"], d[best_rule]),
            "llm_vs_tree": paired_compare(d["llm_flash"], d["rule_tree"]),
            "capture_vs_best_rule_mean": round(statistics.mean(cap), 4),
            "n": n}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--seeds", type=int, default=12)
    ap.add_argument("--per-seed", type=int, default=18)
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--rho", type=float, default=RHO_MAIN)
    ap.add_argument("--alpha", type=float, default=ALPHA_MAIN)
    ap.add_argument("--regime", default="R,S,H")
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--temp", type=float, default=0.0)
    ap.add_argument("--out", default=os.path.join(_HERE, "..", "..", "results", "v2gate_llm.json"))
    args = ap.parse_args()
    seeds = list(range(2 if args.quick else args.seeds))
    per = 2 if args.quick else args.per_seed
    regimes = args.regime.split(",")
    key = None if args.no_cache else ds_client.load_key()

    series, audit = run(seeds, per, args.n, args.rho, B_BUDGET, args.alpha,
                        regimes, not args.no_cache, key, workers=args.workers,
                        temperature=args.temp)
    summ = summarize(series)
    json.dump({"meta": {"seeds": seeds, "per_seed": per, "n": args.n,
                        "rho": args.rho, "alpha": args.alpha, "B": B_BUDGET,
                        "model": ds_client.MODEL, "temperature": args.temp},
               "summary": summ, "audit": audit},
              open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("\n===== LLM gate summary =====")
    for g in regimes:
        s = summ[g]
        print(f"\n[档 {g}] best_rule={s['best_rule_arm']}({s['best_rule_mean']})  "
              + "  ".join(f"{a}={s['arms'][a]['mean']:.3f}" for a in RULE_ARMS + ['llm_flash']))
        c = s["llm_vs_best_rule"]
        print(f"    LLM-best={c['mean_diff']:+.4f} boot[{c['bootstrap_lo']:+.4f},"
              f"{c['bootstrap_hi']:+.4f}] sig={c['both_exclude_zero']}  capture={s['capture_vs_best_rule_mean']:+.3f}")
        au = audit[g]
        print(f"    audit n={au['n']} parse_fail={au['parse_fail']} over_budget={au['over_budget']} "
              f"uncached_calls={au['uncached']} tok(p/c)={au['prompt_tokens']}/{au['completion_tokens']}")


if __name__ == "__main__":
    main()
