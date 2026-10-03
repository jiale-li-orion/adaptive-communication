"""diagnose_belief.py — HMM 最优在线滤波后，当前状态到底还能不能判？

逐拍记录每条 markov 路径 (真实好/坏, 后验 belief)，分布与混淆率。
若长突发下持续期 belief 已接近 0/1、仅翻转边界模糊，则强规则天花板高、信息 gap 应小；
若 belief 长期压在中间（无法判），则当前状态对规则本质不可见，oracle 优势是原理性的。
"""
from __future__ import annotations
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from env import generate_trace, MultipathEnv
from controllers import RuleMpcController

def quantile(xs, q):
    xs = sorted(xs)
    if not xs: return float("nan")
    return xs[min(len(xs)-1, int(q*(len(xs)-1)))]

def main():
    for b in ["iid","chirpbox","heavy"]:
        rec = {p: {"good":[], "bad":[]} for p in ["cellular","satellite"]}
        for seed in range(20):
            tr = generate_trace(seed=seed, K=3, burst=b, T=336)
            env = MultipathEnv(tr, energy_budget_wh=1950)
            ctrl = RuleMpcController()
            for _ in range(tr.T):
                v = env.view()
                tg = env.true_good()
                alloc = ctrl.decide(v)
                for p in ("cellular","satellite"):
                    bel = ctrl._belief(p, v)
                    rec[p]["good" if tg[p] else "bad"].append(bel)
                env.step(alloc)
        print(f"\n===== burst={b}（紧预算1950，rule 驱动产生观测）=====")
        for p in ("cellular","satellite"):
            g, bd = rec[p]["good"], rec[p]["bad"]
            fn = sum(1 for x in g if x < 0.5)/max(1,len(g))     # 真实好却判成偏坏（漏）
            fp = sum(1 for x in bd if x > 0.5)/max(1,len(bd))   # 真实坏却判成偏好（误，浪费之源）
            mid_g = sum(1 for x in g if 0.25<=x<=0.75)/max(1,len(g))
            mid_b = sum(1 for x in bd if 0.25<=x<=0.75)/max(1,len(bd))
            print(f"  {p:9s} n(good/bad)={len(g)}/{len(bd)}")
            print(f"    belief|good  mean={sum(g)/len(g):.3f} 中位={quantile(g,.5):.3f} q10={quantile(g,.1):.3f} q90={quantile(g,.9):.3f}  漏报(b<.5)={fn*100:4.1f}%  落在[.25,.75]={mid_g*100:4.1f}%")
            print(f"    belief|bad   mean={sum(bd)/len(bd):.3f} 中位={quantile(bd,.5):.3f} q10={quantile(bd,.1):.3f} q90={quantile(bd,.9):.3f}  误报(b>.5)={fp*100:4.1f}%  落在[.25,.75]={mid_b*100:4.1f}%")

if __name__=="__main__": main()
