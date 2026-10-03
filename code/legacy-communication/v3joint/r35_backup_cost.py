# -*- coding: utf-8 -*-
"""r35 — C3 真实代价: 中断期北斗短报文备份资费有多少花在注定过期/无效样本上。
中断期(h4-20)主路断, 中心 received 的样本只能经备份(短报文按条/字节计费)。
逐样本: received_at in [4h,20h] 视为经备份; 按其 taken 所属 routine 义务算 deadline
(P=300 h6后 / 600 h6前, deadline=(taken//P+2)P, 半开), 判 on-time / 过期 / 无义务(冗余)。
maxcov 按 deadline 贪心, 槽有空闲时可能填积压过期样本 -> 这部分资费无业务价值,
可行性证书(已知 S_time/过期)可在发送前抑制。
"""
import os, sys, math
_HERE = os.path.dirname(os.path.abspath(__file__)); _CODE = os.path.dirname(_HERE)
for p in [_HERE, _CODE] + [os.path.join(_CODE, d) for d in
        ("physics", "runtime", "experiments", "analysis", "monitoring", "instance")]:
    if p not in sys.path:
        sys.path.insert(0, p)
from collections import Counter
from joint_run import run_joint

UP_ONLY = [(0, 600, "blue"), (6 * 3600, 300, "yellow")]
OUT_LO, OUT_HI = 4 * 3600, 20 * 3600
H6 = 6 * 3600


def deadline_of(taken):
    P = 300 if taken >= H6 else 600
    return (taken // P + 2) * P


r, inst, obligations = run_joint(
    seed=0, task_hours=48, tail_hours=1, arm="local", groups=2,
    sample_interval_s=600, report_period_s=600, routine_period_s=600,
    harvest_mode="solar", harvest_peak_wh_per_hour=0.03, capacity_wh=0.05,
    initial_soc=1.0, outage_start_h=4, outage_hours=16, enable_backup=True,
    backup_rate_s=1200, backup_bytes=78, backup_chooser="maxcov",
    mission_schedule=UP_ONLY, mission_mode="dayfeed", collect_rows=True)

bk = r["backup"]
print("== r35 中断期备份资费有效性 ==")
print(f"backup summary: packets={bk['backup_packets']} records={bk['backup_records']} "
      f"bytes={bk['backup_bytes_sent']} opportunities={bk['backup_opportunities']} "
      f"suppressed={bk['backup_suppressed']}")

# 中断期经备份 received 的样本
ontime = late = 0
late_bytes = ontime_bytes = 0
recv_hour = Counter()
for sid, s in inst.log.samples.items():
    tr = inst.log.transit.get(sid)
    if tr is None or tr.received_at is None:
        continue
    if OUT_LO <= tr.received_at < OUT_HI:
        b = 6 if s.measurand == "displacement" else 4
        dl = deadline_of(s.taken_at)
        recv_hour[tr.received_at // 3600] += 1
        if tr.received_at <= dl:
            ontime += 1; ontime_bytes += b
        else:
            late += 1; late_bytes += b
print(f"\n中断期经备份 received 记录: on-time={ontime} ({ontime_bytes}B), "
      f"过期={late} ({late_bytes}B)")
tot = ontime + late
print(f"过期记录占比(资费浪费上界): {late}/{tot} = {late/max(1,tot):.3f}, "
      f"过期字节 {late_bytes}B / {ontime_bytes+late_bytes}B")
# 每个备份包固定 20B 头也计费; 过期样本若独占/填槽, 连带浪费
print(f"按条计费(含整包头分摊): 若抑制过期样本, 最多省记录 {late} 条; "
      f"短报文常按包计费, 仅当整包皆过期才省包")
# 中断期 received 按小时(看是否集中在恢复边缘/槽空闲填充)
print("中断期备份 received 按小时:", dict(sorted(recv_hour.items())))
