#!/usr/bin/env python3
"""
test_opportunity.py — the control plane's two load-bearing properties.

1. OPPORTUNITY BOUND. A node offers a downlink opportunity only where its own uplink created
   one. Attempts, not deliveries, are what spend it: an attempt that fails still consumed the
   window. A model that bounds only deliveries would let a runtime retry without limit and still
   look correct.

2. AIRTIME IS REAL. Time on air is preamble plus header plus coded payload at the node's
   spreading factor and bandwidth. Payload bits over a nominal bitrate gives a smaller and wrong
   number, and it is wrong by most exactly for the short frames this deployment sends most of.

Also checked: a command cannot be delivered without an uplink; two different operations queued
for the same node in the same hour do not share one random outcome; a backhaul outage refuses the
command at the center rather than silently dropping it; draws are order-free.

Run: python3 code/experiments/test_opportunity.py
"""
from __future__ import annotations

import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, *(_os.path.join(_CODE, d) for d in ("physics", "runtime",
                                                     "experiments", "analysis", "monitoring"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from opportunity import ControlPlane, LoRaProfile, DownlinkMessage      # noqa: E402
from deterministic import stable_uniform                                # noqa: E402

FAIL: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{('  — ' + detail) if detail else ''}")
    if not ok:
        FAIL.append(name)


def expect_raise(name: str, fn, exc=AssertionError) -> None:
    try:
        fn()
    except exc as e:
        check(name, True, str(e)[:76])
        return
    except Exception as e:                                    # noqa: BLE001
        check(name, False, f"抛出了 {type(e).__name__}: {e}")
        return
    check(name, False, "没有抛错")


# ------------------------------------------------------------------ airtime
def hand_airtime_ms(sf: int, payload_bytes: int, bw_khz: float = 125.0, cr: int = 1,
                    preamble: int = 8) -> float:
    """The Semtech formula written out independently of the implementation under test."""
    tsym = (2 ** sf) / (bw_khz * 1000.0) * 1000.0
    t_pre = (preamble + 4.25) * tsym
    de = 1 if (sf >= 11 and bw_khz == 125.0) else 0
    num = 8 * payload_bytes - 4 * sf + 28 + 16 - 20 * 0
    den = 4 * (sf - 2 * de)
    n_pay = 8 + max(math.ceil(num / den) * (cr + 4), 0)
    return t_pre + n_pay * tsym


def test_airtime() -> None:
    print("\n[1] 空口时间")
    p = LoRaProfile()

    # A widely published anchor: SF12 / BW125 / CR4-5 / 13 B is about 1155 ms.
    anchor = p.time_on_air_ms(12, 13)
    check("SF12, 13 B 落在公开锚点 1155 ms 附近", abs(anchor - 1155.1) < 2.0,
          f"{anchor:.1f} ms")

    worst = 0.0
    for sf in range(7, 13):
        for pl in (9, 20, 38, 100):
            expected = hand_airtime_ms(sf, pl)
            got = p.time_on_air_ms(sf, pl)
            worst = max(worst, abs(got - expected))
    check("全部 SF × 载荷与独立算式一致", worst < 1e-6, f"最大偏差 {worst:.2e} ms")

    # The preamble is a real cost for short frames, so a payload-per-bitrate estimate
    # understates them. Show the size of the error rather than asserting it in prose.
    sf, pl = 12, 9
    naive = 8 * pl / (293.0 * 125.0 / 125.0) * 1000.0        # bits / nominal bitrate
    real = p.time_on_air_ms(sf, pl)
    check("载荷/标称速率会低估短帧", real > naive * 1.5,
          f"真实 {real:.1f} ms 对 近似 {naive:.1f} ms，低估 {100 * (1 - naive / real):.0f}%")

    check("SF7 与 SF12 的差距是数量级",
          p.time_on_air_ms(12, 38) / p.time_on_air_ms(7, 38) > 20.0,
          f"{p.time_on_air_ms(12, 38) / p.time_on_air_ms(7, 38):.1f}x")

    def bad_sf():
        p.time_on_air_ms(13, 38)
    expect_raise("非法 SF 报错", bad_sf, ValueError)


# ------------------------------------------------------------------ the bound
def test_opportunity_bound() -> None:
    print("\n[2] 机会上界：下行机会数 ≤ 上行次数 × 每次上行的下行额度")
    plane = ControlPlane(LoRaProfile(), seed=1, downlink_per_uplink=1)
    node = "r01"
    for identity in range(10):
        plane.center_send(node, DownlinkMessage(identity=f"op:{identity}", kind="command",
                                                payload_bytes=38, enqueued_at=0), hour=0)
    check("十条命令都进了网关队列", plane.queued_count(node) == 10)

    for uplink_index in range(3):
        plane.uplink(node, hour=uplink_index, sf=9, payload_bytes=20)
    plane.check_opportunity_bound()
    check("三次上行只产生三次下行尝试", plane.downlink_attempts == 3,
          f"attempts={plane.downlink_attempts}, uplinks={plane.uplinks}")

    # A retry budget cannot manufacture opportunities.
    for extra in range(50):
        plane.uplink(node, hour=100 + extra, sf=9, payload_bytes=20)
    plane.check_opportunity_bound()
    check("补到 53 次上行后上界仍成立",
          plane.opportunities_used[node] <= plane.downlink_opportunities(node),
          f"used={plane.opportunities_used[node]} limit={plane.downlink_opportunities(node)}")

    # The bound must be breakable, or the assertion proves nothing.
    broken = ControlPlane(LoRaProfile(), seed=1, downlink_per_uplink=1)
    broken.opportunities_used["r01"] = 5
    broken.opportunities_created["r01"] = 2
    expect_raise("人为越界时断言触发", broken.check_opportunity_bound)


def test_no_uplink_no_downlink() -> None:
    print("\n[3] 没有上行就没有下行")
    plane = ControlPlane(LoRaProfile(), seed=2)
    plane.center_send("r01", DownlinkMessage(identity="op:1", kind="command",
                                            payload_bytes=38, enqueued_at=0), hour=0)
    plane.check_opportunity_bound()
    check("仅有入队不产生任何下行尝试", plane.downlink_attempts == 0)
    check("命令仍留在网关队列里", plane.queued_count("r01") == 1)

    rec = plane.uplink("r01", hour=1, sf=9, payload_bytes=20)
    check("第一次上行才产生投递机会", plane.downlink_attempts == 1)
    check("上行记录里绑定的是该次机会", rec.opportunity_index == 0)


def test_downlink_per_uplink() -> None:
    print("\n[4] 每次上行的下行额度是场景参数")
    for budget in (1, 2, 4):
        plane = ControlPlane(LoRaProfile(), seed=3, downlink_per_uplink=budget)
        # Pick an hour where the backhaul is up, or the queue stays empty and the bound is
        # satisfied trivially by nothing happening at all.
        hour = next(h for h in range(200) if plane.backhaul_available(h))
        for identity in range(8):
            plane.center_send("r01", DownlinkMessage(identity=f"op:{identity}",
                                                     kind="command", payload_bytes=38,
                                                     enqueued_at=hour), hour=hour)
        assert plane.queued_count("r01") == 8, "队列必须非空，否则本项平凡通过"
        plane.uplink("r01", hour=hour, sf=9, payload_bytes=20)
        plane.check_opportunity_bound()
        check(f"额度 {budget} 时一次上行最多尝试 {budget} 次",
              plane.downlink_attempts == budget,
              f"attempts={plane.downlink_attempts}, 队列剩 {plane.queued_count('r01')}")

    def bad():
        ControlPlane(LoRaProfile(), seed=3, downlink_per_uplink=0)
    expect_raise("额度为 0 时拒绝构造", bad, ValueError)


def test_identity_separates_draws() -> None:
    print("\n[5] 同节点同小时的不同操作不共享结局")
    node = "r01"
    outcomes = set()
    for identity in range(200):
        plane = ControlPlane(LoRaProfile(), seed=7, downlink_per_uplink=1)
        plane.center_send(node, DownlinkMessage(identity=f"op:{identity}", kind="command",
                                                payload_bytes=38, enqueued_at=0), hour=5)
        plane.uplink(node, hour=5, sf=9, payload_bytes=20)
        outcomes.add(plane.downlink_delivered)
    check("不同 identity 得到两种结局", len(outcomes) == 2, f"结局集合 {outcomes}")

    a = stable_uniform(7, "rx-win", node, 5, 0, "op:1")
    b = stable_uniform(7, "rx-win", node, 5, 0, "op:2")
    check("相邻 identity 的抽样不同", a != b, f"{a:.6f} vs {b:.6f}")

    # order-free: draws do not depend on how many came before
    first = stable_uniform(7, "rx-win", node, 5, 0, "op:1")
    for i in range(500):
        stable_uniform(7, "rx-win", "r02", i, 0, f"op:{i}")
    check("500 次其它抽样后同一键的值不变",
          stable_uniform(7, "rx-win", node, 5, 0, "op:1") == first)


def test_backhaul_and_expiry() -> None:
    print("\n[6] 回传中断与过期")
    # Find an hour where the backhaul is down, then confirm the center is refused, not ignored.
    plane = ControlPlane(LoRaProfile(), seed=11)
    down_hour = next(h for h in range(200) if not plane.backhaul_available(h))
    ok = plane.center_send("r01", DownlinkMessage(identity="op:x", kind="command",
                                                 payload_bytes=38, enqueued_at=down_hour),
                           hour=down_hour)
    check("回传中断时中心被拒绝而非静默丢弃", ok is False and plane.queued_count("r01") == 0,
          f"hour={down_hour}")

    up_hour = next(h for h in range(200) if plane.backhaul_available(h))
    ok2 = plane.center_send("r01", DownlinkMessage(identity="op:y", kind="command",
                                                  payload_bytes=38, enqueued_at=up_hour),
                            hour=up_hour)
    check("回传可用时进入网关队列", ok2 is True and plane.queued_count("r01") == 1)

    # An expired command is dropped without spending an opportunity on it.
    plane2 = ControlPlane(LoRaProfile(), seed=12)
    plane2.center_send("r01", DownlinkMessage(identity="op:stale", kind="command",
                                              payload_bytes=38, enqueued_at=0, expires_at=3),
                       hour=0)
    plane2.uplink("r01", hour=99, sf=9, payload_bytes=20)
    check("过期命令不占用机会", plane2.downlink_attempts == 0 and plane2.downlink_expired == 1,
          f"attempts={plane2.downlink_attempts} expired={plane2.downlink_expired}")
    plane2.check_opportunity_bound()


def test_energy_accounting() -> None:
    print("\n[7] 能量账")
    plane = ControlPlane(LoRaProfile(), seed=13)
    hour = next(h for h in range(200) if plane.backhaul_available(h))
    plane.center_send("r01", DownlinkMessage(identity="op:1", kind="command",
                                            payload_bytes=38, enqueued_at=hour), hour=hour)
    plane.uplink("r01", hour=hour, sf=12, payload_bytes=38)
    e = plane.energy["r01"]
    check("发射与接收分别计费", e.tx_wh > 0 and e.rx_wh > 0,
          f"tx={e.tx_wh:.3e} Wh rx={e.rx_wh:.3e} Wh")

    # The RX window is opened after every uplink even when nothing is waiting to be delivered.
    idle = ControlPlane(LoRaProfile(), seed=13)
    idle.uplink("r01", hour=hour, sf=12, payload_bytes=38)
    check("空队列时接收窗口仍计费", idle.energy["r01"].rx_wh > 0,
          f"rx={idle.energy['r01'].rx_wh:.3e} Wh")

    sf7 = ControlPlane(LoRaProfile(), seed=13)
    sf7.uplink("r01", hour=hour, sf=7, payload_bytes=38)
    check("SF12 上行的能量高于 SF7",
          e.tx_wh > sf7.energy["r01"].tx_wh,
          f"SF12 {e.tx_wh:.3e} Wh 对 SF7 {sf7.energy['r01'].tx_wh:.3e} Wh")


def main() -> int:
    print("控制面机会模型回归测试")
    test_airtime()
    test_opportunity_bound()
    test_no_uplink_no_downlink()
    test_downlink_per_uplink()
    test_identity_separates_draws()
    test_backhaul_and_expiry()
    test_energy_accounting()
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
