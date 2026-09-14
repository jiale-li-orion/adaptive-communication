# -*- coding: utf-8 -*-
"""紧义务在能量可行前提下：密采是否提高服务？此时各策略服务/能耗对比。"""
import os, sys, statistics as st
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint
ARMS=[("fixed_sparse",("fixed900",3600)),("fixed_dense",("fixed900",600)),
      ("ea_aoi",("ea_aoi",3600)),("eh_aoi",("eh_aoi",3600))]
def run(arm,si,s,period,peak,soc,bo):
    return run_joint(seed=s,groups=2,arm=arm,sample_interval_s=si,report_period_s=900,
                     routine_period_s=period,task_hours=48,tail_hours=1,outage_start_h=4,
                     outage_hours=16,enable_backup=True,backup_rate_s=300,backup_bytes=78,
                     harvest_mode="solar",harvest_peak_wh_per_hour=peak,initial_soc=soc,
                     blackout_frac=bo,blackout_start_h=4)[0]
for tag,peak,soc,bo in [("能量充足",0.03,1.0,0.0),("能量中等",0.012,1.0,0.0)]:
  for period in (600,3600):
    print(f"\n### {tag} period={period} oh16")
    for name,(arm,si) in ARMS:
        rs=[run(arm,si,s,period,peak,soc,bo) for s in range(8)]
        print(f"  {name:13s} rout={st.mean(r['routine']['delivered']/r['routine']['n'] for r in rs):.4f} "
              f"alive={st.mean(r['survival']['alive'] for r in rs):.2f} "
              f"soc={st.mean(r['survival']['mean_final_soc'] for r in rs):.3f} "
              f"air={st.mean(r['communication']['airtime_uplink_h']*3600 for r in rs):.0f}s")
