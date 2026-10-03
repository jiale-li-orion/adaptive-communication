# -*- coding: utf-8 -*-
"""D 反事实时间线：同一节点在 ea_aoi/eh_aoi/anchor/fixed 下的档位-电量-存活轨迹。"""
import os, sys
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint

COND=dict(task_hours=48,tail_hours=1,outage_start_h=4.0,outage_hours=16.0,
          enable_backup=True,backup_rate_s=300,backup_bytes=78,
          harvest_mode="solar",harvest_peak_wh_per_hour=0.005,
          initial_soc=0.5,blackout_frac=0.3,blackout_start_h=4.0,trace=True)
ARMS={"ea_aoi":("ea_aoi",True,True),"eh_aoi":("eh_aoi",True,True),
      "anchor":("cup",False,True),"fixed900":("fixed900",True,True)}

def hourly_track(inst, nid):
    # state 事件: (t,nid,'state',sample_interval,report_period,soc,alive)
    last={}
    for ev in inst.trace_events:
        if ev[2]!="state" or ev[1]!=nid: continue
        h=ev[0]//3600
        last[h]=(ev[3],ev[4],ev[6],ev[5])   # si, rp, alive, soc
    return last

# 找一个 ea_aoi 下死亡的节点
target=None
for s in range(6):
    r,inst,_=run_joint(seed=s,groups=2,arm="ea_aoi",**COND)
    if r["survival"]["dead"]:
        target=(s,r["survival"]["dead"][0]); break
print("选定 seed,node =",target)
seed,nid=target
tracks={}
for name,(arm,uw,gs) in ARMS.items():
    r,inst,_=run_joint(seed=seed,groups=2,arm=arm,cup_use_window=uw,cup_gate_sampling=gs,**COND)
    tracks[name]=hourly_track(inst,nid)
    dense=sum(1 for h,v in tracks[name].items() if v[0]==600)
    print(f"\n== {name}: dense600 小时数={dense}, final alive={r['survival']['alive']:.1f}, "
          f"该节点末态={tracks[name].get(48)}")
print("\n小时  中断  | ea_aoi(si,rp,soc,alive)            eh_aoi                         anchor                         fixed900")
for h in range(0,49,2):
    def fmt(t):
        v=t.get(h)
        return "—" if not v else f"{v[0]}/{v[1]} s{v[3]*1e3:05.1f}mWh a{int(v[2])}"
    flag = "DOWN" if 4<=h<20 else " up "
    print(f"h{h:02d} {flag} | {fmt(tracks['ea_aoi']):>30} | {fmt(tracks['eh_aoi']):>28} | {fmt(tracks['anchor']):>28} | {fmt(tracks['fixed900']):>20}")
