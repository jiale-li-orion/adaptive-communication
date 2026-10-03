# -*- coding: utf-8 -*-
import os,sys
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE,_CODE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint
BASE=dict(task_hours=48,tail_hours=1,outage_start_h=4,outage_hours=16,enable_backup=True,
    harvest_mode='solar',harvest_peak_wh_per_hour=.03,initial_soc=1.,blackout_frac=0.,
    sample_interval_s=600,report_period_s=600,routine_period_s=600,
    backup_rate_s=600,backup_bytes=78,collect_rows=True)
def run(ch):
    r,_,_=run_joint(seed=0,groups=2,arm="grid600x600",backup_chooser=ch,**BASE)
    return {x["oid"]:x["first_heard_at"] for x in r["rows"]}
R={ch:run(ch) for ch in ["edf","latest","cover","obligation"]}
ks=set.intersection(*[set(v) for v in R.values()])
import itertools
for a,b in itertools.combinations(R,2):
    same=sum(1 for k in ks if R[a][k]==R[b][k])
    print(f"heard一致 {a:10s} vs {b:10s}: {same}/{len(ks)} = {same/len(ks):.3f}")
