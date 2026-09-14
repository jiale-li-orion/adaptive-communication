# -*- coding: utf-8 -*-
"""配对统计：fixed900 为基准，16 种子配对 routine 差的均值/95%CI/符号；并测接入+回传双中断。"""
import os, sys, math, json, statistics as st
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint
ARMS=["fixed900","ea_aoi","eh_aoi","anchor"]
def t95(n):  # 双侧 95% t 临界（近似表）
    return {4:2.776,6:2.571,8:2.365,12:2.201,16:2.131,20:2.093}.get(n,2.0)
def routine(r): return r["routine"]["delivered"]/r["routine"]["n"]
def block(cond,seeds,tag):
    vals={a:[routine(run_joint(seed=s,groups=2,arm=(a if a!="anchor" else "cup"),
            cup_use_window=False,cup_gate_sampling=True,**cond)[0]) for s in seeds] for a in ARMS}
    alive={a:round(st.mean(run_joint(seed=s,groups=2,arm=(a if a!="anchor" else "cup"),
            cup_use_window=False,cup_gate_sampling=True,**cond)[0]["survival"]["alive"] for s in seeds),2) for a in ARMS}
    base=vals["fixed900"]; n=len(seeds); tc=t95(n)
    print(f"\n### {tag}（{n} 种子）  fixed mean={st.mean(base):.4f}")
    for a in ARMS:
        d=[vals[a][i]-base[i] for i in range(n)]
        m=st.mean(d); sd=st.pstdev(d)*math.sqrt(n/(n-1)) if n>1 else 0
        ci=tc*sd/math.sqrt(n)
        neg=sum(1 for x in d if x<-1e-9); zero=sum(1 for x in d if abs(x)<=1e-9)
        print(f"  {a:9s} Δ={m*100:+7.2f}pp 95%CI[{(m-ci)*100:+6.2f},{(m+ci)*100:+6.2f}] "
              f"更差{neg}/{n} 持平{zero} 存活{alive[a]}")
    return {a:vals[a] for a in ARMS}
SEEDS=tuple(range(16))
common=dict(task_hours=48,tail_hours=1,outage_start_h=4.0,enable_backup=True,
            backup_rate_s=300,backup_bytes=78,harvest_mode="solar",initial_soc=0.5)
r1=block(dict(common,outage_hours=16.0,harvest_peak_wh_per_hour=0.005,blackout_frac=0.3,
              blackout_start_h=4.0),SEEDS,"紧张 oh16 pk.005 bo.3")
r2=block(dict(common,outage_hours=32.0,harvest_peak_wh_per_hour=0.003,initial_soc=0.4,
              blackout_frac=0.4,blackout_start_h=4.0),SEEDS,"深失稳 oh32 pk.003 bo.4")
# 双中断：回传 oh16 叠接入中断 h8-h12
r3=block(dict(common,outage_hours=16.0,harvest_peak_wh_per_hour=0.005,blackout_frac=0.3,
              blackout_start_h=4.0,access_outage_start_h=8.0,access_outage_hours=4.0),
         tuple(range(8)),"双中断 回传oh16+接入h8-12")
json.dump({"stressed":r1,"deep":r2,"dual":r3},open(os.path.join(_CODE,"..","results","v3joint_paired.json"),"w"),indent=1)
print("\nsaved v3joint_paired.json")
