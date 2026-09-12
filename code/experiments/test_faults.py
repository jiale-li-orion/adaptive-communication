#!/usr/bin/env python3
"""
test_faults.py — the six diagnostic faults, and the properties that make them auditable.

The fault trajectories exist for semantic validation, so what has to hold is not a rate. What has to
hold is that each class can be read off the event list without reading the code that produced it:

  ONE CLASS PER TRAJECTORY. A trajectory injects its own class and nothing else. If a second class
  leaked in, an effect could be attributed to the wrong fault, and the whole point of injecting one
  class at a time would be gone.

  DETERMINISTIC AND ORDER-FREE. The same spec gives the same events, byte for byte; `events()`
  can be asked twice; other draws happening in between change nothing; and asking `active()` before
  `events()` changes nothing either. A fault trajectory that shifted when the caller asked an extra
  question would make two arms incomparable through the fault rather than through the runtime.

  INSIDE THE RUN, SORTED, EXPLAINED. Every event lies inside [0, hours * 3600) with its whole
  coverage window, the list is sorted by (at_s, kind, node_id), and the detail is non-empty: an
  injection with no recorded detail cannot be audited event by event.

  `active()` AGREES WITH `events()`. Half-open windows, checked at the start, the last covered tick
  and the first uncovered instant, for a named node, for every node and for a node-less query.

  THE TWO RESTARTS ARE DISTINGUISHABLE. `coordinator_restart` names no station, `node_restart`
  always names one, and each carries what a runtime needs to decide what it lost.

  A STALE COMMAND CARRIES BOTH INSTANTS. The delayed arrival and the original issue instant, with
  the holdout between them and the ordering condition that makes the release stale.

  THE CONTROL INJECTS NOTHING. `FaultFree` is a trajectory like the others in shape and empty in
  content: no events, and `active()` false at every instant and every node.

Run: python3 code/experiments/test_faults.py
"""
from __future__ import annotations

# --- module resolution -------------------------------------------------------
import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, *(_os.path.join(_CODE, d) for d in ("physics", "runtime",
                                                     "experiments", "analysis", "monitoring"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)
# -----------------------------------------------------------------------------

import json

from deterministic import stable_uniform
from faults import (KIND_DEFAULTS, KINDS, KIND_SCOPE, MIN_PROFILE_GAP_S, FaultFree, FaultInjector,
                    FaultSpec, reference_node_ids)
from node_model import TICK_S

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{('  — ' + detail) if detail else ''}")
    if not ok:
        FAILURES.append(name)


# ---------------------------------------------------------------- helpers
def canon(events: list) -> str:
    """The trajectory as canonical JSON. Equal strings are what "byte-identical" means here."""
    return json.dumps([{"at_s": e.at_s, "kind": e.kind, "node_id": e.node_id, "detail": e.detail}
                       for e in events], sort_keys=True, ensure_ascii=False)


def canon_bytes(events: list) -> bytes:
    return canon(events).encode("utf-8")


def hhmmss(seconds: int) -> str:
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def _fmt_value(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False) if isinstance(value, dict) \
        else str(value)


def fmt_event(event) -> str:
    body = " ".join(f"{k}={_fmt_value(v)}" for k, v in sorted(event.detail.items())
                    if k != "coverage_s")
    node = event.node_id or "(network)"
    return f"t={hhmmss(event.at_s)} node={node} cover={event.detail['coverage_s']}s {body}"


def sort_key(event) -> tuple:
    return (event.at_s, event.kind, event.node_id or "")


def probe_instants(events: list, hours: int) -> list[int]:
    """Instants to interrogate: every event's start, its middle, its end, and the run's ends."""
    total_s = hours * 3600
    instants = {0, total_s - TICK_S}
    for event in events:
        coverage_s = event.detail["coverage_s"]
        instants.update({event.at_s - TICK_S, event.at_s + coverage_s // 2,
                         event.at_s + coverage_s})
    return sorted(t for t in instants if 0 <= t < total_s)


# ---------------------------------------------------------------- signature
def test_each_class_alone() -> None:
    print("\n[1] 六类各自独立构造，事件只有本类，且各有自己的形状")
    shapes, key_sets = {}, {}
    for kind in KINDS:
        inj = FaultInjector(FaultSpec(kind=kind))
        events = inj.events()
        check(f"{kind}: 轨迹非空", len(events) > 0, f"count={len(events)}")
        check(f"{kind}: 每个事件都是本类", all(e.kind == kind for e in events))
        check(f"{kind}: detail 非空", all(e.detail for e in events))
        if KIND_SCOPE[kind] == "network":
            check(f"{kind}: 网络范围故障不命名节点", all(e.node_id is None for e in events))
        else:
            check(f"{kind}: 命名节点都在参考部署内",
                  all(e.node_id in reference_node_ids() for e in events))

        # nothing of another class is active where this class injects
        others = []
        for at_s in probe_instants(events, inj.spec.hours):
            for other in KINDS:
                if other != kind and inj.active(other, at_s, None):
                    others.append((other, at_s))
        check(f"{kind}: 本类事件时刻没有其它类覆盖", not others, str(others[:3]))

        key_sets[kind] = tuple(sorted({k for e in events for k in e.detail}))
        shapes[kind] = (len(events), events[0].at_s, events[-1].at_s)

    distinct_keys = len({v for v in key_sets.values()})
    check("六类的 detail 字段集两两不同", distinct_keys == len(KINDS),
          f"{distinct_keys}/{len(KINDS)} 组不同")
    distinct_shapes = len({v for v in shapes.values()})
    check("六类默认轨迹的 (count, first, last) 两两不同", distinct_shapes == len(KINDS),
          f"{distinct_shapes}/{len(KINDS)} 组不同")


# ---------------------------------------------------------------- determinism
def test_determinism_and_idempotence() -> None:
    print("\n[2] 同 spec 逐字节一致，events() 幂等")
    for kind in KINDS:
        spec = FaultSpec(kind=kind, seed=7)
        first = canon_bytes(FaultInjector(spec).events())
        again = canon_bytes(FaultInjector(spec).events())
        check(f"{kind}: 两次构造逐字节一致", first == again)

        inj = FaultInjector(spec)
        a = inj.events()
        b = inj.events()
        check(f"{kind}: 同一次构造里连问两次结果相同", canon_bytes(a) == canon_bytes(b))
        check(f"{kind}: describe 也一致",
              json.dumps(inj.describe(), sort_keys=True) == json.dumps(inj.describe(),
                                                                      sort_keys=True))

        # the returned trajectory is a copy: editing it must not edit the record
        a[0].detail["tampered"] = True
        del a[:]
        check(f"{kind}: 调用方改动手里的副本不影响记录",
              canon_bytes(inj.events()) == first and len(inj.events()) == len(b))


def test_order_free_draws() -> None:
    print("\n[3] 交错其它抽样、交错其它轨迹，都不改变本类事件")
    for kind in KINDS:
        spec = FaultSpec(kind=kind, seed=3)
        before = canon_bytes(FaultInjector(spec).events())

        # draws of every other shape a run takes, in the middle
        for i in range(500):
            stable_uniform(3, "ul", "n07", i, 0)
            stable_uniform(3, "rx-win", "n07", i, 0, f"n07:profile:g{i}")
            stable_uniform(3, "backhaul", i)

        # and another trajectory of a different class, built and interrogated in between
        other_kind = KINDS[(KINDS.index(kind) + 1) % len(KINDS)]
        other = FaultInjector(FaultSpec(kind=other_kind, seed=3))
        other.events()
        other.active(other_kind, 0, None)
        other.active(kind, 0, None)

        after = canon_bytes(FaultInjector(spec).events())
        check(f"{kind}: 500 次交错抽样后事件不变", before == after)

        # asking active() first, then events(): the same trajectory either way
        inj = FaultInjector(spec)
        inj.active(kind, 0, None)
        inj.active(kind, TICK_S, "n00")
        check(f"{kind}: 先问 active 再取 events 结果不变", canon_bytes(inj.events()) == before)


# ---------------------------------------------------------------- window shape
def test_events_inside_run_sorted() -> None:
    print("\n[4] 事件落在运行区间内、按 (at_s, kind, node_id) 排序、覆盖窗不越界")
    for kind in KINDS:
        bad, detail = [], ""
        for seed in (0, 1, 5, 42):
            spec = FaultSpec(kind=kind, seed=seed)
            inj = FaultInjector(spec)
            events = inj.events()
            total_s = spec.hours * 3600
            inside = all(0 <= e.at_s < total_s for e in events)
            window = all(e.at_s + e.detail["coverage_s"] <= total_s for e in events)
            on_clock = all(e.at_s % TICK_S == 0 and e.detail["coverage_s"] % TICK_S == 0
                           and e.detail["coverage_s"] >= TICK_S for e in events)
            ordered = events == sorted(events, key=sort_key)
            if not (inside and window and on_clock and ordered):
                bad.append(f"seed={seed} inside={inside} window={window} "
                           f"on_clock={on_clock} ordered={ordered}")
        check(f"{kind}: 区间/时钟/排序（4 个 seed）", not bad, "; ".join(bad) or detail)


# ---------------------------------------------------------------- active()
def test_active_agrees_with_events() -> None:
    print("\n[5] active() 与 events() 一致：窗口起点、最后一个 tick、第一个未覆盖时刻")
    for kind in KINDS:
        spec = FaultSpec(kind=kind, seed=11)
        inj = FaultInjector(spec)
        events = inj.events()
        total_s = spec.hours * 3600
        named = {e.node_id for e in events if e.node_id is not None}
        untargeted = next((nid for nid in reference_node_ids() if nid not in named), None)

        start_ok, end_ok, inside_ok = True, True, True
        for event in events:
            coverage_s = event.detail["coverage_s"]
            node = event.node_id
            start_ok = start_ok and inj.active(kind, event.at_s, node)
            end_ok = end_ok and not inj.active(kind, event.at_s + coverage_s, node)
            inside_ok = inside_ok and inj.active(kind, event.at_s + coverage_s - TICK_S, node)
        check(f"{kind}: 窗口起点为真", start_ok)
        check(f"{kind}: 窗口终点为假（半开区间）", end_ok)
        check(f"{kind}: 最后一个被覆盖的 tick 为真", inside_ok)

        overlapping = [(a.at_s, b.at_s) for a in events for b in events
                       if a is not b and a.node_id == b.node_id
                       and a.at_s <= b.at_s < a.at_s + a.detail["coverage_s"]]
        check(f"{kind}: 同类同节点的窗口互不重叠", not overlapping, str(overlapping[:2]))
        check(f"{kind}: 末个窗口结束后不再覆盖",
              not inj.active(kind, events[-1].at_s + events[-1].detail["coverage_s"], None))

        if KIND_SCOPE[kind] == "node" and untargeted is not None:
            covered = [t for t in probe_instants(events, spec.hours)
                       if inj.active(kind, t, untargeted)]
            check(f"{kind}: 未涉及的节点 {untargeted} 不被覆盖", not covered, str(covered[:3]))
        if KIND_SCOPE[kind] == "network":
            covered = [t for t in probe_instants(events, spec.hours)
                       if inj.active(kind, t, "n07")]
            check(f"{kind}: 网络范围故障对该网络内任意节点成立", len(covered) > 0,
                  f"{len(covered)} 个探测时刻")

        check(f"{kind}: 不带节点查询时按通配返回真", inj.active(kind, events[0].at_s, None))
        outside = next((t for t in range(total_s - TICK_S, -1, -TICK_S)
                        if not inj.active(kind, t, None)), None)
        check(f"{kind}: 运行区间内存在不被覆盖的时刻", outside is not None,
              f"例如 t={hhmmss(outside) if outside is not None else '无'}")


# ---------------------------------------------------------------- restarts
def test_restart_classes_are_distinguishable() -> None:
    print("\n[6] coordinator_restart 不命名节点，node_restart 一定命名")
    coord = FaultInjector(FaultSpec(kind="coordinator_restart")).events()
    check("coordinator_restart 的事件不带节点", all(e.node_id is None for e in coord))
    check("coordinator_restart 说明这是中心进程",
          all(e.detail.get("process") == "center" for e in coord))
    check("coordinator_restart 记录内存态丢失",
          all(e.detail.get("volatile_state_lost") is True for e in coord))
    check("coordinator_restart 记录停机区间与恢复时刻",
          all(e.detail["resumed_at_s"] == e.at_s + e.detail["downtime_s"] > e.at_s for e in coord))
    check("coordinator_restart 说明链路未断",
          all(e.detail.get("backhaul_up") is True and e.detail.get("gateway_up") is True
              for e in coord))

    node = FaultInjector(FaultSpec(kind="node_restart")).events()
    check("node_restart 的事件全部带节点",
          all(e.node_id in reference_node_ids() for e in node), str([e.node_id for e in node]))
    check("node_restart 记录停运区间与恢复时刻",
          all(e.detail["recovered_at_s"] == e.at_s + e.detail["outage_s"] > e.at_s for e in node))
    check("node_restart 记录实际后果：采样与上行中断、易失状态丢失",
          all(e.detail.get("sampling_suspended") is True
              and e.detail.get("uplinks_suspended") is True
              and e.detail.get("volatile_state_lost") is True for e in node))
    check("node_restart 重启序号按节点累计",
          all(e.detail["restart_epoch"] >= 1 for e in node))

    both = {(e.at_s, tuple(sorted(e.detail))) for e in coord} & \
           {(e.at_s, tuple(sorted(e.detail))) for e in node}
    check("两类的 (时刻, 字段集) 不重合", not both, str(list(both)[:2]))

    pinned = FaultInjector(FaultSpec(kind="node_restart", nodes=("n05",))).events()
    check("指定节点后只在指定节点上重启", pinned and all(e.node_id == "n05" for e in pinned),
          f"count={len(pinned)}")


# ---------------------------------------------------------------- stale
def test_stale_command_carries_both_instants() -> None:
    print("\n[7] stale_command 同时带迟到时刻与原始下发时刻")
    inj = FaultInjector(FaultSpec(kind="stale_command"))
    events = inj.events()
    ok = True
    for event in events:
        d = event.detail
        ok = ok and d["arrives_at_s"] == event.at_s
        ok = ok and 0 <= d["issued_at_s"] < event.at_s
        ok = ok and d["delay_s"] == event.at_s - d["issued_at_s"]
        ok = ok and d["issued_at_s"] % TICK_S == 0 and d["delay_s"] % TICK_S == 0
        ok = ok and d["stale_against"] == {"newer_issued_after_s": d["issued_at_s"],
                                           "in_force_before_s": event.at_s}
        ok = ok and d["holdout_gaps"] == d["delay_s"] // MIN_PROFILE_GAP_S
        if not ok:
            break
    check("过期命令带迟到时刻、原始下发时刻与两者之差", ok,
          f"example {events[0].detail['issued_at_s']} -> {events[0].at_s}")
    check("默认扣留跨过至少一个档位间隙",
          all(e.detail["delay_s"] >= 2 * MIN_PROFILE_GAP_S for e in events),
          f"min delay {min(e.detail['delay_s'] for e in events)} s, gap {MIN_PROFILE_GAP_S} s")
    check("默认扣留有界", all(e.detail["delay_s"] <= 4 * MIN_PROFILE_GAP_S for e in events),
          f"max delay {max(e.detail['delay_s'] for e in events)} s")

    fixed = FaultInjector(FaultSpec(kind="stale_command", delay_s=3 * TICK_S)).events()
    check("显式扣留被采用", fixed and all(e.detail["delay_s"] == 3 * TICK_S for e in fixed))
    check("扣留短于一个档位间隙时 holdout_gaps 为 0",
          all(e.detail["holdout_gaps"] == 0 for e in fixed))
    check("过期命令仍带下发时刻", all(e.detail["issued_at_s"] == e.at_s - 3 * TICK_S
                                      for e in fixed))


# ---------------------------------------------------------------- backhaul
def test_backhaul_only_scope() -> None:
    print("\n[8] backhaul_only 不命名节点，且说明接入仍然可用")
    inj = FaultInjector(FaultSpec(kind="backhaul_only"))
    events = inj.events()
    check("backhaul_only 的事件不带节点", all(e.node_id is None for e in events))
    check("backhaul_only 说明网关与接入仍在",
          all(e.detail.get("gateway_up") is True and e.detail.get("access_up") is True
              for e in events))
    check("backhaul_only 说明中心收不到上行",
          all(e.detail.get("center_receives_uplinks") is False for e in events))
    check("backhaul_only 的窗口以小时计",
          all(e.detail["outage_s"] >= 3600 for e in events),
          f"{[e.detail['outage_s'] for e in events]}")
    check("backhaul_only 恢复时刻在事件时刻之后",
          all(e.detail["restored_at_s"] == e.at_s + e.detail["outage_s"] for e in events))


# ---------------------------------------------------------------- control
def test_fault_free() -> None:
    print("\n[9] FaultFree：无事件，处处不活跃")
    free = FaultFree()
    check("FaultFree 事件为空", free.events() == [])
    d = free.describe()
    check("FaultFree 的 describe 为空轨迹",
          d["count"] == 0 and d["first_at_s"] is None and d["last_at_s"] is None
          and d["nodes"] == ())
    instants = (0, TICK_S, 12 * 3600, 30 * 3600, 72 * 3600 - TICK_S, 10 ** 9)
    bad = [(kind, t, nid) for kind in KINDS for t in instants
           for nid in (None, "n00", "n15") if free.active(kind, t, nid)]
    check("FaultFree 的 active 在任何种类、时刻、节点上都是假", not bad, str(bad[:3]))

    carried = FaultFree(FaultSpec(kind="node_restart", seed=4, hours=48)).describe()
    check("FaultFree 可携带本次运行的 seed 与时长",
          carried["seed"] == 4 and carried["hours"] == 48 and carried["kind"] == "fault_free")


# ---------------------------------------------------------------- knobs
def test_knobs_and_rejections() -> None:
    print("\n[10] 显式旋钮生效，非法 spec 抛错")
    two = FaultInjector(FaultSpec(kind="request_lost", count=2)).events()
    check("count 限制事件数", len(two) == 2, f"count={len(two)}")
    check("count 从 first_at_s 按 period 展开",
          [e.at_s for e in two] == [3600, 3600 + KIND_DEFAULTS["request_lost"]["period_s"]])

    spread = FaultInjector(FaultSpec(kind="backhaul_only", first_at_s=3600, count=3)).events()
    gaps = [b.at_s - a.at_s for a, b in zip(spread, spread[1:])]
    period_s, jitter_s = KIND_DEFAULTS["backhaul_only"]["period_s"], \
        KIND_DEFAULTS["backhaul_only"]["jitter_s"]
    check("period 决定间隔，jitter 在 period 两侧各挪动不超过 jitter_s",
          all(period_s - jitter_s <= g < period_s + jitter_s for g in gaps),
          f"gaps={gaps} period={period_s} jitter={jitter_s}")
    check("jitter 不改变事件数与先后顺序", len(spread) == 3
          and [e.at_s for e in spread] == sorted(e.at_s for e in spread))

    wide = FaultInjector(FaultSpec(kind="ack_lost", duration_s=2 * 3600)).events()
    check("duration 决定覆盖窗", all(e.detail["coverage_s"] == 2 * 3600 for e in wide))

    no_jitter = FaultInjector(FaultSpec(kind="node_restart", jitter_s=TICK_S,
                                        first_at_s=3600)).events()
    check("首个事件落在 first_at_s 之上的 jitter 内",
          3600 <= no_jitter[0].at_s < 3600 + TICK_S, f"at_s={no_jitter[0].at_s}")

    def rejects(name: str, **kw) -> None:
        try:
            FaultSpec(**kw)
        except ValueError:
            check(name, True)
        else:
            check(name, False, f"{kw} 没有抛错")

    rejects("未知类名抛错", kind="no_such_fault")
    rejects("hours=0 抛错", kind="request_lost", hours=0)
    rejects("非整数 hours 抛错", kind="request_lost", hours=72.0)
    rejects("负 seed 抛错", kind="request_lost", seed=-1)
    rejects("count=0 抛错", kind="request_lost", count=0)
    rejects("离开 60 s 时钟的时长抛错", kind="node_restart", duration_s=90)
    rejects("短于一个 tick 的窗口抛错", kind="request_lost", duration_s=30)
    rejects("网络范围故障指定节点抛错", kind="backhaul_only", nodes=("n00",))
    rejects("重复节点抛错", kind="node_restart", nodes=("n05", "n05"))
    rejects("把单个节点当序列传入抛错", kind="node_restart", nodes="n05")
    rejects("与本类无关的旋钮抛错", kind="request_lost", delay_s=3600)
    rejects("与本类无关的旋钮抛错（in_force）", kind="node_restart", in_force_s=3600)
    rejects("扣留长于首次到达时点抛错（命令会被写在下发之前）",
            kind="stale_command", first_at_s=3600)
    rejects("显式扣留长于 first_at_s 时抛错", kind="stale_command", first_at_s=6 * 3600,
            delay_s=12 * 3600)

    try:
        FaultInjector(FaultSpec(kind="request_lost")).active("no_such_fault", 0)
    except ValueError:
        check("active 对未知类名抛错", True)
    else:
        check("active 对未知类名抛错", False)

    # A schedule that does not fit the run yields no events rather than an invented instant. The
    # behaviour is pinned here so that a fault trajectory which is empty by accident is visible in
    # describe() instead of being read as a fault-free run.
    empty = FaultInjector(FaultSpec(kind="backhaul_only", first_at_s=70 * 3600))
    check("窗口放不进运行区间时不排事件，describe 报 count=0",
          empty.events() == [] and empty.describe()["count"] == 0
          and empty.describe()["first_at_s"] is None)
    short = FaultInjector(FaultSpec(kind="coordinator_restart", hours=6)).events()
    check("很短的运行里默认排不进去，轨迹为空", short == [])


def test_seed_moves_the_trajectory_not_the_count() -> None:
    print("\n[11] seed 改变轨迹的形状，不改变事件数")
    for kind in KINDS:
        runs = [FaultInjector(FaultSpec(kind=kind, seed=s)) for s in range(6)]
        events = [r.events() for r in runs]
        counts = {len(e) for e in events}
        check(f"{kind}: 事件数不随 seed 变化", len(counts) == 1, f"counts={sorted(counts)}")
        check(f"{kind}: seed 确实改变轨迹", len({canon_bytes(e) for e in events}) > 1,
              f"{len({canon_bytes(e) for e in events})}/6 条不同")
        if KIND_SCOPE[kind] == "node":
            targets = {tuple(e.node_id for e in ev) for ev in events}
            check(f"{kind}: seed 改变命中的节点序列", len(targets) > 1,
                  f"{len(targets)}/6 组不同")


# ---------------------------------------------------------------- audit
def print_audit() -> None:
    print("\n[audit] 一类一条轨迹（默认 72 h / seed 0）：首个事件、事件数、末个事件")
    for kind in KINDS:
        inj = FaultInjector(FaultSpec(kind=kind))
        events = inj.events()
        d = inj.describe()
        nodes = ",".join(d["nodes"]) if d["nodes"] else "(network)"
        print(f"\n  {kind}  count={d['count']}  nodes={nodes}  covered={d['covered_s']}s")
        print(f"    first  {fmt_event(events[0])}")
        print(f"    last   {fmt_event(events[-1])}")
    free = FaultFree()
    print(f"\n  fault_free  count={free.describe()['count']}  nodes=(none)  covered=0s")
    print("    first  (无注入)")
    print("    last   (无注入)")


def main() -> int:
    print("六类诊断故障回归测试")
    test_each_class_alone()
    test_determinism_and_idempotence()
    test_order_free_draws()
    test_events_inside_run_sorted()
    test_active_agrees_with_events()
    test_restart_classes_are_distinguishable()
    test_stale_command_carries_both_instants()
    test_backhaul_only_scope()
    test_fault_free()
    test_knobs_and_rejections()
    test_seed_moves_the_trajectory_not_the_count()
    print_audit()
    print("\n" + "-" * 74)
    if FAILURES:
        print(f"  {len(FAILURES)} 项失败：")
        for name in FAILURES:
            print(f"    - {name}")
        return 1
    print("  全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
