# -*- coding: utf-8 -*-
"""R19 稳健性: 备份整包成功率 0.95(标准≥95%),其余同 r14。看 cover 排序是否保持。6种子。"""
import os,sys,json,statistics as st
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE,_CODE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint
SEEDS=(0,1,2,3,4,5)
BASE=dict(task_hours=48,tail_hours=1,outage_start_h=4,outage_hours=16,enable_backup=True,
    harvest_mode='solar',harvest_peak_wh_per_hour=.03,initial_soc=1.,blackout_frac=0.,
    sample_interval_s=600,report_period_s=600,routine_period_s=600,backup_p_succ=.95)
GRID={"r300_b78_sat":(300,78),"r600_b78":(600,78),"r900_b78":(900,78),"r1200_b200":(1200,200)}
CHOOSERS=("edf","obligation","latest","salvage","cover")
out={}
for tag,(rate,by) in GRID.items():
    out[tag]={}
    for ch in CHOOSERS:
        sv=[]
        for sd in SEEDS:
            r,_,_=run_joint(seed=sd,groups=2,arm="grid600x600",backup_rate_s=rate,
                            backup_bytes=by,backup_chooser=ch,**BASE)
            sv.append(r["routine"]["delivered"]/r["routine"]["n"])
        out[tag][ch]=round(st.mean(sv),4)
    best=max(v for k,v in out[tag].items() if k!="cover")
    print(f"{tag:12s}",{k:f'{v:.4f}' for k,v in out[tag].items()},
          f"| cover-best={out[tag]['cover']-best:+.4f}",flush=True)
json.dump(out,open(os.path.join(_CODE,"..","results","v3joint_r19_loss95.json"),"w"),indent=1,ensure_ascii=False)
print("saved r19 loss95")
