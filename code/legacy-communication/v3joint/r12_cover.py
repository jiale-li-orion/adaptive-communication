# -*- coding: utf-8 -*-
"""R12 J1: cover 是否在四档统一支配/追平各档最强基线。"""
import os,sys,json,statistics as st
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE,_CODE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint
SEEDS=(0,1,2,3,4,5)
BASE=dict(task_hours=48,tail_hours=1,outage_start_h=4,outage_hours=16,enable_backup=True,
    harvest_mode='solar',harvest_peak_wh_per_hour=.03,initial_soc=1.,blackout_frac=0.,
    sample_interval_s=600,report_period_s=600,routine_period_s=600)
GRID=[("r300_b78_sat",300,78),("r600_b78",600,78),("r900_b78",900,78),("r1200_b200",1200,200)]
CHOOSERS=["edf","obligation","latest","salvage","cover"]
out={}
for tag,rate,bytes_ in GRID:
    out[tag]={}
    for ch in CHOOSERS:
        sv=[];rec=[];pkt=[];byt=[]
        for sd in SEEDS:
            r,_,_=run_joint(seed=sd,groups=2,arm="grid600x600",backup_rate_s=rate,
                            backup_bytes=bytes_,backup_chooser=ch,**BASE)
            rr=r["routine"]; b=r["backup"]
            sv.append(rr["delivered"]/rr["n"]); rec.append(b.get("backup_records",0))
            pkt.append(b.get("backup_packets",0)); byt.append(b.get("backup_bytes_sent",0))
        out[tag][ch]=dict(svc=round(st.mean(sv),4),svc_min=round(min(sv),3),svc_max=round(max(sv),3),
            rec=round(st.mean(rec),0),pkt=round(st.mean(pkt),0),bytes=round(st.mean(byt),0))
        print(f"{tag:12s} {ch:10s} svc={out[tag][ch]['svc']:.4f}[{out[tag][ch]['svc_min']},{out[tag][ch]['svc_max']}] rec={out[tag][ch]['rec']:.0f} pkt={out[tag][ch]['pkt']:.0f} bytes={out[tag][ch]['bytes']:.0f}",flush=True)
    print("",flush=True)
json.dump(out,open(os.path.join(_CODE,"..","results","v3joint_r12_cover.json"),"w"),indent=1,ensure_ascii=False)
print("saved r12")
