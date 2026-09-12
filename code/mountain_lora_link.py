#!/usr/bin/env python3
"""
mountain_lora_link.py — pure-software feasibility study of a LoRa monitoring link over REAL
mountain terrain. No hardware, no field campaign, no GIS/GDAL install.

Pipeline (fully offline once SRTM tiles are fetched):
  1. read real SRTM1 tiles (.hgt, 3601x3601 int16 big-endian) straight into numpy
  2. lay out a real ridge-top gateway and real valley/ridge nodes; sample terrain profiles
     at the DEM's native resolution (no over-sampling)
  3. run Longley-Rice ITM v1.2.2 point-to-point (via `itmlogic`) exactly as its own driver does
  4. apply the variability term (`avar`) so the budget uses a *reliability level*, not the median
  5. close the LoRa link budget (SX1276 sensitivities per SF) and map margin -> usable SF
  6. estimate per-uplink airtime and hence the energy the node must supply

Site: lat 30-31 N, lon 94-95 E — Bome County, Nyingchi, Tibet (Yigong area, one of the largest
recorded landslides). Terrain is real SRTM1, not synthetic.

Deps: numpy, itmlogic
Refs: Hufford, NTIA Report 82-100; Oughton et al., JOSS 5:2266 (2020).
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
HGT_DIR = os.path.normpath(os.path.join(HERE, "..", "data", "dem", "hgt"))
S3 = "https://s3.amazonaws.com/elevation-tiles-prod/skadi"

SRTM1_SPACING_KM = 30.87 / 1000.0     # 1 arc-second latitude ~ 30.87 m


# ----------------------------------------------------------------- SRTM access
def read_hgt(tile: str) -> np.ndarray:
    path = os.path.join(HGT_DIR, f"{tile}.hgt")
    if not os.path.exists(path):
        raise SystemExit(
            f"missing {path}\n  curl -L -o {path}.gz {S3}/{tile[:3]}/{tile}.hgt.gz && gunzip {path}.gz")
    raw = np.fromfile(path, dtype=">i2")
    n = int(round(math.sqrt(raw.size)))
    return raw.reshape(n, n)


def elev_at(dem, tile, lat, lon) -> float:
    n = dem.shape[0]
    lat0 = int(tile[1:3]) * (1 if tile[0] == "N" else -1)
    lon0 = int(tile[4:7]) * (1 if tile[3] == "E" else -1)
    r = min(max(int(round((lat0 + 1 - lat) * (n - 1))), 0), n - 1)
    c = min(max(int(round((lon - lon0) * (n - 1))), 0), n - 1)
    return float(dem[r, c])


def haversine_km(p1, p2) -> float:
    la1, lo1, la2, lo2 = map(math.radians, [p1[0], p1[1], p2[0], p2[1]])
    h = (math.sin((la2 - la1) / 2) ** 2
         + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2)
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def terrain_profile(dem, tile, p1, p2):
    """Sample at ~native DEM spacing; never finer (over-sampling corrupts ITM roughness stats)."""
    d_km = haversine_km(p1, p2)
    npts = int(min(600, max(25, math.ceil(d_km / SRTM1_SPACING_KM))))
    lats = np.linspace(p1[0], p2[0], npts)
    lons = np.linspace(p1[1], p2[1], npts)
    return [elev_at(dem, tile, a, b) for a, b in zip(lats, lons)], d_km, npts


# --------------------------------------------------------- Longley-Rice (ITM)
def itm_loss(fmhz: float, d_km: float, hg, elevs, qr_pct=(50.0,),
             qc_pct=50.0, eps=15.0, sgm=0.005, ipol=1, ens0=301.0, klim=5, mdvarx=11):
    """Total propagation loss (dB) = free-space loss + ITM correction, at given
    reliability (qr) and confidence (qc) levels — the driver's own convention."""
    from itmlogic.preparatory_subroutines.qlrpfl import qlrpfl
    from itmlogic.lrprop import lrprop
    from itmlogic.statistics.avar import avar
    from itmlogic.misc.qerfi import qerfi

    pfl = [len(elevs) - 1, 0] + [float(e) for e in elevs]
    prop = {
        "fmhz": fmhz, "d": d_km, "hg": list(hg), "ipol": ipol,
        "eps": eps, "sgm": sgm, "klim": klim, "lvar": 5, "gma": 157e-9,
        "ens": ens0, "klimx": 0, "mdvarx": mdvarx, "mdp": -1,
    }
    pfl[1] = d_km * 1000.0 / pfl[0]
    prop["pfl"] = pfl
    prop["kwx"] = 0
    prop["wn"] = fmhz / 47.7
    prop["gme"] = prop["gma"] * (1 - 0.04665 * math.exp(prop["ens"] / 179.3))
    zq = complex(eps, 376.62 * sgm / prop["wn"])
    prop["zgnd"] = np.sqrt(zq - 1)
    if ipol != 0:
        prop["zgnd"] = prop["zgnd"] / zq

    prop = qlrpfl(prop)
    prop = lrprop(d_km, prop)
    aref_median = float(prop["aref"])

    # Free-space loss, dB. Computed directly in km: prop['dist'] is in metres internally
    # (pfl[1] is metres), so the driver's own fs expression is not reusable here.
    fs = 20.0 * math.log10(d_km) + 20.0 * math.log10(fmhz) - 27.55

    # qerfi takes the levels as fractions, exactly as the ITM driver passes them (qr/100)
    zr = qerfi([q / 100.0 for q in qr_pct])
    zc = qerfi([qc_pct / 100.0])
    losses = {}
    for q, z in zip(qr_pct, zr):
        avar1, prop = avar(z, 0, zc[0], prop)
        losses[q] = fs + avar1
    return losses, aref_median, fs


# ------------------------------------------------------------- LoRa link budget
SENS_125KHZ = {7: -123.0, 8: -126.0, 9: -129.0, 10: -132.0, 11: -134.5, 12: -137.0}
BITRATE_125 = {7: 5469, 8: 3125, 9: 1758, 10: 977, 11: 537, 12: 293}   # bit/s, BW125 CR4/5


def best_sf(loss_db: float, tx=14.0, g_tx=2.0, g_rx=2.0, feeder=1.0):
    """Highest data rate (lowest SF) whose margin is positive; else None."""
    prx = tx + g_tx + g_rx - feeder - loss_db
    for sf in sorted(SENS_125KHZ):
        if prx - SENS_125KHZ[sf] > 0:
            return sf, prx - SENS_125KHZ[sf]
    return None, prx - SENS_125KHZ[12]


def airtime_ms(sf: int, payload_b: int = 20, bw_khz: float = 125.0) -> float:
    br = BITRATE_125[sf] * bw_khz / 125.0
    return 8 * payload_b / br * 1000.0


def main() -> None:
    tile = "N30E094"
    dem = read_hgt(tile)
    print(f"SRTM1 {tile}: {dem.shape}, elevation {dem.min():.0f}-{dem.max():.0f} m")

    gw = (30.330, 94.780)
    e_gw = elev_at(dem, tile, *gw)
    print(f"gateway on ridge {gw} @ {e_gw:.0f} m\n")

    nodes = [("valley A", (30.300, 94.860)),
             ("valley B", (30.360, 94.900)),
             ("valley C", (30.270, 94.800)),
             ("far D",    (30.200, 94.930)),
             ("far E",    (30.420, 94.700))]

    hdr = (f"{'node':<10}{'dist_km':>8}{'node_m':>8}{'obstr_m':>9}"
           f"{'FS_dB':>8}{'L50_dB':>8}{'L90_dB':>8}{'L99_dB':>8}"
           f"{'SF@L50':>8}{'SF@L90':>8}{'SF@L99':>8}")
    print(hdr); print("-" * len(hdr))

    rows = []
    for name, pt in nodes:
        prof, d, npts = terrain_profile(dem, tile, gw, pt)
        line = np.linspace(e_gw + 2.0, prof[-1] + 2.0, len(prof))
        obstr = float(np.max(np.array(prof) - line))
        losses, aref, fs = itm_loss(868.0, d, (2.0, 2.0), prof, qr_pct=(50.0, 90.0, 99.0))
        sf50, _ = best_sf(losses[50.0]); sf90, _ = best_sf(losses[90.0]); sf99, _ = best_sf(losses[99.0])
        fmt = lambda s: f"SF{s}" if s else "none"
        rows.append((name, d, prof[-1], obstr, fs, losses, (sf50, sf90, sf99), npts))
        print(f"{name:<10}{d:>8.2f}{prof[-1]:>8.0f}{obstr:>9.0f}"
              f"{fs:>8.1f}{losses[50.0]:>8.1f}{losses[90.0]:>8.1f}{losses[99.0]:>8.1f}"
              f"{fmt(sf50):>8}{fmt(sf90):>8}{fmt(sf99):>8}")

    print("\nEnergy per uplink (20 B payload) at the reliability-90% spreading factor:")
    print(f"{'node':<10}{'SF':>5}{'airtime_ms':>12}{'I_tx_mA':>9}{'charge_uC':>12}{'mAh/yr@1/h':>12}")
    for name, d, e, obstr, fs, losses, (sf50, sf90, sf99), npts in rows:
        sf = sf90 or sf99 or 12
        toa = airtime_ms(sf)
        i_tx = 44.0                     # SX1276 @ +14 dBm
        charge_uc = i_tx * toa * 1000 / 1000.0 * 1000 / 1000.0   # mA*ms -> uC
        per_hour = i_tx * toa / 3600.0 / 1000.0                  # mAh per uplink
        mAh_yr = per_hour * 24 * 365
        print(f"{name:<10}{sf:>5}{toa:>12.0f}{i_tx:>9.0f}{charge_uc:>12.1f}{mAh_yr:>12.2f}")

    print("\nFor scale: a 3.6 V 3600 mAh LiSOCl2 cell delivers ~3600 mAh once.")
    print("Assumes 868 MHz, TX 14 dBm, 2 dBi both ends, 1 dB feeder, BW 125 kHz, 2 m antennas,")
    print("ground eps=15 / sigma=0.005 S/m, continental temperate climate, mdvarx=11.")
    print("Airtime is payload-only (preamble/header/CRC excluded) -> treat as a lower bound.")


if __name__ == "__main__":
    main()
