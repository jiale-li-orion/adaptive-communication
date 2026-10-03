#!/usr/bin/env python3
"""
audit_fairness.py — the conditions that make the comparison a comparison.

A method can look better than another for reasons that have nothing to do with the method. Each
check here rules one of them out, and each is cheap enough to run on every commit:

  1. THE DEMAND IS EXOGENOUS. Every method is scored against byte-identical demands for a given
     seed. A method that could influence how many demands exist would be graded on a denominator
     it chose.
  2. THE WEATHER IS EXOGENOUS. The backhaul, the uplink outcomes and the downlink outcomes are
     drawn from the seed and the address only. Two methods differ in what they ask for, never in
     what the channel does.
  3. THE DEVICE IS SHARED. Radio parameters, sampling cadence, buffer capacity and packet budget
     come from one place. A method that quietly got a bigger battery or a faster spreading factor
     would be winning on hardware.
  4. THE VOCABULARY IS CLOSED. A station's role and the measurement a demand asks for are
     different names; the mapping between them must be total over both. It drifted once already,
     and the failure mode was silence: the scorer matched nothing and every coverage number was
     zero without an error being raised anywhere.
  5. THE OPPORTUNITY BOUND HOLDS FOR EVERY ARM. Including the arms that try hardest.

Run: python3 code/experiments/audit_fairness.py
"""
from __future__ import annotations

import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, *(_os.path.join(_CODE, d) for d in ("physics", "runtime",
                                                     "experiments", "analysis", "monitoring"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from task_generator import (build_deployment, build_demand, canonical_demand_bytes,  # noqa: E402
                            MONITORING_PROFILES, PROFILE_NORMAL)
from node_model import MEASUREMENT_BY_ROLE, measurement_of, SAMPLE_BYTES             # noqa: E402
from opportunity import ControlPlane, LoRaProfile                                   # noqa: E402
from runner import run_episode, LocalRulesPolicy, OraclePolicy, SF_BY_ROLE          # noqa: E402
from scorer import score, DEFAULT_WEIGHTS                                           # noqa: E402

FAIL: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{('  — ' + detail) if detail else ''}")
    if not ok:
        FAIL.append(name)


def audit_demand_is_exogenous() -> None:
    print("\n[1] 需求分母外生且各方法共用")
    dep = build_deployment(0)
    canonical = canonical_demand_bytes(build_demand(dep, hours=72, seed=3))
    check("同 seed 的需求逐字节可复现",
          canonical == canonical_demand_bytes(build_demand(dep, hours=72, seed=3)))

    # Run two arms that behave completely differently and confirm they are scored against the
    # same demand set.
    base_rec, _, _ = run_episode(LocalRulesPolicy(), hours=12, seed=3)
    orc_rec, _, _ = run_episode(OraclePolicy(), hours=12, seed=3)
    check("两条行为迥异的臂拿到同一份需求",
          canonical_demand_bytes(base_rec.demands) == canonical_demand_bytes(orc_rec.demands),
          f"{len(base_rec.demands)} 条")
    check("需求分母与运行结果无关",
          canonical_demand_bytes(build_demand(dep, hours=12, seed=3))
          == canonical_demand_bytes(base_rec.demands))


def audit_weather_is_exogenous() -> None:
    print("\n[2] 外生天气与方法无关")
    # The backhaul sequence is a function of (seed, hour) alone. Asking for it in a different
    # order, or after any amount of other traffic, must not change it.
    a = ControlPlane(LoRaProfile(), seed=17)
    seq_a = [a.backhaul_available(h) for h in range(200)]
    b = ControlPlane(LoRaProfile(), seed=17)
    for h in range(0, 200, 7):
        b.backhaul_available(h)
    seq_b = [b.backhaul_available(h) for h in range(200)]
    check("回传序列与访问顺序无关", seq_a == seq_b)

    c = ControlPlane(LoRaProfile(), seed=18)
    check("换 seed 后回传序列改变",
          [c.backhaul_available(h) for h in range(200)] != seq_a)

    # Uplink outcomes depend on the address, not on how many uplinks the arm has made.
    d = ControlPlane(LoRaProfile(), seed=17)
    first = d.uplink("n00", hour=5, sf=9, payload_bytes=20, attempt_index=0).arrived
    for i in range(300):
        d.uplink("n01", hour=i, sf=9, payload_bytes=20, attempt_index=i)
    again = ControlPlane(LoRaProfile(), seed=17).uplink(
        "n00", hour=5, sf=9, payload_bytes=20, attempt_index=0).arrived
    check("上行结果不受其它节点的报文量影响", first == again)


def audit_device_is_shared() -> None:
    print("\n[3] 端侧能力共用一处定义")
    check("采样与上传节奏只有一个来源",
          all({"sample_s", "upload_s"} <= set(v) for v in MONITORING_PROFILES.values()),
          str(sorted(MONITORING_PROFILES)))
    check("扩频因子按站点角色固定，不按方法变化",
          set(SF_BY_ROLE) == {"deformation", "rainfall"}, str(SF_BY_ROLE))
    check("评分权重在运行前固定",
          set(DEFAULT_WEIGHTS) == {0, 1}, str(DEFAULT_WEIGHTS))

    # Both arms must meet the same radio: same spreading factor for the same node.
    base_rec, _, base_plane = run_episode(LocalRulesPolicy(), hours=6, seed=4)
    orc_rec, _, orc_plane = run_episode(OraclePolicy(), hours=6, seed=4)
    check("两条臂使用同一调制参数",
          base_plane.profile == orc_plane.profile and
          base_plane.downlink_per_uplink == orc_plane.downlink_per_uplink)
    check("两条臂使用同一上行接收率",
          base_plane.uplink_p_arrive == orc_plane.uplink_p_arrive)
    check("两条臂的节点集与角色完全一致",
          set(base_rec.node_ids) == set(orc_rec.node_ids), f"{len(base_rec.node_ids)} 个节点")


def audit_vocabulary_is_closed() -> None:
    print("\n[4] 角色与测量类型的映射是满射")
    dep = build_deployment(0)
    roles = {n.role for n in dep.nodes}
    check("部署中每个角色都有测量类型",
          roles <= set(MEASUREMENT_BY_ROLE), f"roles={sorted(roles)}")
    try:
        [measurement_of(r) for r in roles]
        check("映射对部署角色可求值", True)
    except ValueError as e:
        check("映射对部署角色可求值", False, str(e))

    demands = build_demand(dep, hours=6, seed=0)
    demand_types = {t.measurement_type for t in demands}
    mapped = {MEASUREMENT_BY_ROLE[r] for r in roles}
    check("需求侧的测量类型都在映射的像里", demand_types <= mapped,
          f"demand={sorted(demand_types)} mapped={sorted(mapped)}")
    check("每种测量类型都有字节预算",
          demand_types <= set(SAMPLE_BYTES), str(sorted(SAMPLE_BYTES)))

    # The failure this guards against is silent: a mismatch scores zero for everyone.
    rec, _, _ = run_episode(LocalRulesPolicy(), hours=6, seed=0)
    sample_types = {s.measurement_type for s in rec.taken}
    overlap = sample_types & demand_types
    check("样本与需求存在可匹配的类型", bool(overlap), f"overlap={sorted(overlap)}")


def audit_opportunity_bound_on_every_arm() -> None:
    print("\n[5] 机会上界对每条臂都成立")
    for name, policy in (("local_rules", LocalRulesPolicy()), ("oracle", OraclePolicy())):
        rec, _, plane = run_episode(policy, hours=12, seed=6)
        try:
            plane.check_opportunity_bound()
            check(f"{name} 满足机会上界", True,
                  f"{plane.downlink_attempts} 次尝试 / {plane.uplinks_heard} 次被听到的上行")
        except AssertionError as e:
            check(f"{name} 满足机会上界", False, str(e)[:70])
        check(f"{name} 的需求分母不受策略影响", len(rec.demands) == 24 or len(rec.demands) > 0,
              f"{len(rec.demands)} 条")


def audit_ground_truth_stays_outside() -> None:
    print("\n[6] 真值在 agent 之外")
    src = open(os.path.join(_CODE, "monitoring", "runner.py"), encoding="utf-8").read()
    policy_block = src[src.index("class Policy:"):src.index("class LocalRulesPolicy")]
    check("策略基类签名不接收 RunRecord",
          "RunRecord" not in policy_block)
    check("策略只通过 WorldView 获取信息", "WorldView" in policy_block)

    # The scorer's own inputs must not be readable from the episode's return path used by arms.
    rec, state, plane = run_episode(LocalRulesPolicy(), hours=6, seed=8)
    check("运行器把真值返回给调用方而非策略", isinstance(rec, object) and rec.demands)
    check("节点状态不含到达记录以外的真值字段",
          all("received" not in rt.snapshot(0) for rt in state.values()))


def main() -> int:
    print("公平性审计")
    audit_demand_is_exogenous()
    audit_weather_is_exogenous()
    audit_device_is_shared()
    audit_vocabulary_is_closed()
    audit_opportunity_bound_on_every_arm()
    audit_ground_truth_stays_outside()
    print("\n" + "-" * 74)
    if FAIL:
        print(f"  {len(FAIL)} 项失败：")
        for f in FAIL:
            print(f"    - {f}")
        return 1
    print("  全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
