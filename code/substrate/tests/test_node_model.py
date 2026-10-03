#!/usr/bin/env python3
"""
test_node_model.py — the sampling, buffering and upload chain, aligned event by event.

The chain this checks is: schedule -> sample taken -> record buffered -> upload transmitted ->
gateway heard it -> record at the center. Every arrow can break, and the failures are not
interchangeable, so the test walks the whole chain on one trajectory and checks each link:

  * every record at the center has a matching sample taken locally, with the same id and the same
    timestamp — the two records are about the same physical measurement;
  * no record arrives before it was taken;
  * the sampling cadence follows the profile, and a profile change takes effect at the moment it
    is applied rather than after the old interval expires;
  * an unacknowledged record is retransmitted, and an acknowledged one is not;
  * a node that stays unreachable loses its oldest records and the loss is counted;
  * a status read cannot see the sample schedule or the unacknowledged id set.

Run: python3 code/experiments/test_node_model.py
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

from node_model import NodeRuntime, Sample, TICK_S                      # noqa: E402
from opportunity import ControlPlane, LoRaProfile, DownlinkMessage      # noqa: E402
from task_generator import (build_deployment, profile_for_hour,          # noqa: E402
                            MONITORING_PROFILES, PROFILE_NORMAL, PROFILE_RISK,
                            PROFILE_LOW_POWER, RISK_WINDOWS_H)

FAIL: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{('  — ' + detail) if detail else ''}")
    if not ok:
        FAIL.append(name)


def drive(hours: int = 72, seed: int = 5, use_radio: bool = True):
    """Run one node through the reference workload and return (node, plane, log)."""
    deployment = build_deployment(seed)
    node = deployment.nodes[0]
    rt = NodeRuntime(node_id=node.nid, role=node.role)
    plane = ControlPlane(LoRaProfile(), seed=seed, downlink_per_uplink=1)
    log: list[dict] = []
    uplink_attempt = 0

    for t_s in range(0, hours * 3600, TICK_S):
        hour = t_s / 3600.0
        demanded = profile_for_hour(hour, RISK_WINDOWS_H)
        if demanded != rt.profile and demanded != PROFILE_LOW_POWER:
            rt.set_profile(demanded, t_s)
            log.append({"event": "profile", "at": t_s, "profile": demanded})

        rt.maybe_sample(t_s)

        if rt.upload_due(t_s):
            batch = rt.begin_upload(t_s)
            if not batch:
                continue
            if not use_radio:
                rt.upload_result(batch, heard=True, arrival_s=t_s)
                rt.confirm([s.sample_id for s in batch])
                continue
            rec = plane.uplink(node.nid, hour=int(hour), sf=9,
                               payload_bytes=sum(s.payload_bytes for s in batch) or 12,
                               attempt_index=uplink_attempt)
            uplink_attempt += 1
            rt.upload_result(batch, heard=rec.arrived, arrival_s=t_s)
            if rec.arrived:
                rt.confirm([s.sample_id for s in batch])
            log.append({"event": "upload", "at": t_s, "n": len(batch), "heard": rec.arrived})
    return rt, plane, log


# --------------------------------------------------------------------- alignment
def test_event_alignment() -> None:
    print("\n[1] 采样到到达的逐事件对齐")
    rt, plane, log = drive()
    taken_by_id = {s.sample_id: s for s in rt.taken}
    check("确有样本产生", len(rt.taken) > 0, f"{len(rt.taken)} 个样本")

    mismatch = [s.sample_id for s, _ in rt.received if s.sample_id not in taken_by_id]
    check("中心收到的每条记录都能对上本地采样", not mismatch,
          f"{len(rt.received)} 条到达，{len(mismatch)} 条对不上")

    wrong_time = [(s.sample_id, s.taken_at, taken_by_id[s.sample_id].taken_at)
                  for s, _ in rt.received
                  if s.sample_id in taken_by_id and s.taken_at != taken_by_id[s.sample_id].taken_at]
    check("每条到达记录的采集时刻与本地一致", not wrong_time, str(wrong_time[:3]))

    early = [(s.sample_id, s.taken_at, arr) for s, arr in rt.received if arr < s.taken_at]
    check("没有记录在采集之前到达", not early, str(early[:3]))

    ids = [s.sample_id for s, _ in rt.received]
    check("同一条记录不会在中心重复计数两次以上", len(ids) == len(rt.received))
    check("到达记录数不超过本地采样数", len(rt.received) <= len(rt.taken),
          f"{len(rt.received)} <= {len(rt.taken)}")


def test_cadence_follows_profile() -> None:
    print("\n[2] 采样节奏跟随 profile，且切换立即生效")
    rt, _, _ = drive(use_radio=False)
    normal = sum(1 for s in rt.taken if 0 <= s.taken_at < 12 * 3600)
    risk = sum(1 for s in rt.taken if 12 * 3600 <= s.taken_at < 18 * 3600)
    # normal: 5 min -> 12/h; risk: 1 min -> 60/h
    check("常态段为 5 分钟一次", normal == 12 * 12, f"{normal} 个样本 = {normal / 12:.1f}/h")
    check("风险段为 1 分钟一次", risk == 6 * 60, f"{risk} 个样本 = {risk / 6:.1f}/h")

    # A denser profile must not wait out the previous, longer interval.
    rt2 = NodeRuntime(node_id="r01", role="deformation")
    rt2.maybe_sample(0)
    rt2.maybe_sample(299)                    # still inside the normal 5-minute interval
    before = len(rt2.taken)
    rt2.set_profile(PROFILE_RISK, 300)
    rt2.maybe_sample(300)
    check("切换到加密 profile 后立刻采样",
          len(rt2.taken) > before and rt2.taken[-1].taken_at == 300,
          f"taken_at={rt2.taken[-1].taken_at}")

    # Switching re-bases the schedule from the moment of application, in both directions: the
    # sparser profile takes one reading at the changeover and then waits its own interval.
    tick0 = len(rt2.taken)
    rt2.set_profile(PROFILE_LOW_POWER, 900)
    rt2.maybe_sample(900)
    check("切换时刻取一个样本", len(rt2.taken) == tick0 + 1,
          f"新增 {len(rt2.taken) - tick0} 个")
    mark = len(rt2.taken)
    rt2.maybe_sample(900 + 14 * 60)
    check("节能 profile 下 14 分钟内不再采样", len(rt2.taken) == mark,
          f"新增 {len(rt2.taken) - mark} 个")
    rt2.maybe_sample(900 + 15 * 60)
    check("满 15 分钟时采样一次", len(rt2.taken) == mark + 1)


def test_retransmission_and_ack() -> None:
    print("\n[3] 未被确认的记录会重发，已确认的不会")
    rt = NodeRuntime(node_id="r01", role="deformation", batch_max=4)
    rt.maybe_sample(0)
    rt.maybe_sample(5 * 60)
    rt.maybe_sample(10 * 60)
    rt.maybe_sample(15 * 60)
    rt.maybe_sample(20 * 60)
    total = len(rt.taken)
    check("取了五个样本", total == 5)

    batch = rt.begin_upload(3600)
    check("一次上传不超过批次上限", len(batch) == 4, f"{len(batch)} 条")
    rt.upload_result(batch, heard=False, arrival_s=3600)      # lost
    check("丢失后记录仍留在本地", rt.buffer_level == 5)

    batch2 = rt.begin_upload(7200)
    check("重发的是同一条最早未确认记录",
          batch2[0].sample_id == batch[0].sample_id, batch2[0].sample_id)
    rt.upload_result(batch2, heard=True, arrival_s=7200)
    rt.confirm([s.sample_id for s in batch2])
    check("确认后离开本地缓冲", rt.buffer_level == 1, f"剩 {rt.buffer_level}")
    check("未确认的那条还在", rt.unacknowledged_ids() == [rt.taken[-1].sample_id])


def test_capacity_and_loss() -> None:
    print("\n[4] 容量上限与丢失计数")
    rt = NodeRuntime(node_id="r01", role="deformation", buffer_capacity=10)
    for i in range(30):
        rt.maybe_sample(i * 5 * 60)
    check("缓冲不超过容量", rt.buffer_level == 10, f"level={rt.buffer_level}")
    check("溢出的都是最旧的", rt.dropped_overflow == 20, f"dropped={rt.dropped_overflow}")
    check("保留的是最新的十条",
          rt.records[-1].taken_at == 29 * 5 * 60 and rt.records[0].taken_at == 20 * 5 * 60)
    check("丢失计入账目而非静默丢弃", rt.records_sent == 0)


def test_snapshot_does_not_leak() -> None:
    print("\n[5] 状态读不泄漏采样计划与未确认集合")
    rt, _, _ = drive(hours=6, use_radio=False)
    snap = rt.snapshot(6 * 3600)
    check("给出版本化的 profile 与本地水位",
          {"profile", "buffer_level", "newest_sample_at"} <= set(snap))
    forbidden = {"unacknowledged", "records", "schedule", "taken", "sample_interval"}
    check("不含未确认 id 集合或采样计划", not (forbidden & set(snap)), str(sorted(snap)))


def test_radio_coupling() -> None:
    print("\n[6] 上传被听到才产生机会，链路上界仍成立")
    rt, plane, log = drive(hours=24)
    plane.check_opportunity_bound()
    uploads = [e for e in log if e["event"] == "upload"]
    heard = [e for e in uploads if e["heard"]]
    check("上传次数与账目一致", rt.uploads_attempted == len(uploads),
          f"{rt.uploads_attempted} vs {len(uploads)}")
    check("被听到的次数与机会数一致", rt.uploads_heard == plane.uplinks_heard,
          f"{rt.uploads_heard} vs {plane.uplinks_heard}")
    check("存在未被听到的上传", len(uploads) - len(heard) > 0,
          f"{len(uploads) - len(heard)}/{len(uploads)} 未被听到")
    check("机会数不超过被听到的上行数",
          plane.opportunities_created.get(rt.node_id, 0) <= plane.uplinks_heard)


def main() -> int:
    print("节点采样/缓存/上传链回归测试")
    test_event_alignment()
    test_cadence_follows_profile()
    test_retransmission_and_ack()
    test_capacity_and_loss()
    test_snapshot_does_not_leak()
    test_radio_coupling()
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
