# -*- coding: utf-8 -*-
"""R01 重放：earliest(修复后官方) vs last(旧覆盖口径) 两套评分对比；证明只改评分、不改轨迹。
旁路记录每个 sample 最后一次 heard/received(复刻旧覆盖行为)，运行后用 last 重评得旧口径。"""
import os, sys, copy, json
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE,_CODE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint
from network import Center, Instance
from scoring import evaluate

def replay(arm, cond):
    last_h, last_r = {}, {}
    orig_recv = Center.receive; orig_heard = Instance._note_gateway_heard
    def recv(self,item,t):
        for s in item.payload or (): last_r[s.sample_id]=t      # 覆盖=旧口径
        return orig_recv(self,item,t)
    def heard(self,node,t,batch):
        for s in batch: last_h[s.sample_id]=t
        return orig_heard(self,node,t,batch)
    Center.receive, Instance._note_gateway_heard = recv, heard
    try:
        res,inst,obl = run_joint(seed=0,groups=2,arm=arm,collect_rows=True,**cond)
    finally:
        Center.receive, Instance._note_gateway_heard = orig_recv, orig_heard
    H = cond['task_hours']+cond.get('tail_hours',1)
    # 新官方口径=修复后 earliest（res 即此）。构造 last 口径 log 重评。
    lastlog = copy.copy(inst.log)
    lastlog.transit = {sid: copy.copy(tr) for sid,tr in inst.log.transit.items()}
    for sid,tr in lastlog.transit.items():
        if sid in last_h: tr.heard_at = last_h[sid]
        if sid in last_r: tr.received_at = last_r[sid]
    old = evaluate(obl, lastlog, H, inst.nodes.keys(), task_hours=cond['task_hours'])
    def routine(ev):
        rk=ev['by_kind']['routine']; return rk['delivered'], rk['n']
    def event(ev):
        ek=ev['by_kind'].get('event',{}); return ek.get('delivered',0), ek.get('n',0)
    nr,ntot = routine(res); or_,otot = routine(old)
    ne,net_ = event(res); oe,oet = event(old)
    n_override = sum(1 for sid,tr in inst.log.transit.items()
                     if (sid in last_h and last_h[sid]!=tr.heard_at)
                     or (sid in last_r and last_r[sid]!=tr.received_at))
    return dict(arm=arm, cond={k:cond[k] for k in ('harvest_peak_wh_per_hour','initial_soc','blackout_frac','outage_hours')},
        routine_earliest_new=(nr,ntot), routine_last_old=(or_,otot), routine_changed=nr-or_,
        event_earliest_new=(ne,net_), event_last_old=(oe,oet),
        samples_with_overridden_arrival=n_override,
        survival=res['survival'], downlink=res['communication']['downlink_attempts'],
        airtime_s=round(res['communication']['airtime_uplink_h']*3600,1),
        note='same run; earliest vs last differ only in scoring; survival/command/airtime identical by construction')

STRESS=dict(task_hours=48,tail_hours=1,outage_start_h=4,outage_hours=16,enable_backup=True,
    backup_rate_s=300,backup_bytes=78,harvest_mode='solar',harvest_peak_wh_per_hour=.005,
    initial_soc=.5,blackout_frac=.3,blackout_start_h=4)
TIGHT=dict(task_hours=48,tail_hours=1,outage_start_h=4,outage_hours=16,enable_backup=True,
    backup_rate_s=300,backup_bytes=78,harvest_mode='solar',harvest_peak_wh_per_hour=.03,
    initial_soc=1.,blackout_frac=0.,sample_interval_s=300,report_period_s=300,routine_period_s=300)
out=[]
for arm,cond in [('fixed900',STRESS),('ea_aoi',STRESS),('fixed900',TIGHT)]:
    r=replay(arm,cond); out.append(r)
    print(f"{arm:9s} {'TIGHT' if cond is TIGHT else 'STRESS'} routine new(earliest)={r['routine_earliest_new']} "
          f"old(last)={r['routine_last_old']} Δ={r['routine_changed']:+d} event {r['event_earliest_new']}vs{r['event_last_old']} "
          f"overridden={r['samples_with_overridden_arrival']} alive={r['survival']['alive']:.2f}",flush=True)
json.dump(out,open(os.path.join(_CODE,"..","results","v3joint_r01_replay.json"),"w"),indent=1,ensure_ascii=False)
print("saved v3joint_r01_replay.json")
