# -*- coding: utf-8 -*-
"""能量承重可行性：弱采能/多日下，各臂服务-存活-电量是否分化。"""
import os, sys, statistics as st
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint

def cell(arm, hours, mode, peak, soc0, seeds=(0,1,2,3), rate=120):
    out=[]
    for s in seeds:
        r,_,_=run_joint(seed=s,groups=2,arm=arm,task_hours=hours,tail_hours=1,
                        outage_start_h=4.0,outage_hours=min(8.0,hours-4),
                        enable_backup=True,backup_rate_s=rate,backup_bytes=78,
                        harvest_mode=mode,harvest_peak_wh_per_hour=peak,
                        harvest_wh_per_hour=peak,initial_soc=soc0)
        out.append(r)
    f=lambda key: round(st.mean(x[key] for x in out),3)
    return dict(rout=round(st.mean(x["routine"]["delivered"]/x["routine"]["n"] for x in out),4),
                event=round(st.mean(x["event"]["deliver_rate"] for x in out),4),
                air=round(st.mean(x["communication"]["airtime_uplink_h"]*3600 for x in out),1),
                alive=f"survival_alive", soc=lambda: None)

def show(hours, mode, peak, soc0, rate=120):
    print(f"\n### hours={hours} mode={mode} peak={peak} soc0={soc0} rate={rate}")
    for arm in ("local","fixed900","ea_aoi"):
        rs=[run_joint(seed=s,groups=2,arm=arm,task_hours=hours,tail_hours=1,
                      outage_start_h=4.0,outage_hours=min(8.0,hours-4),
                      enable_backup=True,backup_rate_s=rate,backup_bytes=78,
                      harvest_mode=mode,harvest_peak_wh_per_hour=peak,
                      harvest_wh_per_hour=peak,initial_soc=soc0)[0] for s in (0,1,2,3)]
        sv=rs[0]["survival"]
        print(f"  {arm:9s} rout={st.mean(r['routine']['delivered']/r['routine']['n'] for r in rs):.4f} "
              f"event={st.mean(r['event']['deliver_rate'] for r in rs):.3f} "
              f"air={st.mean(r['communication']['airtime_uplink_h']*3600 for r in rs):.1f}s "
              f"alive={st.mean(r['survival']['alive'] for r in rs):.1f}/{sv['n']} "
              f"meanSoc={st.mean(r['survival']['mean_final_soc'] for r in rs):.3f}")

# 12h 不同弱采能
for pk in (0.005,0.01,0.02):
    show(12,"solar",pk,1.0)
# 多日 72h、弱采能、初始半电
show(72,"solar",0.01,0.5)
show(72,"solar",0.02,0.5)
