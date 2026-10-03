# -*- coding: utf-8 -*-
"""第一阶相图：采能强度 × 回传中断长度 → 各策略服务/存活，刻画闭环失稳区域。
失稳 = 端到端 AoI/SoC 闭环(ea/eh)相对开环 fixed900 的服务损失；anchor 应在全相空间不劣。"""
import os, sys, json, statistics as st
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint

PEAKS=[0.003,0.005,0.008,0.012,0.020]
OUTAGES=[0,4,8,16,32]
ARMS={"fixed900":("fixed900",True,True),"ea_aoi":("ea_aoi",True,True),
      "eh_aoi":("eh_aoi",True,True),"anchor":("cup",False,True)}
SEEDS=(0,1,2,3)
grid={}
for pk in PEAKS:
  for oh in OUTAGES:
    for name,(arm,uw,gs) in ARMS.items():
      rs=[run_joint(seed=s,groups=2,arm=arm,task_hours=48,tail_hours=1,
                    outage_start_h=4.0,outage_hours=float(oh),
                    enable_backup=True,backup_rate_s=300,backup_bytes=78,
                    harvest_mode="solar",harvest_peak_wh_per_hour=pk,initial_soc=0.5,
                    cup_use_window=uw,cup_gate_sampling=gs)[0] for s in SEEDS]
      grid[f"{pk}|{oh}|{name}"]=dict(
        rout=round(st.mean(r["routine"]["delivered"]/r["routine"]["n"] for r in rs),4),
        alive=round(st.mean(r["survival"]["alive"] for r in rs),2),
        soc=round(st.mean(r["survival"]["mean_final_soc"] for r in rs),3),
        air=round(st.mean(r["communication"]["airtime_uplink_h"]*3600 for r in rs),0))
      print(f"pk={pk} oh={oh:2d} {name:9s} {grid[f'{pk}|{oh}|{name}']}")
out=os.path.join(_CODE,"..","results","v3joint_phase.json")
json.dump(grid,open(out,"w",encoding="utf-8"),ensure_ascii=False,indent=1)
print("saved",out)
# 失稳热图：ea/eh 相对 fixed 的 routine 损失(pp)
print("\n=== ea_aoi 相对 fixed900 的 routine 损失(pp)，行=采能peak，列=中断h ==")
print("peak\\oh "+"".join(f"{o:8d}" for o in OUTAGES))
for pk in PEAKS:
  row=[]
  for oh in OUTAGES:
    base=grid[f"{pk}|{oh}|fixed900"]["rout"]; ea=grid[f"{pk}|{oh}|ea_aoi"]["rout"]
    row.append(f"{(ea-base)*100:8.1f}")
  print(f"{pk:6.3f} "+"".join(row))
print("\n=== eh_aoi 相对 fixed900 的 routine 损失(pp) ===")
print("peak\\oh "+"".join(f"{o:8d}" for o in OUTAGES))
for pk in PEAKS:
  row=[]
  for oh in OUTAGES:
    base=grid[f"{pk}|{oh}|fixed900"]["rout"]
    eh=grid[f"{pk}|{oh}|eh_aoi"]["rout"]
    row.append(f"{(eh-base)*100:8.1f}")
  print(f"{pk:6.3f} "+"".join(row))
