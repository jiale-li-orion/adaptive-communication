# -*- coding: utf-8 -*-
"""诊断 C: C0 无变更 vs dayfeed, 中断窗内节点->网关 heard 是否同样衰减归零。"""
import os,sys
from collections import defaultdict
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE,_CODE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint
BASE=dict(seed=0,task_hours=48,tail_hours=1,arm="local",groups=2,
    sample_interval_s=600,report_period_s=600,routine_period_s=600,
    harvest_mode="solar",harvest_peak_wh_per_hour=0.03,initial_soc=1.0,
    outage_start_h=4,outage_hours=16,enable_backup=True,
    backup_rate_s=1200,backup_bytes=78,backup_chooser="maxcov",collect_rows=True)
UP=[(0,600,"blue"),(6*3600+150,300,"yellow")]
def buckets(rows):
    B=defaultdict(lambda:[0,0,0,0])
    for x in rows:
        if x["kind"]!="routine": continue
        h=int(x["release_at"]//3600); b=B[h]
        b[0]+=1
        if x["collected"]: b[1]+=1
        if x["heard_on_time"]: b[2]+=1
        if x["received_on_time"]: b[3]+=1
    return B
rC,_,_=run_joint(mission_schedule=None,**BASE)
rD,_,_=run_joint(mission_schedule=UP,mission_mode="dayfeed",**BASE)
BC,BD=buckets(rC["rows"]),buckets(rD["rows"])
print(" h | C0 n/coll/heard/recv | dayfeed n/coll/heard/recv")
for h in range(3,26):
    c=BC.get(h,[0,0,0,0]); d=BD.get(h,[0,0,0,0])
    mark=" 断" if 4<=h<20 else " 通"
    print(f" {h:2d}{mark} | {c[0]:3d}/{c[1]:3d}/{c[2]:3d}/{c[3]:3d} | {d[0]:3d}/{d[1]:3d}/{d[2]:3d}/{d[3]:3d}")
