#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""H/S 档分角色归因（命中 LLM 缓存，不产生新调用）：LLM 到底识别了谁、被谁骗。"""
import os, sys, random, collections
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [_HERE, os.path.join(_HERE, "..", "v2probe"), os.path.join(_HERE, "..", "analysis")]
from world_gen import gen_instance
from arms import run_rule_arms, arm_from_llm_scores
import ds_client

ARMS = ["rule_linear", "rule_keyword", "rule_tree", "llm_flash"]
REG_OFFSET = {"S": 50000, "H": 90000}


def main():
    key = ds_client.load_key()
    for regime in ["H", "S"]:
        seeds, per = range(12), 18
        # pick[arm][ptype]=选中次数；tot[ptype]=该 ptype 出现次数
        pick = {a: collections.Counter() for a in ARMS}
        tot = collections.Counter()
        resid_recall = {a: [0, 0] for a in ARMS}     # oracle 选 residual 时该臂也选 [hit,n]
        look_false = {a: [0, 0] for a in ARMS}       # oracle 不选 lookalike 时该臂误选 [fp,n]
        for s in seeds:
            for k in range(per):
                rng = random.Random(s * 1000 + k + REG_OFFSET[regime])
                cands = gen_instance(rng, regime)
                res = run_rule_arms(cands)
                scores, _ = ds_client.decide(cands, key=key)   # 命中缓存
                llm = arm_from_llm_scores(cands, scores)
                ch = {a: res[a].choices for a in ["rule_linear", "rule_keyword", "rule_tree"]}
                ch["llm_flash"] = llm.choices
                oc = res["oracle"].choices
                for i, c in enumerate(cands):
                    tot[c.ptype] += 1
                    for a in ARMS:
                        if ch[a][i] is not None:
                            pick[a][c.ptype] += 1
                    if c.ptype == "hidden_residual":
                        if oc[i] is not None:
                            for a in ARMS:
                                resid_recall[a][1] += 1
                                resid_recall[a][0] += int(ch[a][i] is not None)
                    if c.ptype == "distractor_lookalike":
                        if oc[i] is None:
                            for a in ARMS:
                                look_false[a][1] += 1
                                look_false[a][0] += int(ch[a][i] is not None)
        print(f"\n========== 档 {regime} 分角色选中率 ==========")
        ptypes = list(tot)
        print("arm".ljust(14) + "".join(p[:14].ljust(16) for p in ptypes))
        for a in ARMS:
            row = a.ljust(14)
            for p in ptypes:
                row += f"{pick[a][p]}/{tot[p]}={pick[a][p]/tot[p]:.2f}".ljust(16)
            print(row)
        if regime == "H":
            print("\n hidden_residual 召回（oracle 选时该臂也选）:")
            for a in ARMS:
                h, n = resid_recall[a]
                print(f"   {a:14s} {h}/{n} = {h/n:.3f}")
            print("\n distractor_lookalike 误选（oracle 不选时该臂选了）:")
            for a in ARMS:
                h, n = look_false[a]
                print(f"   {a:14s} {h}/{n} = {h/n:.3f}")


if __name__ == "__main__":
    main()
