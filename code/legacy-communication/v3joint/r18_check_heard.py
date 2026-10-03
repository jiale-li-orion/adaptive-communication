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
    return {x["oid"]:(x["first_heard_at"],x["n_heard"],x["deadline"],x["release_at"]) for x in r["rows"]}
A=run("edf"); B=run("cover"); C=run("latest")
keys=set(A)&set(B)&set(C)
same=sum(1 for k in keys if A[k]==B[k]==C[k])
print(f"义务数={len(keys)}  heard/n_heard/deadline/release 三者完全一致: {same}/{len(keys)}")
diff=[k for k in keys if not(A[k]==B[k]==C[k])]
for k in diff[:5]: print(" diff",k,"edf",A[k],"cover",B[k],"latest",C[k])
