# -*- coding: utf-8 -*-
"""r24 任务变更诊断(doc38 修正后): 在线义务视图门控(h20 才到网关) + 半开独立观测语义。
取代 r22_probe/doc36 中受信息泄漏与闭区间双配影响的数字; 旧 raw 保留、结论以本表为准。
对齐 t_u=h6 现在是干净主口径(半开消除双配); 错位仅作相位敏感性。"""
import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__)); _CODE = os.path.dirname(_HERE)
for p in [_HERE, _CODE] + [os.path.join(_CODE, d) for d in
        ("physics", "runtime", "experiments", "analysis", "monitoring", "instance")]:
    if p not in sys.path:
        sys.path.insert(0, p)
from joint_run import run_joint

BASE = dict(seed=0, task_hours=48, tail_hours=1, arm="local", groups=2,
    sample_interval_s=600, report_period_s=600, routine_period_s=600,
    harvest_mode="solar", harvest_peak_wh_per_hour=0.03, initial_soc=1.0,
    outage_start_h=4, outage_hours=16, enable_backup=True,
    backup_rate_s=1200, backup_bytes=78, backup_chooser="maxcov")


def run(tag, mode, sched):
    kw = dict(BASE)
    if mode is not None:
        kw.update(mission_schedule=sched, mission_mode=mode)
    r, inst, _ = run_joint(**kw)
    rr = r["routine"]; b = r["backup"]; sv = r["survival"]
    dead = [(n.node_id, n.dead_at) for n in inst.nodes.values() if not getattr(n, "alive", True)]
    gw = [t.get("gateway_received_at") for t in r.get("mission_timing", [])]
    print(f"--- {tag} ---")
    print(f"  svc={rr['delivered']/rr['n']:.4f} n={rr['n']} missColl={rr.get('missing_collection')} "
          f"missDeliv={rr.get('missing_delivery')} dead={len(dead)} 末SoC={sv['mean_final_soc']}")
    print(f"  backup rec={b.get('backup_records')} pkt={b.get('backup_packets')} "
          f"refusals={len(r.get('mission_refusals', []))} gw_received_at={gw}")


UPa = [(0, 600, "blue"), (6 * 3600, 300, "yellow")]
run("C0-blue 恒定600(无变更)", None, None)
for m in ("ignore", "comply", "energy_gate", "sustain", "dayfeed"):
    run(f"{m} 升级600->300 对齐h6(半开主口径)", m, UPa)

UPm = [(0, 600, "blue"), (6 * 3600 + 150, 300, "yellow")]
for m in ("ignore", "dayfeed"):
    run(f"{m} 错位h6+150(相位敏感性)", m, UPm)
