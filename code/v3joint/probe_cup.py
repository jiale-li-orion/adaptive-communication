# -*- coding: utf-8 -*-
"""C-up 对照：cup vs local/fixed900/ea_aoi，含去窗口消融；full, bh8, 多备用频度。"""
import os, sys, statistics as st
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint

SEEDS=list(range(8))
def cell(arm, rate, up=.74, use_window=True):
    rs=[run_joint(seed=s,groups=2,arm=arm,task_hours=12,tail_hours=1,
                  outage_start_h=4.0,outage_hours=8.0,uplink_p_arrive=up,
                  enable_backup=True,backup_rate_s=rate,backup_bytes=78,
                  backup_chooser="edf",cup_use_window=use_window)[0] for s in SEEDS]
    def m(path):
        v=[]
        for r in rs:
            x=r
            for k in path.split("."): x=x[k]
            v.append(x)
        return st.mean(v)
    return dict(rout=round(st.mean(r["routine"]["delivered"]/r["routine"]["n"] for r in rs),4),
                event=round(m("event.deliver_rate"),4),
                air=round(m("communication.airtime_uplink_h")*3600,1),
                cmd=round(m("communication.downlink_attempts"),2),
                pkt=round(m("backup.backup_packets"),1),
                rec=round(m("backup.backup_records"),1))

for rate in (120,300,600):
    print(f"\n########## backup rate={rate}s, 78B, full bh8 ##########")
    for arm in ("local","fixed900","ea_aoi","cup"):
        print(f"  {arm:9s} {cell(arm,rate)}")
    print(f"  {'cup_noWin':9s} {cell('cup',rate,use_window=False)}  # 消融:不看下游窗口")
print("\n########## 紧接入 u=.50, rate=300 ##########")
for arm in ("local","fixed900","ea_aoi","cup"):
    print(f"  {arm:9s} {cell(arm,300,up=.50)}")
