# -*- coding: utf-8 -*-
"""R09 方向探针(二)：硬稀缺备份下，义务级仲裁(obligation)相对 item级EDF/FIFO 是否有增益。
若 obligation 去重+按真实义务截止能显著多覆盖不同义务⇒决策层上移到义务级资源仲裁有空间(X1/X3);
若各 chooser 都被容量上界压在同一水平⇒内容选择也无空间,负结果封到资源面。"""
import os,sys,json,statistics as st
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE,_CODE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint
SEEDS=(0,1,2,3,4,5)
BASE=dict(task_hours=48,tail_hours=1,outage_start_h=4,outage_hours=16,enable_backup=True,
    harvest_mode='solar',harvest_peak_wh_per_hour=.03,initial_soc=1.,blackout_frac=0.,
    sample_interval_s=600,report_period_s=600,routine_period_s=600)
SCARCE=[("r600_b78",600,78),("r1200_b200",1200,200),("r900_b78",900,78)]
CHOOSERS=["edf","obligation","fifo","latest"]
out={}
for tag,rate,bytes_ in SCARCE:
    out[tag]={}
    for ch in CHOOSERS:
        sv=[];rec=[];sup=[];uniq=[]
        for s in SEEDS:
            r,_,_=run_joint(seed=s,groups=2,arm="grid600x600",backup_rate_s=rate,
                            backup_bytes=bytes_,backup_chooser=ch,**BASE)
            rr=r["routine"]; b=r["backup"]
            sv.append(rr["delivered"]/rr["n"]); rec.append(b.get("backup_records",0))
            sup.append(b.get("backup_suppressed",0))
        out[tag][ch]=dict(svc=round(st.mean(sv),4),svc_min=round(min(sv),3),svc_max=round(max(sv),3),
            rec=round(st.mean(rec),0),sup=round(st.mean(sup),0))
        print(f"{tag:10s} {ch:10s} svc={out[tag][ch]['svc']:.4f}[{out[tag][ch]['svc_min']},{out[tag][ch]['svc_max']}] rec={out[tag][ch]['rec']:.0f} sup={out[tag][ch]['sup']:.0f}",flush=True)
    print("",flush=True)
json.dump(out,open(os.path.join(_CODE,"..","results","v3joint_r09_chooser_scarce.json"),"w"),indent=1,ensure_ascii=False)
print("saved r09")
