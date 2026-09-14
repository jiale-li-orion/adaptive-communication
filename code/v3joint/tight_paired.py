# -*- coding: utf-8 -*-
"""紧 regime(period=300风险窗) 配对：静态配置前沿 vs ea/eh，6种子，存json供前沿图。"""
import os, sys, json, math, statistics as st
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint
ARMS=["grid600x300","grid600x600","grid900x300","grid900x600","grid1800x900","grid3600x900","ea_aoi","eh_aoi"]
SEEDS=tuple(range(6))
data={}
for arm in ARMS:
    rows=[]
    for s in SEEDS:
        r=run_joint(seed=s,groups=2,arm=arm,sample_interval_s=3600,report_period_s=900,
                    routine_period_s=300,task_hours=48,tail_hours=1,outage_start_h=4,outage_hours=16,
                    enable_backup=True,backup_rate_s=300,backup_bytes=78,harvest_mode="solar",
                    harvest_peak_wh_per_hour=0.03,initial_soc=1.0,blackout_frac=0.0)[0]
        rows.append(dict(rout=r["routine"]["delivered"]/r["routine"]["n"],
                         air=r["communication"]["airtime_uplink_h"]*3600,
                         soc=r["survival"]["mean_final_soc"],alive=r["survival"]["alive"]))
    data[arm]=rows
    print(f"{arm:13s} rout={st.mean(x['rout'] for x in rows):.4f} air={st.mean(x['air'] for x in rows):.0f} "
          f"soc={st.mean(x['soc'] for x in rows):.3f}",flush=True)
# 配对：ea/eh 相对前沿代表 grid600x600
base=[x["rout"] for x in data["grid600x600"]]
for a in ("ea_aoi","eh_aoi","grid600x300"):
    d=[data[a][i]["rout"]-base[i] for i in range(len(base))]
    m=st.mean(d); sd=st.pstdev(d)*math.sqrt(len(d)/(len(d)-1)); ci=2.571*sd/math.sqrt(len(d))
    print(f"Δ {a} - grid600x600 = {m*100:+.2f}pp CI[{(m-ci)*100:+.2f},{(m+ci)*100:+.2f}]")
json.dump(data,open(os.path.join(_CODE,"..","results","v3joint_tight.json"),"w"),indent=1)
print("saved v3joint_tight.json")
