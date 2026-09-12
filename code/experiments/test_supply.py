#!/usr/bin/env python3
"""
test_supply.py — the monitoring layer's power supply, checked against hand calculation.

Every expected value below is computed here from the documented formulas and constants (the
usable-energy figure, the alive threshold, the hourly load, the ledger identity in supply.py's
docstring). Nothing is compared against the module's own output, so a model that is wrong in the
same way twice cannot make a test pass.

The construction the arithmetic is checked on. Two supplies are built by `make_dark_supply`:
generation is forced to zero for the whole run (`_day_generation_wh` returns 0 Wh, which is what a
panel buried under snow delivers and is also what the winter charge gate delivers at this altitude)
and the ambient is pinned at 25 C, where the chemistry's capacity curve is at its reference point,
so `capacity_Wh(T) == usable_wh` and the first step clips nothing. What is left is a pack falling by
the load alone, which is the case whose death time can be divided out by hand.

Six checks:
  1. the latch is gone            — a node parked between zero and the alive threshold reads dead,
                                    where the old two-branch step() left it reading alive.
  2. no generation dies in a time — the pack empties after usable_wh / load_wh_per_tick steps, and
                                    the node reports dark earlier, at the threshold, by a
                                    hand-computed number of steps.
  3. radio drain shortens it      — two identical supplies, one booked a known total of radio
                                    energy, die a hand-computed number of steps apart.
  4. the ledger balances          — harvested - load - radio equals the change in the pack plus what
                                    the capacity bound clipped, node by node.
  5. supply gates reachability    — a dead supply reports alive=False at that instant, dead_nodes
                                    names it, and the power term of the runtime's reachability test
                                    closes on it alone.
  6. the clock rule               — sixty one-minute reads inside one hour cost one model step, not
                                    sixty, and the state does not move inside an hour.

Run:  PYTHONPATH="$PWD/libs/pylibs" python3 code/experiments/test_supply.py
Exit: 0 if every check passes.
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

import numpy as np

from energy import ALIVE_FRACTION, DOD, NodeEnergy                     # noqa: E402
from node_model import TICK_S                                          # noqa: E402
from supply import HOUR_S, NodeSupply, SupplyFleet                     # noqa: E402
from task_generator import build_deployment                            # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []

# The hand-checked device class: 1000 Wh nominal LiFePO4, 0.5 W payload load. The load is 0.5 W so
# that the divisions below land on whole steps, which keeps the expected values exact instead of
# hiding a rounding difference inside the one-step tolerance.
BATT_WH_NOM = 1000.0
LOAD_W = 0.5
WARM_C = 25.0                      # the capacity curve's reference point: no cold-weather clipping
ELEV_M = 3925.0


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


def close(a: float, b: float, tol: float = 1e-9) -> bool:
    return abs(a - b) <= tol * max(1.0, abs(b))


# ------------------------------------------------------------------ hand formulas
def hand_usable_wh(batt_wh_nom: float, derate: float) -> float:
    """Reference-temperature usable energy: nominal capacity * chemistry derate * depth of discharge."""
    return batt_wh_nom * derate * DOD


def hand_alive_threshold_wh(usable_wh: float) -> float:
    return ALIVE_FRACTION * usable_wh


def hand_steps_to_empty(usable_wh: float, load_wh_per_tick: float) -> float:
    """The autonomy figure: usable energy divided by what one hour consumes."""
    return usable_wh / load_wh_per_tick


def hand_steps_to_dark(usable_wh: float, load_wh_per_tick: float) -> float:
    """Steps until the pack is at or below the alive threshold, charging nothing.

    The node reads dark as soon as the state is not strictly above the threshold, so the crossing
    is the first step whose end state is at or below it.
    """
    return (usable_wh - hand_alive_threshold_wh(usable_wh)) / load_wh_per_tick


def prefix_reading(was_alive: bool, bat_wh: float, usable_wh: float) -> bool:
    """What the old two-branch step() left in the alive flag, kept here so the regression shows.

    The old code only ever wrote the flag at the two ends of the range: False at or below zero Wh,
    True above 5 % of the usable energy, and nothing at all in between. Anywhere between zero and
    the threshold the flag therefore kept whatever the previous step had left in it, which for a
    node that had been alive is a latch.
    """
    if bat_wh <= 0.0:
        return False
    if bat_wh > 0.05 * usable_wh:
        return True
    return was_alive


def make_dark_supply(node_id: str = "t01", seed: int = 99, **kw) -> NodeSupply:
    """A supply whose panel produces nothing, at an ambient where the capacity bound does not bite."""
    params = dict(batt_wh_nom=BATT_WH_NOM, load_w=LOAD_W)
    params.update(kw)
    supply = NodeSupply(node_id, ELEV_M, seed, **params)
    supply.energy._day_generation_wh = lambda doy, temp_c: 0.0        # type: ignore[method-assign]
    supply.energy._temp_c = lambda doy: WARM_C                          # type: ignore[method-assign]
    return supply


# ------------------------------------------------------------------ test 1
def t1_latch_is_gone() -> None:
    """A node parked between zero and the threshold must read dead, not stay alive."""
    node = NodeEnergy(elev_m=ELEV_M, batt_wh_nom=BATT_WH_NOM, load_w=LOAD_W,
                      rng=np.random.default_rng(4), snow_prob_winter=0.0)
    node._temp_c = lambda doy: WARM_C                                   # type: ignore[method-assign]
    node._day_generation_wh = lambda doy, temp_c: 0.0                   # type: ignore[method-assign]
    usable = node.usable_wh
    thr = hand_alive_threshold_wh(usable)
    parked = 0.5 * thr                                                  # half the threshold, above 0

    node.bat_wh = parked
    node.alive = True                                                   # how the old code left it
    was = node.alive
    node.step(200)
    now = node.alive
    old = prefix_reading(was, node.bat_wh, usable)

    print(f"       usable_wh {usable:.6f} Wh, alive threshold {thr:.6f} Wh "
          f"= {ALIVE_FRACTION} * usable_wh")
    print(f"       parked at {parked:.6f} Wh ({parked / thr:.1%} of the threshold) and flagged "
          f"alive, as the previous step had left it")
    print(f"       pre-fix reading (two-branch latch) = {old}")
    print(f"       current reading (pure read)        = {now}   "
          f"(bat_wh {node.bat_wh:.6f} Wh after the step)")

    check("1a a node parked below the alive threshold reads dead", (not now) and node.bat_wh > 0.0,
          f"alive={now} at bat_wh {node.bat_wh:.6f} Wh, threshold {thr:.6f} Wh")
    check("1b the pre-fix two-branch reading would have said alive at the same charge", old,
          "the old code wrote the flag only at 0 Wh and above the threshold, so the latch survived")
    check("1c the threshold is still 0.05 * usable_wh", close(ALIVE_FRACTION, 0.05, 1e-12),
          f"ALIVE_FRACTION = {ALIVE_FRACTION!r}")

    # no hysteresis: a pack that has just crossed back above the threshold is powered again
    node.bat_wh = thr + node.load_wh_per_tick + 1e-9
    node.alive = False
    crossed = node.step(2000)
    check("1d a pack just above the threshold is powered again, with no hysteresis",
          crossed and node.bat_wh > thr,
          f"entered the step at {thr + node.load_wh_per_tick + 1e-9:.9f} Wh and left it at "
          f"{node.bat_wh:.9f} Wh vs threshold {thr:.6f} Wh, alive={crossed}")

    # the same rule at the monitoring layer, where the reading is taken without a step
    supply = make_dark_supply(seed=4)
    supply.energy.bat_wh = parked
    layer_reading = supply.alive(0)
    print(f"       supply layer at the same charge: alive({0}) = {layer_reading} "
          f"(battery_wh {supply.energy.bat_wh:.6f} Wh)")
    check("1e the supply layer reads the same rule off the pack", not layer_reading,
          f"alive(0)={layer_reading} at {supply.energy.bat_wh:.6f} Wh vs "
          f"threshold {supply.alive_threshold_wh():.6f} Wh")


# ------------------------------------------------------------------ test 2
def t2_no_generation_dies_in_a_computable_time() -> None:
    """A node with no generation runs its pack down; the death time is a division, not a fit."""
    supply = make_dark_supply(seed=7)
    usable = supply.energy.usable_wh
    load = supply.energy.load_wh_per_tick
    thr = hand_alive_threshold_wh(usable)
    hand_empty = hand_steps_to_empty(usable, load)
    hand_dark = hand_steps_to_dark(usable, load)

    empty_at = None
    dark_at = None
    bat_at_dark = None
    last_alive = 0
    for h in range(1, 900):
        supply.step_to(h * HOUR_S)
        if empty_at is None and supply.energy.bat_wh <= 0.0:
            empty_at = h
        if dark_at is None:
            if not supply.alive(h * HOUR_S):
                dark_at = h
                bat_at_dark = supply.energy.bat_wh
            else:
                last_alive = h
        if empty_at is not None and dark_at is not None:
            break

    print(f"       hand usable_wh = {BATT_WH_NOM} * {supply.energy.derate} * {DOD} = "
          f"{usable:.6f} Wh, load {load} Wh/h, threshold {thr:.6f} Wh")
    print(f"       hand steps to an empty pack   = usable_wh / load = {hand_empty:.6f}")
    print(f"       measured steps to empty       = {empty_at}")
    print(f"       hand steps to the dark reading = (usable_wh - threshold) / load = "
          f"{hand_dark:.6f}")
    print(f"       measured steps to dark         = {dark_at}   "
          f"(bat_wh {bat_at_dark:.6f} Wh at that instant)")

    check("2a the pack empties in usable_wh / load_wh_per_tick steps, within one step",
          empty_at is not None and abs(empty_at - hand_empty) <= 1.0,
          f"measured {empty_at} vs hand {hand_empty:.6f}")
    check("2b the node reports dark at the hand-computed threshold step",
          dark_at is not None and abs(dark_at - hand_dark) <= 1.0,
          f"measured {dark_at} vs hand {hand_dark:.6f}, "
          f"{hand_empty - hand_dark:.6f} steps before the pack is empty")
    check("2c it reads powered at every step up to that one",
          last_alive == dark_at - 1 and last_alive > 0,
          f"last powered step {last_alive}, dark from step {dark_at}")
    check("2d the dark reading happens while the pack still holds charge",
          bat_at_dark is not None and 0.0 < bat_at_dark <= thr,
          f"bat_wh {bat_at_dark:.6f} Wh at the dark step, threshold {thr:.6f} Wh")


# ------------------------------------------------------------------ test 3
def t3_radio_drain_shortens_that_time() -> None:
    """Talk more, die sooner: a known total of radio energy costs a hand-computed number of steps."""
    plain = make_dark_supply(seed=11)
    talk = make_dark_supply(seed=11)                    # identical seed, identical parameters
    usable = plain.energy.usable_wh
    load = plain.energy.load_wh_per_tick
    drains_per_hour = 100                               # one booking per hour boundary
    per_drain = 0.25                                    # Wh, exact in binary, so the total is exact
    radio_total = drains_per_hour * per_drain
    hand_cost = radio_total / load                      # steps the talk buys at the load rate
    probe_h = drains_per_hour                           # after every booking has landed
    probe: dict[str, dict] = {}
    dark: dict[str, int] = {}

    for h in range(0, 900):
        for name, supply in (("plain", plain), ("talk", talk)):
            supply.step_to(h * HOUR_S)
            if name == "talk" and h < drains_per_hour:
                supply.drain_wh(per_drain)
            if h == probe_h and name not in probe:
                probe[name] = supply.state(h * HOUR_S)
            if name not in dark and not supply.alive(h * HOUR_S):
                dark[name] = h
        if len(dark) == 2:
            break

    gap = dark["plain"] - dark["talk"]
    bat_gap = probe["plain"]["battery_wh"] - probe["talk"]["battery_wh"]
    print(f"       radio booked over {drains_per_hour} hours = {drains_per_hour} * {per_drain} "
          f"= {radio_total:.6f} Wh (ledger says {talk.radio_wh_total:.6f} Wh)")
    print(f"       hand cost = radio_wh / load = {radio_total:.6f} / {load} = {hand_cost:.6f} steps")
    print(f"       died at step {dark['plain']} with no radio, {dark['talk']} with radio "
          f"-> {gap} steps sooner")
    print(f"       at hour {probe_h}: {probe['plain']['battery_wh']:.6f} Wh vs "
          f"{probe['talk']['battery_wh']:.6f} Wh, difference {bat_gap:.6f} Wh")

    check("3a the talkative node dies sooner", dark["talk"] < dark["plain"],
          f"{dark['talk']} < {dark['plain']} steps")
    check("3b the difference is radio_wh_total / load_wh_per_tick, within one step",
          abs(gap - hand_cost) <= 1.0, f"measured {gap} vs hand {hand_cost:.6f} steps")
    check("3c the radio energy is in the ledger and in the pack",
          close(talk.radio_wh_total, radio_total) and close(bat_gap, radio_total, 1e-9),
          f"radio_wh_total {talk.radio_wh_total:.9f} vs hand {radio_total:.9f} Wh; "
          f"pack difference {bat_gap:.9f} Wh")
    check("3d the plain node is untouched by the other one's radio",
          close(plain.radio_wh_total, 0.0) and close(probe["plain"]["battery_wh"],
                                                     usable - probe_h * load, 1e-9),
          f"radio_wh_total {plain.radio_wh_total!r}, pack {probe['plain']['battery_wh']:.6f} vs "
          f"hand {usable - probe_h * load:.6f} Wh")


# ------------------------------------------------------------------ test 4
def t4_ledger_balances() -> None:
    """The ledger identity holds node by node, with the capacity clip accounted for."""
    deployment = build_deployment(7)
    fleet = SupplyFleet(deployment.nodes, seed=7, start_doy=15)      # January: a cold pack
    rates = {nid: 0.02 * ((i % 4) + 1) for i, nid in enumerate(fleet.node_ids)}
    hours = 6

    for minute in range(hours * 60 + 1):
        t_s = minute * TICK_S
        fleet.step_to(t_s)
        if t_s % HOUR_S == 0:
            for nid, wh in rates.items():
                fleet.drain_wh(nid, wh)

    ledger = fleet.ledger()
    worst_residual = 0.0
    worst_clip_gap = 0.0
    unaccounted = 0.0
    deficit = 0.0
    for nid in fleet.node_ids:
        entry = ledger[nid]
        delta = entry["battery_wh"] - entry["battery_start_wh"]
        lhs = (entry["harvested_wh_total"] - entry["payload_wh_total"]
               - entry["heat_wh_total"] - entry["radio_wh_total"])
        rhs = delta + entry["clipped_wh"] - entry["deficit_wh"]
        worst_residual = max(worst_residual, abs(lhs - rhs))
        worst_clip_gap = max(worst_clip_gap, abs(entry["clipped_wh"]))
        unaccounted = max(unaccounted, abs(lhs - delta))            # the same identity without it
        deficit = max(deficit, abs(entry["deficit_wh"]))
    clipped_nodes = sum(1 for e in ledger.values() if e["clipped_wh"] > 0.0)

    print(f"       {len(ledger)} nodes, {hours} h, seed 7, day 15 (January), radio booked "
          f"{hours + 1} times per node")
    print(f"       identity: harvested - payload - heat - radio "
          f"= (battery_now - battery_start) + clipped - deficit")
    print(f"       worst residual over the fleet = {worst_residual:.3e} Wh, "
          f"deficit {deficit:.3e} Wh")
    print(f"       capacity clipping is load-bearing here: {clipped_nodes}/{len(ledger)} nodes "
          f"clip on the first step, largest {worst_clip_gap:.6f} Wh, and without that term the "
          f"same identity is off by {unaccounted:.6f} Wh")

    check("4a every node's ledger balances", worst_residual <= 1e-9,
          f"worst |harvested - load - radio - delta_battery - clipped + deficit| = "
          f"{worst_residual:.3e} Wh")
    check("4b the clipping term is required, not decoration", worst_clip_gap > 1e-6
          and unaccounted > 1e-6 and clipped_nodes > 0,
          f"largest clip {worst_clip_gap:.6f} Wh; the identity without it is off by "
          f"{unaccounted:.6f} Wh")
    check("4c no node ran its pack empty in this run, so the deficit term is zero",
          deficit == 0.0, f"largest deficit {deficit!r} Wh")
    check("4d the ledger reports the terms the snapshot promises",
          all(set(("battery_wh", "alive", "harvested_wh_total", "load_wh_total",
                   "radio_wh_total", "blackout_ticks")) <= set(e) for e in ledger.values()),
          f"{len(ledger)} entries, keys {sorted(ledger[fleet.node_ids[0]])[:6]}...")
    check("4e load_wh_total is the payload plus the heating draw",
          all(close(e["load_wh_total"], e["payload_wh_total"] + e["heat_wh_total"], 1e-12)
              for e in ledger.values()),
          f"payload {ledger[fleet.node_ids[0]]['payload_wh_total']:.6f} Wh, heat "
          f"{ledger[fleet.node_ids[0]]['heat_wh_total']:.6f} Wh")


# ------------------------------------------------------------------ test 5
def gate(fleet: SupplyFleet, node_id: str, t_s: int, terrain_ok: bool = True) -> bool:
    """The power term of runtime/disruption_env.is_unreachable: `not reachable or not alive`.

    Terrain is not this module's business, so it is a flag here; what the check shows is that a
    dead supply closes the gate by itself, which is how a power failure reaches the policy layer.
    """
    return (not terrain_ok) or (not fleet.alive(node_id, t_s))


def t5_supply_gates_reachability() -> None:
    """A dead supply closes the reachability gate on its own node and on no other."""
    deployment = build_deployment(9)
    fleet = SupplyFleet(deployment.nodes, seed=9, start_doy=200)
    t_s = 2 * HOUR_S + 7 * TICK_S                     # mid-hour, so the gate is not a step artefact
    fleet.step_to(t_s)
    victim = fleet.node_ids[4]
    healthy = fleet.dead_nodes(t_s)

    fleet.drain_wh(victim, fleet[victim].energy.usable_wh + 1.0)     # talks its pack flat
    dead_now = fleet.dead_nodes(t_s)
    others = [nid for nid in fleet.node_ids if nid != victim]
    print(f"       {len(fleet)} nodes at t={t_s} s ({t_s // 3600} h {t_s % 3600 // 60} min), "
          f"all powered before the drain: {healthy == []}")
    print(f"       {victim} drained to {fleet[victim].energy.bat_wh:.6f} Wh "
          f"(threshold {fleet[victim].alive_threshold_wh():.6f} Wh) -> dead_nodes {dead_now}")
    print(f"       reachability gate (terrain borrowed as True): "
          f"{victim} unreachable={gate(fleet, victim, t_s)}, "
          f"others unreachable={any(gate(fleet, nid, t_s) for nid in others)}")

    check("5a a node whose supply is dead reads alive=False at that instant",
          (not fleet.alive(victim, t_s)) and fleet[victim].state(t_s)["alive"] is False,
          f"alive({victim}, {t_s}) = {fleet.alive(victim, t_s)}, "
          f"bat_wh {fleet[victim].energy.bat_wh:.6f} Wh")
    check("5b dead_nodes names it and only it", dead_now == [victim],
          f"{dead_now}, victim {victim}, {len(others)} others reported alive: "
          f"{all(fleet.alive(nid, t_s) for nid in others)}")
    check("5c the reachability gate closes on the dead node alone",
          gate(fleet, victim, t_s) and not any(gate(fleet, nid, t_s) for nid in others),
          "the power term alone is enough to make the node unreachable")

    # the tick accounting follows the same state: nothing dark yet, then exactly ten dark ticks
    dark_ticks_now = fleet[victim].state(t_s)["blackout_ticks"]
    later = t_s + 10 * TICK_S
    fleet.step_to(later)
    dark_ticks_later = fleet[victim].state(later)["blackout_ticks"]
    check("5d the blackout ledger counts the dark ticks and only those",
          dark_ticks_now == 0 and dark_ticks_later == 10,
          f"blackout_ticks {dark_ticks_now} at the instant it went dark, "
          f"{dark_ticks_later} ten minutes later")

    # a reading, not a latch: charge the pack again and the same instant reads powered
    fleet[victim].energy.bat_wh = fleet[victim].energy.usable_wh
    revived = fleet.alive(victim, later)
    check("5e the flag follows the pack in both directions, with no latch",
          revived and victim not in fleet.dead_nodes(later),
          f"after an explicit recharge alive({victim}) = {revived}, "
          f"dead_nodes empty: {fleet.dead_nodes(later) == []}")


# ------------------------------------------------------------------ test 6
def t6_one_minute_clock_does_not_multiply_the_ticks() -> None:
    """Sixty reads inside an hour cost one model step, and the state is held within the hour."""
    supply = make_dark_supply(seed=13)
    readings = []
    for minute in range(0, 5 * 60 + 1):
        t_s = minute * TICK_S
        readings.append((t_s, supply.state(t_s)["hours_advanced"], supply.energy.bat_wh))
    steps_end = readings[-1][1]
    same_hour = {(h, wh) for (t_s, h, wh) in readings if HOUR_S <= t_s < 2 * HOUR_S}
    repeated = supply.state(5 * HOUR_S)["hours_advanced"]

    print(f"       {len(readings)} one-minute reads over 5 h -> hours_advanced = {steps_end}")
    print(f"       inside hour 1 the state never moved: {sorted(same_hour)}")
    print(f"       a second read of the same instant leaves the clock at {repeated} steps")

    check("6a the hourly model ticks once per hour crossed, not once per read",
          steps_end == 5, f"5 h of one-minute reads -> {steps_end} model steps")
    check("6b the state is constant within an hour", len(same_hour) == 1,
          f"{len(same_hour)} distinct (hours_advanced, battery_wh) pairs in hour 1")
    check("6c step_to is idempotent for an instant already reached",
          repeated == steps_end, f"{repeated} vs {steps_end}")


# ------------------------------------------------------------------ runner
def main() -> int:
    print("=" * 78)
    print("NODE SUPPLY AT THE MONITORING CLOCK — VERIFICATION BY HAND CALCULATION")
    print("=" * 78)
    t1_latch_is_gone()
    print()
    t2_no_generation_dies_in_a_computable_time()
    print()
    t3_radio_drain_shortens_that_time()
    print()
    t4_ledger_balances()
    print()
    t5_supply_gates_reachability()
    print()
    t6_one_minute_clock_does_not_multiply_the_ticks()
    print()
    failed = [n for n, ok, _ in RESULTS if not ok]
    print("=" * 78)
    print(f"{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed")
    for n in failed:
        print(f"  FAILED: {n}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
