#!/usr/bin/env python3
"""
energy.py — per-node energy state driven by real altitude and temperature physics.

Replaces the placeholder recharge in disruption_env.py (`bat += 0.05`) with the mechanism
that the field evidence points to: at altitude, a LiFePO4 pack cannot be charged for most of
the year, so the node runs down its initial charge and goes silent for long stretches.

Physics and parameters are the ones flagged in docs/s2-scenario (see §9.6 of the archived
feasibility note): standard lapse rate, LiFePO4 ~50 % capacity at -20 C and NO charging below
+5 C, snow burial stopping generation outright, and Tibetan-plateau insolation.

Deps: numpy only.
"""
from __future__ import annotations

import math

import numpy as np

# ---------------------------------------------------------------- climate
LAPSE_C_PER_KM = 6.5
SEA_LEVEL_JAN_C = 6.0          # sea-level January mean at ~30 N
SEASONAL_SWING_C = 12.0        # Jan -> Jul amplitude

# ---------------------------------------------------------------- chemistry
# name: (capacity derate at -20 C, can accept charge below the gate?)
CHEMISTRY = {
    "LiFePO4": (0.50, False),
    "NMC622":  (0.11, False),
    "VRLA":    (0.65, True),
}
CHARGE_GATE_C = 5.0

# ---------------------------------------------------------------- solar
SYSTEM_DERATE = 0.75
PEAK_FACTOR = 0.75             # clear-sky plateau insolation, fraction of STC
DOD = 0.70                     # usable depth of discharge


class NodeEnergy:
    """Energy state for one monitoring node. Tick = 1 hour."""

    def __init__(self, elev_m: float, lat_deg: float = 30.33,
                 panel_w: float = 100.0, batt_wh_nom: float = 1200.0,
                 load_w: float = 0.67, chemistry: str = "LiFePO4",
                 rng: np.random.Generator | None = None,
                 snow_prob_winter: float = 0.10,
                 temp_offset_c: float = 0.0,
                 heated: bool = False):
        self.elev_m = elev_m
        self.lat = lat_deg
        self.panel_w = panel_w
        self.batt_wh_nom = batt_wh_nom
        self.load_wh_per_tick = load_w                      # 1 h tick => Wh == W
        self.chem = chemistry
        self.derate, self.can_charge_cold = CHEMISTRY[chemistry]
        self.rng = rng or np.random.default_rng(0)
        self.snow_prob = snow_prob_winter
        self.temp_offset_c = temp_offset_c
        # a heated battery box removes the charge gate; real sites differ in whether they have one
        self.heated = heated

        self.snow_left = 0
        self.usable_wh = batt_wh_nom * self.derate * DOD
        self.bat_wh = self.usable_wh
        self.alive = True
        self._hour = 0

    # ------------------------------------------------------------------
    def _temp_c(self, day_of_year: int) -> float:
        base = (SEA_LEVEL_JAN_C - LAPSE_C_PER_KM * self.elev_m / 1000.0
                + SEASONAL_SWING_C * math.sin(math.radians(360.0 * (day_of_year - 105) / 365.0)))
        return base + self.temp_offset_c + float(self.rng.normal(0, 2.0))

    def _daylight_h(self, day_of_year: int) -> float:
        decl = 23.44 * math.sin(math.radians(360.0 * (284 + day_of_year) / 365.0))
        cos_h = -math.tan(math.radians(self.lat)) * math.tan(math.radians(decl))
        cos_h = max(-1.0, min(1.0, cos_h))
        return 2 * math.degrees(math.acos(cos_h)) / 15.0

    def _generation_wh(self, day_of_year: int, temp_c: float) -> float:
        if self.snow_left > 0:
            return 0.0                                   # buried panel: no generation
        dl = self._daylight_h(day_of_year)
        temp_gain = 1.0 + max(0.0, (25.0 - temp_c)) * 0.0035   # cold panels are more efficient
        gen = self.panel_w * dl * PEAK_FACTOR * SYSTEM_DERATE * temp_gain
        if not self.can_charge_cold and not self.heated and temp_c < CHARGE_GATE_C:
            return 0.0                                   # the charge gate binds
        return gen

    # ------------------------------------------------------------------
    def step(self, day_of_year: int) -> bool:
        """Advance one hour. Returns whether the node is alive (powered) afterwards."""
        self._hour += 1
        t = self._temp_c(day_of_year)

        # snow events, concentrated in winter
        winter = 1.0 if (day_of_year < 120 or day_of_year > 300) else 0.35
        if self.snow_left == 0 and self.rng.random() < self.snow_prob * winter / 24.0:
            self.snow_left = int(self.rng.integers(1, 4))
        if self.snow_left > 0:
            self.snow_left -= 1

        # generation accrues only over daylight hours
        hourly_gen = self._generation_wh(day_of_year, t) / max(self._daylight_h(day_of_year), 1e-6)
        self.bat_wh = min(self.bat_wh + hourly_gen - self.load_wh_per_tick, self.usable_wh)

        if self.bat_wh <= 0.0:
            self.bat_wh = 0.0
            self.alive = False
        elif self.bat_wh > 0.05 * self.usable_wh:
            self.alive = True
        return self.alive
