#!/usr/bin/env python3
"""
supply.py — per-node power at the monitoring layer's one-minute clock.

WHAT THIS FILE IS. `physics/energy.py` owns the mechanism: one battery per node, advanced one hour
at a time by altitude-driven temperature, the chemistry's charge gate, insolation and load. This
module puts that mechanism on the clock the monitoring layer actually runs on, which is one minute
(node_model.TICK_S), and adds the one energy term the monitoring layer knows about and the physics
does not: what the radio spends when the node talks. A node that talks more therefore dies sooner,
and `drain_wh` is how that talk is charged.

THE CLOCK RULE. The state is held within an hour. An hourly step happens when the clock crosses an
hour boundary and only then; reading the state sixty times inside one hour costs no model ticks and
changes nothing. Nothing is interpolated between boundaries, because there is nothing between them
to interpolate: the model has one tick per hour and no sub-hour trace, and a smoother invented here
would be a claim the physics never made. A node's power state is constant within an hour, apart from
the radio it fires off, which is charged the moment it is booked.

WHAT THE LEDGER SAYS. Every node keeps the terms a reader needs to check the state against them,
and the identity is exact:

    harvested - payload - heat - radio  =  (battery_now - battery_start) + clipped - deficit

  * harvested, payload and heat are the physics terms, accumulated from the hourly steps;
  * radio is what `drain_wh` has booked, and it is charged into the pack immediately rather than
    waiting for the next hour, so "talk more, die sooner" is a consequence of the arithmetic;
  * clipped is energy the capacity bound would not hold, including the constructor's own overshoot
    (a fresh pack is set to the reference-temperature usable energy, which at a cold ambient is
    above capacity_Wh(T) and is clipped on the first step — see the note in energy.py);
  * deficit is energy called for that an empty pack could not supply. It is normally zero, and it
    exists so that the identity stays an identity instead of turning into a hope.

`alive` is a read of the pack, not a flag carried forward. `NodeEnergy.step` recomputes it every
hour and this module recomputes it from the same rule (`energy.ALIVE_FRACTION`) at any instant it
is asked, which is what lets a drain that empties a pack take the node dark between two hour
boundaries. Nothing here latches in either direction. `blackout_ticks` counts one-minute ticks the
node spent dark, at the same resolution: ticks are attributed to the state that held across them,
so looking more often never changes the count.

EVIDENCE LAYER. The panel rating, the latitude, the chemistry, the heated-enclosure flag and every
hourly constant behind them are **A: research reference assumptions about a class of device**
(README D16). They describe what a station of this kind might be, not what a specific unit was
measured to do; a real deployment replaces them with its own bill of materials and its own site
record.

Deps: standard library, numpy (through energy.py), and this repository's physics, runtime and
monitoring modules.
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

from typing import Iterator, Sequence

import numpy as np

from deterministic import stable_uniform
from energy import ALIVE_FRACTION, DEFAULT_HEAT_W, NodeEnergy
from node_model import TICK_S

HOUR_S = 3600                    # the energy model's own tick: one hour
TICKS_PER_HOUR = HOUR_S // TICK_S


def _identify(item) -> tuple[str, float]:
    """Read (node_id, elevation) off a deployment node, a pair or a mapping.

    The fleet is built from whatever the caller has: the deployment's `Node` objects carry `nid`
    and `elev_m`, and a caller that has neither can hand over `(node_id, elev_m)` pairs. Elevation
    is the only per-node geometry the energy model uses.
    """
    if isinstance(item, dict):
        nid = item.get("nid", item.get("node_id"))
        elev = item.get("elev_m")
    elif isinstance(item, (tuple, list)) and len(item) == 2:
        nid, elev = item
    else:
        nid = getattr(item, "nid", None)
        elev = getattr(item, "elev_m", None)
    if nid is None or elev is None:
        raise TypeError(f"cannot read (node_id, elev_m) from {item!r}")
    return str(nid), float(elev)


class NodeSupply:
    """One node's power supply: the hourly energy model plus the radio's share of it."""

    def __init__(self, node_id: str, elev_m: float, seed: int, *,
                 heated: bool = False, panel_w: float = 100.0,
                 lat_deg: float = 30.33, chemistry: str = "LiFePO4",
                 batt_wh_nom: float = 1200.0, load_w: float = 0.67,
                 heat_w: float = DEFAULT_HEAT_W, snow_prob_winter: float = 0.10,
                 temp_offset_c: float = 0.0, start_doy: int = 1) -> None:
        self.node_id = str(node_id)
        self.seed = int(seed)
        self.start_doy = int(start_doy)

        # A-layer device class, kept on the supply so an audit can read what was assumed
        self.elev_m = float(elev_m)
        self.lat_deg = float(lat_deg)
        self.panel_w = float(panel_w)
        self.chemistry = str(chemistry)
        self.heated = bool(heated)

        # The seed is used verbatim, so two supplies built with the same seed and the same
        # parameters see the same weather and differ only in what a caller books against them.
        # SupplyFleet derives a distinct seed per node from the fleet seed and the node id.
        self.energy = NodeEnergy(elev_m=self.elev_m, lat_deg=self.lat_deg, panel_w=self.panel_w,
                                 batt_wh_nom=batt_wh_nom, load_w=load_w, chemistry=self.chemistry,
                                 rng=np.random.default_rng(self.seed),
                                 snow_prob_winter=snow_prob_winter, temp_offset_c=temp_offset_c,
                                 heated=self.heated, heat_w=heat_w)

        # --- ledger, zeroed at construction ---
        self.battery_start_wh = self.energy.bat_wh
        self.harvested_wh_total = 0.0
        self.payload_wh_total = 0.0
        self.heat_wh_total = 0.0
        self.radio_wh_total = 0.0
        self.clipped_wh = 0.0
        self.deficit_wh = 0.0
        self.hours_advanced = 0

        # --- clock and blackout segments ---
        self.clock_s = 0                     # the frontier: reads are served here, never behind it
        self._blackout_closed = 0
        self._seg_tick = 0                   # first one-minute tick of the current state segment
        self._seg_dead = not self._live()

    def __repr__(self) -> str:
        return (f"NodeSupply({self.node_id!r}, elev {self.elev_m:.0f} m, "
                f"{self.energy.bat_wh:.1f} Wh at t={self.clock_s} s)")

    # ------------------------------------------------------------------ power state
    def _live(self) -> bool:
        """The power state right now, read off the pack.

        The rule is energy.py's, and ALIVE_FRACTION is imported rather than repeated so the two
        cannot drift apart: above the threshold the node is powered, at or below it the node is
        dark. Reading it from the state is what makes a drain able to take a node down mid-hour.
        """
        return self.energy.bat_wh > ALIVE_FRACTION * self.energy.usable_wh

    def alive_threshold_wh(self) -> float:
        """The charge below which the node is dark, in Wh."""
        return ALIVE_FRACTION * self.energy.usable_wh

    def _note_state(self, at_s: int) -> None:
        """Attribute the one-minute ticks up to `at_s` to the state that held across them.

        Called at every evaluation — an hourly step, a radio drain, a read — so `blackout_ticks`
        counts whole ticks the node spent dark and does not depend on how often a caller looks.
        """
        tick = max(self._seg_tick, int(at_s) // TICK_S)
        dead = not self._live()
        if dead == self._seg_dead:
            return
        if self._seg_dead:
            self._blackout_closed += tick - self._seg_tick
        self._seg_tick = tick
        self._seg_dead = dead

    def _blackout_ticks(self) -> int:
        tick = self.clock_s // TICK_S
        extra = tick - self._seg_tick if self._seg_dead else 0
        return self._blackout_closed + max(0, extra)

    # ------------------------------------------------------------------ clock
    def step_to(self, t_s: int) -> None:
        """Advance the hourly model up to `t_s`. Idempotent for a t_s already reached.

        The model ticks once per hour boundary crossed, not once per call, so the monitoring
        layer's one-minute clock drives it without multiplying its work by sixty.
        """
        t_s = int(t_s)
        if t_s > self.clock_s:
            self.clock_s = t_s
        while self.hours_advanced < self.clock_s // HOUR_S:
            self._advance_one_hour()

    def _advance_one_hour(self) -> None:
        """Run the hour that ends at the next boundary, and book what it did.

        The run clock starts at second 0 on day `start_doy`: hours 1..24 of the run are that day,
        hours 25..48 the next, and so on. The calendar is the run's own, so the weather a fleet sees
        depends on when in the year the deployment is simulated rather than on wall-clock time.
        """
        hour_index = self.hours_advanced + 1                 # 1-based: the hour being completed
        boundary_s = hour_index * HOUR_S
        self._note_state(boundary_s)                         # the state held up to the boundary

        doy = self.start_doy + (hour_index - 1) // 24
        before = self.energy.bat_wh
        self.energy.step(doy)
        self.hours_advanced = hour_index

        gen = self.energy.hourly_gen_wh
        payload = self.energy.load_wh_per_tick
        heat = self.energy.heat_w if self.energy.heating_active else 0.0
        expected = before + gen - payload - heat            # the state before the bounds apply
        actual = self.energy.bat_wh
        if expected > actual:
            self.clipped_wh += expected - actual            # the capacity bound would not hold it
        elif actual > expected:
            self.deficit_wh += actual - expected            # an empty pack: the draw went unserved

        self.harvested_wh_total += gen
        self.payload_wh_total += payload
        self.heat_wh_total += heat
        self._note_state(boundary_s)                         # the new state holds from here on

    # ------------------------------------------------------------------ the interface
    def alive(self, t_s: int) -> bool:
        """Whether the node has power at `t_s`. Callers do not have to call step_to first."""
        self.step_to(t_s)
        self._note_state(self.clock_s)
        return self._live()

    def drain_wh(self, wh: float) -> None:
        """Book radio energy spent right now. Enters the ledger at once, not at the next hour.

        The draw leaves the pack immediately, because the talk that costs the energy happens
        between hour boundaries and a ledger that waited for the next step would let a node talk
        its pack empty without paying for it. The amount is counted whether or not the pack can
        supply it: the unserved part is booked as deficit, which keeps the ledger an identity.
        The check "is this node powered" belongs to the caller, not here — a drain is a
        measurement of what the radio spent, and refusing to record it would hide the spend.
        """
        wh = float(wh)
        if wh < 0.0:
            raise ValueError(f"radio energy cannot be negative: {wh!r}")
        self._note_state(self.clock_s)
        self.radio_wh_total += wh
        served = min(wh, max(0.0, self.energy.bat_wh))
        self.energy.bat_wh -= served
        if served < wh:
            self.deficit_wh += wh - served
        self._note_state(self.clock_s)

    def state(self, t_s: int) -> dict:
        """An auditable snapshot at `t_s`: the pack, the power state and the ledger behind them."""
        self.step_to(t_s)
        self._note_state(self.clock_s)
        return {
            "node_id": self.node_id,
            "t_s": self.clock_s,                 # the frontier; reads never rewind the clock
            "hours_advanced": self.hours_advanced,
            "battery_wh": self.energy.bat_wh,
            "battery_start_wh": self.battery_start_wh,
            "usable_wh": self.energy.usable_wh,
            "alive_threshold_wh": self.alive_threshold_wh(),
            "alive": self._live(),
            "harvested_wh_total": self.harvested_wh_total,
            "payload_wh_total": self.payload_wh_total,
            "heat_wh_total": self.heat_wh_total,
            "load_wh_total": self.payload_wh_total + self.heat_wh_total,
            "radio_wh_total": self.radio_wh_total,
            "clipped_wh": self.clipped_wh,
            "deficit_wh": self.deficit_wh,
            "blackout_ticks": self._blackout_ticks(),
            "heating_active": bool(self.energy.heating_active),
            "elev_m": self.elev_m,
            "lat_deg": self.lat_deg,
            "panel_w": self.panel_w,
            "chemistry": self.chemistry,
            "heated": self.heated,
        }


class SupplyFleet:
    """One NodeSupply per node, stepped together.

    The fleet seed addresses the weather of each node through (seed, node id) rather than through
    position, so a node's trace does not depend on where it sits in the sequence handed in, and two
    runs that differ only in that order see the same weather.
    """

    def __init__(self, nodes: Sequence, seed: int, *, heated: bool = False,
                 panel_w: float = 100.0, lat_deg: float = 30.33, chemistry: str = "LiFePO4",
                 batt_wh_nom: float = 1200.0, load_w: float = 0.67,
                 heat_w: float = DEFAULT_HEAT_W, snow_prob_winter: float = 0.10,
                 temp_offset_c: float = 0.0, start_doy: int = 1) -> None:
        self.seed = int(seed)
        self.supplies: dict[str, NodeSupply] = {}
        for item in nodes:
            nid, elev_m = _identify(item)
            if nid in self.supplies:
                raise ValueError(f"duplicate node id in fleet: {nid!r}")
            self.supplies[nid] = NodeSupply(
                nid, elev_m, self._node_seed(nid), heated=heated, panel_w=panel_w,
                lat_deg=lat_deg, chemistry=chemistry, batt_wh_nom=batt_wh_nom, load_w=load_w,
                heat_w=heat_w, snow_prob_winter=snow_prob_winter,
                temp_offset_c=temp_offset_c, start_doy=start_doy)
        self.node_ids: tuple[str, ...] = tuple(sorted(self.supplies))

    def _node_seed(self, node_id: str) -> int:
        """A per-node seed addressed by the fleet seed and the node id, so order cannot matter."""
        return int(stable_uniform(self.seed, "supply", node_id) * 2 ** 32)

    def __len__(self) -> int:
        return len(self.supplies)

    def __iter__(self) -> Iterator[NodeSupply]:
        return iter(self.supplies[nid] for nid in self.node_ids)

    def __getitem__(self, node_id: str) -> NodeSupply:
        return self.supplies[node_id]

    # ------------------------------------------------------------------ the interface
    def step_to(self, t_s: int) -> None:
        """Advance every node's hourly model up to `t_s`. Idempotent once reached."""
        for supply in self.supplies.values():
            supply.step_to(t_s)

    def alive(self, node_id: str, t_s: int) -> bool:
        """Whether `node_id` has power at `t_s`. Steps to `t_s` if the clock is behind it."""
        return self.supplies[node_id].alive(t_s)

    def drain_wh(self, node_id: str, wh: float) -> None:
        """Book radio energy against one node. Enters that node's ledger immediately."""
        self.supplies[node_id].drain_wh(wh)

    def dead_nodes(self, t_s: int) -> list[str]:
        """The nodes without power at `t_s`, in canonical node-id order."""
        self.step_to(t_s)
        return [nid for nid in self.node_ids if not self.supplies[nid].alive(t_s)]

    def ledger(self) -> dict:
        """Per-node totals for the audit, at each node's current clock.

        Each entry is the node's snapshot plus `residual_wh`, the value the ledger identity should
        leave at zero:

            harvested - payload - heat - radio - (battery_now - battery_start) - clipped + deficit

        A caller that reads a ledger can therefore check the arithmetic instead of trusting it.
        """
        out: dict[str, dict] = {}
        for nid in self.node_ids:
            supply = self.supplies[nid]
            entry = supply.state(supply.clock_s)
            entry["residual_wh"] = (
                entry["harvested_wh_total"] - entry["payload_wh_total"] - entry["heat_wh_total"]
                - entry["radio_wh_total"]
                - (entry["battery_wh"] - entry["battery_start_wh"])
                - entry["clipped_wh"] + entry["deficit_wh"])
            out[nid] = entry
        return out
