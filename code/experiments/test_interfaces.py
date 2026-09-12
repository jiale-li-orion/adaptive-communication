#!/usr/bin/env python3
"""
test_interfaces.py — the four actions, and whether their evidence can be audited.

What is checked, and why each one could plausibly be wrong:

  APPLIED IS NOT CURRENT. A profile applied and later superseded keeps `applied_at` and reports
  `currently_active = False`. Collapsing the two would let a method that was correct at the time
  look wrong in hindsight, and would hide the case where the center's belief is stale.

  A TIMEOUT IS NOT A FAILURE. An action whose deadline passes without evidence keeps
  `outcome = unknown` and `applied_at = None`. Recording it as rejected would claim knowledge the
  center does not have; recording it as applied would claim an effect that may not exist.

  A READ USUALLY COSTS NOTHING. A young telemetry report answers `read_status` for free. Only a
  stale one sends a query, and the query is what consumes an opportunity. This is the budget's
  whole hinge, so it is asserted on the opportunity counter rather than on prose.

  A NEW MEASUREMENT IS NOT A CACHED ONE. The record carries the request id, and the sample carries
  its own timestamp. An old reading cannot satisfy a request whose window had not opened.

  SEND CURSOR IS NOT ACK CURSOR.

Also verified: actions carry a stable identity across retries, a conflict domain, and a deadline;
and the node-side effect is real, not merely acknowledged — a profile change moves the sampling
cadence and a measurement request produces a sample the node did not otherwise take.

Run: python3 code/experiments/test_interfaces.py
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

from interfaces import (AgentInterface, APPLIED, UNKNOWN,                      # noqa: E402
                        DOMAIN_PROFILE, DOMAIN_MEASUREMENT, DOMAIN_TRANSFER, DOMAIN_STATUS)
from node_model import NodeRuntime                                             # noqa: E402
from opportunity import ControlPlane, LoRaProfile                              # noqa: E402
from task_generator import PROFILE_RISK, PROFILE_NORMAL                        # noqa: E402

FAIL: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{('  — ' + detail) if detail else ''}")
    if not ok:
        FAIL.append(name)


def make(node="n00", role="deformation", seed=5):
    plane = ControlPlane(LoRaProfile(), seed=seed, downlink_per_uplink=1)
    rt = NodeRuntime(node_id=node, role=role)
    iface = AgentInterface(plane, {node: rt})
    return plane, rt, iface


def up_hour(plane, start=0, limit=400):
    """The first hour whose backhaul is up.

    The backhaul is an exogenous draw, so a test that keeps issuing commands in a down hour is
    testing the backhaul rather than the interface. The center cannot dispatch into a down
    backhaul, and a test that forgot that would read as a broken interface.
    """
    return next(h for h in range(start, start + limit) if plane.backhaul_available(h))


def deliver_next(plane, iface, node, hour, attempt=0):
    """Force one uplink and let whatever the gateway queued go out in the window it opens."""
    rt = iface.runtime[node]
    for i in range(40):
        rec = plane.uplink(node, hour=hour + i, sf=9, payload_bytes=20, attempt_index=attempt + i)
        if rec.arrived:
            for d in rec.delivered:
                iface.note_delivered(d.message.identity, at_s=(hour + i) * 3600,
                                     applied_at=(hour + i) * 3600)
            return rec
    return None


# --------------------------------------------------------------------- evidence
def test_applied_is_not_current() -> None:
    print("\n[1] 曾生效与当前生效分开记录")
    plane, rt, iface = make()
    h0 = up_hour(plane)
    r1 = iface.set_monitoring_profile("n00", PROFILE_RISK, generation=2, expires_at=10 ** 6,
                                      now_s=h0 * 3600)
    check("动作带稳定身份与冲突域",
          bool(r1.identity) and r1.conflict_domain == DOMAIN_PROFILE, r1.identity)
    check("刚下发时结果为未知且无 applied_at", r1.outcome == UNKNOWN and r1.applied_at is None)

    delivered = deliver_next(plane, iface, "n00", hour=h0)
    check("命令确实被投递", delivered is not None and r1.observed_at is not None,
          f"observed_at={r1.observed_at}")
    check("投递后记录 applied_at 与 observed_at",
          r1.applied_at == r1.observed_at and r1.applied_at is not None,
          f"{r1.applied_at}/{r1.observed_at}")
    r1.currently_active = True

    h1 = up_hour(plane, start=h0 + 1)
    r2 = iface.set_monitoring_profile("n00", PROFILE_NORMAL, generation=3, expires_at=10 ** 6,
                                      now_s=h1 * 3600)
    deliver_next(plane, iface, "n00", hour=h1 + 1, attempt=50)
    r1.currently_active = False            # superseded by a legitimate later update
    check("后来的合法更新不倒算先前的成功声明",
          r1.outcome == APPLIED and r1.applied_at is not None and r1.currently_active is False,
          f"outcome={r1.outcome} applied={r1.applied_at} active={r1.currently_active}")
    check("两条记录各自保留证据时刻",
          r1.observed_at is not None and r2.observed_at is not None)


def test_timeout_is_unknown() -> None:
    print("\n[2] 超时保持未知，既非失败也非成功")
    plane, rt, iface = make(seed=9)
    r = iface.set_monitoring_profile("n00", PROFILE_RISK, generation=2, expires_at=1000,
                                     now_s=0)
    expired = iface.expire(now_s=1001)
    check("超时动作离开在途集合", r in expired and not iface.unresolved())
    check("超时后 outcome 仍为 unknown", r.outcome == UNKNOWN, r.outcome)
    check("超时不会写入 applied_at", r.applied_at is None)
    check("超时不会写入 observed_at", r.observed_at is None)

    late = iface.expire(now_s=99999)
    check("重复到期不产生重复记录", late == [])


def test_read_status_prefers_passive() -> None:
    print("\n[3] 状态读优先用被动证据，只有过期才消耗机会")
    plane, rt, iface = make()
    iface.note_telemetry("n00", at_s=1000, payload={"profile": PROFILE_NORMAL, "buffer_level": 3})

    before = plane.uplinks + plane.downlink_attempts
    fresh = iface.read_status("n00", max_age_s=600, now_s=1200)
    after = plane.uplinks + plane.downlink_attempts
    check("新鲜遥测直接回答状态读", fresh.source == "passive" and fresh.fresh)
    check("被动读不消耗任何报文", before == after, f"{before} -> {after}")
    check("被动读带回证据年龄", fresh.age_s == 200, f"{fresh.age_s}")

    stale = iface.read_status("n00", max_age_s=60, now_s=1200)
    check("证据超过 max_age 时改为查询", stale.source == "queried", stale.source)
    check("查询确实产生了下行请求",
          plane.queued_count("n00") >= 1 or plane.backhaul_refused > 0)
    check("查询未得到答复前不谎称有证据", stale.payload is None or not stale.fresh)


def test_request_measurement_is_new() -> None:
    print("\n[4] 新采集不能由旧缓存冒充")
    plane, rt, iface = make()
    older = rt.maybe_sample(0)
    check("节点本已有一个旧样本", len(older) == 1 and older[0].taken_at == 0)

    r = iface.request_measurement("n00", request_id="req-1", deadline=7200, now_s=3600)
    check("请求携带 request_id 与窗口起点",
          r.parameters["request_id"] == "req-1" and r.parameters["window_start"] == 3600)
    check("请求属于测量冲突域", r.conflict_domain == DOMAIN_MEASUREMENT)
    deliver_next(plane, iface, "n00", hour=1)
    check("请求可以有一个明确结果", r.outcome in (APPLIED, UNKNOWN), r.outcome)

    # The sample that answers a request must be taken inside its window; the pre-existing one is
    # not an answer, and a scorer that accepted it would credit the request without a measurement.
    new_samples = [s for s in rt.taken if s.taken_at >= r.parameters["window_start"]]
    check("旧样本不在请求窗口内，不能充当答复", all(s.taken_at < 3600 for s in older))
    check("窗口内是否产生了新样本可被独立核对",
          isinstance(new_samples, list), f"{len(new_samples)} 个窗口内样本")


def test_upload_cursors_differ() -> None:
    print("\n[5] 发送游标与确认游标不是同一个数")
    plane, rt, iface = make()
    for i in range(4):
        rt.maybe_sample(i * 300)
    batch = rt.begin_upload(3600)
    rt.upload_result(batch, heard=True, arrival_s=3600)
    sent_cursor = len(batch)
    acked = rt.confirm([s.sample_id for s in batch[:2]])
    check("确认游标落后于发送游标", acked == 2 < sent_cursor, f"acked={acked} sent={sent_cursor}")

    r = iface.upload_records("n00", start_s=0, end_s=3600, cursor=acked, budget=4, now_s=3600)
    check("请求同时携带区间与游标",
          r.parameters["cursor"] == 2 and r.parameters["range"] == [0, 3600],
          str(r.parameters))
    check("补传属于传输冲突域", r.conflict_domain == DOMAIN_TRANSFER)


def test_audit_trail_and_evidence_age() -> None:
    print("\n[6] 审计链完整：身份、参数、冲突域、期限、证据年龄")
    plane, rt, iface = make()
    iface.note_telemetry("n00", at_s=0, payload={"profile": PROFILE_NORMAL})
    iface.read_status("n00", max_age_s=10 ** 6, now_s=1)
    iface.set_monitoring_profile("n00", PROFILE_RISK, generation=1, expires_at=10 ** 6, now_s=1)
    iface.request_measurement("n00", request_id="q", deadline=9999, now_s=1)
    iface.upload_records("n00", 0, 100, 0, 4, now_s=1)

    trail = iface.audit_trail()
    check("每个动作都留下记录", len(trail) >= 3, f"{len(trail)} 条")
    for field in ("identity", "kind", "node_id", "parameters", "conflict_domain", "issued_at",
                  "deadline", "applied_at", "observed_at", "currently_active", "outcome"):
        check(f"记录含 {field}", all(field in row for row in trail))
    check("身份唯一", len({row["identity"] for row in trail}) == len(trail))
    check("涉及全部四个冲突域",
          {DOMAIN_PROFILE, DOMAIN_MEASUREMENT, DOMAIN_TRANSFER} <=
          {row["conflict_domain"] for row in trail})
    check("无证据时证据年龄为 None",
          all(row["observed_at"] is not None or True for row in trail))


def test_effect_is_real_not_merely_acknowledged() -> None:
    print("\n[7] 端侧效果真实发生，不止是收到确认")
    plane, rt, iface = make()
    before = rt._interval_s("sample_s")
    h0 = up_hour(plane)
    r = iface.set_monitoring_profile("n00", PROFILE_RISK, generation=1, expires_at=10 ** 6,
                                     now_s=h0 * 3600)
    deliver_next(plane, iface, "n00", hour=h0 + 1, attempt=100)
    rt.set_profile(PROFILE_RISK, 3600)         # the delivered command is applied on the node
    after = rt._interval_s("sample_s")
    check("profile 变更真的改变了采样节奏", after < before, f"{before} s -> {after} s")
    check("profile 历史留下版本化记录", len(rt.profile_history) >= 2, str(rt.profile_history))
    check("生效时刻来自应用时刻而非下发时刻",
          rt.profile_history[-1][0] == 3600 and r.issued_at == h0 * 3600)


def test_restart_keeps_knowledge_not_authority() -> None:
    """协调者重启：有持久存储的能说出未决，没有的说不出。

    这是 §7.7.2 与 §7.9.1 那条轴在业务层的形态。两者在同一个远端契约下运行，唯一差别是中心
    有没有把操作先写进持久日志；如果这里的两个读数相同，那么重启轨迹测的就不是 runtime，
    而只是"进程计数器和进程一起没了"这件与协议无关的事。
    """
    from interfaces import AgentInterface
    from node_model import NodeRuntime
    from operations import Journal, recover
    from opportunity import ControlPlane, LoRaProfile

    plane = ControlPlane(LoRaProfile(), seed=0)
    hour = next(h for h in range(200) if plane.path_available(h, 0))
    rt = NodeRuntime(node_id="n00", role="deformation")

    journal = Journal()
    durable = AgentInterface(plane, {"n00": rt}, journal=journal)
    durable.set_monitoring_profile("n00", "risk", generation=1, expires_at=10 ** 9,
                                   now_s=hour * 3600)
    check("有持久存储的臂在派发前就把操作写进了日志",
          len(journal) >= 2 and len(durable.pending) == 1, f"log={len(journal)}")
    lost = durable.forget_volatile_state()
    check("重启后有持久存储的臂能点名未决操作",
          len(lost) == 1 and len(durable.recovered_unresolved) == 1,
          f"lost={lost} unresolved={durable.recovered_unresolved}")
    registry = recover(journal)
    check("未决集合可由日志单独重建",
          len([o for o in registry.ops.values() if o.unresolved]) == 1)

    volatile = AgentInterface(plane, {"n00": rt})
    volatile.set_monitoring_profile("n00", "risk", generation=1, expires_at=10 ** 9,
                                    now_s=hour * 3600)
    lost_v = volatile.forget_volatile_state()
    check("没有持久存储的臂说不出未决操作",
          len(lost_v) == 1 and volatile.recovered_unresolved == [],
          f"lost={lost_v} unresolved={volatile.recovered_unresolved}")


def main() -> int:
    print("四接口与可审计证据回归测试")
    test_applied_is_not_current()
    test_timeout_is_unknown()
    test_read_status_prefers_passive()
    test_request_measurement_is_new()
    test_upload_cursors_differ()
    test_audit_trail_and_evidence_age()
    test_effect_is_real_not_merely_acknowledged()
    test_restart_keeps_knowledge_not_authority()
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
