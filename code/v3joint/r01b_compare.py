# -*- coding: utf-8 -*-
"""R01-B 行为对照：遥测单调化(去乱序)对策略行为的影响。False=旧覆盖行为, True=按read_at单调。
fixed* 不据 reports 决策应逐位相同；ea_aoi 据 reports 的 SoC 决策，量化其行为/服务变化。"""
import os,sys,json
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE,_CODE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint
from network import Center

STRESS=dict(task_hours=48,tail_hours=1,outage_start_h=4,outage_hours=16,enable_backup=True,
    backup_rate_s=300,backup_bytes=78,harvest_mode='solar',harvest_peak_wh_per_hour=.005,
    initial_soc=.5,blackout_frac=.3,blackout_start_h=4)

def run(arm,mono):
    Center.monotonic_telemetry=mono
    res,inst,obl=run_joint(seed=0,groups=2,arm=arm,**STRESS)
    rk=res['by_kind']['routine']; ek=res['by_kind'].get('event',{})
    return dict(routine=(rk['delivered'],rk['n']), event=(ek.get('delivered',0),ek.get('n',0)),
        alive=round(res['survival']['alive'],3), mean_final_soc=round(res['survival']['mean_final_soc'],4),
        downlink=res['communication']['downlink_attempts'],
        airtime_s=round(res['communication']['airtime_uplink_h']*3600,1))

out={}
for arm in ('fixed900','ea_aoi'):
    off=run(arm,False); on=run(arm,True)
    out[arm]=dict(off_override=off, on_monotonic=on,
        routine_delta=on['routine'][0]-off['routine'][0],
        alive_delta=round(on['alive']-off['alive'],3))
    print(f"\n{arm}:",flush=True)
    print("  override(旧):",off,flush=True)
    print("  monotonic(新):",on,flush=True)
    print("  Δroutine:",on['routine'][0]-off['routine'][0]," Δalive:",round(on['alive']-off['alive'],3),flush=True)
Center.monotonic_telemetry=False
json.dump(out,open(os.path.join(_CODE,"..","results","v3joint_r01b_telemetry.json"),"w"),indent=1,ensure_ascii=False)
print("\nsaved v3joint_r01b_telemetry.json")
