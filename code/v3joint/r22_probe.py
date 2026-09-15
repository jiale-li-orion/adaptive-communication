# -*- coding: utf-8 -*-
"""顺序2 探查 v3: 48h 升级片段, 弱能量 solar.03 + h4-20中断 + 容量稀缺备份(maxcov)。
对齐相位 t_u=h6; 对比 ignore/comply/energy_gate/sustain; 错位相位验证边界双配。"""
import os,sys
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE,_CODE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint

BASE=dict(seed=0,task_hours=48,tail_hours=1,arm="local",groups=2,
    sample_interval_s=600,report_period_s=600,routine_period_s=600,
    harvest_mode="solar",harvest_peak_wh_per_hour=0.03,initial_soc=1.0,
    outage_start_h=4,outage_hours=16,enable_backup=True,
    backup_rate_s=1200,backup_bytes=78,backup_chooser="maxcov")

def run(tag,mode,sched):
    kw=dict(BASE)
    if mode is not None: kw.update(mission_schedule=sched,mission_mode=mode)
    r,inst,obs=run_joint(**kw)
    rr=r["routine"]; b=r["backup"]; sv=r["survival"]
    iv=[n.sample_interval_s for n in inst.nodes.values()]
    dead=[(n.node_id,n.dead_at) for n in inst.nodes.values() if not getattr(n,"alive",True)]
    print(f"--- {tag} ---")
    print(f"  svc={rr['delivered']/rr['n']:.4f} n={rr['n']} missColl={rr.get('missing_collection')} missDeliv={rr.get('missing_delivery')}")
    print(f"  末SoC={sv['mean_final_soc']} dead={len(dead)} {dead[:4]} 终态300={sum(1 for x in iv if x==300)}/600={sum(1 for x in iv if x==600)}")
    print(f"  backup rec={b.get('backup_records')} pkt={b.get('backup_packets')} refusals={len(r.get('mission_refusals',[]))}")

UPa=[(0,600,"blue"),(6*3600,300,"yellow")]
run("C0-blue 恒定600",None,None)
run("ignore 升级不响应(对齐)", "ignore", UPa)
run("comply 全加密(对齐)", "comply", UPa)
run("energy_gate 一次性(对齐)", "energy_gate", UPa)
run("sustain 持续滞回(对齐)", "sustain", UPa)
run("dayfeed 昼夜前馈(对齐)", "dayfeed", UPa)
# 错位相位: t_u 偏移半个新周期 150s, 打破旧600样本对300窗的边界双配
UPm=[(0,600,"blue"),(6*3600+150,300,"yellow")]
run("ignore 升级不响应(错位150)", "ignore", UPm)
run("sustain 持续滞回(错位150)", "sustain", UPm)
run("dayfeed 昼夜前馈(错位150)", "dayfeed", UPm)
