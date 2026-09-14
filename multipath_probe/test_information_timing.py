"""信息返回时序探针的最小语义测试。"""
from __future__ import annotations

import os
import sys

import math

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import itertools  # noqa: E402

from env import (BAD_TX_SUCCESS, GOOD_TX_SUCCESS, PATH_SPECS, ROUTINE,  # noqa: E402
                 Trace)
from information_timing import (ARM_SEQ_DEFERRED, STOP_REASONS,  # noqa: E402
                                InformationPolicy, Sample, TimingEnv, run_arm)


def tiny_trace(cell_good=False, sat_good=True, hours=2):
    return Trace(
        seed=17,
        K=2,
        burst="chirpbox",
        T=hours,
        paths=["cellular", "satellite"],
        link_good={
            "cellular": np.array([cell_good] * hours, dtype=bool),
            "satellite": np.array([sat_good] * hours, dtype=bool),
        },
        event_hours={0},
        uav_canceled=set(),
    )


def test_zero_attempt_is_not_evidence():
    env = TimingEnv(tiny_trace())
    env.begin_epoch()
    env.end_epoch()
    assert env.evidence == []


def test_probe_and_data_evidence_are_both_retained():
    env = TimingEnv(tiny_trace(), energy_budget=20.0)
    env.begin_epoch()
    probe = env.attempt("cellular", "probe")
    data = env.attempt("cellular", "data")
    env.end_epoch()
    assert probe is not None and data is not None
    assert [(x.kind, x.t, x.path) for x in env.evidence] == [
        ("probe", 0, "cellular"),
        ("data", 0, "cellular"),
    ]


def test_same_epoch_data_ack_changes_the_next_path_choice():
    trace = tiny_trace(cell_good=False, sat_good=True, hours=1)
    sequential = run_arm(trace, "data_ack", energy_budget=None)
    batch = run_arm(trace, "history_only", energy_budget=None)
    seq_paths = [x["path"] for x in sequential["action_ledger"] if x["kind"] == "data"]
    batch_paths = [x["path"] for x in batch["action_ledger"] if x["kind"] == "data"]
    assert seq_paths[:2] == ["cellular", "satellite"]
    assert batch_paths[:2] == ["cellular", "cellular"]


def test_two_ack_gate_waits_for_two_observations_before_switching():
    trace = tiny_trace(cell_good=False, sat_good=True, hours=1)
    result = run_arm(trace, "data_ack", energy_budget=None, feedback_batch_size=2)
    paths = [x["path"] for x in result["action_ledger"] if x["kind"] == "data"]
    assert paths[:3] == ["cellular", "cellular", "satellite"]


def test_probe_does_not_shift_paired_data_outcome_key():
    trace = tiny_trace(cell_good=True, sat_good=True, hours=1)
    plain = TimingEnv(trace, energy_budget=20.0)
    plain.begin_epoch()
    plain_data = plain.attempt("cellular", "data")

    probed = TimingEnv(trace, energy_budget=20.0)
    probed.begin_epoch()
    probed.attempt("cellular", "probe")
    probed_data = probed.attempt("cellular", "data")
    assert plain_data is not None and probed_data is not None
    assert plain_data.success == probed_data.success
    assert plain_data.draw_key == probed_data.draw_key


def test_paid_probe_is_visible_before_first_data_choice():
    trace = tiny_trace(cell_good=False, sat_good=True, hours=1)
    result = run_arm(trace, "paid_probe", energy_budget=None)
    ledger = result["action_ledger"]
    assert ledger[0]["kind"] == "probe"
    assert ledger[0]["path"] == "cellular"
    assert ledger[1]["kind"] == "data"
    assert ledger[1]["path"] == "satellite"
    assert ledger[0]["returned_before_action_index"] == 1


def test_all_arms_preserve_sample_conservation():
    trace = tiny_trace(hours=4)
    for arm in ("history_only", "data_ack", "paid_probe", "current_truth"):
        result = run_arm(trace, arm, energy_budget=30.0)
        assert result["event_delivered"] + result["missed_event"] == result["event_total"]
        assert result["routine_delivered"] + result["missed_routine"] == result["routine_total"]


def test_run_is_deterministic_and_denominators_are_shared():
    trace = tiny_trace(hours=4)
    first = run_arm(trace, "data_ack", energy_budget=30.0)
    second = run_arm(trace, "data_ack", energy_budget=30.0)
    assert first == second
    denominators = {
        (run_arm(trace, arm, energy_budget=30.0)["event_total"],
         run_arm(trace, arm, energy_budget=30.0)["routine_total"])
        for arm in ("history_only", "data_ack", "paid_probe", "current_truth")
    }
    assert denominators == {(12, 16)}


def test_stop_ledger_is_complete_and_consistent():
    """**P0 停止原因台账**：每个 epoch 恰好一条，且原因码与原始量一致。

    旧读数里「队列空 / 无可用路径 / q 门槛 / 容量 / 配额 / 额度」**六种原因同形**，
    都表现为「没有下一次尝试」。台账把它们分开，并同时保留当时的原始量，
    因此下面可以直接**核对码与量**（而不是相信一个标签）。
    """
    res = run_arm(tiny_trace(hours=3), "data_ack", 20.0)
    rows = res["stop_ledger"]
    assert len(rows) == 3, rows
    assert {r["t"] for r in rows} == {0, 1, 2}
    assert sum(res["stop_reason_counts"].values()) == len(rows)
    for r in rows:
        assert r["reason"] in STOP_REASONS, r
        # 码与量必须自洽
        if r["reason"] == "queue_empty":
            assert r["queue_len"] == 0
        if r["reason"] == "q_threshold":
            assert r["n_eligible"] > 0 and r["n_scored"] == 0 and not r["dropped_q"] is None
        if r["reason"] == "path_capacity":
            assert r["cap_left"], r
        if r["reason"] == "epoch_allowance":
            assert r["allowance"] is not None
        # 台账里的信念是**当时**读到的，必须是合法概率
        for path, value in r["belief"].items():
            assert 0.0 < value < 1.0, (path, value)
    # 一条**反例**：把 q 门槛顶到 1.0 以上，路径存在也会被拒 ⇒ 原因必须是 `q_threshold`
    policy = InformationPolicy("data_ack")
    policy._q = lambda env, path: 0.0
    env = TimingEnv(tiny_trace(hours=1), energy_budget=20.0)
    env.begin_epoch()
    policy.start_epoch(env)
    policy.run_epoch(env)
    reasons = [r["reason"] for r in policy.stop_ledger]
    assert reasons == ["q_threshold"], reasons


def _run_policy(trace, policy, budget):
    """与 `run_arm` 同构地跑一个**现成策略对象**，并带上策略侧诊断字段。"""
    env = TimingEnv(trace, energy_budget=budget)
    for _ in range(trace.T):
        env.begin_epoch()
        policy.start_epoch(env)
        policy.run_epoch(env)
        env.end_epoch()
    res = env.finalize()
    res["deferred_applied"] = policy.deferred_applied
    res["stop_ledger"] = list(policy.stop_ledger)
    return res


def _actions(res):
    return [(r["t"], r["path"], r["kind"], r["success"]) for r in res["action_ledger"]]


def test_deferred_ack_control_defers_but_does_not_discard():
    """**P0 同 epoch「收到 ACK 但延后使用」控制**（doc 58 §P0 第 2 条）。

    两件事必须同时成立，否则这个控制既不是「延后」也不是「同一循环」：

      1. **一个有反馈能力但忽略反馈的策略，必须复现无反馈策略**——
         把 `data_ack`（用反馈）的 `update` 换成空操作后，它的**动作序列**必须与
         `seq_deferred_ack`（同一个逐次循环、ACK 只收不用）**逐位相同**；
      2. **「延后」不等于「丢弃」**：多 epoch 时延后证据必须在下一个 epoch 被并入
         （`deferred_applied > 0`），而 `data_ack` 恒为 0（它当场就用）。
    """
    tr1 = tiny_trace(hours=1)
    ignoring = InformationPolicy("data_ack")
    ignoring.update = lambda evidence: None
    a = _actions(_run_policy(tr1, ignoring, 20.0))
    b = _actions(_run_policy(tr1, InformationPolicy(ARM_SEQ_DEFERRED), 20.0))
    assert a == b, (a, b)
    assert _run_policy(tr1, InformationPolicy(ARM_SEQ_DEFERRED), 20.0)["deferred_applied"] == 0
    tr2 = tiny_trace(hours=2)
    r2 = _run_policy(tr2, InformationPolicy(ARM_SEQ_DEFERRED), 20.0)
    assert r2["deferred_applied"] > 0, r2["deferred_applied"]
    r3 = _run_policy(tr2, InformationPolicy("data_ack"), 20.0)
    assert r3["deferred_applied"] == 0
    # 二者仍然共享同一执行循环：尝试次数的**上界**由同一额度与同一停止条件决定
    assert len(r2["action_ledger"]) >= 1 and len(r3["action_ledger"]) >= 1


def test_two_path_single_datum_delivery_matches_enumeration():
    """**P0 有限状态校验**（doc 58 §P0 第 3 条）：两条路径、**一条**有期限的数据、≤3 次尝试。

    不带任何新的现场含义：链路只有「好 / 坏」两态，单次成功概率是已知常数
    （`GOOD_TX_SUCCESS` / `BAD_TX_SUCCESS`），因此**期望交付可以枚举**：
    在给定的尝试序列下 `P(交付) = 1 − Π(1 − p_i)`，而每个 `p_i` 只有两个取值、
    序列长度 ≤ 3 ⇒ 可能取值只有下面枚举出来的那**少数几个**。

    校验两条：
      1. 每个种子算出来的解析概率**必须落在枚举集合内**（不是近似，是精确）；
      2. 400 个种子的**实际交付率**必须与解析概率的均值一致到二项抽样误差内。
    """
    paths = ("cellular", "satellite")
    enumerated = sorted({1.0 - math.prod(1.0 - p for p in combo)
                         for n in (1, 2, 3)
                         for combo in itertools.product((GOOD_TX_SUCCESS, BAD_TX_SUCCESS),
                                                        repeat=n)})
    # 额度恰好只够 **3 次最便宜的尝试**：`energy_allowance` = 0.75×预算（S=1、`hours_left`=1），
    # 因此预算取 4.0 时额度为 3.0，而 cellular 每次 1.0 ⇒ 最多 3 次。
    budget = 4.0 * PATH_SPECS["cellular"]["energy"]
    analytic, delivered, n_attempts = [], [], []
    for seed in range(400):
        trace = Trace(seed=seed, K=2, burst="chirpbox", T=1, paths=list(paths),
                      link_good={"cellular": np.array([False]), "satellite": np.array([True])},
                      event_hours=set(), uav_canceled=set())
        # 只放**一条**数据：清掉本小时自动到达的样本，替换成一条期限很远的记录
        env = TimingEnv(trace, energy_budget=budget)
        policy = InformationPolicy("data_ack")
        env.begin_epoch()
        env.queue = [Sample("only", 0, ROUTINE, 10, 1)]
        policy.start_epoch(env)
        policy.run_epoch(env)
        env.end_epoch()
        res = env.finalize()
        acts = [r for r in res["action_ledger"] if r["kind"] == "data"]
        prod = 1.0
        for row in acts:
            p = GOOD_TX_SUCCESS if row["true_good"] else BAD_TX_SUCCESS
            prod *= (1.0 - p)
        analytic.append(1.0 - prod)
        delivered.append(res["routine_delivered"])
        n_attempts.append(len(acts))
    assert max(n_attempts) <= 3, n_attempts                    # ≤3 次尝试
    for value in analytic:
        assert any(abs(value - e) < 1e-12 for e in enumerated), (value, enumerated)
    mean_analytic = sum(analytic) / len(analytic)
    mean_delivered = sum(delivered) / len(delivered)
    sd = (0.25 / len(analytic)) ** 0.5                          # 二项方差上界 0.25
    assert abs(mean_analytic - mean_delivered) <= 4 * sd, (mean_analytic, mean_delivered)
    assert 0.0 < mean_delivered < 1.0


def main():
    tests = [obj for name, obj in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"{len(tests)} passed, 0 failed")


if __name__ == "__main__":
    main()
