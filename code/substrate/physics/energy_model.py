#!/usr/bin/env python3
"""
energy_model.py — can a solar-powered mountain monitoring node / relay survive winter?

Motivated by the verified finding that the operative failure mode in Tibetan geohazard
networks is the POWER PATH (snow-buried panels stop generating; -20 C halves LiFePO4
capacity and blocks charging below +5 C), not radio propagation.

Simulates a daily energy balance for one year at a high-altitude site:
  generation  = panel_W * peak-sun-hours(latitude, day) * system derate * snow factor
  storage     = nominal_Ah * temp_derate(T) * usable_DOD
  charge gate = LiFePO4 cannot charge below +5 C  -> charging only possible on warm days
  load        = MCU sleep + wake + sensor + LoRa uplink at the SF the link requires

Reports the number of blackout days and the minimum state of charge.

Parameters for the temperature/charge behaviour are taken from published sources flagged
in SIMULATION_FIRST_FEASIBILITY.md §9.6. Everything else is stated explicitly below so the
model can be challenged.

Deps: numpy only.
"""
from __future__ import annotations

import math

import numpy as np

# ---------------------------------------------------------------- site
LAT_DEG = 30.33          # Bome / Yigong, Tibet
ALT_M = 3925.0           # the siting-constrained relay candidate from relay_siting.py
T_SEA_JAN_C = 6.0        # nominal sea-level January mean at this latitude
LAPSE_C_PER_M = 0.0065   # standard lapse rate -> the 3925 m site is much colder

# ---------------------------------------------------------------- storage
CHEMISTRY = {
    # name: (capacity derate at -20C, can charge below 0C?)
    "LiFePO4": (0.50, False),   # ~50 % capacity at -20 C; charging blocked below +5 C
    "NMC622":  (0.11, False),   # 11.3 % at -25 C
    "VRLA":    (0.65, True),    # 65 % at -15 C, can accept charge when cold
}
CHARGE_GATE_C = 5.0             # LiFePO4 charge floor
DOD = 0.70                      # usable depth of discharge
BATT_AH_NOM = 100.0             # nominal capacity, matched to the published 100 Ah sizing
BATT_V = 12.0
BATT_WH_NOM = BATT_AH_NOM * BATT_V

# ---------------------------------------------------------------- generation
PANEL_W = 100.0                 # installed PV
SYSTEM_DERATE = 0.75            # soiling, angle, MPPT, wiring, ageing

# ---------------------------------------------------------------- load
# The literature sizing anchor for a no-grid geohazard station is ~0.6 W average load
# (30 W PV + 70 Ah -> 15 rain-days). The previous version of this model omitted the
# sensing subsystem entirely and produced 0.01 Wh/day, ~1400x too low. Components below
# are explicit so the total can be checked against that anchor.

PRESETS = {
    # name: dict of average power components in W
    "relay_only": {
        "regulator_quiescent": 0.010,
        "mcu_sleep":           0.002,
        "radio_rx":            0.001,
        "radio_tx":            0.001,
    },
    "monitoring_station": {
        "regulator_quiescent": 0.020,
        "mcu_sleep":           0.005,
        "radio_rx":            0.002,
        "radio_tx":            0.002,
        "gnss_displacement":   0.250,   # duty-cycled GNSS, the dominant consumer
        "tilt_crack":          0.050,
        "rain_gauge":          0.005,
        "soil_moisture":       0.060,
        "sensor_warmup":       0.206,   # warm-up + settling, spread over the day
    },
}

I_SLEEP_UA = 15.0                 # kept for reference; superseded by PRESETS
BATT_V = 12.0
SF_AIRTIME_MS = {7: 29, 8: 51, 9: 91, 10: 164, 11: 298, 12: 546}   # 20 B payload
LINK_SF = 12                      # worst case: the SF the terrain forces at this site
UPLINKS_PER_DAY = 24.0            # now only scales the radio terms


def daily_load_wh(preset: str, sf: int = LINK_SF, uplinks_per_day: float = UPLINKS_PER_DAY) -> float:
    """Average daily energy in Wh for a named load preset."""
    p = PRESETS[preset]
    w = sum(p.values())
    # scale the radio terms by the uplink rate and the airtime the SF forces
    radio_base = p["radio_rx"] + p["radio_tx"]
    toa_scale = SF_AIRTIME_MS[sf] / SF_AIRTIME_MS[7]
    radio = radio_base * (uplinks_per_day / 24.0) * toa_scale
    w = w - radio_base + radio
    return w * 24.0


def panel_factor(day: int, temp_c: float, snow_days: int) -> float:
    """Fraction of nominal PV yield on a given day."""
    # daylight length at this latitude
    decl = 23.44 * math.sin(math.radians(360.0 * (284 + day) / 365.0))
    cosH = -math.tan(math.radians(LAT_DEG)) * math.tan(math.radians(decl))
    cosH = max(-1.0, min(1.0, cosH))
    daylight_h = 2 * math.degrees(math.acos(cosH)) / 15.0
    # Tibetan plateau has high clear-sky insolation: ~0.75 kW/m2 peak, thin-air gain
    peak_factor = 0.75
    # cold panels are slightly MORE efficient
    temp_gain = 1.0 + max(0.0, (25.0 - temp_c)) * 0.0035
    yield_wh = PANEL_W * daylight_h * peak_factor * SYSTEM_DERATE * temp_gain
    if snow_days > 0:
        yield_wh = 0.0            # buried panel: generation stops
    return yield_wh


def simulate(chemistry: str, load_wh: float, seed: int = 7, preset: str = '',
             temp_offset_c: float = 0.0,
             snow_prob_winter: float = 0.10, snow_len_days: int = 3,
             years: int = 1) -> dict:
    rng = np.random.default_rng(seed)
    derate, can_charge_cold = CHEMISTRY[chemistry]
    eff_wh = BATT_WH_NOM * derate * DOD

    soc = eff_wh
    snow_left = 0
    blackout_days = 0
    min_soc = eff_wh
    gen_total = load_total = 0.0
    blackout_by_month = np.zeros(12)

    n_days = 365 * years
    for d in range(n_days):
        doy = d % 365
        # seasonal temperature, altitude-adjusted
        t_mean = (T_SEA_JAN_C - LAPSE_C_PER_M * ALT_M
                  + 12.0 * math.sin(math.radians(360.0 * (doy - 105) / 365.0)))
        t_day = t_mean + temp_offset_c + rng.normal(0, 3.0)
        t_night = t_mean + temp_offset_c - 8.0 + rng.normal(0, 3.0)

        # snow events concentrate in winter
        winter = 1.0 if doy < 120 or doy > 300 else 0.35
        if snow_left == 0 and rng.random() < snow_prob_winter * winter:
            snow_left = rng.integers(1, snow_len_days + 1)

        gen = panel_factor(doy, t_day, snow_left)
        if snow_left > 0:
            snow_left -= 1

        # charging gate: LiFePO4 cannot charge below the floor temperature
        if not can_charge_cold and t_day < CHARGE_GATE_C:
            gen = 0.0
        # and capacity is derated at night when it is coldest
        eff_now = BATT_WH_NOM * derate * DOD * (
            1.0 if t_night > -10 else 0.85)

        soc = min(soc + gen - load_wh, eff_now)
        gen_total += gen
        load_total += load_wh
        if soc <= 0.0:
            soc = 0.0
            blackout_days += 1
            blackout_by_month[(doy // 31) % 12] += 1
        min_soc = min(min_soc, soc)

    return {
        "chemistry": chemistry,
        "preset": preset,
        "effective_storage_Wh": eff_wh,
        "load_Wh_per_day": load_wh,
        "blackout_days": int(blackout_days),
        "blackout_pct": 100.0 * blackout_days / n_days,
        "min_soc_Wh": min_soc,
        "gen_Wh_total": gen_total,
        "load_Wh_total": load_total,
        "blackout_by_month": blackout_by_month,
    }


def main() -> None:
    print("=" * 78)
    print("SOLAR + BATTERY VIABILITY FOR A HIGH-ALTITUDE SITE")
    print("=" * 78)
    print(f"site            : lat {LAT_DEG} N, altitude {ALT_M:.0f} m "
          f"(mean Jan temp {T_SEA_JAN_C - LAPSE_C_PER_M*ALT_M:.1f} C)")
    print(f"panel           : {PANEL_W:.0f} W, system derate {SYSTEM_DERATE}")
    print(f"battery         : {BATT_AH_NOM:.0f} Ah / {BATT_V:.0f} V ({BATT_WH_NOM:.0f} Wh), DoD {DOD}")
    print(f"charge gate     : LiFePO4 cannot charge below {CHARGE_GATE_C:.0f} C")
    print()
    for preset in PRESETS:
        load = daily_load_wh(preset)
        print(f"--- preset: {preset}  ->  {load:.2f} Wh/day  ({load/24:.3f} W avg) ---")
        print(f"{'chemistry':<12}{'usable Wh':>11}{'autonomy d':>12}{'blackout d/yr':>15}{'%':>8}")
        for chem in CHEMISTRY:
            derate, _ = CHEMISTRY[chem]
            r = simulate(chem, load, preset=preset)
            print(f"{chem:<12}{r['effective_storage_Wh']:>11.0f}"
                  f"{r['effective_storage_Wh']/load:>12.0f}"
                  f"{r['blackout_days']:>15d}{r['blackout_pct']:>8.1f}")
        print()
    print("Blackout months, monitoring_station + LiFePO4 (1=Jan):")
    r = simulate("LiFePO4", daily_load_wh("monitoring_station"), preset="monitoring_station")
    print("  " + "  ".join(f"{m+1}:{v}" for m, v in enumerate(r["blackout_by_month"].astype(int))))
    print()
    print("Sensitivity: monitoring_station + LiFePO4, panel size")
    print(f"{'panel W':>9}{'blackout d/yr':>15}{'%':>8}")
    for pw in (30, 60, 100, 150, 200):
        globals()['PANEL_W'] = pw
        r = simulate("LiFePO4", daily_load_wh("monitoring_station"), preset="monitoring_station")
        print(f"{pw:>9}{r['blackout_days']:>15d}{r['blackout_pct']:>8.1f}")
    globals()['PANEL_W'] = 100.0
    print()
    print("Sensitivity: monitoring_station + LiFePO4 @100 W, snow-burial probability")
    print(f"{'p(snow)/day':>12}{'blackout d/yr':>15}{'%':>8}")
    for pp in (0.0, 0.05, 0.10, 0.20):
        r = simulate("LiFePO4", daily_load_wh("monitoring_station"),
                     preset="monitoring_station", snow_prob_winter=pp)
        print(f"{pp:>12.2f}{r['blackout_days']:>15d}{r['blackout_pct']:>8.1f}")
    print()
    print("CLIMATE SENSITIVITY — the absolute result depends on the temperature baseline,")
    print("which has NOT been verified against station data. Swinging the baseline:")
    print(f"{'offset C':>10}{'Jan mean C':>13}{'Jul mean C':>13}"
          f"{'blackout station':>18}{'blackout relay':>16}")
    for off in (-6, -3, 0, 3, 6, 9, 12):
        jan = T_SEA_JAN_C - LAPSE_C_PER_M*ALT_M + off
        jul = jan + 12.0
        rs = simulate("LiFePO4", daily_load_wh("monitoring_station"),
                      preset="monitoring_station", temp_offset_c=off)
        rr = simulate("LiFePO4", daily_load_wh("relay_only"),
                      preset="relay_only", temp_offset_c=off)
        print(f"{off:>10}{jan:>13.1f}{jul:>13.1f}"
              f"{rs['blackout_days']:>18d}{rr['blackout_days']:>16d}")
    print()
    print("The charge gate binds whenever the daytime temperature stays below "
          f"{CHARGE_GATE_C:.0f} C:")
    print("in that regime no amount of PV can refill the pack, so panel sizing stops mattering")
    print("and the only levers are battery chemistry, a heated enclosure, or a lower site.")
    print()
    print("NOTE: snow days force generation to exactly 0 (buried panel). At this altitude the")
    print("LiFePO4 charge gate also zeroes generation for most of the winter regardless of snow.")


if __name__ == "__main__":
    main()
