# -*- coding: utf-8 -*-
"""任务紧度轴：不同义务周期下，'按义务周期开环采样' vs 端到端AoI闭环(ea/eh)。
能量充足以隔离能量；验证开环在任意紧度都不劣、闭环从不占优。"""
import os, sys, statistics as st
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint
def run(arm,si,s,period):
    return run_joint(seed=s,groups=2,arm=arm,sample_interval_s=si,report_period_s=min(900,period),
                     routine_period_s=period,task_hours=48,tail_hours=1,outage_start_h=4,outage_hours=16,
                     enable_backup=True,backup_rate_s=300,backup_bytes=78,harvest_mode="solar",
                     harvest_peak_wh_per_hour=0.03,initial_soc=1.0,blackout_frac=0.0)[0]
print("能量充足 peak.03 soc1 bo0, oh16；openloop 采样=义务周期")
for period in (300,600,900,1800,3600):
    print(f"\n## obligation period = {period}s")
    for name,arm,si in [("openloop(P)","fixed900",period),("ea_aoi","ea_aoi",3600),("eh_aoi","eh_aoi",3600)]:
        rs=[run(arm,si,s,period) for s in range(8)]
        print(f"  {name:11s} rout={st.mean(r['routine']['delivered']/r['routine']['n'] for r in rs):.4f} "
              f"soc={st.mean(r['survival']['mean_final_soc'] for r in rs):.3f} "
              f"air={st.mean(r['communication']['airtime_uplink_h']*3600 for r in rs):.0f}s "
              f"cmd={st.mean(r['communication']['downlink_attempts'] for r in rs):.0f}")
