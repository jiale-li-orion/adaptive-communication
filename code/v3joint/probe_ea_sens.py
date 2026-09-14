# -*- coding: utf-8 -*-
"""ea_aoi 失稳的参数稳健性：扫 SoC 阈值/密采档/回滞，紧张工况 8 种子，对照 fixed900。
判据先写定：变体若仍落后 fixed 且死节点=机制性；若靠高阈值(几乎不进dense≈不闭环)才稳=支持结论。"""
import os, sys, statistics as st
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE,_CODE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
import center as C
# 运行时注入参数变体工厂（不修改 center.py）
C.ARMS["eaoi_h005"]=lambda: C.EnergyAoiPolicy(healthy_wh=0.005)
C.ARMS["eaoi_h020"]=lambda: C.EnergyAoiPolicy(healthy_wh=0.020)
C.ARMS["eaoi_h030"]=lambda: C.EnergyAoiPolicy(healthy_wh=0.030)
C.ARMS["eaoi_d1200"]=lambda: C.EnergyAoiPolicy(dense_interval_s=1200)
C.ARMS["eaoi_fast600"]=lambda: C.EnergyAoiPolicy(fast_period_s=600)
from joint_run import run_joint
KW=dict(groups=2,task_hours=48,tail_hours=1,outage_start_h=4,outage_hours=16,
        enable_backup=True,backup_rate_s=300,backup_bytes=78,harvest_mode="solar",
        harvest_peak_wh_per_hour=0.005,initial_soc=0.5,blackout_frac=0.3)
order=[("fixed900","open-loop fixed900"),("ea_aoi","default h=.010/d600/f300"),
       ("eaoi_h005","more aggressive h=.005"),("eaoi_h020","conservative h=.020"),
       ("eaoi_h030","very conservative h=.030"),("eaoi_d1200","dense interval 1200"),
       ("eaoi_fast600","fast report 600"),("ea_aoi_h","hysteresis exit.006/n2")]
import json
out={}
print("stressed oh16 peak.005 soc.5 bo.3, 8 seeds",flush=True)
for arm,desc in order:
    rs=[run_joint(seed=s,arm=arm,**KW)[0] for s in range(8)]
    rec=dict(rout=st.mean(r['routine']['delivered']/r['routine']['n'] for r in rs),
             alive=st.mean(r['survival']['alive'] for r in rs),
             soc=st.mean(r['survival']['mean_final_soc'] for r in rs),
             cmd=st.mean(r['communication']['downlink_attempts'] for r in rs))
    out[arm]=rec
    print(f"{arm:12s} {desc:26s} rout={rec['rout']:.4f} alive={rec['alive']:.2f} "
          f"soc={rec['soc']:.3f} cmd={rec['cmd']:.0f}",flush=True)
json.dump(out,open(os.path.join(_CODE,"..","results","v3joint_ea_sens.json"),"w"),indent=1)
print("saved v3joint_ea_sens.json / DONE",flush=True)
