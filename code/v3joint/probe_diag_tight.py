# -*- coding: utf-8 -*-
"""诊断 period=300 风险窗：开环高频为何崩(.054)、ea为何(.46)更好。看 A/B/C 损失与积压/空口。"""
import os, sys, statistics as st
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint
def abc(rows):
    A=B=C=deliv=0
    for r in rows:
        if r.get("kind")!="routine": continue
        d=r.get("delivered"); fh=r.get("first_heard_at"); fr=r.get("first_received_at"); dl=r.get("deadline")
        if d: deliv+=1; continue
        if fh is None: A+=1
        elif fh>dl: B+=1
        elif fr is None or fr>dl: C+=1
    return deliv,A,B,C
for name,arm,si,rp in [("openloop300","fixed900",300,300),("ea_aoi","ea_aoi",3600,900),("eh_aoi","eh_aoi",3600,900)]:
    D=As=Bs=Cs=0; caches=[]; bk=[]; air=[]
    for s in range(4):
        r,inst,obl=run_joint(seed=s,groups=2,arm=arm,sample_interval_s=si,report_period_s=rp,
            routine_period_s=300,task_hours=48,tail_hours=1,outage_start_h=4,outage_hours=16,
            enable_backup=True,backup_rate_s=300,backup_bytes=78,harvest_mode="solar",
            harvest_peak_wh_per_hour=0.03,initial_soc=1.0,blackout_frac=0.0,collect_rows=True)
        d,a,b,c=abc(r["rows"]); D+=d;As+=a;Bs+=b;Cs+=c
        caches.append(inst.cache_len_sum/max(1,inst.cache_len_n))
        bk.append(r.get("backup",{}).get("gated",0)); air.append(r["communication"]["airtime_uplink_h"]*3600)
    tot=D+As+Bs+Cs
    print(f"{name:12s} deliv={D/tot:.3f} A未到网关={As} B到网关晚={Bs} C按时到没赶上中心={Cs} | "
          f"网关均积压={st.mean(caches):.1f} backup_gated={st.mean(bk):.0f} air={st.mean(air):.0f}s")
