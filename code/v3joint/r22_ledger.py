# -*- coding: utf-8 -*-
"""顺序2 诊断: dayfeed 已采未送义务的时间分布, 判别瓶颈是硬容量还是采集×交付机会错配。
错位相位(真实, 避免边界双配)。逐义务按 release 小时分桶: 采到/到网关及时/到中心及时。"""
import os,sys
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
OUT_LO,OUT_HI=4*3600,20*3600

def ledger(tag,mode,sched):
    kw=dict(BASE)
    if mode is not None: kw.update(mission_schedule=sched,mission_mode=mode)
    r,inst,obs=run_joint(**kw)
    rows=r["rows"]
    # 只看 routine 位移义务(排除网关雨量与事件), 按 release 小时分桶
    buckets={}
    for x in rows:
        if x["kind"]!="routine": continue
        h=int(x["release_at"]//3600)
        b=buckets.setdefault(h,{"n":0,"coll":0,"heard_ontime":0,"recv_ontime":0,"heard_but_not_recv":0})
        b["n"]+=1
        if x["collected"]: b["coll"]+=1
        if x["heard_on_time"]: b["heard_ontime"]+=1
        if x["received_on_time"]: b["recv_ontime"]+=1
        if x["heard_on_time"] and not x["received_on_time"]: b["heard_but_not_recv"]+=1
    print(f"=== {tag}: svc={r['routine']['delivered']/r['routine']['n']:.3f} ===")
    print(" h | 主路 |  n | 采到 | 到网关及时 | 到中心及时 | 卡在回传 %")
    for h in sorted(buckets):
        b=buckets[h]; link="断" if OUT_LO<=h*3600<OUT_HI else "通"
        day="昼" if (6<=h%24<18) else "夜"
        print(f" {h:2d} {day} {link} | {b['n']:3d} | {b['coll']:3d} | {b['heard_ontime']:3d} | {b['recv_ontime']:3d} | {b['heard_but_not_recv']:3d} ({100*b['heard_but_not_recv']/max(1,b['heard_ontime']):.0f}%)")

ledger("dayfeed 错位","dayfeed",UP)
