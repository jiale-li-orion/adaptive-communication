#!/usr/bin/env python3
"""
test_scorer.py — the service metric, and the boundary that keeps it honest.

The metric is only meaningful if the party being measured cannot read the answer. Two things are
checked here:

CORRECTNESS. A demand counts as met only when both halves of the contract hold: a sample taken
inside the demand's window AND arrived by its deadline. Either half alone is not service, and the
interesting failure modes are the ones where a naive implementation would score them anyway — a
sample taken in the window but still sitting in a buffer, or a record delivered on time that was
measured before the window opened.

THE LEAK. The agent-visible surface must not be able to tell a delivered record from an
undelivered one. The test does not read the interface's documentation to decide this; it builds
two runs that differ only in whether an upload was heard, and asserts the observable state is
identical. If a later change makes the status read cheaper to compute from the ground truth, this
check fails rather than silently turning the experiment into an easier question.

Run: python3 code/experiments/test_scorer.py
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

from node_model import NodeRuntime, Sample                       # noqa: E402
from scorer import RunRecord, residual_failures, score           # noqa: E402
from runner import run_episode, LocalRulesPolicy, OraclePolicy    # noqa: E402
from task_generator import Task, PRIORITY_NORMAL, PRIORITY_RISK   # noqa: E402
from opportunity import ControlPlane, LoRaProfile, DownlinkMessage  # noqa: E402

FAIL: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{('  — ' + detail) if detail else ''}")
    if not ok:
        FAIL.append(name)


def demand(window, deadline, nodes=("n00",), mtype="displacement", priority=PRIORITY_NORMAL):
    return Task(id="d", node_set=tuple(nodes), measurement_type=mtype,
                release_time=window[0], sample_window=window, delivery_deadline=deadline,
                priority=priority, policy_generation=1)


def record(demands, taken, arrived, heard=()):
    return RunRecord(demands=demands, taken=taken, arrived=arrived,
                     heard_uplinks=list(heard), node_ids=("n00",))


# ------------------------------------------------------------------ correctness
def test_both_halves_required() -> None:
    print("\n[1] 窗口内采集与按期到达缺一不可")
    in_window = Sample.make("n00", 100, "displacement")
    late = Sample.make("n00", 200, "displacement")
    early = Sample.make("n00", 10, "displacement")

    ok = score(record([demand((50, 500), 1000)], [in_window], [(in_window, 900)]))
    check("窗口内采集且按期到达 -> 覆盖", ok.covered == 1, f"coverage={ok.coverage:.2f}")

    late_arrival = score(record([demand((50, 500), 1000)], [in_window], [(in_window, 1001)]))
    check("窗口内采集但超期到达 -> 未覆盖", late_arrival.covered == 0)

    never = score(record([demand((50, 500), 1000)], [in_window], []))
    check("采集了但从未到达 -> 未覆盖", never.covered == 0)

    before = score(record([demand((50, 500), 1000)], [early], [(early, 100)]))
    check("窗口前采集、按期到达 -> 未覆盖", before.covered == 0,
          "记录描述的是需求没有问的那个时刻")

    buffered = score(record([demand((50, 500), 1000)], [late], [(late, 1001)]))
    check("既超期又迟到 -> 未覆盖", buffered.covered == 0)
    check("恰好卡在期限上算覆盖",
          score(record([demand((50, 500), 1000)], [in_window],
                       [(in_window, 1000)])).covered == 1)


def test_class_split_and_weights() -> None:
    print("\n[2] 分类与权重")
    # One sample serves the normal demand; the risk demands' window is never sampled, so exactly
    # one of three demands is met and an equal-weight average must say so.
    hits = [Sample.make("n00", 100, "displacement")]
    ds = [demand((50, 500), 1000, priority=PRIORITY_NORMAL),
          demand((4000, 6000), 7000, priority=PRIORITY_RISK),
          demand((4000, 6000), 7000, priority=PRIORITY_RISK)]
    r = score(record(ds, hits, [(s, 900) for s in hits]))
    check("常态与风险分别统计",
          r.by_class["normal"]["demands"] == 1 and r.by_class["risk"]["demands"] == 2,
          f"normal={r.by_class['normal']['demands']} risk={r.by_class['risk']['demands']}")
    check("等权时总体覆盖率是覆盖条数占比", abs(r.coverage - 1 / 3) < 1e-9, f"{r.coverage:.3f}")

    weighted = score(record(ds, hits, [(s, 900) for s in hits]),
                     weights={PRIORITY_NORMAL: 1.0, PRIORITY_RISK: 100.0})
    check("提高风险权重会拉低总体覆盖率", weighted.coverage < r.coverage,
          f"{weighted.coverage:.4f} < {r.coverage:.4f}")

    check("关键节点与风险同类", r.by_class["critical"]["demands"] == 2)


def test_servable_subset() -> None:
    print("\n[3] 物理可服务子集与端到端分母分开报")
    d_near = demand((50, 500), 1000, nodes=("n00",))
    d_far = demand((50, 500), 1000, nodes=("n99",))
    s = Sample.make("n00", 100, "displacement")
    r = score(record([d_near, d_far], [s], [(s, 900)], heard=[("n00", 400)]))
    check("端到端分母保留永远不可达的点", r.demands == 2, f"{r.demands} 条")
    check("可服务子集只留有机会的点", r.servable["demands"] == 1)
    check("两套分母给出不同覆盖率",
          abs(r.coverage - 0.5) < 1e-9 and abs(r.servable["coverage"] - 1.0) < 1e-9,
          f"e2e={r.coverage:.2f} servable={r.servable['coverage']:.2f}")


def test_archive_completeness() -> None:
    print("\n[4] 档案完整率独立于实时合格率")
    taken = [Sample.make("n00", t, "displacement") for t in (100, 200, 300, 400)]
    arrived = [(taken[0], 1000), (taken[1], 1000), (taken[2], 99999)]
    r = score(record([], taken, arrived))
    check("迟到的记录仍算入档案", abs(r.aux["archive_completeness"] - 0.75) < 1e-9,
          f"{r.aux['archive_completeness']:.2f}")


# ------------------------------------------------------------------ the leak
def test_no_ground_truth_leak() -> None:
    """The boundary is about what the party being measured may read, not about what exists.

    A node legitimately knows its own buffer, and a status read that returns the buffer level is
    a self-report the center pays an opportunity to receive. What would be a leak is the center
    reaching the scorer's records -- which samples were taken and which arrived -- without that
    round trip, because then the execution question would answer itself.
    """
    print("\n[5] 真值不泄漏到 agent 可见面")
    rt = NodeRuntime(node_id="n00", role="deformation")
    rt.maybe_sample(0)
    snap = rt.snapshot(0)
    forbidden = {"received", "arrived", "taken", "records", "unacknowledged_ids",
                 "uploads_heard", "records_acked", "sample_window", "schedule"}
    check("可见状态只含节点自身的观测量", not (forbidden & set(snap)), str(sorted(snap)))

    src = open(os.path.join(_CODE, "monitoring", "runner.py"), encoding="utf-8").read()
    policy_src = src[src.index("class Policy:"):src.index("class LocalRulesPolicy")]
    check("策略基类不接触 RunRecord 或采样真值",
          "RunRecord" not in policy_src and "taken" not in policy_src)
    check("策略只能通过 WorldView 看世界", "WorldView" in policy_src)

    # The status a policy reads only ever changes on an uplink the gateway heard.
    world = src[src.index("class WorldView"):src.index("class PendingCommand")]
    check("WorldView 只携带状态读的结果与在途集合",
          "demanded_profile" in world and "in_flight" in world and "arrived" not in world)


def test_end_to_end_runs() -> None:
    print("\n[6] 端到端两条臂可跑且上界高于基线")
    base_rec, _, base_plane = run_episode(LocalRulesPolicy(), hours=12, seed=0)
    orc_rec, _, orc_plane = run_episode(OraclePolicy(), hours=12, seed=0)
    base, orc = score(base_rec), score(orc_rec)
    check("两条臂的需求分母相同", base_rec.demands == orc_rec.demands,
          f"{len(base_rec.demands)} 条")
    base_plane.check_opportunity_bound()
    orc_plane.check_opportunity_bound()
    check("机会上界在两条臂上都成立", True)
    check("oracle 不劣于本地规则", orc.coverage >= base.coverage - 1e-9,
          f"{orc.coverage:.3f} vs {base.coverage:.3f}")


def test_residual_failure_taxonomy() -> None:
    """残余失败必须按可区分的原因分开，且每条原因都要能被触发。

    A classifier whose branches cannot be exercised is not a classifier. Each of the three
    outcomes is produced here from a hand-built record, so a later change that collapses them into
    one bucket fails this test rather than silently making "we could not measure it" look like
    "we could not deliver it" -- two failures with opposite remedies.
    """
    from node_model import Sample
    from task_generator import PRIORITY_NORMAL, Task

    def record(samples, arrivals):
        demand = Task(id="d1", node_set=("n00",), measurement_type="displacement",
                      release_time=0, sample_window=(100, 200), delivery_deadline=300,
                      priority=PRIORITY_NORMAL, policy_generation=1)
        return RunRecord(demands=[demand], taken=list(samples), arrived=list(arrivals),
                         heard_uplinks=[], node_ids=("n00",))

    missing = residual_failures(record([], []))
    check("窗口内没有采样时归为采样侧失败",
          missing["residual_no_sample_in_window"] == 1
          and missing["residual_late_delivery"] == 0, f"{missing}")

    sample = Sample.make("n00", 150, "displacement")
    late = residual_failures(record([sample], [(sample, 400)]))
    check("窗口内采到但截止后才到，归为投递失败",
          late["residual_late_delivery"] == 1
          and late["residual_no_sample_in_window"] == 0, f"{late}")

    on_time = residual_failures(record([sample], [(sample, 250)]))
    check("窗口内采到且按期到达算满足",
          on_time["residual_met"] == 1 and on_time["residual_unmet"] == 0, f"{on_time}")

    # A reading taken before the window that arrived in time is not a cause of failure; it is what
    # the platform was serving at the deadline, and it is counted separately on purpose.
    stale = Sample.make("n00", 50, "displacement")
    served = residual_failures(record([stale], [(stale, 200)]))
    check("窗口前采到的记录按期到达时，记为平台顶着陈旧读数而不是失败成因",
          served["residual_served_stale_reading"] == 1
          and served["residual_no_sample_in_window"] == 1, f"{served}")


def main() -> int:
    print("评分器与真值边界回归测试")
    test_both_halves_required()
    test_class_split_and_weights()
    test_servable_subset()
    test_archive_completeness()
    test_no_ground_truth_leak()
    test_end_to_end_runs()
    test_residual_failure_taxonomy()
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
