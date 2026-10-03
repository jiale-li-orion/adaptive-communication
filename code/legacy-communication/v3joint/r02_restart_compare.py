# -*- coding: utf-8 -*-
"""R02 复机模型敏感性：永久死亡(None) vs 回充复机(mult=2/3/5)。量化主结论对吸收态假设的敏感性。"""
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

def run(arm,mult,cond,collect=False):
    Node.restart_threshold_mult=mult
    kw={} if not collect else {"collect_rows":True}
    res,inst,obl=run_joint(seed=0,groups=2,arm=arm,**cond,**kw)
    rk=res['by_kind']['routine']
    restarts=sum(n.restarts for n in inst.nodes.values())
    out=dict(routine=round(rk['delivered']/rk['n'],4), routine_n=rk['n'],
             alive=round(res['survival']['alive'],3), restarts=restarts,
             final_soc=round(res['survival']['mean_final_soc'],4))
    if collect:
        rows=res.get('rows',[])
        out['collected_frac']=round(sum(r['collected'] for r in rows)/max(1,len(rows)),4)
    Node.restart_threshold_mult=None
    return out

result={"stressed":{},"tight_openloop":{}}
print("=== STRESSED (seed0) ===",flush=True)
for arm in ('fixed900','ea_aoi'):
    result['stressed'][arm]={}
    for mult in (None,2.0,3.0,5.0):
        r=run(arm,mult,STRESS); result['stressed'][arm][str(mult)]=r
        print(f"{arm:9s} mult={str(mult):>4}: {r}",flush=True)
print("\n=== TIGHT openloop fixed900 (R5 反例: 原0存活/末电满/缺采4754) ===",flush=True)
for mult in (None,3.0):
    r=run('fixed900',mult,TIGHT,collect=True); result['tight_openloop'][str(mult)]=r
    print(f"mult={str(mult):>4}: {r}",flush=True)
json.dump(result,open(os.path.join(_CODE,"..","results","v3joint_r02_restart.json"),"w"),indent=1,ensure_ascii=False)
print("\nsaved v3joint_r02_restart.json")
