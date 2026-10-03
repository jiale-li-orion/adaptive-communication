# -*- coding: utf-8 -*-
"""风险窗 period=300：合法静态配置网格前沿 vs 端到端反馈闭环，判别紧 regime 是否需要自适应。"""
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
ARMS=[f"grid{s}x{r}" for s in (300,600,900,1800) for r in (300,600,900)]+["ea_aoi","eh_aoi"]
print("period=300 风险窗, 能量充足, oh16, 8种子")
print(f"{'arm':14s} {'rout':>7s} {'soc':>6s} {'air_s':>7s} {'cmd':>4s}")
for arm in ARMS:
    rs=[run(arm,s) for s in range(8)]
    print(f"{arm:14s} {st.mean(r['routine']['delivered']/r['routine']['n'] for r in rs):7.4f} "
          f"{st.mean(r['survival']['mean_final_soc'] for r in rs):6.3f} "
          f"{st.mean(r['communication']['airtime_uplink_h']*3600 for r in rs):7.0f} "
          f"{st.mean(r['communication']['downlink_attempts'] for r in rs):4.0f}")
