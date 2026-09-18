# -*- coding: utf-8 -*-
"""r37b — 定位 maxcov_ontime 相对 maxcov 少送的 ~8 条中断期 on-time 样本的机制(只读诊断)。
两次 run 同 seed;  diff 中断期经备份、按黄级300 deadline 判 on-time 的样本 sid 集合。
对 maxcov 送了、ontime 没送的样本, 打印 taken/heard/received、黄级d300、网关蓝级d600、
所在备份槽, 以及它在 ontime run 里的最终 transit 状态, 判定是口径错位还是跨包/机会动态。
"""
import os, sys, math
_HERE = os.path.dirname(os.path.abspath(__file__)); _CODE = os.path.dirname(_HERE)
for p in [_HERE, _CODE] + [os.path.join(_CODE, d) for d in
        ("physics", "runtime", "experiments", "analysis", "monitoring", "instance")]:
    if p not in sys.path:
        sys.path.insert(0, p)
from joint_run import run_joint

UP_ONLY = [(0, 600, "blue"), (6 * 3600, 300, "yellow")]
RATE, CAP = 1200, 78
OUT_LO, OUT_HI = 4 * 3600, 20 * 3600
H6 = 6 * 3600
COMMON = dict(seed=0, task_hours=48, tail_hours=1, arm="local", groups=2,
              sample_interval_s=600, report_period_s=600, routine_period_s=600,
              harvest_mode="solar", harvest_peak_wh_per_hour=0.03, capacity_wh=0.05,
              initial_soc=1.0, outage_start_h=4, outage_hours=16, enable_backup=True,
              backup_rate_s=RATE, backup_bytes=CAP,
              mission_schedule=UP_ONLY, mission_mode="dayfeed", collect_rows=True)


def d300(t):
    return (t // 300 + 2) * 300


def d600(t):
    return (t // 600 + 2) * 600


def ontime_set(chooser):
    r, inst, _ = run_joint(backup_chooser=chooser, **COMMON)
    s = {}
    for sid, sx in inst.log.samples.items():
        tr = inst.log.transit.get(sid)
        if tr and tr.received_at is not None and OUT_LO <= tr.received_at < OUT_HI \
                and tr.received_at <= d300(sx.taken_at):
            s[sid] = (sx, tr)
    return r, inst, s


def main():
    rm, im, Sm = ontime_set("maxcov")
    rc, ic, Sc = ontime_set("maxcov_ontime")
    lost = sorted(set(Sm) - set(Sc), key=lambda sid: Sm[sid][1].received_at)
    print(f"maxcov on-time={len(Sm)}, maxcov_ontime on-time={len(Sc)}, 丢失={len(lost)}")
    print(f"maxcov packets={rm['backup']['backup_packets']} bytes={rm['backup']['backup_bytes_sent']}; "
          f"ontime packets={rc['backup']['backup_packets']} bytes={rc['backup']['backup_bytes_sent']}")
    for sid in lost:
        sx, tr = Sm[sid]
        tc = ic.log.transit.get(sid)
        slot = tr.received_at
        print(f"\nsid={sid} node={sx.node_id} m={sx.measurand}")
        print(f"  taken={sx.taken_at} heard={tr.heard_at} maxcov_received={slot} "
              f"d300={d300(sx.taken_at)} d600={d600(sx.taken_at)} 槽%1200={slot%RATE}")
        print(f"  在 ontime run: heard={getattr(tc,'heard_at',None)} "
              f"received={getattr(tc,'received_at',None)} dropped={getattr(tc,'dropped_at',None)}")
        # 该样本在 maxcov 发送槽, 按网关蓝级口径是否已过期?
        print(f"  发送槽相对 d600: 槽-{d600(sx.taken_at)}={slot-d600(sx.taken_at)} "
              f"(负=蓝级仍可救); 相对 d300: {slot-d300(sx.taken_at)} (负=黄级on-time)")


if __name__ == "__main__":
    main()
