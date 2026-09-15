# -*- coding: utf-8 -*-
"""R01 旧产物影响：earliest 修复后重跑 stressed seed0-3 四臂，与存档(旧覆盖口径)逐种子对比。"""
import os,sys,json,statistics as st
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE,_CODE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint
ARMS=["fixed900","ea_aoi","eh_aoi","anchor"]
cond=dict(task_hours=48,tail_hours=1,outage_start_h=4.0,outage_hours=16.0,enable_backup=True,
    backup_rate_s=300,backup_bytes=78,harvest_mode="solar",initial_soc=0.5,
    harvest_peak_wh_per_hour=0.005,blackout_frac=0.3,blackout_start_h=4.0)
SEEDS=(0,1,2,3)
old=json.load(open(os.path.join(_CODE,"..","results","v3joint_paired.json")))["stressed"]
def routine(res): return res["routine"]["delivered"]/res["routine"]["n"]
report={}
print(f"{'arm':9s} {'seed':>4} {'old(last)':>10} {'new(earliest)':>13} {'Δpp':>8}")
for a in ARMS:
    rows=[]
    for i,s in enumerate(SEEDS):
        nv=routine(run_joint(seed=s,groups=2,arm=(a if a!="anchor" else "cup"),
                             cup_use_window=False,cup_gate_sampling=True,**cond)[0])
        ov=old[a][i]; rows.append((ov,nv))
        print(f"{a:9s} {s:4d} {ov:10.4f} {nv:13.4f} {(nv-ov)*100:+8.2f}",flush=True)
    om=st.mean(x[0] for x in rows); nm=st.mean(x[1] for x in rows)
    report[a]=dict(old_mean=om,new_mean=nm,delta_pp=(nm-om)*100,pairs=rows)
    print(f"{'':9s} {'mean':>4} {om:10.4f} {nm:13.4f} {(nm-om)*100:+8.2f}\n",flush=True)
json.dump(report,open(os.path.join(_CODE,"..","results","v3joint_r01_impact_dev4.json"),"w"),indent=1,ensure_ascii=False)
print("saved v3joint_r01_impact_dev4.json")
