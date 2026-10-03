# -*- coding: utf-8 -*-
"""采样门控归因：文献门限 eh_aoi 是否也失稳；只门控上报 vs 门控采样。"""
import os, sys, statistics as st
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint

# arm -> (实际arm, use_window, gate_sampling)
ARMS={
 "local":        ("local",True,True),
 "fixed900":     ("fixed900",True,True),
 "ea_aoi":       ("ea_aoi",True,True),
 "eh_aoi":       ("eh_aoi",True,True),
 "report_only":  ("cup",False,False),   # 只按义务相位门控上报、采样恒稀(=oblig_slack思路)
 "anchor_full":  ("cup",False,True),    # 义务相位门控采样+上报(新)
}
def show(tag,hours,peak,soc0,blackout,outage_h,seeds=(0,1,2,3,4,5)):
    print(f"\n### {tag}: {hours}h peak={peak} soc0={soc0} bo={blackout}")
    for name,(arm,uw,gs) in ARMS.items():
        rs=[run_joint(seed=s,groups=2,arm=arm,task_hours=hours,tail_hours=1,
                      outage_start_h=4.0,outage_hours=outage_h,
                      enable_backup=True,backup_rate_s=300,backup_bytes=78,
                      harvest_mode="solar",harvest_peak_wh_per_hour=peak,
                      initial_soc=soc0,blackout_frac=blackout,blackout_start_h=4.0,
                      cup_use_window=uw,cup_gate_sampling=gs)[0] for s in seeds]
        print(f"  {name:12s} rout={st.mean(r['routine']['delivered']/r['routine']['n'] for r in rs):.4f} "
              f"event={st.mean(r['event']['deliver_rate'] for r in rs):.3f} "
              f"alive={st.mean(r['survival']['alive'] for r in rs):.2f} "
              f"soc={st.mean(r['survival']['mean_final_soc'] for r in rs):.3f} "
              f"air={st.mean(r['communication']['airtime_uplink_h']*3600 for r in rs):.0f}s "
              f"cmd={st.mean(r['communication']['downlink_attempts'] for r in rs):.0f}")
show("宽松",48,0.03,1.0,0.0,16)
show("紧张",48,0.005,0.5,0.3,16)
show("极紧",48,0.003,0.4,0.4,16)
