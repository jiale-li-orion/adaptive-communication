"""diagnose_info_vs_policy.py — 归因分解：oracle 优势 = 状态信息？还是分配算法？

三臂：
  oracle : 真实状态 + oracle 决策（只在好路径发）
  cheat  : 真实状态 + rule_mpc 的 knapsack/能量轨迹分配器（完美信息喂给规则决策器）
  rule   : HMM 后验 + 同一分配器
判读：
  cheat≈oracle >> rule  → 差距纯来自状态信息（强规则决策器不弱，是信息买不到）
  cheat≈rule < oracle   → 差距来自决策器（我把规则写弱了，必须先加强规则）
  oracle>cheat>rule     → 两者皆有
"""
from __future__ import annotations
import argparse, json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from env import generate_trace, MultipathEnv                       # noqa: E402
from controllers import OracleController, RuleMpcController        # noqa: E402

T975 = {1:12.706,2:4.303,3:3.182,4:2.776,5:2.571,6:2.447,7:2.365,8:2.306,9:2.262,
        10:2.228,11:2.201,12:2.179,13:2.160,14:2.145,15:2.131,16:2.120,17:2.110,
        18:2.101,19:2.093,20:2.086}
def t975(df):
    if df<=0: return float("nan")
    for k in sorted(T975):
        if df<=k: return T975[k]
    return 1.96
def paired(d):
    n=len(d); m=sum(d)/n
    var=sum((x-m)**2 for x in d)/(n-1); se=math.sqrt(var/n); h=t975(n-1)*se
    return m,m-h,m+h

class CheatRule(RuleMpcController):
    """完美当前状态 + 规则的分配器。"""
    def __init__(self):
        super().__init__(); self._truth={}
    def decide(self, view, true_good=None):
        self._truth = true_good or {}
        return super().decide(view)
    def _belief(self, p, view):
        return 1.0 if self._truth.get(p) else 0.0

def run(trace, arm, budget):
    env = MultipathEnv(trace, energy_budget_wh=budget)
    ctrl = OracleController() if arm=="oracle" else (CheatRule() if arm=="cheat" else RuleMpcController())
    for _ in range(trace.T):
        v=env.view()
        a = ctrl.decide(v, env.true_good()) if arm in ("oracle","cheat") else ctrl.decide(v)
        env.step(a)
    return env.finalize()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--seeds",type=int,default=20); args=ap.parse_args()
    budgets=[None,2100,1950,1800]; Bs=["iid","chirpbox","heavy"]; arms=["oracle","cheat","rule"]
    out=[]
    for b in Bs:
        print(f"\n===== burst={b} =====")
        print(f"{'budget':>7} | {'oracle':>7} {'cheat':>7} {'rule':>7} | oracle-cheat [95%] | cheat-rule [95%]")
        for budget in budgets:
            acc={a:[] for a in arms}
            for seed in range(args.seeds):
                tr=generate_trace(seed=seed,K=3,burst=b,T=336)
                for a in arms: acc[a].append(run(tr,a,budget))
            er={a:sum(m["event_rate"] for m in acc[a])/args.seeds for a in arms}
            oc=paired([(o-c)*100 for o,c in zip([m["event_rate"] for m in acc["oracle"]],
                                                 [m["event_rate"] for m in acc["cheat"]])])
            cr=paired([(c-r)*100 for c,r in zip([m["event_rate"] for m in acc["cheat"]],
                                                 [m["event_rate"] for m in acc["rule"]])])
            lab="loose" if budget is None else str(budget)
            print(f"{lab:>7} | {er['oracle']*100:7.1f} {er['cheat']*100:7.1f} {er['rule']*100:7.1f} | "
                  f"{oc[0]:6.2f} [{oc[1]:6.2f},{oc[2]:6.2f}] | {cr[0]:6.2f} [{cr[1]:6.2f},{cr[2]:6.2f}]")
            out.append({"burst":b,"budget":budget,"event_rate":er,"oracle_cheat":oc,"cheat_rule":cr})
    with open(os.path.join(HERE,"results","info_vs_policy.json"),"w",encoding="utf-8") as f:
        json.dump(out,f,ensure_ascii=False,indent=2)

if __name__=="__main__": main()
