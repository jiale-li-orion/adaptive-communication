#!/usr/bin/env python3
"""
relay_siting.py — siting-constrained greedy relay placement over REAL mountain terrain.

Fixes the two flaws in the first coverage run:
  1. the previous "best relay" was a 4510 m mountaintop — an unrealistic site. Here candidates
     are constrained by an elevation band and a local-slope limit (installability proxies).
  2. the previous cumulative figure reused single-relay scores instead of computing the actual
     union. Here it is a proper greedy set cover with a real union at every step.

Pipeline: SRTM1 DEM -> slope map -> feasible relay sites -> per-site coverage of the
points that the gateway cannot reach -> greedy set cover.

Deps: numpy, itmlogic (multiprocessing used if available).
"""
from __future__ import annotations

import math
import os
import sys
import time
from multiprocessing import Pool

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


HERE = os.path.dirname(os.path.abspath(__file__))
from mountain_lora_link import (read_hgt, itm_loss, terrain_profile,  # noqa: E402
                                best_sf, elev_at, haversine_km)

OUT = os.path.normpath(os.path.join(HERE, "..", "..", "results"))
TILE = "N30E094"
FREQ = 868.0
REL = 90.0
TX, GTX, GRX, FEED = 14.0, 2.0, 2.0, 1.0

# siting constraints (installability proxies)
ELEV_MIN, ELEV_MAX = 2500.0, 4000.0   # below 2500 m is often forested/valley; above 4000 m is
                                      # rock/ice with no access and no reliable solar
SLOPE_MAX_DEG = 15.0                  # a relay mast and panel need reasonably flat ground
SPACING_M = 30.87

_DEM = None


def _init():
    global _DEM
    _DEM = read_hgt(TILE)


def _reach(args):
    """Return 1 if a terminal at (lat2,lon2) can reach a terminal at (lat1,lon1)."""
    la1, lo1, la2, lo2 = args
    prof, d, _ = terrain_profile(_DEM, TILE, (la1, lo1), (la2, lo2))
    if d < 0.05 or d > 40.0:
        return 1 if d < 0.05 else 0
    losses, _, _ = itm_loss(FREQ, d, (2.0, 2.0), prof, qr_pct=(REL,))
    sf, _ = best_sf(losses[REL], TX, GTX, GRX, FEED)
    return 1 if sf is not None else 0


def slope_deg(dem, i, j):
    """Local terrain slope in degrees from the 30 m DEM (central difference)."""
    z = dem
    dzdx = (z[i, min(j + 1, z.shape[1] - 1)] - z[i, max(j - 1, 0)]) / (2 * SPACING_M)
    dzdy = (z[min(i + 1, z.shape[0] - 1), j] - z[max(i - 1, 0), j]) / (2 * SPACING_M)
    return math.degrees(math.atan(math.hypot(dzdx, dzdy)))


def main() -> None:
    dem = read_hgt(TILE)
    gw = (30.330, 94.780)
    lat0, lat1, lon0, lon1 = 30.220, 30.440, 94.670, 94.890
    N = 121
    lats = np.linspace(lat0, lat1, N)
    lons = np.linspace(lon0, lon1, N)

    # ---- reuse the gateway coverage grid already computed
    grid = np.loadtxt(os.path.join(OUT, "coverage_grid.csv"), delimiter=",", skiprows=1)
    sf_grid = grid[:, 3].reshape(N, N)
    un = [(i, j) for i in range(N) for j in range(N) if sf_grid[i, j] < 0]
    print(f"unreachable-from-gateway points: {len(un)} / {N*N} "
          f"({100*len(un)/(N*N):.1f} %)")

    # thin the target list for tractability (every 2nd in each direction)
    tgt = [(i, j) for (i, j) in un if i % 4 == 0 and j % 4 == 0]
    tgt_scale = len(un) / max(len(tgt), 1)
    print(f"target points after thinning : {len(tgt)} (scale factor {tgt_scale:.2f})")

    # ---- feasible relay sites
    cand = []
    for i in range(2, N - 2):
        for j in range(2, N - 2):
            e = elev_at(dem, TILE, lats[i], lons[j])
            if not (ELEV_MIN <= e <= ELEV_MAX):
                continue
            gi = int(round((31 - lats[i]) * 3600))
            gj = int(round((lons[j] - 94) * 3600))
            if not (0 <= gi < 3601 and 0 <= gj < 3601):
                continue
            if slope_deg(dem, gi, gj) > SLOPE_MAX_DEG:
                continue
            cand.append((i, j, e))
    print(f"feasible relay sites         : {len(cand)} "
          f"(elev {ELEV_MIN:.0f}-{ELEV_MAX:.0f} m, slope <= {SLOPE_MAX_DEG:.0f} deg)")

    cand = cand[::max(1, len(cand)//300)]
    if not cand:
        print("no feasible relay sites under these constraints"); return
    elevations = [c[2] for c in cand]
    print(f"  candidate elevation: min {min(elevations):.0f}  "
          f"median {np.median(elevations):.0f}  max {max(elevations):.0f} m")

    # ---- coverage set of each candidate over the target points
    jobs = []
    owner = []
    for k, (i, j, e) in enumerate(cand):
        rl = (lats[i], lons[j])
        for (ti, tj) in tgt:
            jobs.append((rl[0], rl[1], lats[ti], lons[tj]))
            owner.append(k)
    print(f"\nITM evaluations: {len(jobs)} — running with {os.cpu_count()} workers", flush=True)

    t0 = time.time()
    with Pool(processes=min(os.cpu_count() or 4, 12), initializer=_init) as pool:
        res = pool.map(_reach, jobs, chunksize=256)
    print(f"done in {time.time()-t0:.0f}s", flush=True)

    res = np.array(res, dtype=bool)
    owner = np.array(owner)
    cover = {k: np.zeros(len(tgt), dtype=bool) for k in range(len(cand))}
    for k in range(len(cand)):
        m = owner == k
        cover[k] = res[m]

    # ---- greedy set cover
    uncovered = np.ones(len(tgt), dtype=bool)
    chosen = []
    print("\ngreedy relay placement (real union at each step):")
    print(f"{'step':<6}{'lat':>10}{'lon':>10}{'elev_m':>9}{'new_pts':>9}"
          f"{'%of_unreach':>13}{'cum_%unreach':>14}")
    for step in range(1, 11):
        best_k, best_gain = None, 0
        for k in range(len(cand)):
            gain = int((cover[k] & uncovered).sum())
            if gain > best_gain:
                best_k, best_gain = k, gain
        if best_k is None or best_gain == 0:
            print("  no further gain — stopping")
            break
        uncovered &= ~cover[best_k]
        i, j, e = cand[best_k]
        chosen.append(cand[best_k])
        served = int((~uncovered).sum())
        frac_un = 100.0 * served / len(tgt)
        # scale back up to the full unreachable set
        cum_points = served * tgt_scale
        overall = 100.0 * (N * N - len(un) + cum_points) / (N * N)
        print(f"{step:<6}{lats[i]:>10.3f}{lons[j]:>10.3f}{e:>9.0f}{best_gain:>9}"
              f"{100.0*best_gain/len(tgt):>13.1f}{frac_un:>14.1f}"
              f"   (overall ~{min(overall,100):.1f}%)")

    with open(os.path.join(OUT, "relay_siting_summary.txt"), "w") as f:
        f.write("Siting-constrained greedy relay placement\n")
        f.write(f"constraints: elevation {ELEV_MIN:.0f}-{ELEV_MAX:.0f} m, "
                f"slope <= {SLOPE_MAX_DEG:.0f} deg\n")
        f.write(f"feasible sites: {len(cand)}; targets: {len(tgt)} "
                f"(from {len(un)} unreachable)\n\n")
        for n, (i, j, e) in enumerate(chosen, 1):
            f.write(f"relay {n}: lat {lats[i]:.4f} lon {lons[j]:.4f} elev {e:.0f} m\n")
    print(f"\nwrote {os.path.join(OUT,'relay_siting_summary.txt')}")


if __name__ == "__main__":
    main()
