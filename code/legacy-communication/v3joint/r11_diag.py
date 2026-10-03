# -*- coding: utf-8 -*-
"""R11 根因诊断(一): obligation 在饱和档(r300,带宽够)为何只有 .838?
对比同 seed obligation vs latest(edf) 的逐义务结果,定位 obligation 丢失的义务:
是否集中在中断窗、是否"采到但没送到"(=去重误杀候选)、样本-义务是否跨窗多匹配。"""
import os,sys
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE,_CODE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint
BASE=dict(task_hours=48,tail_hours=1,outage_start_h=4,outage_hours=16,enable_backup=True,
    harvest_mode='solar',harvest_peak_wh_per_hour=.03,initial_soc=1.,blackout_frac=0.,
    sample_interval_s=600,report_period_s=600,routine_period_s=600,
    backup_rate_s=300,backup_bytes=78,collect_rows=True)
def run(ch,seed=0):
    r,inst,obls=run_joint(seed=seed,groups=2,arm="grid600x600",backup_chooser=ch,**BASE)
    return r,inst,obls
rO,instO,_=run("obligation"); rL,instL,_=run("latest")
def summ(r,tag):
    rows=r["rows"]; P=600
    n=len(rows); coll=sum(1 for x in rows if x["collected"]); deli=sum(1 for x in rows if x["received_on_time"])
    coll_but_late=[x for x in rows if x["collected"] and not x["received_on_time"]]
    inout=sum(1 for x in coll_but_late if 4*3600<=x.get("first_heard_at",0)<20*3600 or 4*3600<=(x.get("taken_at",0))<20*3600)
    print(f"[{tag}] n={n} collected={coll} delivered_on_time={deli} ({deli/n:.3f}) 采到未按时到={len(coll_but_late)} 其中落在中断窗={inout}")
    return { (x.get("node"),x.get("taken_at")):x for x in rows}
o=summ(rO,"obligation"); l=summ(rL,"latest")
# obligation 丢、latest 成的义务(同 node+taken)
lost=[k for k in o if (not o[k]["received_on_time"]) and l.get(k,{}).get("received_on_time")]
print("obligation丢而latest成的义务数:",len(lost))
for k in lost[:12]:
    a,b=o[k],l[k]
    print(" node",k[0],"taken",k[1],"dl",a.get("deadline"),
          "O:heard",a.get("first_heard_at"),"recv",a.get("first_received_at"),
          "| L:heard",b.get("first_heard_at"),"recv",b.get("first_received_at"))
# 样本-义务匹配数分布(看是否一份样本匹配多义务=跨窗预支)
plane=instO.plane
multi=0;tot=0; examples=[]
for key,lst in getattr(plane,"_obl_index",{}).items():
    pass
# 直接统计每个 obligation 窗口与相邻窗口是否共享样本:用 exogenous matches
print("backup obligation packets/sup:",rO["backup"]["backup_packets"],rO["backup"]["backup_suppressed"])
