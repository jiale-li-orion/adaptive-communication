#!/usr/bin/env python3
"""
test_energy_model.py — verifies the node energy model by hand calculation.

Every expected value below is computed here from the documented formulas and constants
(daylight length from the declination, panel yield, the unit conversion, the ledger in the
module docstring). Nothing is compared against the model's own output, so a wrong model
cannot make a test pass.

Three checks:
  1. daily generation  — the 24 harvested hours sum to panel_w * daylight_h * peak *
                         derate * temperature gain, and the pre-fix 24/dl behaviour would
                         have failed the same assertion by ~2x.
  2. night is dark     — no harvesting outside the daylight window, and the battery falls
                         by the load alone.
  3. heating costs     — a heated node ends strictly lower, by exactly heat_w * cold hours.

Plus the capacity clip, the per-chemistry capacity curve, and the alive threshold.

Section 4 also pins three defects this task did not fix, so a later change to them is visible:
a fresh node starts above capacity_Wh(T) at a cold ambient (4d), `alive` is never reset to
False while the state is positive (4h), and the flag only turns True above the 5 % threshold
(4e/4i). Each is reported as current behaviour rather than asserted as correct.

Run:  PYTHONPATH="$PWD/libs/pylibs" python3 code/experiments/test_energy_model.py
Exit: 0 if every check passes.
"""
from __future__ import annotations

# --- module resolution -------------------------------------------------------
import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, *(_os.path.join(_CODE, d) for d in ("physics", "runtime",
                                                     "experiments", "analysis"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)
# -----------------------------------------------------------------------------

import math

import numpy as np

from energy import CHEMISTRY, DOD, PEAK_FACTOR, SYSTEM_DERATE, NodeEnergy  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


def close(a: float, b: float, tol: float = 1e-9) -> bool:
    return abs(a - b) <= tol * max(1.0, abs(b))


# ------------------------------------------------------------------ hand formulas
def hand_declination_deg(doy: int) -> float:
    """Cooper's equation, the same form the module uses."""
    return 23.44 * math.sin(math.radians(360.0 * (284 + doy) / 365.0))


def hand_daylight_h(doy: int, lat_deg: float) -> float:
    cos_h = -math.tan(math.radians(lat_deg)) * math.tan(math.radians(hand_declination_deg(doy)))
    cos_h = max(-1.0, min(1.0, cos_h))
    return 2.0 * math.degrees(math.acos(cos_h)) / 15.0


def hand_window_h(doy: int, lat_deg: float) -> tuple[float, float]:
    """Sunrise and sunset as hours from midnight; the window is centred on 12:00."""
    half = hand_daylight_h(doy, lat_deg) / 2.0
    return 12.0 - half, 12.0 + half


def hand_temp_gain(temp_c: float) -> float:
    return 1.0 + max(0.0, (25.0 - temp_c)) * 0.0035


def hand_daily_wh(panel_w: float, daylen_h: float, temp_c: float) -> float:
    """The panel's whole-day yield: W * h * dimensionless factors -> Wh."""
    return panel_w * daylen_h * PEAK_FACTOR * SYSTEM_DERATE * hand_temp_gain(temp_c)


def hand_overlap_h(hour: int, rise: float, set_: float) -> float:
    return max(0.0, min(hour + 1.0, set_) - max(float(hour), rise))


def make_node(**kw) -> NodeEnergy:
    """A node with a deterministic trace: snow off, no temperature noise once frozen."""
    base = dict(elev_m=3925.0, lat_deg=30.33, panel_w=100.0, batt_wh_nom=6000.0,
                load_w=0.67, chemistry="LiFePO4", rng=np.random.default_rng(11),
                snow_prob_winter=0.0, temp_offset_c=0.0, heated=False)
    base.update(kw)
    return NodeEnergy(**base)


def freeze(node: NodeEnergy, daylen_h: float, temp_c: float, snow: int = 0) -> None:
    """Hold the panel term at a hand-computable value: fixed temperature, given snow state.

    The daylight length stays the model's own; `daylen_h` is the hand-computed length and
    check 1a confirms the two agree.
    """
    node._temp_c = lambda doy: temp_c                       # type: ignore[method-assign]
    node.snow_left = snow


def fresh_state_overshoot() -> float:
    """How far above capacity_Wh(T) the constructor leaves a fresh node at T = -20 C.

    The constructor sets the state to `usable_wh`, the reference-temperature usable energy,
    which at a cold ambient exceeds capacity_Wh(T), so the first step clips it down by this
    much (check 4d). In no test below is a node started from the constructor default.
    """
    node = make_node()
    return node.bat_wh - node.capacity_Wh(-20.0)


# ------------------------------------------------------------------ test 1
def t1_daily_generation() -> None:
    doy, lat, panel_w, temp_c = 172, 30.33, 100.0, 7.0
    daylen = hand_daylight_h(doy, lat)
    rise, set_ = hand_window_h(doy, lat)
    expected = hand_daily_wh(panel_w, daylen, temp_c)
    unit = expected / daylen                       # Wh per full hour of daylight
    buggy = expected * 24.0 / daylen               # the pre-fix daily total

    node = make_node(panel_w=panel_w, lat_deg=lat)
    freeze(node, daylen, temp_c)
    per_hour = [node._generation_hour_wh(doy, temp_c, h) for h in range(24)]
    total_gen = sum(per_hour)
    load_total = 24.0 * node.load_wh_per_tick

    print(f"       doy={doy}, lat={lat} N, panel={panel_w:.0f} W, T fixed at {temp_c:.1f} C")
    print(f"       hand daylight length        = {daylen:.6f} h  "
          f"(model {node._daylight_h(doy):.6f} h)")
    print(f"       hand daylight window        = [{rise:.4f}, {set_:.4f}] h")
    print(f"       hand daily generation       = {expected:.6f} Wh  "
          f"= {panel_w:.0f} W * {daylen:.6f} h * {PEAK_FACTOR} * {SYSTEM_DERATE} * "
          f"{hand_temp_gain(temp_c):.6f}")
    print(f"       harvested over 24 h         = {total_gen:.6f} Wh")
    print(f"       pre-fix behaviour           = {buggy:.6f} Wh  "
          f"({buggy / expected:.4f}x the hand figure, over by {buggy - expected:.3f} Wh)")

    check("1a daylight length matches the hand formula", close(node._daylight_h(doy), daylen),
          f"{node._daylight_h(doy):.6f} vs {daylen:.6f} h")
    check("1b harvested 24 h energy equals the hand daily figure", close(total_gen, expected),
          f"{total_gen:.9f} vs {expected:.9f} Wh")
    check("1c the pre-fix 24/dl behaviour would FAIL check 1b at a 1 % tolerance",
          not close(buggy, expected, 0.01),
          f"old {buggy:.3f} Wh vs hand {expected:.3f} Wh, tolerance {0.01 * expected:.3f} Wh")

    interior = [h for h in range(24) if hand_overlap_h(h, rise, set_) >= 1.0]
    worst = max(abs(per_hour[h] - unit) for h in interior)
    check("1d each full daylight hour carries daily_wh / daylight_h", worst <= 1e-9,
          f"{len(interior)} full hours at {unit:.6f} Wh each, worst deviation {worst:.3e} Wh")

    # the same 24 h through the public step(), on a pack with room to spare
    # the same 24 h through the public step(), with enough headroom that nothing clips: the
    # pack must have room for a whole day of generation or the clip silently discards it
    led = make_node(panel_w=panel_w, lat_deg=lat, batt_wh_nom=8000.0)
    freeze(led, daylen, temp_c)
    hand_start = 1.5 * expected
    led.bat_wh = hand_start
    assert hand_start + expected < led.capacity_Wh(temp_c)
    assert hand_start - load_total > 0.05 * led.usable_wh
    hand_state = hand_start
    harvested = 0.0
    worst_state = 0.0
    clipped = False
    for h in range(24):
        hand_state += per_hour[h] - led.load_wh_per_tick
        clipped = clipped or hand_state > led.capacity_Wh(temp_c)
        hand_state = min(hand_state, led.capacity_Wh(temp_c))
        led.step(doy)
        harvested += led.hourly_gen_wh
        worst_state = max(worst_state, abs(led.bat_wh - hand_state))
    check("1e step() books the same energy as the hand sum", close(harvested, expected),
          f"{harvested:.9f} vs {expected:.9f} Wh")
    check("1f step() follows the hand ledger hour by hour",
          (not clipped) and worst_state <= 1e-12,
          f"no clipping needed; worst deviation {worst_state:.3e} Wh over 24 steps; final "
          f"{led.bat_wh:.6f} vs hand {hand_state:.6f} Wh")
    check("1g the day's net gain is the hand generation minus the hand load",
          close((led.bat_wh - hand_start) + load_total, expected, 1e-9),
          f"{(led.bat_wh - hand_start) + load_total:.6f} vs {expected:.6f} Wh")


# ------------------------------------------------------------------ test 2
def t2_night_is_dark() -> None:
    doy, lat, temp_c = 80, 30.33, 7.0          # 21 March: a clean 12 h window
    daylen = hand_daylight_h(doy, lat)
    rise, set_ = hand_window_h(doy, lat)
    load = 0.67

    lit = [h for h in range(24) if hand_overlap_h(h, rise, set_) > 0.0]
    dark = [h for h in range(24) if h not in lit]

    node = make_node(lat_deg=lat, load_w=load)
    freeze(node, daylen, temp_c)
    start = 0.5 * node.capacity_Wh(temp_c)      # below the clip bound: the bound cannot mask
    node.bat_wh = start                         # a night-hour change, and above the threshold

    dark_gen = 0.0
    dark_drops: list[float] = []
    light_gen = 0.0
    alive = True
    for h in range(24):
        before = node.bat_wh
        alive = node.step(doy)
        if h in dark:
            dark_gen += node.hourly_gen_wh
            dark_drops.append(before - node.bat_wh)
        else:
            light_gen += node.hourly_gen_wh
    end_hand = start - 24.0 * load + light_gen
    print(f"       doy={doy}, lat={lat} N, T fixed at {temp_c:.1f} C, load {load} W")
    print(f"       hand window = [{rise:.4f}, {set_:.4f}] h -> {len(lit)} lit hours "
          f"({lit[0]}..{lit[-1]}), {len(dark)} dark hours")
    print(f"       harvested in the dark hours   = {dark_gen!r} Wh")
    print(f"       harvested in the lit hours    = {light_gen:.6f} Wh  "
          f"(hand daily figure {hand_daily_wh(100.0, daylen, temp_c):.6f} Wh)")
    print(f"       battery {start:.4f} -> {node.bat_wh:.4f} Wh  "
          f"(hand {end_hand:.4f} Wh), alive={alive}")

    check("2a every dark hour harvests exactly zero", dark_gen == 0.0,
          f"sum over {len(dark)} dark hours = {dark_gen!r} Wh")
    check("2b every dark hour falls by exactly the load",
          all(close(d, load, 1e-12) for d in dark_drops),
          f"{len(dark_drops)} dark hours, drops {sorted({round(d, 12) for d in dark_drops})} Wh")
    check("2c the dark hours are exactly the complement of the daylight window",
          len(dark) > 0 and len(lit) + len(dark) == 24, f"lit {lit} / dark {dark}")
    check("2d daylight hours do harvest", light_gen > 0.0, f"{light_gen:.6f} Wh in lit hours")
    check("2e the whole-day change equals the hand ledger",
          close(node.bat_wh, end_hand, 1e-12),
          f"{node.bat_wh:.9f} vs {end_hand:.9f} Wh")


# ------------------------------------------------------------------ test 3
def t3_heating_costs() -> None:
    doy, lat, temp_c, heat_w, panel_w = 15, 30.33, -8.0, 8.0, 8.0
    daylen = hand_daylight_h(doy, lat)
    gate = 5.0                                   # the LiFePO4 charge gate

    plain = make_node(lat_deg=lat, panel_w=panel_w, heated=False, heat_w=heat_w)
    warm = make_node(lat_deg=lat, panel_w=panel_w, heated=True, heat_w=heat_w)
    freeze(plain, daylen, temp_c)
    freeze(warm, daylen, temp_c)
    start = 0.5 * warm.capacity_Wh(temp_c)       # identical state, below the clip bound
    plain.bat_wh = start
    warm.bat_wh = start

    # hand figures: a flat -8 C trace, so every hour in the daylight window gets the same
    # energy; at -8 C the unheated LiFePO4 sits below its gate and harvests nothing
    daily_warm = hand_daily_wh(panel_w, daylen, temp_c)
    unit_warm = daily_warm / daylen
    hand_gen = sum(unit_warm * hand_overlap_h(h, *hand_window_h(doy, lat)) for h in range(24))
    expected_heat_wh = heat_w * 24.0
    expected_diff = expected_heat_wh - hand_gen

    heat_used = 0.0
    gen_plain = gen_warm = 0.0
    for _ in range(24):
        plain.step(doy)
        warm.step(doy)
        heat_used += heat_w if warm.heating_active else 0.0
        gen_plain += plain.hourly_gen_wh
        gen_warm += warm.hourly_gen_wh

    diff = plain.bat_wh - warm.bat_wh
    print(f"       doy={doy}, T fixed at {temp_c:.1f} C, charge gate {gate:.1f} C, "
          f"heat_w {heat_w} W, panel {panel_w:.0f} W")
    print(f"       unheated battery             = {plain.bat_wh:.6f} Wh  "
          f"(harvested {gen_plain:.6f} Wh: below the gate, gated to zero)")
    print(f"       heated battery               = {warm.bat_wh:.6f} Wh  "
          f"(harvested {gen_warm:.6f} Wh, hand {hand_gen:.6f} Wh)")
    print(f"       difference                   = {diff:.6f} Wh")
    print(f"       hand heating cost            = heat_w * cold_hours = {heat_w} W * 24 h "
          f"= {expected_heat_wh:.6f} Wh")
    print(f"       hand difference              = heat cost - heated generation = "
          f"{expected_heat_wh:.6f} - {hand_gen:.6f} = {expected_diff:.6f} Wh")
    print(f"       heating active for {heat_used / heat_w:.1f} h")

    check("3a the heated node ends strictly lower", warm.bat_wh < plain.bat_wh,
          f"{warm.bat_wh:.6f} < {plain.bat_wh:.6f} Wh")
    check("3b the difference equals the hand heating cost minus the hand generation",
          close(diff, expected_diff, 1e-9),
          f"{diff:.9f} vs {expected_diff:.9f} Wh")
    check("3c the heating draw is exactly heat_w * cold hours, by hand",
          close(heat_used, expected_heat_wh, 1e-12),
          f"{heat_used:.6f} vs {expected_heat_wh:.6f} Wh")
    check("3d heating is off at or above the gate",
          not make_node(heated=True)._heat_on(gate),
          f"_heat_on({gate}) = {make_node(heated=True)._heat_on(gate)}")
    vrla = make_node(chemistry="VRLA", heated=True)
    check("3e a chemistry that charges cold pays no heating", not vrla._heat_on(-8.0),
          f"gate {vrla.charge_gate_c}, can_charge_cold={vrla.can_charge_cold}")


# ------------------------------------------------------------------ clipping / curve / alive
def t4_clip_curve_and_alive() -> None:
    doy, lat, temp_c = 172, 30.33, 7.0
    daylen = hand_daylight_h(doy, lat)

    # (i) clipping: a tiny pack with a huge panel must never exceed capacity_Wh(t)
    tiny = make_node(lat_deg=lat, batt_wh_nom=2.0, panel_w=600.0)
    freeze(tiny, daylen, temp_c)
    cap = tiny.capacity_Wh(temp_c)
    hand_cap = 2.0 * tiny.derate * DOD * tiny._capacity_fraction(temp_c)
    over = 0.0
    for _ in range(48):
        tiny.step(doy)
        over = max(over, tiny.bat_wh - tiny.capacity_Wh(temp_c))
    print(f"       tiny pack capacity_Wh({temp_c:.0f} C) = {cap:.6f} Wh  "
          f"(hand 2.0 * {tiny.derate} * {DOD} * {tiny._capacity_fraction(temp_c):.6f} "
          f"= {hand_cap:.6f} Wh)")

    # (ii) the curve reproduces each chemistry's documented derate at -20 C
    print("       chemistry capacity fraction at -20 C:")
    curve_ok = True
    for chem, entry in CHEMISTRY.items():
        derate = entry[0]
        got = make_node(chemistry=chem)._capacity_fraction(-20.0)
        ok = close(got, derate)
        curve_ok = curve_ok and ok
        print(f"         {chem:<10} documented {derate:.2f}, curve {got:.6f}  "
              f"{'ok' if ok else 'MISMATCH'}")

    check("4a capacity_Wh matches the hand product", close(cap, hand_cap),
          f"{cap:.9f} vs {hand_cap:.9f} Wh")
    check("4b state of charge never exceeds capacity_Wh(t)", over <= 0.0,
          f"worst overflow {over:.3e} Wh over 48 steps")
    check("4c every chemistry's curve reproduces its documented -20 C derate", curve_ok)
    # below the measured end of the curve the derate is held, not driven to zero: a pack still
    # holds charge at -40 C, while a zero capacity would zero the state and kill the node
    cold_ok = True
    for chem, entry in CHEMISTRY.items():
        frac = make_node(chemistry=chem)._capacity_fraction(-40.0)
        cold_ok = cold_ok and frac > 0.0 and close(frac, entry[0])
    check("4c2 capacity holds at the measured derate below -20 C, never zero", cold_ok,
          "checked -40 C on all three chemistries")

    # (iii) a fresh node's stored energy exceeds capacity_Wh(T) when the ambient is cold
    fresh = make_node(lat_deg=lat)               # the constructor sets bat_wh = usable_wh
    cold_cap = fresh.capacity_Wh(-20.0)
    hand_overshoot = fresh.usable_wh * (1.0 - fresh._capacity_fraction(-20.0))
    print(f"       fresh node: bat_wh {fresh.bat_wh:.1f} Wh, usable_wh {fresh.usable_wh:.1f} Wh, "
          f"capacity_Wh(-20 C) {cold_cap:.1f} Wh -> starts "
          f"{fresh_state_overshoot():.1f} Wh above its own clip bound at -20 C")
    check("4d the first step clips a fresh node to capacity_Wh(T) at a cold ambient",
          fresh.bat_wh > cold_cap and close(fresh_state_overshoot(), hand_overshoot, 1e-12),
          f"{fresh.bat_wh:.6f} > {cold_cap:.6f} Wh at -20 C, overshoot "
          f"{fresh_state_overshoot():.6f} vs hand {hand_overshoot:.6f} Wh "
          f"(reported, not fixed here)")

    # (iv) alive never turns True at or below 5 % of usable energy.
    #     A freshly constructed node is already alive and no branch resets the flag while the
    #     state is positive, so the flag has to be cleared before each case for the assertion
    #     to mean anything.
    node = make_node(lat_deg=lat)
    freeze(node, daylen, -20.0)                  # below the gate: no generation can mask it
    thr = 0.05 * node.usable_wh
    flipped_low = False
    for x in (0.0, 1e-3, 0.25, 0.999):
        mid = x * thr
        node.bat_wh = mid + 1e-9 * (thr - mid)   # a hair above x*thr, exactly x*thr when x=0
        node.alive = False
        if node.step(doy):
            flipped_low = True
    print(f"       alive threshold = 5 % of usable_wh = {thr:.6f} Wh "
          f"(usable_wh {node.usable_wh:.6f} Wh, capacity_Wh(-20 C) "
          f"{node.capacity_Wh(-20.0):.6f} Wh)")
    check("4e alive never turns True at or below the 5 % threshold", not flipped_low,
          f"threshold {thr:.6f} Wh, checked 0 / 0.1 % / 25 % / 99.9 % of it")
    check("4f the threshold is exactly 0.05 * usable_wh",
          close(0.05 * node.usable_wh, thr, 1e-12), f"{thr:.9f} Wh")
    # the same node does report True once the state passes the threshold
    node.bat_wh = 1.3 * thr
    node.alive = False
    check("4g alive turns True once the state passes the threshold", node.step(doy),
          f"bat_wh {node.bat_wh:.6f} Wh vs threshold {thr:.6f} Wh")
    # and it is NOT reset to False while the state is positive but below the threshold:
    # neither branch runs above 0 Wh, so a live node stays flagged alive at any charge level.
    # Reported as a separate defect; this check pins the current behaviour.
    latch = make_node(lat_deg=lat)
    freeze(latch, daylen, -20.0)
    latch.bat_wh = 0.5 * thr
    latch.alive = True
    latch.step(doy)
    check("4h a live node below the 5 % threshold is not flagged dead (current behaviour)",
          latch.alive and latch.bat_wh > 0.0,
          f"bat_wh {latch.bat_wh:.6f} Wh is below threshold {thr:.6f} Wh but alive={latch.alive}")

    # (v) the state lands exactly on the threshold: strictly greater is required, so False
    edge = make_node(lat_deg=lat, batt_wh_nom=1024.0)
    freeze(edge, daylen, temp_c, snow=1)         # no generation
    edge_thr = 0.05 * edge.usable_wh
    edge.bat_wh = edge_thr + edge.load_wh_per_tick
    edge.alive = False
    edge_delta = edge.bat_wh - edge_thr
    edge.alive = edge.step(doy)
    check("4i alive is False when the state ends exactly on the threshold",
          (not edge.alive) and close(edge.bat_wh, edge_thr, 1e-12),
          f"bat_wh {edge.bat_wh!r} Wh, threshold {edge_thr!r} Wh "
          f"(met exactly: {close(edge.bat_wh, edge_thr, 1e-12)}, margin was "
          f"{edge_delta!r} Wh, alive={edge.alive})")

    # (vi) recovery: an empty pack under a buried panel stays dead at 0 Wh
    dead = make_node(lat_deg=lat, batt_wh_nom=40.0, panel_w=2000.0)
    freeze(dead, daylen, temp_c, snow=1)
    dead.bat_wh = 0.0
    dead.alive = False
    dead.step(doy)
    stayed_dead = (not dead.alive) and dead.bat_wh == 0.0
    check("4j an empty pack under a buried panel stays dead at 0 Wh", stayed_dead,
          f"alive={dead.alive}, bat_wh={dead.bat_wh:.6f}")

    # (vii) with charging restored the flag flips only once above the threshold
    freeze(dead, daylen, temp_c)                 # snow cleared, panel live again
    dead.bat_wh = 0.0
    dead.alive = False
    early_flip = False
    for _ in range(24):
        dead.step(doy)
        if dead.alive and dead.bat_wh <= 0.05 * dead.usable_wh:
            early_flip = True
    check("4k alive only turns True above the threshold once charging resumes",
          (not early_flip) and dead.alive,
          f"alive={dead.alive}, bat_wh={dead.bat_wh:.6f} Wh vs threshold "
          f"{0.05 * dead.usable_wh:.6f} Wh")

# ------------------------------------------------------------------ runner
def main() -> int:
    print("=" * 78)
    print("NODE ENERGY MODEL — VERIFICATION BY HAND CALCULATION")
    print("=" * 78)
    t1_daily_generation()
    print()
    t2_night_is_dark()
    print()
    t3_heating_costs()
    print()
    t4_clip_curve_and_alive()
    print()
    failed = [n for n, ok, _ in RESULTS if not ok]
    print("=" * 78)
    print(f"{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed")
    for n in failed:
        print(f"  FAILED: {n}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
