#!/usr/bin/env python3
"""test_joint.py — v3joint 联合层的正确性锚点与不变量。

直接运行：`python3 code/v3joint/test_joint.py`（也可被 pytest 收集）。
核心是 A0：**关闭备用腿时，联合层必须与封版 v1.1 `one_seed` 逐位一致**——叠加层零副作用，
否则后续任何"联合收益"都可能只是实现差异制造的假象。
"""
from __future__ import annotations

import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, *(_os.path.join(_CODE, d) for d in ("physics", "runtime", "experiments",
                                                      "analysis", "monitoring", "instance"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

from instance_run import one_seed           # noqa: E402
from joint_run import run_joint             # noqa: E402

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


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n全部 {len(fns)} 项锚点/不变量通过。")


if __name__ == "__main__":
    _run_all()
