# -*- coding: utf-8 -*-
"""C-send 信号探查：义务级截止+冗余抑制装包 vs 朴素EDF（full, 长中断, 稀疏备用）。"""
import os, sys, statistics as st
_HERE = os.path.dirname(os.path.abspath(__file__))
_CODE = os.path.dirname(_HERE)
for p in [_HERE] + [os.path.join(_CODE, d) for d in
                    ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0, p)
from joint_run import run_joint

SEEDS = list(range(8))
def cell(arm, rate, chooser, suppress=True, up=0.74):
    rs = [run_joint(seed=s, groups=2, arm=arm, task_hours=12, tail_hours=1,
                    outage_start_h=4.0, outage_hours=8.0, uplink_p_arrive=up,
                    enable_backup=True, backup_rate_s=rate, backup_bytes=78,
                    backup_chooser=chooser, backup_suppress=suppress)[0] for s in SEEDS]
    def m(path):
        vals=[]
        for r in rs:
            v=r
            for k in path.split("."): v=v[k]
            vals.append(v)
        return st.mean(vals)
    return dict(rout=round(st.mean(r["routine"]["delivered"]/r["routine"]["n"] for r in rs),4),
                event=round(m("event.deliver_rate"),4),
                pkt=round(m("backup.backup_packets"),2),
                rec=round(m("backup.backup_records"),2),
                byte=round(m("backup.backup_bytes_sent"),1),
                supp=round(m("backup.backup_suppressed"),1))

for arm in ("local","fixed900","ea_aoi"):
    for rate in (120,300,600):
        edf = cell(arm,rate,"edf")
        obl = cell(arm,rate,"obligation",True)
        obln = cell(arm,rate,"obligation",False)
        print(f"\n=== arm={arm} rate={rate} (full,bh8,78B) ===")
        print(f"  edf朴素   : {edf}")
        print(f"  obl+抑制  : {obl}")
        print(f"  obl无抑制 : {obln}")
