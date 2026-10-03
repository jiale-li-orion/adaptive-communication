# -*- coding: utf-8 -*-
"""前提探查：紧义务(period=600s,grace=600)下，固定稀采3600 vs 固定密采600 是否有服务/能耗差。
若密采在紧任务无服务价值，则'紧任务'方向无意义、守住第一阶边界；若有，再设计原则性 anchor。"""
import os, sys, statistics as st
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint
def block(tag,period,seeds=tuple(range(8))):
    print(f"\n### {tag} period={period} (grace=period) 紧张能量 oh16")
    for label,si in [("fixed_sparse_si3600",3600),("fixed_dense_si600",600),("fixed_si300",300)]:
        rs=[run_joint(seed=s,groups=2,arm="fixed900",sample_interval_s=si,report_period_s=900,
                      routine_period_s=period,task_hours=48,tail_hours=1,
                      outage_start_h=4,outage_hours=16,enable_backup=True,backup_rate_s=300,
                      backup_bytes=78,harvest_mode="solar",harvest_peak_wh_per_hour=0.005,
                      initial_soc=0.5,blackout_frac=0.3,blackout_start_h=4)[0] for s in seeds]
        print(f"  {label:20s} rout={st.mean(r['routine']['delivered']/r['routine']['n'] for r in rs):.4f} "
              f"n={rs[0]['routine']['n']} alive={st.mean(r['survival']['alive'] for r in rs):.2f} "
              f"soc={st.mean(r['survival']['mean_final_soc'] for r in rs):.3f} "
              f"air={st.mean(r['communication']['airtime_uplink_h']*3600 for r in rs):.0f}s")
block("紧义务",600)
block("对照松义务(原)",3600)
