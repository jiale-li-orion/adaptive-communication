#!/usr/bin/env python3
"""
los_vs_itm.py — geometric line-of-sight over the real DEM, cross-checked against Longley-Rice ITM.

Two questions, both answerable without a GPU.

1. The ITM coverage run already labelled every grid point reachable or not ("-1" = no spreading
   factor closes the link even at SF12). A geometric visibility test asks a different and much
   cruder question: is there terrain in the way at all. Where the two disagree is informative,
   because ITM reaches around obstructions by diffraction and the geometric test cannot.

2. Every ray-traced pipeline that puts a DEM into a mesh has to pick a mesh resolution. The mesh
   used here is a 121x121 lattice, i.e. about 204 m, while the DEM is 1 arc-second, about 30 m.
   Coarse sampling shaves peaks, so it can turn a blocked link into a visible one. This measures
   how many verdicts flip, which is the number anyone doing terrain ray tracing needs.

Geometry matches the ITM run: 868 MHz, 2 m antenna at both ends, great-circle path sampled at the
DEM's own spacing, and a 4/3-earth curvature term (at 16 km the bulge is tens of metres, far more
than the antenna heights, so omitting it is not a small error).

Deps: numpy.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os

import numpy as np

# --- module resolution -------------------------------------------------------
# Scripts live in code/{physics,runtime,experiments,analysis}; any of them may import from
# another group, so the code root and every group directory go on the path.
import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, *(_os.path.join(_CODE, d) for d in ("physics", "runtime",
                                                     "experiments", "analysis"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)
# -----------------------------------------------------------------------------

from dem_to_mitsuba import (BOX, DEG_LAT_M, GW_LAT, GW_LON, TILE, elev_at, load_tile)
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
GRID = os.path.join(ROOT, "results", "coverage_grid.csv")
OUT = os.path.join(ROOT, "results")

FREQ_HZ = 868e6
LAMBDA = 299792458.0 / FREQ_HZ
ANT_H = 2.0                 # metres above ground, both ends (same as mountain_lora_link.py)
EARTH_K = 4.0 / 3.0         # effective earth radius factor
EARTH_R = 6371000.0


def load_grid() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    lat, lon, sf = [], [], []
    with open(GRID) as f:
        for r in csv.DictReader(f):
            lat.append(float(r["lat"]))
            lon.append(float(r["lon"]))
            sf.append(int(r["best_sf(-1=unreachable)"]))
    return np.array(lat), np.array(lon), np.array(sf)


def bilinear(dem: np.ndarray, lat: np.ndarray, lon: np.ndarray, px: float = 1.0) -> np.ndarray:
    """Vectorised bilinear elevation lookup. Row 0 of an SRTM tile is the north edge.

    `px` is how many DEM pixels one sample of `dem` spans. Without it, a downsampled array is
    still indexed on the full tile's 3600 arc-second convention, every lookup clamps to the
    corner, and the resolution sweep silently reports the same answer at every scale.
    """
    n = dem.shape[0]
    lat0 = float(TILE[1:3])
    lon0 = float(TILE[4:7])
    r = np.clip(((lat0 + 1.0 - lat) * 3600.0) / px - 0.5, 0.0, n - 1.001)
    c = np.clip(((lon - lon0) * 3600.0) / px - 0.5, 0.0, n - 1.001)
    r0 = r.astype(np.int32)
    c0 = c.astype(np.int32)
    dr = r - r0
    dc = c - c0
    return (dem[r0, c0] * (1 - dr) * (1 - dc) + dem[r0 + 1, c0] * dr * (1 - dc)
            + dem[r0, c0 + 1] * (1 - dr) * dc + dem[r0 + 1, c0 + 1] * dr * dc)


def sample_dem(dem: np.ndarray, lat0: float, lon0: float, scale: float) -> np.ndarray:
    """Resample the DEM onto a coarser lattice, the same way the mesh does."""
    if scale == 1:
        return dem
    n = dem.shape[0]
    idx = np.linspace(0, n - 1, (n - 1) // scale + 1)
    i0 = np.floor(idx).astype(int)
    i1 = np.minimum(i0 + 1, n - 1)
    f = (idx - i0)[:, None]
    rows = dem[i0] * (1 - f) + dem[i1] * f
    f2 = (idx - i0)[None, :]
    return rows[:, i0] * (1 - f2) + rows[:, i1] * f2


def visibility(dem: np.ndarray, lat: np.ndarray, lon: np.ndarray,
               n_samples: int = 700, px: float = 1.0) -> dict:
    """Great-circle visibility and first-Fresnel clearance for each point toward the gateway."""
    gw_elev = float(elev_at(dem, GW_LAT, GW_LON))
    h_gw = gw_elev + ANT_H

    s = np.linspace(0.0, 1.0, n_samples)[None, :]
    la = lat[:, None] + s * (GW_LAT - lat[:, None])
    lo = lon[:, None] + s * (GW_LON - lon[:, None])
    prof = bilinear(dem, la, lo, px)

    d_m = np.sqrt(((lat - GW_LAT) * DEG_LAT_M) ** 2
                  + ((lon - GW_LON) * DEG_LAT_M * math.cos(math.radians(GW_LAT))) ** 2)
    d_m = np.maximum(d_m, 1.0)
    d_km = d_m / 1000.0

    e_pt = prof[:, 0]
    h_pt = e_pt + ANT_H
    line = h_pt[:, None] + s * (h_gw - h_pt)[:, None]

    # 4/3-earth bulge: the surface stands this much higher than the straight chord
    d1 = s * d_km[:, None]
    d2 = d_km[:, None] - d1
    bulge = d1 * d2 * 1000.0 / (2.0 * EARTH_K * EARTH_R / 1000.0)

    clearance = line - (prof + bulge)
    # interior samples only: the two endpoints are antennas, not obstructions
    interior = clearance[:, 1:-1]
    min_clr = interior.min(axis=1)

    r1 = np.sqrt(LAMBDA * d1 * d2 * 1e6) / 1.0        # metres; d in km -> *1e6 inside sqrt
    r1_interior = r1[:, 1:-1]
    worst_ratio = (interior / np.maximum(r1_interior, 1e-6)).min(axis=1)

    los = min_clr > 0.0
    # the usual radio-engineering rule: a link is clear if 60% of the first Fresnel zone is free
    clear_60 = worst_ratio > 0.6
    return {
        "d_km": d_km,
        "min_clearance_m": min_clr,
        "fresnel_ratio": worst_ratio,
        "los": los,
        "clear_60": clear_60,
        "gw_elev": gw_elev,
    }


def confusion(geom_los: np.ndarray, itm_reachable: np.ndarray) -> dict:
    """Agreement between a geometric verdict and ITM's reachability verdict."""
    tp = int(np.sum(geom_los & itm_reachable))          # LoS and ITM says reachable
    fn = int(np.sum(~geom_los & itm_reachable))         # blocked geometrically, ITM still closes
    fp = int(np.sum(geom_los & ~itm_reachable))         # visible, ITM still cannot close
    tn = int(np.sum(~geom_los & ~itm_reachable))        # blocked and ITM cannot close
    total = tp + fn + fp + tn
    return {"los_and_reachable": tp, "blocked_but_reachable": fn,
            "los_but_unreachable": fp, "blocked_and_unreachable": tn,
            "total": total, "agreement": (tp + tn) / max(total, 1)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=700)
    ap.add_argument("--scales", default="1,7,27",
                    help="DEM downsampling factors; 27 lands near the 121x121 mesh lattice")
    args = ap.parse_args()

    lat, lon, sf = load_grid()
    itm_reach = sf >= 0
    dem = load_tile()
    print(f"点位数 {len(lat)}   ITM 可达 {int(itm_reach.sum())} "
          f"({100*itm_reach.mean():.1f}%)   不可达 {int((~itm_reach).sum())}")

    gw_elev = float(elev_at(dem, GW_LAT, GW_LON))
    d_km = np.sqrt(((lat - GW_LAT) * DEG_LAT_M) ** 2
                   + ((lon - GW_LON) * DEG_LAT_M * math.cos(math.radians(GW_LAT))) ** 2) / 1000.0
    print(f"网关高程 {gw_elev:.0f} m   距离 {d_km.min():.1f} .. {d_km.max():.1f} km "
          f"(中位 {np.median(d_km):.1f} km)")

    rows = []
    dems = {1: dem}
    for scale in [int(x) for x in args.scales.split(",")]:
        if scale not in dems:
            dems[scale] = sample_dem(dem, 0, 0, scale)
        d2 = dems[scale]
        spacing = scale * 30.87
        # reuse the accurate DEM for the endpoint heights; only the profile is coarsened
        got = visibility(d2, lat, lon, args.samples, px=scale)
        c = confusion(got["los"], itm_reach)
        c60 = confusion(got["clear_60"], itm_reach)
        rows.append({"scale": scale, "spacing_m": spacing, "los": c, "clear60": c60,
                     "los_frac": float(got["los"].mean()),
                     "clear60_frac": float(got["clear_60"].mean())})
        print()
        print(f"--- 剖面分辨率 {spacing:.0f} m (下采样 x{scale}) ---")
        print(f"  几何可见 {int(got['los'].sum())} ({100*got['los'].mean():.1f}%)   "
              f"60% 菲涅尔余隙 {int(got['clear_60'].sum())} ({100*got['clear_60'].mean():.1f}%)")
        print(f"  与 ITM 一致率      {100*c['agreement']:.1f}%   "
              f"(可见且可达 {c['los_and_reachable']}, 遮挡但可达 {c['blocked_but_reachable']}, "
              f"可见但不可达 {c['los_but_unreachable']}, 遮挡且不可达 {c['blocked_and_unreachable']})")
        print(f"  60% 余隙与 ITM 一致率 {100*c60['agreement']:.1f}%")

        if scale == 1:
            # where does geometry say blocked but ITM still closes the link? that is diffraction
            idx = np.where(~got["los"] & itm_reach)[0]
            if len(idx):
                print(f"  ITM 靠绕射闭合的遮挡点 {len(idx)}  个例距离 "
                      f"{d_km[idx].min():.1f}..{d_km[idx].max():.1f} km, "
                      f"最小余隙 {got['min_clearance_m'][idx].min():.1f} m")

    with open(os.path.join(OUT, "los_vs_itm.json"), "w") as f:
        json.dump({"gateway_elev_m": gw_elev, "antenna_h_m": ANT_H,
                   "freq_mhz": FREQ_HZ / 1e6, "points": int(len(lat)),
                   "itm_reachable": int(itm_reach.sum()), "rows": rows},
                  f, indent=2, ensure_ascii=False)
    print(f"\n已写 results/los_vs_itm.json")


if __name__ == "__main__":
    main()
