# -*- coding: utf-8 -*-
"""R17 诊断: cover2 丢、cover 成的义务长什么样?验证 doc28 机理(matches 是否真不完美)。"""
import os,sys
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE,_CODE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint
BASE=dict(task_hours=48,tail_hours=1,outage_start_h=4,outage_hours=16,enable_backup=True,
    harvest_mode='solar',harvest_peak_wh_per_hour=.03,initial_soc=1.,blackout_frac=0.,
    sample_interval_s=600,report_period_s=600,routine_period_s=600,
    backup_rate_s=600,backup_bytes=78,collect_rows=True)
def run(ch):
    r,_,_=run_joint(seed=0,groups=2,arm="grid600x600",backup_chooser=ch,**BASE); return r
rc=run("cover"); r2=run("cover2")
def key(x): return (x.get("node"),x.get("taken_at"))
C={key(x):x for x in rc["rows"]}; D={key(x):x for x in r2["rows"]}
lost=[k for k in D if (not D[k]["received_on_time"]) and C.get(k,{}).get("received_on_time")]
print("cover成 cover2丢 义务数:",len(lost))
import statistics as st
for k in lost[:10]:
    a,b=C[k],D[k]
    print(" node",k[0],"taken",k[1],"dl",a.get("deadline"),
          "| cover: heard",a.get("first_heard_at"),"recv",a.get("first_received_at"),
          "| cover2: heard",b.get("first_heard_at"),"recv",b.get("first_received_at"))
# 汇总两者备份发送与逐义务交付
for tag,r in (("cover",rc),("cover2",r2)):
    rows=r["rows"]; ot=sum(1 for x in rows if x["received_on_time"])
    print(f"[{tag}] ontime={ot}/{len(rows)}={ot/len(rows):.3f} backup rec={r['backup']['backup_records']} pkt={r['backup']['backup_packets']}")
# matches 是否确定同源: 抽一条样本看 _sample_obl 与义务窗口
print("routine window 例: P=600 grace=600 deadline=(i+2)P; matches 仅依赖 taken_at(确定)")
