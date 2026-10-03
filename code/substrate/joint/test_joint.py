#!/usr/bin/env python3
"""test_joint.py — v3joint 联合层的正确性锚点与不变量。

直接运行：`python3 code/substrate/joint/test_joint.py`（也可被 pytest 收集）。
核心是 A0：**关闭备用腿时，联合层必须与封版 v1.1 `one_seed` 逐位一致**——叠加层零副作用，
否则后续任何"联合收益"都可能只是实现差异制造的假象。
"""
from __future__ import annotations

import os as _os, sys as _sys
from types import SimpleNamespace
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, *(_os.path.join(_CODE, d) for d in ("physics", "runtime", "reference",
                                                      "monitoring", "instance"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

from instance_run import one_seed           # noqa: E402
from joint_run import run_joint             # noqa: E402
from joint_plane import JointControlPlane   # noqa: E402
from mission_policy import MissionChangePolicy  # noqa: E402

COMPARE_BLOCKS = ("routine", "event", "communication", "energy")


def _blocks(res):
    return {k: res.get(k) for k in COMPARE_BLOCKS}


# ---------------------------------------------------------------- A0 逐位等价
def test_disabled_backup_bitidentical_to_v11():
    """enable_backup=False 的联合层 == one_seed（groups=2 对齐其写死规模），三种链路态各验。"""
    # 每态给 (one_seed 入参, run_joint 入参)，两者参数名不同处在此显式映射
    states = [
        ({}, {}),
        (dict(outage_start_h=4.0, outage_hours=4.0),
         dict(outage_start_h=4.0, outage_hours=4.0)),
        (dict(access_outage_h=4.0, access_outage_start_h=4.0),
         dict(access_outage_hours=4.0, access_outage_start_h=4.0)),
    ]
    for ref_kw, joint_kw in states:
        for seed in range(3):
            ref = one_seed(seed=seed, task_hours=12, tail_hours=1, arm="local",
                           obligation_ledger=True, **ref_kw)
            got, _, _ = run_joint(seed=seed, task_hours=12, tail_hours=1, arm="local",
                                  groups=2, enable_backup=False, collect_rows=True, **joint_kw)
            for b in COMPARE_BLOCKS:
                assert got[b] == ref[b], f"seed{seed} {ref_kw} block {b} 不一致: {got[b]} vs {ref[b]}"
            # 逐义务台账也必须逐位相同
            assert [ (r["delivered"], r["first_heard_at"], r["first_received_at"])
                     for r in got["rows"]] == \
                   [(r["delivered"], r["first_heard_at"], r["first_received_at"])
                    for r in ref["_obligations"]], f"seed{seed} {ref_kw} 逐义务台账不一致"


# ---------------------------------------------------------------- A1 备用不差（单调）
def test_backup_never_hurts():
    for seed in range(4):
        off, _, _ = run_joint(seed=seed, groups=1, per_group=4, arm="local",
                              outage_start_h=4.0, outage_hours=4.0, enable_backup=False)
        on, _, _ = run_joint(seed=seed, groups=1, per_group=4, arm="local",
                             outage_start_h=4.0, outage_hours=4.0, enable_backup=True)
        assert on["routine"]["delivered"] >= off["routine"]["delivered"]
        assert on["event"]["slots_delivered"] >= off["event"]["slots_delivered"]


# ---------------------------------------------------------------- A2 failover：主路 up 不发备用
def test_failover_silent_when_primary_up():
    # 主回传恒好（p_good=1.0）时 failover 必须全程静默；注意 p_good=.62 的"无外生中断"
    # 仍是间歇链路，随机坏小时启用备用是正确行为，不在此断言。
    r, _, _ = run_joint(seed=0, groups=2, arm="local", backhaul_p_good=1.0,
                        enable_backup=True)
    assert r["backup"]["backup_packets"] == 0, "主回传全程可用时 failover 不应发备用"


# ---------------------------------------------------------------- A3 容量约束
def test_backup_capacity_respected():
    # 净荷容量 = 26-20 = 6B，恰好一条位移样本；每包至多 1 条记录
    r, _, _ = run_joint(seed=0, groups=2, arm="local", outage_start_h=4.0, outage_hours=4.0,
                        enable_backup=True, backup_bytes=26, backup_header_bytes=20)
    b = r["backup"]
    assert b["backup_bytes_sent"] <= b["backup_packets"] * 26
    assert b["backup_records"] >= b["backup_packets"]


# ---------------------------------------------------------------- A4 主备不重复交付
def test_no_duplicate_delivery():
    res, inst, _ = run_joint(seed=1, groups=2, arm="local",
                             outage_start_h=4.0, outage_hours=4.0, enable_backup=True)
    # 网关最终积压里不得残留已被备用取走、又被主路重发的痕迹：总交付不超义务数
    assert res["routine"]["delivered"] <= res["routine"]["n"]
    # 每条 transit 记录至多一个 received_at（HopLog 单值），且收到数=主路+备用记账之和量级一致
    n_recv = sum(1 for t in inst.log.transit.values() if t.received_at is not None)
    assert n_recv >= res["backup"]["backup_records"]


# ---------------------------------------------------------------- A5 deadline equality 仍可发送
def test_backup_deadline_equal_is_still_ontime():
    """发送发生在 deadline 当拍仍可得分；ontime chooser 不能提前一拍判 terminal。"""
    plane = object.__new__(JointControlPlane)
    plane.backup_chooser = "maxcov_ontime"
    plane.sample_bytes = {"displacement": 6}
    plane._cover_seen = set()
    plane._obl_index = {}
    plane.period_s = 600
    sample = SimpleNamespace(sample_id="s0", node_id="n0", measurand="displacement",
                             taken_at=0)
    item = SimpleNamespace(heard_at_s=600, node_id="n0", payload=[sample])
    # Fallback deadline = (floor(0/600)+2)*600 = 1200.  At exactly t=1200,
    # scorer semantics received_at <= deadline still accepts this sample.
    picked, used = plane._cover_family_pack(
        [((1200, 600, "n0"), item, sample, frozenset({"obl0"}))],
        t_s=1200, cap=6)
    assert used == 6, "deadline 当拍仍应允许占用备份包"
    assert [s.sample_id for _it, samples in picked.values() for s in samples] == ["s0"]


# ---------------------------------------------------------------- A6 repair actuator: access assist
def test_access_assist_window_is_bounded_and_audited():
    """接入补强只在声明窗口内绕过强制 outage，并留下时长/命中账。"""
    base, ib, _ = run_joint(
        seed=0, task_hours=10, tail_hours=1, groups=1, per_group=4, arm="local",
        access_outage_start_h=4.0, access_outage_hours=4.0,
        enable_backup=False, collect_rows=True)
    got, ig, _ = run_joint(
        seed=0, task_hours=10, tail_hours=1, groups=1, per_group=4, arm="local",
        access_outage_start_h=4.0, access_outage_hours=4.0,
        access_assist_windows=[(5 * 3600, 6 * 3600)],
        enable_backup=False, collect_rows=True)
    assert got["repair"]["access_assist_duration_s"] == 3600
    assert ig.access_assist_bypassed > 0
    assert ig.access_blocked < ib.access_blocked
    # 这是能力窗口，不是“保证服务单调”的定理；这里只钉住执行语义和审计账。
    assert got["repair"]["backup_boost_duration_s"] == 0


# ---------------------------------------------------------------- A7 repair actuator: backup boost
def test_backup_boost_window_is_bounded_and_audited():
    """备用回传增强只在窗口内换 profile，并单独计增强期包/字节。"""
    got, _ig, _ = run_joint(
        seed=0, task_hours=10, tail_hours=1, groups=1, per_group=4, arm="local",
        outage_start_h=4.0, outage_hours=4.0,
        enable_backup=True, backup_rate_s=1200, backup_bytes=78,
        backup_boost_windows=[(5 * 3600, 6 * 3600)],
        backup_boost_rate_s=60, backup_boost_bytes=100000)
    rep = got["repair"]
    assert rep["backup_boost_duration_s"] == 3600
    assert rep["backup_boost_packets"] > 0
    assert rep["backup_boost_bytes_sent"] > 0
    assert got["backup"]["backup_boost_bytes_sent"] == rep["backup_boost_bytes_sent"]


# ---------------------------------------------------------------- A8 explicit empty windows == default
def test_empty_repair_windows_are_default_semantics():
    """显式空 repair schedule 不得改变任何主评分/通信/能量块。"""
    a, _, _ = run_joint(seed=2, task_hours=8, tail_hours=1, groups=1, per_group=4,
                        arm="local", outage_start_h=3.0, outage_hours=3.0,
                        access_outage_start_h=4.0, access_outage_hours=2.0)
    b, _, _ = run_joint(seed=2, task_hours=8, tail_hours=1, groups=1, per_group=4,
                        arm="local", outage_start_h=3.0, outage_hours=3.0,
                        access_outage_start_h=4.0, access_outage_hours=2.0,
                        access_assist_windows=[], backup_boost_windows=[])
    assert _blocks(a) == _blocks(b)
    assert a["backup"] == b["backup"]


# ------------------------------------------------------ A9 custom mission placement
def test_custom_mission_policy_placement_default_is_center_and_gateway_is_explicit():
    """外部 mission policy 默认仍在 center；显式 gateway placement 才能产生 gateway-origin commands。"""
    schedule = [(0, 3600, "blue"), (4 * 3600, 300, "yellow")]
    common = dict(
        seed=0,
        task_hours=8,
        tail_hours=1,
        groups=1,
        per_group=4,
        arm="local",
        outage_start_h=3.0,
        outage_hours=4.0,
        mission_schedule=schedule,
    )
    implicit, _, _ = run_joint(
        mission_policy_obj=MissionChangePolicy(schedule, mode="comply"),
        **common,
    )
    explicit_center, _, _ = run_joint(
        mission_policy_obj=MissionChangePolicy(schedule, mode="comply"),
        mission_policy_placement="center",
        **common,
    )
    gateway, _, _ = run_joint(
        mission_policy_obj=MissionChangePolicy(schedule, mode="comply"),
        mission_policy_placement="gateway",
        **common,
    )
    assert _blocks(implicit) == _blocks(explicit_center)
    assert implicit["communication"] == explicit_center["communication"]
    assert implicit["command_counters"].get("commands_sent_by_gateway", 0) == 0
    assert explicit_center["command_counters"].get("commands_sent_by_gateway", 0) == 0
    assert gateway["command_counters"].get("commands_sent_by_gateway", 0) > 0


def test_future_task_notice_reaches_gateway_before_effect_without_early_execution():
    """future-effective mission revision may arrive early, but obligation view changes only at effect time."""
    schedule = [(0, 3600, "blue"), (4 * 3600, 300, "yellow")]
    common = dict(
        seed=0,
        task_hours=8,
        tail_hours=1,
        groups=1,
        per_group=4,
        arm="local",
        outage_start_h=3.0,
        outage_hours=4.0,
        mission_schedule=schedule,
        mission_mode="comply",
    )
    base, _, _ = run_joint(**common)
    zero, _, _ = run_joint(mission_notice_lead_s=0, **common)
    assert _blocks(base) == _blocks(zero)
    assert base["mission_timing"] == zero["mission_timing"]
    assert base["mission_transport"] == zero["mission_transport"]

    delegated, _, _ = run_joint(
        mission_gateway_delegate=True,
        mission_notice_lead_s=3 * 3600,
        mission_segment_payload_bytes=32,
        **common,
    )
    timing = delegated["mission_timing"][0]
    assert timing["issued_at"] == 3600
    assert timing["effective_at"] == 4 * 3600
    assert timing["gateway_received_at"] is not None
    assert timing["gateway_received_at"] < timing["effective_at"]
    assert timing["gateway_effective_at"] == timing["effective_at"]
    assert delegated["mission_transport"]["bytes_delivered"] == 32
    assert delegated["command_counters"].get("commands_sent_by_gateway", 0) > 0


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n全部 {len(fns)} 项锚点/不变量通过。")


if __name__ == "__main__":
    _run_all()
