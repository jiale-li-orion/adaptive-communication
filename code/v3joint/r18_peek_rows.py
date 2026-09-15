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
r,_,_=run_joint(seed=0,groups=2,arm="grid600x600",backup_chooser="cover",**BASE)
rows=r["rows"]; print("n rows",len(rows)); print("keys:",sorted(rows[0].keys()))
for x in rows[:3]: print(x)
