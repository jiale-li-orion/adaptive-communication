"""run_final_arms.py — 终裁：全知上界 vs 最强传统信念规划 vs 普通强规则 vs 现状。

oracle     : 当前真实状态 + 只在好路径发（全知上界）
cheat      : 当前真实状态 + 与规则相同的 knapsack 分配器（分离"信息"与"算法"）
belief_mpc : HMM 信念 + 随机模型预测控制（传统方法天花板，不看真实状态、不预知 event）
rule_mpc   : HMM 信念 + 单拍 fractional-knapsack（普通强规则）
fixed      : 工程现状固定优先级
关键量：oracle-belief_mpc = 连最强传统规划都吃不掉的残差信息/决策价值。
"""
from __future__ import annotations
import argparse, json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from env import generate_trace, MultipathEnv
from controllers import (OracleController, RuleMpcController, BeliefMPC, FixedController)
T975={1:12.706,2:4.303,3:3.182,4:2.776,5:2.571,6:2.447,7:2.365,8:2.306,9:2.262,10:2.228,
      11:2.201,12:2.179,13:2.160,14:2.145,15:2.131,16:2.120,17:2.110,18:2.101,19:2.093,20:2.086}
def t975(df):
    if df<=0: return float("nan")
    for k in sorted(T975):
        if df<=k: return T975[k]
    return 1.96
def paired(d):
    n=len(d); m=sum(d)/n
    var=sum((x-m)**2 for x in d)/(n-1); se=math.sqrt(var/n); h=t975(n-1)*se
    return {"mean":m,"lo":m-h,"hi":m+h,"w":sum(x>1e-12 for x in d),
            "l":sum(x<-1e-12 for x in d)}

class CheatMPC(BeliefMPC):
    """与 belief_mpc 同一求解器，唯一差别：当前状态信念被替换为真实点分布（全知信息）。"""
    def decide(self, view, true_good=None):
        self._ov = true_good or {}
        return super().decide(view, true_good)

def mk(arm):
    return {"oracle":OracleController,"cheat_mpc":CheatMPC,"belief_mpc":BeliefMPC,
            "rule_mpc":RuleMpcController,"fixed":FixedController}[arm]()

def run(trace, arm, budget):
    env=MultipathEnv(trace, energy_budget_wh=budget)
    c=mk(arm)
    for _ in range(trace.T):
        v=env.view()
        a=c.decide(v, env.true_good()) if arm in ("oracle","cheat_mpc") else c.decide(v)
        env.step(a)
    return env.finalize()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--seeds",type=int,default=20)
    ap.add_argument("--out",default=os.path.join(HERE,"results","final_arms.json")); args=ap.parse_args()
    budgets=[None,2100,1950,1800]; Bs=["iid","chirpbox","heavy"]
    arms=["oracle","cheat_mpc","belief_mpc","rule_mpc","fixed"]; rows=[]
    for b in Bs:
        for budget in budgets:
            acc={a:[] for a in arms}
            for seed in range(args.seeds):
                tr=generate_trace(seed=seed,K=3,burst=b,T=336)
                for a in arms: acc[a].append(run(tr,a,budget))
            er={a:sum(m["event_rate"] for m in acc[a])/args.seeds for a in arms}
            diffs={a:paired([(o-x)*100 for o,x in zip(
                [m["event_rate"] for m in acc["oracle"]],
                [m["event_rate"] for m in acc[a]])]) for a in arms if a!="oracle"}
            rows.append({"burst":b,"budget":budget,"event_rate":er,"oracle_minus":diffs})
    json.dump({"seeds":args.seeds,"rows":rows},open(args.out,"w",encoding="utf-8"),
              ensure_ascii=False,indent=2)
    print("="*120)
    print("终裁 K=3：事件交付率%，及 oracle−各臂(pp)[95%区间] W/L")
    print("="*120)
    for b in Bs:
        print(f"\n--- {b} ---")
        print(f"{'budget':>6} | {'oracle':>6} {'chMPC':>6} {'belMPC':>6} {'rule':>6} {'fixed':>6} || "
              f"or-chMPC | or-mpc [W/L] | or-rule | or-fixed")
        for r in [x for x in rows if x["burst"]==b]:
            e=r["event_rate"]; d=r["oracle_minus"]
            def f(k): x=d[k]; return f"{x['mean']:6.2f}[{x['lo']:5.2f},{x['hi']:5.2f}] {x['w']}/{x['l']}"
            lab="loose" if r["budget"] is None else str(r["budget"])
            print(f"{lab:>6} | {e['oracle']*100:6.1f} {e['cheat_mpc']*100:6.1f} {e['belief_mpc']*100:6.1f} "
                  f"{e['rule_mpc']*100:6.1f} {e['fixed']*100:6.1f} || {f('cheat_mpc')} | {f('belief_mpc')} | "
                  f"{f('rule_mpc')} | {f('fixed')}")
    print(f"\n已写：{args.out}")

if __name__=="__main__": main()
