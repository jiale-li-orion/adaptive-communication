# -*- coding: utf-8 -*-
"""诊断 B: dayfeed 错位一次运行, rows 与 ObligationSet 逐小时对账, 定位行数缺失。"""
import os,sys
from collections import Counter,defaultdict
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
r,inst,obset=run_joint(mission_schedule=UP,mission_mode="dayfeed",**BASE)
rows=r["rows"]
print("rows 总数",len(rows)," ObligationSet 数",len(obset.obligations)," routine.n",r["routine"]["n"])
oids=[x["oid"] for x in rows]; print("oid 唯一",len(oids)==len(set(oids)))
# 期望: ObligationSet 里 routine 按小时×测项
exp=defaultdict(Counter); act=defaultdict(Counter)
for o in obset.obligations:
    if o.kind=="routine": exp[int(o.release_at//3600)][o.measurand]+=1
for x in rows:
    if x["kind"]=="routine": act[int(x["release_at"]//3600)][x["node_id"]] and None
    if x["kind"]=="routine": act[int(x["release_at"]//3600)]["_n"]+=1
for h in [0,6,7,24,25,36,37,47]:
    print(f"h{h:2d} exp={dict(exp[h])} act_n={act[h]['_n']}")
# release_at 原始值抽样: 升级段位移
uprows=sorted([x for x in rows if x["kind"]=="routine" and x["node_id"]=="n00" and x["release_at"]>=21750],
              key=lambda z:z["release_at"])
print("n00 升级段前12个 release:",[x["release_at"] for x in uprows[:12]])
print("n00 升级段 h37 窗内 release:",sorted([x["release_at"] for x in uprows if 133200<=x["release_at"]<136800]))
