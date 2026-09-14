# -*- coding: utf-8 -*-
"""方向验证：能量自治边际轴（充裕→紧张，对所有臂相同），服务-存活曲线。
不构造让某臂必败的角落；看是否存在一段合理区间，机会感知相对最强本地反馈 ea_aoi Pareto 占优。"""
import os, sys, statistics as st
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint

def show(tag, hours, peak, soc0, blackout, outage_h, seeds=(0,1,2,3,4,5)):
    print(f"\n### {tag}: {hours}h peak={peak} soc0={soc0} blackout={blackout} outage={outage_h}h")
    for arm in ("local","fixed900","ea_aoi"):
        rs=[]
        for s in seeds:
            r,_,_=run_joint(seed=s,groups=2,arm=arm,task_hours=hours,tail_hours=1,
                            outage_start_h=4.0,outage_hours=outage_h,
                            enable_backup=True,backup_rate_s=300,backup_bytes=78,
                            harvest_mode="solar",harvest_peak_wh_per_hour=peak,
                            initial_soc=soc0,blackout_frac=blackout,blackout_start_h=4.0)
            rs.append(r)
        n=len(rs)
        print(f"  {arm:9s} rout={st.mean(r['routine']['delivered']/r['routine']['n'] for r in rs):.4f} "
              f"event={st.mean(r['event']['deliver_rate'] for r in rs):.3f} "
              f"alive={st.mean(r['survival']['alive'] for r in rs):.2f}/14 "
              f"soc={st.mean(r['survival']['mean_final_soc'] for r in rs):.3f} "
              f"air={st.mean(r['communication']['airtime_uplink_h']*3600 for r in rs):.0f}s "
              f"dead={sorted(set(tuple(r['survival']['dead']) for r in rs))[:2]}")

# 从宽到紧扫能量轴（48h，长中断 4-20h，备用稀疏 t300）
show("宽松", 48, 0.03, 1.0, 0.0, 16)
show("中等", 48, 0.01, 0.6, 0.0, 16)
show("紧张", 48, 0.005, 0.5, 0.3, 16)
show("极紧", 48, 0.003, 0.4, 0.4, 16)
