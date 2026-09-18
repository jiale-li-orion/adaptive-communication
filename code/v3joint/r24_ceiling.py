# -*- coding: utf-8 -*-
"""r24 资源诊断(修复后口径, doc38 §1): 固定 dayfeed 策略、只放宽通信/能量条件。
注意: 这是"**dayfeed 这一条策略**在逐步宽松条件下的表现", 不是联合最优或采集物理上界
(doc38 §1): 它不改变采样/上报策略, 缺采若仍在即说明 dayfeed 本身没解决采集, 但不能
据此断言别的采样/联合策略也只能做到这些。对齐 h6 半开主口径。"""
import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__)); _CODE = os.path.dirname(_HERE)
for p in [_HERE, _CODE] + [os.path.join(_CODE, d) for d in
        ("physics", "runtime", "experiments", "analysis", "monitoring", "instance")]:
    if p not in sys.path:
        sys.path.insert(0, p)
from joint_run import run_joint
UP = [(0, 600, "blue"), (6 * 3600, 300, "yellow")]


def run(tag, **over):
    kw = dict(seed=0, task_hours=48, tail_hours=1, arm="local", groups=2,
        sample_interval_s=600, report_period_s=600, routine_period_s=600,
        harvest_mode="solar", harvest_peak_wh_per_hour=0.03, initial_soc=1.0,
        outage_start_h=4, outage_hours=16, enable_backup=True,
        backup_rate_s=1200, backup_bytes=78, backup_chooser="maxcov",
        mission_schedule=UP, mission_mode="dayfeed")
    kw.update(over)
    r, inst, _ = run_joint(**kw); rr = r["routine"]; sv = r["survival"]; b = r["backup"]
    print(f"{tag:46s} svc={rr['delivered']/rr['n']:.4f} missColl={rr.get('missing_collection')} "
          f"missDeliv={rr.get('missing_delivery')} dead={len(sv['dead'])} rec={b.get('backup_records')}")


run("dayfeed 对齐 稀缺备份 r1200/78(基准)")
run("dayfeed 对齐 饱和备份 r120/78", backup_rate_s=120, backup_bytes=78)
run("dayfeed 对齐 无中断(主路 p=.62)", outage_hours=0)
run("dayfeed 对齐 无中断+主路完美 p=1", outage_hours=0, backhaul_p_good=1.0, uplink_p_arrive=1.0)
run("dayfeed 对齐 饱和备份+主路完美", backup_rate_s=120, backup_bytes=200,
    outage_hours=0, backhaul_p_good=1.0, uplink_p_arrive=1.0)
