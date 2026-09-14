"""信息返回时序探针的最小语义测试。"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from env import Trace  # noqa: E402
from information_timing import InformationPolicy, TimingEnv, run_arm  # noqa: E402


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


def main():
    tests = [obj for name, obj in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"{len(tests)} passed, 0 failed")


if __name__ == "__main__":
    main()
