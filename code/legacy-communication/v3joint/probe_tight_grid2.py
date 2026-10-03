# -*- coding: utf-8 -*-
"""风险窗 period=300 精简：找静态网格最优点 vs ea，判别是否必须自适应。4种子，逐臂flush。"""
import os, sys, statistics as st
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint
def run(arm,s):
    return run_joint(seed=s,groups=2,arm=arm,sample_interval_s=3600,report_period_s=900,
                     routine_period_s=300,task_hours=48,tail_hours=1,outage_start_h=4,outage_hours=16,
                     enable_backup=True,backup_rate_s=300,backup_bytes=78,harvest_mode="solar",
                     harvest_peak_wh_per_hour=0.03,initial_soc=1.0,blackout_frac=0.0)[0]
ARMS=["grid600x300","grid600x600","grid900x300","grid900x600","grid1800x900","ea_aoi"]
print("period=300, 4 seeds, flush",flush=True)
for arm in ARMS:
    rs=[run(arm,s) for s in range(4)]
    print(f"{arm:13s} rout={st.mean(r['routine']['delivered']/r['routine']['n'] for r in rs):.4f} "
          f"soc={st.mean(r['survival']['mean_final_soc'] for r in rs):.3f} "
          f"air={st.mean(r['communication']['airtime_uplink_h']*3600 for r in rs):.0f}s",flush=True)
print("DONE",flush=True)
