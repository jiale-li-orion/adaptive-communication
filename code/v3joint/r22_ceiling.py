# -*- coding: utf-8 -*-
"""顺序2 GO/NO-GO 天花板判别: 放宽回传/去中断, 定位端到端硬瓶颈到底在采集还是回传。
dayfeed 错位相位; 全部 0 死亡(能量段已解)。"""
import os,sys
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE,_CODE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint
UP=[(0,600,"blue"),(6*3600+150,300,"yellow")]
def run(tag,**over):
    kw=dict(seed=0,task_hours=48,tail_hours=1,arm="local",groups=2,
        sample_interval_s=600,report_period_s=600,routine_period_s=600,
        harvest_mode="solar",harvest_peak_wh_per_hour=0.03,initial_soc=1.0,
        outage_start_h=4,outage_hours=16,enable_backup=True,
        backup_rate_s=1200,backup_bytes=78,backup_chooser="maxcov",
        mission_schedule=UP,mission_mode="dayfeed")
    kw.update(over)
    r,inst,_=run_joint(**kw); rr=r["routine"]; sv=r["survival"]; b=r["backup"]
    print(f"{tag:42s} svc={rr['delivered']/rr['n']:.4f} missColl={rr.get('missing_collection')} missDeliv={rr.get('missing_delivery')} dead={len(sv['dead'])} rec={b.get('backup_records')}")

run("dayfeed 错位 稀缺备份 r1200/78(基准)")
run("dayfeed 错位 饱和备份 r120/78", backup_rate_s=120, backup_bytes=78)
run("dayfeed 错位 无中断(主路全程 p=.62)", outage_hours=0)
run("dayfeed 错位 无中断+主路完美 p=1", outage_hours=0, backhaul_p_good=1.0, uplink_p_arrive=1.0)
run("dayfeed 错位 饱和备份+主路完美(纯能量天花板)", backup_rate_s=120, backup_bytes=200,
    outage_hours=0, backhaul_p_good=1.0, uplink_p_arrive=1.0)
