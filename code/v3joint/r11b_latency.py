# -*- coding: utf-8 -*-
"""R11b: 钉死"排队等待过久"机理——晚到样本 网关heard->中心received 的等待时延分布。"""
import os,sys,statistics as st
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE,_CODE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint
BASE=dict(task_hours=48,tail_hours=1,outage_start_h=4,outage_hours=16,enable_backup=True,
    harvest_mode='solar',harvest_peak_wh_per_hour=.03,initial_soc=1.,blackout_frac=0.,
    sample_interval_s=600,report_period_s=600,routine_period_s=600,
    backup_rate_s=300,backup_bytes=78,collect_rows=True)
for ch in ("obligation","latest","edf"):
    r,_,_=run_joint(seed=0,groups=2,arm="grid600x600",backup_chooser=ch,**BASE)
    rows=r["rows"]
    late=[x for x in rows if x["collected"] and not x["received_on_time"]]
    def wait(x):
        h=x.get("first_heard_at"); rc=x.get("first_received_at")
        return (rc-h) if (h is not None and rc is not None) else None
    waits=sorted(w for w in (wait(x) for x in late) if w is not None)
    ontime=[x for x in rows if x["received_on_time"]]
    wot=sorted(w for w in (wait(x) for x in ontime) if w is not None)
    def q(a,q_): return a[int(q_*(len(a)-1))] if a else None
    print(f"[{ch:10s}] 晚到{len(late)} 等待s: p50={q(waits,.5)} p90={q(waits,.9)} max={q(waits,1)} | "
          f"准时{len(ontime)} 等待 p50={q(wot,.5)} p90={q(wot,.9)} | 备份包={r['backup']['backup_packets']}")
