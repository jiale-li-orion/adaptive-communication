# -*- coding: utf-8 -*-
"""R02 四类损失分列：缺采 / 采到未到网关 / 晚到网关 / 准时到网关但晚到中心 / 准时交付。
用 collect_rows 的首次到达台账，按失败最早阶段互斥归类。对比永久死亡 vs 复机。"""
import os,sys,json
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE,_CODE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint
from network import Node

STRESS=dict(task_hours=48,tail_hours=1,outage_start_h=4,outage_hours=16,enable_backup=True,
    backup_rate_s=300,backup_bytes=78,harvest_mode='solar',harvest_peak_wh_per_hour=.005,
    initial_soc=.5,blackout_frac=.3,blackout_start_h=4)
TIGHT=dict(task_hours=48,tail_hours=1,outage_start_h=4,outage_hours=16,enable_backup=True,
    backup_rate_s=300,backup_bytes=78,harvest_mode='solar',harvest_peak_wh_per_hour=.03,
    initial_soc=1.,blackout_frac=0.,sample_interval_s=300,report_period_s=300,routine_period_s=300)
CATS=["delivered_on_time","missing_sample(缺采)","collected_never_gateway(采到未到网关)",
      "late_to_gateway(晚到网关)","gw_ontime_backhaul_late(到网关准时但回传晚)"]
def classify(arm,mult,cond):
    Node.restart_threshold_mult=mult
    res,inst,obl=run_joint(seed=0,groups=2,arm=arm,collect_rows=True,**cond)
    Node.restart_threshold_mult=None
    cnt={c:0 for c in CATS}
    for r in res["rows"]:
        if r.get("received_on_time"): cnt[CATS[0]]+=1
        elif not r["collected"]: cnt[CATS[1]]+=1
        elif r.get("first_heard_at") is None: cnt[CATS[2]]+=1
        elif not r.get("heard_on_time"): cnt[CATS[3]]+=1
        else: cnt[CATS[4]]+=1
    n=len(res["rows"]); alive=round(res["survival"]["alive"],2)
    return dict(n=n,alive=alive,**{c:f"{cnt[c]}({100*cnt[c]/n:.1f}%)" for c in CATS})
cases=[("STRESSED fixed900 永久死亡","fixed900",None,STRESS),
       ("STRESSED ea_aoi 永久死亡","ea_aoi",None,STRESS),
       ("TIGHT fixed900 永久死亡","fixed900",None,TIGHT),
       ("TIGHT fixed900 复机mult3","fixed900",3.0,TIGHT)]
out={}
for tag,arm,mult,cond in cases:
    r=classify(arm,mult,cond); out[tag]=r
    print(f"\n{tag}  n={r['n']} alive={r['alive']}",flush=True)
    for c in CATS: print(f"   {c:42s}{r[c]}",flush=True)
json.dump(out,open(os.path.join(_CODE,"..","results","v3joint_r02_loss_split.json"),"w"),indent=1,ensure_ascii=False)
print("\nsaved v3joint_r02_loss_split.json")
