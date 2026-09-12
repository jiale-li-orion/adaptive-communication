#!/usr/bin/env python3
"""
mountain_lora_feasibility.py — pure-software feasibility check for a LoRa monitoring link
over REAL mountain terrain. No hardware, no field campaign, no GIS install.

Pipeline (fully offline once the SRTM tiles are fetched):
  1. read real SRTM1 tiles (.hgt, 3601x3601 int16 big-endian) directly with numpy — no GDAL
  2. pick a real ridge-top gateway and real valley-floor nodes; extract terrain profiles
  3. run the Longley-Rice Irregular Terrain Model (ITM v1.2.2, via `itmlogic`) point-to-point
  4. close the LoRa link budget (SX1276 sensitivities per spreading factor)
  5. report the propagation regime, link margin, and which SF closes

Site: lat 30-31 N, lon 94-95 E — Bomê County, Nyingchi, Tibet (Yigong area, site of one of the
largest recorded landslides). Terrain is real SRTM1 data, not synthetic.

Deps: numpy, itmlogic  (pip, no GPU, no compiled extensions)
Reference: Oughton et al., JOSS 5:2266 (2020); Hufford, NTIA Report 82-100.
"""
from __future__ import annotations

import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
HGT_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "data", "dem", "hgt"))
S3 = "https://s3.amazonaws.com/elevation-tiles-prod/skadi"


# --------------------------------------------------------------- SRTM access
def read_hgt(tile: str) -> np.ndarray:
    """Read an SRTM1 .hgt tile -> (3601,3601) int16; row 0 is the NORTH edge."""
    path = os.path.join(HGT_DIR, f"{tile}.hgt")
    if not os.path.exists(path):
        raise SystemExit(
            f"missing {path}\n  fetch with:\n"
            f"  curl -L -o {path}.gz {S3}/{tile[:3]}/{tile}.hgt.gz && gunzip {path}.gz")
    raw = np.fromfile(path, dtype=">i2")
    n = int(round(math.sqrt(raw.size)))
    return raw.reshape(n, n)


def tile_of(lat: float, lon: float) -> str:
    return (f"{'N' if lat >= 0 else 'S'}{abs(int(math.floor(lat))):02d}"
            f"{'E' if lon >= 0 else 'W'}{abs(int(math.floor(lon))):03d}")


def elev_at(dem: np.ndarray, tile: str, lat: float, lon: float) -> float:
    n = dem.shape[0]
    lat0 = int(tile[1:3]) * (1 if tile[0] == "N" else -1)
    lon0 = int(tile[4:7]) * (1 if tile[3] == "E" else -1)
    r = min(max(int(round((lat0 + 1 - lat) * (n - 1))), 0), n - 1)
    c = min(max(int(round((lon - lon0) * (n - 1))), 0), n - 1)
    return float(dem[r, c])


def profile(dem: np.ndarray, tile: str, p1, p2, npts: int = 200) -> list[float]:
    lats = np.linspace(p1[0], p2[0], npts)
    lons = np.linspace(p1[1], p2[1], npts)
    return [elev_at(dem, tile, a, b) for a, b in zip(lats, lons)]


def haversine_km(p1, p2) -> float:
    la1, lo1, la2, lo2 = map(math.radians, [p1[0], p1[1], p2[0], p2[1]])
    h = (math.sin((la2 - la1) / 2) ** 2
         + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2)
    return 2 * 6371.0 * math.asin(math.sqrt(h))


# ------------------------------------------------- Longley-Rice / ITM v1.2.2
def itm_point_to_point(fmhz: float, d_km: float, hg: tuple[float, float],
                       elevs_m: list[float], eps: float = 15.0, sgm: float = 0.005,
                       ipol: int = 1, ens0: float = 301.0, klim: int = 5,
                       mdvarx: int = 11):
    """Return (aref_dB, regime). Follows the canonical ITS ITM driver ordering."""
    from itmlogic.preparatory_subroutines.qlrpfl import qlrpfl
    from itmlogic.lrprop import lrprop

    pfl = [len(elevs_m) - 1, 0] + [float(e) for e in elevs_m]

    prop = {
        "fmhz": fmhz,
        "d": d_km,
        "hg": list(hg),
        "ipol": ipol,
        "eps": eps,
        "sgm": sgm,
        "klim": klim,
        "lvar": 5,
        "gma": 157e-9,
        "ens": ens0,
        "klimx": 0,
        "mdvarx": mdvarx,
        "mdp": -1,
    }
    # range step in metres, as the driver does
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
    aref = prop["aref"]

    # propagation regime, per the driver's own classification
    q = prop["dist"] - prop["dlsa"]
    q = max(q - 0.5 * pfl[1] / 1000.0, 0) - max(-q - 0.5 * pfl[1] / 1000.0, 0)
    regime = "LoS" if q < 0 else ("single-horizon" if q == 0 else "double-horizon")
    return float(aref), regime


# ------------------------------------------------------------ LoRa link budget
SENS_125KHZ = {7: -123.0, 8: -126.0, 9: -129.0, 10: -132.0, 11: -134.5, 12: -137.0}

# SF -> nominal bitrate at BW=125kHz, CR=4/5  (for airtime/energy estimates)
BITRATE_125 = {7: 5469, 8: 3125, 9: 1758, 10: 977, 11: 537, 12: 293}  # bit/s


def margin(aref_db: float, sf: int, tx_dbm=14.0, g_tx=2.0, g_rx=2.0,
           feeder=1.0, bw_khz=125.0) -> float:
    sens = SENS_125KHZ[sf] + 10 * math.log10(bw_khz / 125.0)
    prx = tx_dbm + g_tx + g_rx - feeder - aref_db
    return prx - sens


def main() -> None:
    tile = "N30E094"
    dem = read_hgt(tile)
    print(f"SRTM1 {tile}: {dem.shape}, elevation {dem.min():.0f}–{dem.max():.0f} m\n")

    gw = (30.330, 94.780)               # ridge-top gateway
    e_gw = elev_at(dem, tile, *gw)

    nodes = [
        ("valley A", (30.300, 94.860)),
        ("valley B", (30.360, 94.900)),
        ("valley C", (30.270, 94.800)),
        ("far D",    (30.200, 94.930)),
        ("far E",    (30.420, 94.700)),
    ]

    print(f"gateway ridge {gw} @ {e_gw:.0f} m (given 2 m antenna)\n")
    hdr = (f"{'node':<10}{'dist_km':>9}{'node_m':>8}{'min_m':>7}"
           f"{'obstr_m':>9}{'aref_dB':>9}{'regime':>15}"
           f"{'SF7':>7}{'SF12':>7}{'best_SF':>9}")
    print(hdr)
    print("-" * len(hdr))

    results = []
    for name, pt in nodes:
        d = haversine_km(gw, pt)
        prof = profile(dem, tile, gw, pt, 200)
        e_nd = prof[-1]
        line = np.linspace(e_gw + 2.0, e_nd + 2.0, len(prof))
        obs = float(np.max(np.array(prof) - line))

        aref, regime = itm_point_to_point(868.0, max(d, 0.05), (2.0, 2.0), prof)
        m = {sf: margin(aref, sf) for sf in SENS_125KHZ}
        ok = [sf for sf in sorted(m) if m[sf] > 0]
        best = f"SF{ok[0]}" if ok else "none"
        results.append((name, d, aref, regime, m, best, prof, obs, e_nd))

        print(f"{name:<10}{d:>9.2f}{e_nd:>8.0f}{min(prof):>7.0f}{obs:>9.0f}"
              f"{aref:>9.1f}{regime:>15}{m[7]:>7.1f}{m[12]:>7.1f}{best:>9}")

    print("\nPer-SF link margin (dB), positive = closes:")
    print(f"{'node':<10}" + "".join(f"{'SF'+str(sf):>8}" for sf in sorted(SENS_125KHZ)))
    for name, d, aref, regime, m, best, *_ in results:
        print(f"{name:<10}" + "".join(f"{m[sf]:>8.1f}" for sf in sorted(SENS_125KHZ)))

    # rough airtime / energy per uplink for the closing nodes
    print("\nAirtime per 20-byte uplink payload (ms) at the best SF that closes:")
    for name, d, aref, regime, m, best, *_ in results:
        if best == "none":
            print(f"  {name:<10} no SF closes -> node cannot report at all")
            continue
        sf = int(best[2:])
        br = BITRATE_125[sf]
        toa = 8 * 20 / br * 1000
        print(f"  {name:<10} {best:<5} ~{toa:6.0f} ms/20B   "
              f"(SF12 would be ~{8*20/BITRATE_125[12]*1000:.0f} ms)")

    print("\nAssumptions: 868 MHz, TX 14 dBm, 2 dBi both ends, 1 dB feeder, BW 125 kHz,")
    print("2 m antennas, ground eps=15, sigma=0.005 S/m, continental temperate climate,")
    print("mdvarx=11 (point-to-point mobile). SX1276 sensitivities SF7..SF12.")


if __name__ == "__main__":
    main()
