# -*- coding: utf-8 -*-
"""规模轴：S1(5)/9/14 台，紧张档，验证失稳与开环稳健不是 14 台特有。"""
import os, sys, statistics as st
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint
SCALES={"S1_5":(1,4),"N9":(1,None),"full14":(2,None)}
ARMS={"fixed900":("fixed900",True,True),"ea_aoi":("ea_aoi",True,True),
      "eh_aoi":("eh_aoi",True,True),"anchor":("cup",False,True)}
SEEDS=(0,1,2,3)
for sname,(g,pg) in SCALES.items():
  print(f"\n### {sname} (groups={g},per_group={pg}) 紧张档 oh16 pk.005 soc.5 bo.3")
  for name,(arm,uw,gs) in ARMS.items():
    rs=[run_joint(seed=s,groups=g,per_group=pg,arm=arm,task_hours=48,tail_hours=1,
                  outage_start_h=4.0,outage_hours=16.0,enable_backup=True,
                  backup_rate_s=300,backup_bytes=78,harvest_mode="solar",
                  harvest_peak_wh_per_hour=0.005,initial_soc=0.5,blackout_frac=0.3,
                  blackout_start_h=4.0,cup_use_window=uw,cup_gate_sampling=gs)[0] for s in SEEDS]
    print(f"  {name:9s} rout={st.mean(r['routine']['delivered']/r['routine']['n'] for r in rs):.4f} "
          f"alive={st.mean(r['survival']['alive'] for r in rs):.2f}/{rs[0]['survival']['n']} "
          f"soc={st.mean(r['survival']['mean_final_soc'] for r in rs):.3f} "
          f"air={st.mean(r['communication']['airtime_uplink_h']*3600 for r in rs):.0f}s")
