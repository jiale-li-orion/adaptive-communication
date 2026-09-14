"""v2probe 回放引擎自检测试（确定性、不依赖 one_seed，秒级）。

    python3 code/v2probe/test_v2probe.py

覆盖：锚点一致、容量守恒、chooser 排序正确、**不偷看未来**（机会感知只依赖 ≤t 历史）、
速率/K 单调性、主链路已确认不占槽、配对统计方向。退出码非 0 即失败。
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
_CODE = os.path.dirname(_HERE)
for _p in (os.path.join(_CODE, "analysis"), os.path.join(_CODE, "instance")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import backup_model as bm
from stats_util import paired_compare

PASS, FAIL = 0, 0


def check(name: str, cond: bool, detail: str = ""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  {detail}")


def obl(oid, h, dl, primary=False, confirmed=None, release=0, kind="routine"):
    return bm.Obl(oid=oid, kind=kind, release_at=release, deadline=dl, h=h,
                  confirmed_at=confirmed, primary_delivered=primary)


# --------------------------------------------------------------------------- #
def test_anchor_primary_only():
    print("== anchor: primary_only 逐义务 == 主链路台账 ==")
    rows = [obl("a", 0, 900, primary=True), obl("b", 300, 900, primary=False),
            obl("c", None, 900, primary=False)]
    flag = [False, False]
    r = bm.replay(rows, "primary_only", 300, 9, 3600, flag)
    check("final 数 == primary 数", r.n_final_delivered == r.n_primary_delivered == 1)
    check("逐义务相等", r.per_oid == {"a": True, "b": False, "c": False})
    check("从不发包", r.n_packets == 0 and r.n_rescued == 0)
    check("never_heard 计数", r.n_never_heard == 1)


def test_capacity_and_no_regression():
    print("== 容量守恒 / 备用不会减少交付 ==")
    rows = [obl(f"o{i:02d}", 0, 3600) for i in range(10)]
    flag = [False, False]
    for k in (1, 3, 9):
        r = bm.replay(rows, "backup_fifo", 600, k, 3600, flag)
        # 机会 600..3600 共 6 个；每包 ≤K
        check(f"K={k} 总包内发出 == slots", r.n_backup_sent == r.n_slots)
        check(f"K={k} final >= primary", r.n_final_delivered >= r.n_primary_delivered)
        check(f"K={k} rescued+primary==final",
              r.n_rescued + r.n_primary_delivered == r.n_final_delivered)
    # K=1 时每个机会最多救 1 条，6 机会救 6
    r1 = bm.replay(rows, "backup_fifo", 600, 1, 3600, flag)
    check("K=1 × 6 机会救 6", r1.n_rescued == 6, str(r1.n_rescued))


def test_chooser_choice_matters():
    print("== 微缩 P-B：oid 序与紧急度反序时，EDF/机会感知应胜过盲目序 ==")
    # X 紧急(deadline1200) 但 oid 靠后；Y 缓(deadline3600) oid 靠前。
    # 机会 1200/2400/3600，K=1，主链路全程断。
    rows = [obl("z_urgent", 0, 1200), obl("a_slack", 0, 3600)]
    flag = [False, False]  # 主链路全程 down
    r_all = bm.replay(rows, "backup_all", 1200, 1, 3600, flag)
    r_edf = bm.replay(rows, "backup_edf", 1200, 1, 3600, flag)
    r_opp = bm.replay(rows, "backup_opportunity", 1200, 1, 3600, flag)
    check("all(oid序) 只救缓的 1 条", r_all.n_rescued == 1
          and r_all.per_oid["z_urgent"] is False, str(r_all.per_oid))
    check("EDF 两条都救(先救急)", r_edf.n_rescued == 2, str(r_edf.per_oid))
    check("机会感知(主全断→退化为EDF)两条都救", r_opp.n_rescued == 2, str(r_opp.per_oid))


def test_opportunity_no_future_leak():
    print("== 不偷看未来：仅 >t 不同的 up 历史，t 时刻排序必须相同 ==")
    pool = [obl("a", 0, 1800), obl("b", 0, 3000), obl("c", 0, 3600)]
    t = 1200
    f1 = [False, True, True]        # 小时0 down；1,2 up
    f2 = [False, False, False]      # 小时0 与 f1 相同；之后相反
    h1 = bm._history_at(t, f1)
    h2 = bm._history_at(t, f2)
    check("截至 t 的历史聚合相同", (h1.p_up, h1.observed_hours, h1.down_streak_h)
          == (h2.p_up, h2.observed_hours, h2.down_streak_h))
    o1 = [o.oid for o in bm.order_pool("backup_opportunity", list(pool), t, h1)]
    o2 = [o.oid for o in bm.order_pool("backup_opportunity", list(pool), t, h2)]
    check("机会感知排序不依赖未来", o1 == o2, f"{o1} vs {o2}")


def test_monotonicity():
    print("== 单调性：K 越大 / 机会越密，rescued 不减 ==")
    rows = [obl(f"o{i:02d}", 0, 3600) for i in range(12)]
    flag = [False, False]
    base = bm.replay(rows, "backup_edf", 1200, 1, 3600, flag).n_rescued
    big_k = bm.replay(rows, "backup_edf", 1200, 4, 3600, flag).n_rescued
    dense = bm.replay(rows, "backup_edf", 600, 1, 3600, flag).n_rescued
    check("K4 >= K1", big_k >= base, f"{big_k} vs {base}")
    check("rate600 >= rate1200", dense >= base, f"{dense} vs {base}")


def test_failover_gate():
    print("== failover gate：主链路 up 的小时不启用备用 ==")
    rows = [obl("o", 0, 3600, primary=False)]
    # 小时0 主链路 up（机会 600..3000 被 gate），小时1 down（t=3600 启用备用）
    flag = [True, False]
    gated = bm.replay(rows, "backup_edf", 600, 9, 3600, flag, failover_gate=True)
    parallel = bm.replay(rows, "backup_edf", 600, 9, 3600, flag, failover_gate=False)
    check("gate 拦掉 5 个主链路 up 的机会", gated.n_gated_opportunities == 5,
          str(gated.n_gated_opportunities))
    check("gate 下仍在主链路 down 的 3600 救回", gated.n_rescued == 1, str(gated.n_rescued))
    check("并行对照不 gate、首机会即发", parallel.n_gated_opportunities == 0
          and parallel.n_packets == 1)


def test_confirmed_not_in_pool():
    print("== 主链路已确认(≤t) 的义务不再占备用槽 ==")
    rows = [obl("confirmed", 0, 3600, primary=True, confirmed=600),
            obl("need", 0, 3600, primary=False)]
    flag = [False, False]
    r = bm.replay(rows, "backup_edf", 1200, 1, 3600, flag)
    check("只对未确认者发备用", r.n_backup_sent == 1 and r.n_rescued == 1,
          f"sent={r.n_backup_sent} rescued={r.n_rescued}")


def test_expired_and_neverheard():
    print("== 过期不发 / 从不到网关不可救 ==")
    rows = [obl("late", 0, 600),           # 首次机会 1200 已过 deadline
            obl("nh", None, 3600)]
    flag = [False, False]
    r = bm.replay(rows, "backup_edf", 1200, 9, 3600, flag)
    check("过期者不被救", r.per_oid["late"] is False and r.n_rescued == 0)
    check("从不到网关不可救", r.per_oid["nh"] is False and r.n_never_heard == 1)


def test_paired_stats_direction():
    print("== 配对统计方向 ==")
    win = paired_compare([2, 2, 2], [1, 1, 1])
    check("恒定差 1：两区间都排除 0", win["both_exclude_zero"]
          and win["mean_diff"] == 1, str(win))
    tie = paired_compare([1, 2, 3], [1, 2, 3])
    check("完全相同：不排除 0", not tie["bootstrap_excludes_zero"]
          and tie["mean_diff"] == 0)
    cross = paired_compare([2, 0], [0, 2])
    check("互相抵消：均值 0、不排除 0", cross["mean_diff"] == 0
          and not cross["bootstrap_excludes_zero"])


def main():
    test_anchor_primary_only()
    test_capacity_and_no_regression()
    test_chooser_choice_matters()
    test_opportunity_no_future_leak()
    test_monotonicity()
    test_failover_gate()
    test_confirmed_not_in_pool()
    test_expired_and_neverheard()
    test_paired_stats_direction()
    print(f"\nv2probe 自检: PASS={PASS} FAIL={FAIL}")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
