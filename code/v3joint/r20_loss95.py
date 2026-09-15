# -*- coding: utf-8 -*-
"""R20 稳健性补测: 主工具换成 maxcov 后,在备份整包成功率0.95下复测四档(原R19只测cover)。"""
import os,sys,json,statistics as st
from concurrent.futures import ProcessPoolExecutor
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE,_CODE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
SEEDS=(0,1,2,3,4,5)
BASE=dict(task_hours=48,tail_hours=1,outage_start_h=4,outage_hours=16,enable_backup=True,
    harvest_mode='solar',harvest_peak_wh_per_hour=.03,initial_soc=1.,blackout_frac=0.,
    sample_interval_s=600,report_period_s=600,routine_period_s=600,backup_p_succ=.95)
GRID=[("r300_b78_sat",300,78),("r600_b78",600,78),("r900_b78",900,78),("r1200_b200",1200,200)]
CHOOSERS=["edf","obligation","latest","salvage","cover","cover2","maxcov"]
def one(args):
    tag,rate,bytes_,ch,sd=args
    from joint_run import run_joint
    r,_,_=run_joint(seed=sd,groups=2,arm="grid600x600",backup_rate_s=rate,
                    backup_bytes=bytes_,backup_chooser=ch,**BASE)
    return (tag,ch,sd,round(r["routine"]["delivered"]/r["routine"]["n"],4))
if __name__=="__main__":
    jobs=[(t,rate,by,ch,sd) for t,rate,by in GRID for ch in CHOOSERS for sd in SEEDS]
    res={t:{ch:[] for ch in CHOOSERS} for t,_,_ in GRID}
    with ProcessPoolExecutor(max_workers=6) as ex:
        for tag,ch,sd,sv in ex.map(one,jobs): res[tag][ch].append(sv)
    out={}
    for tag,_,_ in GRID:
        out[tag]={ch:dict(svc=round(st.mean(res[tag][ch]),4),svc_min=round(min(res[tag][ch]),3),
                          svc_max=round(max(res[tag][ch]),3),seeds=res[tag][ch]) for ch in CHOOSERS}
        print(tag+"  "+"  ".join(f"{ch}={out[tag][ch]['svc']:.3f}" for ch in CHOOSERS),flush=True)
    json.dump(out,open(os.path.join(_CODE,"..","results","v3joint_r20_loss95_maxcov.json"),"w"),indent=1,ensure_ascii=False)
    print("saved r20_loss95_maxcov")
