# -*- coding: utf-8 -*-
"""R20 held-out(种子6-9): 确认 maxcov/cover2 在选择期保留种子上同样不弱于 cover。
注: 6-9 曾用于 R07,按 doc33 只称 cover/maxcov 选择过程的保留种子,非整条研究未见测试集。"""
import os,sys,json,statistics as st
from concurrent.futures import ProcessPoolExecutor
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE,_CODE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
SEEDS=(6,7,8,9)
BASE=dict(task_hours=48,tail_hours=1,outage_start_h=4,outage_hours=16,enable_backup=True,
    harvest_mode='solar',harvest_peak_wh_per_hour=.03,initial_soc=1.,blackout_frac=0.,
    sample_interval_s=600,report_period_s=600,routine_period_s=600)
GRID=[("r300_b78_sat",300,78),("r600_b78",600,78),("r900_b78",900,78),("r1200_b200",1200,200)]
CHOOSERS=["edf","obligation","latest","salvage","cover","cover2","maxcov"]
def one(args):
    tag,rate,bytes_,ch,sd=args
    from joint_run import run_joint
    r,_,_=run_joint(seed=sd,groups=2,arm="grid600x600",backup_rate_s=rate,
                    backup_bytes=bytes_,backup_chooser=ch,**BASE)
    rr=r["routine"]; b=r["backup"]
    return (tag,ch,sd,round(rr["delivered"]/rr["n"],4),b.get("backup_records",0),b.get("backup_packets",0),b.get("backup_bytes_sent",0))
if __name__=="__main__":
    jobs=[(t,rate,by,ch,sd) for t,rate,by in GRID for ch in CHOOSERS for sd in SEEDS]
    res={t:{ch:{"svc":[],"rec":[],"pkt":[],"bytes":[]} for ch in CHOOSERS} for t,_,_ in GRID}
    with ProcessPoolExecutor(max_workers=6) as ex:
        for tag,ch,sd,sv,rec,pkt,byt in ex.map(one,jobs):
            c=res[tag][ch]; c["svc"].append(sv); c["rec"].append(rec); c["pkt"].append(pkt); c["bytes"].append(byt)
    out={}
    for tag,_,_ in GRID:
        out[tag]={}
        for ch in CHOOSERS:
            c=res[tag][ch]; v=c["svc"]
            out[tag][ch]=dict(svc=round(st.mean(v),4),svc_min=round(min(v),3),svc_max=round(max(v),3),
                rec=round(st.mean(c["rec"])),pkt=round(st.mean(c["pkt"])),bytes=round(st.mean(c["bytes"])),seeds=v)
        print(f"\n{tag}:",flush=True)
        for ch in CHOOSERS:
            m=out[tag][ch]; print(f"  {ch:11s} svc={m['svc']:.4f}[{m['svc_min']},{m['svc_max']}] bytes={m['bytes']}",flush=True)
    json.dump(out,open(os.path.join(_CODE,"..","results","v3joint_r20_heldout69.json"),"w"),indent=1,ensure_ascii=False)
    print("\nsaved r20_heldout69")
