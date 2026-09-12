#!/usr/bin/env python3
"""
energy.py — per-node energy state driven by real altitude and temperature physics.

Replaces the placeholder recharge in disruption_env.py (`bat += 0.05`) with the mechanism
that the field evidence points to: at altitude, a LiFePO4 pack cannot be charged for most of
the year, so the node runs down its initial charge and goes silent for long stretches.

Physics and parameters are the ones flagged in docs/s2-scenario (see §9.6 of the archived
feasibility note): standard lapse rate, LiFePO4 ~50 % capacity at -20 C and NO charging below
+5 C, snow burial stopping generation outright, and Tibetan-plateau insolation.

Energy accounting. The state is one battery, advanced one hour per step:

    E(t+1) = clip( E(t) + harvested_Wh - load_Wh - heat_Wh , 0 , capacity_Wh(T(t+1)) )

One tick is one hour, so a power of P W is P Wh over the tick and the conversion is explicit
below rather than assumed. Harvesting happens only inside the sunrise/sunset window and sums
to the daily figure the panel produces, so the tick count cannot scale the daily yield. The
charge gate, the capacity derate and the heating threshold are properties of the cell
chemistry in CHEMISTRY, not physical constants shared by every pack.

Deps: numpy only.
"""
from __future__ import annotations

import math

import numpy as np

# ---------------------------------------------------------------- climate
LAPSE_C_PER_KM = 6.5
SEA_LEVEL_JAN_C = 6.0          # sea-level January mean at ~30 N
SEASONAL_SWING_C = 12.0        # Jan -> Jul amplitude
DIURNAL_AMPLITUDE_C = 6.0      # half peak-to-peak; coldest ~03:00, warmest ~15:00
COLDEST_HOUR = 3.0             # hour of the temperature minimum
SOLAR_NOON_H = 12.0            # the daylight window is centred here (local solar time)

# ---------------------------------------------------------------- chemistry
# name: (capacity derate at -20 C, can accept charge below the gate?,
#        charge-gate temperature in C, capacity curve as (temperature C, capacity fraction))
#
# A gate of -inf means the chemistry accepts charge at any temperature the site reaches, which
# is the VRLA case. The curve's first point is the documented derate at -20 C, so that figure
# stays exact; the second is the full-capacity reference. Between them the fraction is linear,
# and outside them it is held constant: the measured evidence covers -20 C to +25 C only, and
# holding the -20 C derate below -20 C is conservative (it never claims capacity the chemistry
# was not measured to have). Usable energy is DERATE_CAP_WH * DOD at the reference temperature
# and less when cold; it is never zero, because the pack still holds charge.
CAPACITY_REF_C = 25.0

CHEMISTRY = {
    "LiFePO4": (0.50, False, 5.0, ((-20.0, 0.50), (25.0, 1.0))),
    "NMC622":  (0.11, False, 0.0, ((-20.0, 0.11), (25.0, 1.0))),
    "VRLA":    (0.65, True, -math.inf, ((-20.0, 0.65), (25.0, 1.0))),
}

# ---------------------------------------------------------------- solar
SYSTEM_DERATE = 0.75
PEAK_FACTOR = 0.75             # clear-sky plateau insolation, fraction of STC
DOD = 0.70                     # usable depth of discharge

# ---------------------------------------------------------------- heating
# A heated battery box pays for the heat it makes. The draw applies only while heating is
# active: the box holds the pack at its chemistry's charge gate, so it runs whenever the
# ambient sits below that gate (see _heat_on). The threshold is per chemistry, not a site
# constant, and the draw is what buying the privilege costs.
DEFAULT_HEAT_W = 8.0


class NodeEnergy:
    """Energy state for one monitoring node. Tick = 1 hour."""

    def __init__(self, elev_m: float, lat_deg: float = 30.33,
                 panel_w: float = 100.0, batt_wh_nom: float = 1200.0,
                 load_w: float = 0.67, chemistry: str = "LiFePO4",
                 rng: np.random.Generator | None = None,
                 snow_prob_winter: float = 0.10,
                 temp_offset_c: float = 0.0,
                 heated: bool = False,
                 heat_w: float = DEFAULT_HEAT_W):
        self.elev_m = elev_m
        self.lat = lat_deg
        self.panel_w = panel_w
        self.batt_wh_nom = batt_wh_nom
        self.load_wh_per_tick = load_w                      # 1 h tick => Wh == W
        self.chem = chemistry
        self.derate, self.can_charge_cold, self.charge_gate_c, self.cap_curve = \
            CHEMISTRY[chemistry]
        self.rng = rng or np.random.default_rng(0)
        self.snow_prob = snow_prob_winter
        self.temp_offset_c = temp_offset_c
        # a heated battery box holds the pack above its gate and pays heat_w for the privilege
        self.heated = heated
        self.heat_w = float(heat_w)
        self.heating_active = False
        self.hourly_gen_wh = 0.0        # harvested energy booked in the last step

        self.snow_left = 0
        self.usable_wh = batt_wh_nom * self.derate * DOD
        self.bat_wh = self.usable_wh
        self.alive = True
        self._hour = 0

    # ------------------------------------------------------------------
    def _temp_c(self, day_of_year: int) -> float:
        base = (SEA_LEVEL_JAN_C - LAPSE_C_PER_KM * self.elev_m / 1000.0
                + SEASONAL_SWING_C * math.sin(math.radians(360.0 * (day_of_year - 105) / 365.0)))
        diurnal = DIURNAL_AMPLITUDE_C * -math.cos(math.radians(
            15.0 * (self._hour - COLDEST_HOUR)))
        return base + diurnal + self.temp_offset_c + float(self.rng.normal(0, 2.0))

    def _daylight_h(self, day_of_year: int) -> float:
        decl = self._solar_declination_deg(day_of_year)
        cos_h = -math.tan(math.radians(self.lat)) * math.tan(math.radians(decl))
        cos_h = max(-1.0, min(1.0, cos_h))
        return 2 * math.degrees(math.acos(cos_h)) / 15.0

    def _daylight_window_h(self, day_of_year: int) -> tuple[float, float]:
        """Sunrise and sunset as hours from midnight local solar time."""
        half = self._daylight_h(day_of_year) / 2.0
        return SOLAR_NOON_H - half, SOLAR_NOON_H + half

    def _solar_declination_deg(self, day_of_year: int) -> float:
        return 23.44 * math.sin(math.radians(360.0 * (284 + day_of_year) / 365.0))

    def _daylight_fraction(self, hour: int, day_of_year: int) -> float:
        """Fraction of the hour [hour, hour+1) that lies inside the daylight window."""
        rise, set_ = self._daylight_window_h(day_of_year)
        return max(0.0, min(hour + 1.0, set_) - max(float(hour), rise))

    def _capacity_fraction(self, temp_c: float) -> float:
        """Fraction of nominal capacity available at temp_c, from the chemistry curve."""
        pts = self.cap_curve
        if temp_c <= pts[0][0]:
            return float(pts[0][1])
        if temp_c >= pts[-1][0]:
            return float(pts[-1][1])
        for (t0, f0), (t1, f1) in zip(pts, pts[1:]):
            if t0 <= temp_c <= t1:
                w = (temp_c - t0) / (t1 - t0)
                return float(f0 + w * (f1 - f0))
        return float(pts[-1][1])

    def capacity_Wh(self, temp_c: float) -> float:
        """Usable capacity at this temperature. Clips the state of charge."""
        return self.usable_wh * self._capacity_fraction(temp_c)

    def _day_generation_wh(self, day_of_year: int, temp_c: float) -> float:
        """Energy the panel produces over the whole day, in Wh."""
        if self.snow_left > 0:
            return 0.0                                   # buried panel: no generation
        dl = self._daylight_h(day_of_year)
        temp_gain = 1.0 + max(0.0, (25.0 - temp_c)) * 0.0035   # cold panels are more efficient
        gen = self.panel_w * dl * PEAK_FACTOR * SYSTEM_DERATE * temp_gain
        if not self.can_charge_cold and not self.heated and temp_c < self.charge_gate_c:
            return 0.0                                   # the charge gate binds
        return gen

    def _generation_hour_wh(self, day_of_year: int, temp_c: float, hour: int) -> float:
        """Harvested energy in hour [hour, hour+1), in Wh. Zero outside the daylight window."""
        dl = self._daylight_h(day_of_year)
        if dl <= 0.0:
            return 0.0
        span = self._daylight_fraction(hour, day_of_year)
        if span <= 0.0:
            return 0.0
        # daily energy spread evenly over the daylight window => Wh in this hour
        return self._day_generation_wh(day_of_year, temp_c) * span / dl

    def _heat_on(self, temp_c: float) -> bool:
        """Heating holds the pack at or above the charge gate; it costs heat_w while on."""
        if not self.heated:
            return False
        if self.can_charge_cold:
            return False                                 # this chemistry charges cold anyway
        return temp_c < self.charge_gate_c

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

        # one tick is one hour, so W and Wh are numerically equal over it
        tick_h = 1.0
        self.heating_active = self._heat_on(t)
        heat_wh = self.heat_w * tick_h if self.heating_active else 0.0

        hour = (self._hour - 1) % 24
        self.hourly_gen_wh = self._generation_hour_wh(day_of_year, t, hour)
        cap_wh = self.capacity_Wh(t)
        self.bat_wh = min(
            self.bat_wh + self.hourly_gen_wh - self.load_wh_per_tick - heat_wh,
            cap_wh,
        )

        if self.bat_wh <= 0.0:
            self.bat_wh = 0.0
            self.alive = False
        elif self.bat_wh > 0.05 * self.usable_wh:
            self.alive = True
        return self.alive


# ---------------------------------------------------------------- self-check
def main() -> None:
    doy = 172          # 21 June, near the summer solstice
    lat = 30.33
    node = NodeEnergy(elev_m=3925.0, lat_deg=lat, panel_w=100.0, batt_wh_nom=1000.0,
                      load_w=0.67, rng=np.random.default_rng(3), snow_prob_winter=0.0,
                      temp_offset_c=0.0)
    # freeze the temperature trace so this printout is a hand-checkable figure
    node._temp_c = lambda d: 7.0                                   # type: ignore[method-assign]

    dl = node._daylight_h(doy)
    temp_gain = 1.0 + max(0.0, (25.0 - 7.0)) * 0.0035
    daily = 100.0 * dl * PEAK_FACTOR * SYSTEM_DERATE * temp_gain
    buggy = daily * 24.0 / dl

    total = 0.0
    for _ in range(24):
        total += node._generation_hour_wh(doy, 7.0, node._hour % 24)
        node.step(doy)

    rise, set_ = node._daylight_window_h(doy)
    print(f"day-of-year      : {doy}, lat {lat} N, 100 W panel, T fixed at 7.0 C")
    print(f"daylight window  : sunrise {rise:.3f} h, sunset {set_:.3f} h, "
          f"length {dl:.3f} h")
    print(f"daily generation : {daily:.3f} Wh   (panel_w * daylight_h * peak * derate * gain)")
    print(f"harvested in 24 h: {total:.3f} Wh   (the window-integrated sum)")
    print(f"old buggy total  : {buggy:.3f} Wh   (daily * 24/dl, the pre-fix behaviour)")
    print(f"ratio old/fixed  : {buggy / daily:.3f}x")
    print(f"battery          : started {node.capacity_Wh(7.0):.1f} Wh at 7 C, "
          f"ended {node.bat_wh:.1f} Wh, alive={node.alive}")
    print("                   (the clip bound at 7 C is below usable_wh = "
          f"{node.usable_wh:.1f} Wh, which is the reference-temperature figure)")


if __name__ == "__main__":
    main()
