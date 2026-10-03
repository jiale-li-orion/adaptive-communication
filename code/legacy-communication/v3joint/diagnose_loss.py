# -*- coding: utf-8 -*-
"""定位：未交付义务卡在哪一跳。分类
 A never_heard        : 从未到网关（接入段丢，网关级备用够不到）
 B heard_late         : 到网关但已晚于 deadline（上游太慢/接入延迟）
 C ontime_undelivered : 按时到网关、却没在 deadline 前到中心（回传/备用发送时序，唯一联合可救）
"""
import os, sys, statistics as st
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint

def classify(rate, arm="local", up=0.74, seeds=(0,1,2,3,4,5)):
    agg={}
    for s in seeds:
        r,_,_=run_joint(seed=s,groups=2,arm=arm,task_hours=12,tail_hours=1,
                        outage_start_h=4.0,outage_hours=8.0,uplink_p_arrive=up,
                        enable_backup=(rate is not None),
                        backup_rate_s=rate or 120, backup_bytes=78,
                        backup_chooser="edf", collect_rows=True)
        for row in r["rows"]:
            if row["censored"] or row["delivered"]: continue
            k=row["kind"]
            d=agg.setdefault(k,{"A_never_heard":0,"B_heard_late":0,"C_ontime_undel":0,"n_miss":0})
            d["n_miss"]+=1
            fh=row["first_heard_at"]; dl=row["deadline"]
            if fh is None: d["A_never_heard"]+=1
            elif fh>dl: d["B_heard_late"]+=1
            else: d["C_ontime_undel"]+=1
    print(f"\n### rate={rate} arm={arm} up={up} (seeds {len(seeds)})  未交付义务分跳计数(合计)")
    for k,d in agg.items():
        print(f"  {k:10s} {d}")

for rate in (None, 120, 300, 600):
    classify(rate)
# 紧接入对照
classify(600, up=0.50)
