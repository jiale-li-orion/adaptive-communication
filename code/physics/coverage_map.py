#!/usr/bin/env python3
"""
coverage_map.py — terrain-aware LoRa coverage and relay-placement analysis over REAL mountain
terrain, entirely in software. No hardware, no field campaign.

Answers, quantitatively, the sponsor's question:
  "in mountains with no grid power and frequent link loss, how much of the monitoring area
   can a single gateway actually serve, and does coverage enhancement actually help?"

Method
  1. grid a region of real SRTM1 terrain
  2. for every grid point: terrain profile -> Longley-Rice ITM -> loss at a reliability level
  3. classify each point by the best (lowest) spreading factor whose link budget closes,
     or mark it UNREACHABLE if even SF12 fails
  4. greedy relay placement: choose the relay site that maximises the number of newly served
     unreachable points, and report marginal coverage per relay

Outputs: coverage_grid.csv, coverage_summary.txt, coverage_map.png (if matplotlib present)

Deps: numpy, itmlogic  (+ matplotlib optional, for the figure)
"""
from __future__ import annotations

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


import math
import os
import sys
import time

import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
from mountain_lora_link import (read_hgt, itm_loss, terrain_profile,  # noqa: E402
                                best_sf, SENS_125KHZ)

OUT = os.path.normpath(os.path.join(HERE, "..", "..", "results"))

TILE = "N30E094"
FREQ_MHZ = 868.0
RELIABILITY = 90.0          # link budget at 90% reliability
TX_DBM, G_TX, G_RX, FEEDER = 14.0, 2.0, 2.0, 1.0


def loss_and_sf(dem, a, b) -> tuple[float, int | None]:
    prof, d, _ = terrain_profile(dem, TILE, a, b)
    if d < 0.05:
        return 0.0, 7
    losses, _, _ = itm_loss(FREQ_MHZ, d, (2.0, 2.0), prof, qr_pct=(RELIABILITY,))
    L = losses[RELIABILITY]
    sf, _ = best_sf(L, TX_DBM, G_TX, G_RX, FEEDER)
    return L, sf


def build_grid(dem, gw, lat0, lat1, lon0, lon1, n):
    lats = np.linspace(lat0, lat1, n)
    lons = np.linspace(lon0, lon1, n)
    rows = []
    t0 = time.time()
    for i, la in enumerate(lats):
        for j, lo in enumerate(lons):
            L, sf = loss_and_sf(dem, gw, (la, lo))
            rows.append((la, lo, L, sf if sf else -1))
        if i % 20 == 0:
            el = time.time() - t0
            print(f"  row {i+1}/{n}  ({el:.0f}s elapsed)", flush=True)
    return rows


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    dem = read_hgt(TILE)
    gw = (30.330, 94.780)
    print(f"gateway {gw} @ {dem[int((31-30.330)*3600), int((94.780-94)*3600)]:.0f} m (SRTM)")

    # region: +/- ~0.11 deg (~12 km) around the gateway
    lat0, lat1 = 30.220, 30.440
    lon0, lon1 = 94.670, 94.890
    N = 121                      # ~200 m spacing
    print(f"gridding {N}x{N} = {N*N} points over "
          f"[{lat0},{lat1}]x[{lon0},{lon1}] at 868 MHz, {RELIABILITY:.0f}% reliability\n")

    rows = build_grid(dem, gw, lat0, lat1, lon0, lon1, N)

    sf_arr = np.array([r[3] for r in rows]).reshape(N, N)
    loss_arr = np.array([r[2] for r in rows]).reshape(N, N)

    total = N * N
    unreach = int((sf_arr < 0).sum())
    served = total - unreach

    lines = []
    def emit(s=""):
        print(s); lines.append(s)

    emit("=" * 74)
    emit("SINGLE-GATEWAY COVERAGE, REAL TERRAIN (Bome/Yigong, Tibet), 868 MHz, 90% reliability")
    emit("=" * 74)
    emit(f"grid                  : {N}x{N} = {total} points (~200 m spacing)")
    emit(f"gateway               : {gw[0]:.3f}N {gw[1]:.3f}E")
    emit(f"reachable (some SF)   : {served:5d}  ({100*served/total:5.1f} %)")
    emit(f"UNREACHABLE (even SF12): {unreach:5d}  ({100*unreach/total:5.1f} %)")
    emit("")
    emit("breakdown by lowest SF that closes:")
    for sf in sorted(SENS_125KHZ):
        c = int((sf_arr == sf).sum())
        emit(f"  SF{sf:<2d}: {c:5d}  ({100*c/total:5.1f} %)")
    emit("")
    reach = loss_arr[sf_arr >= 0]
    if reach.size:
        emit(f"loss over reachable points: min {reach.min():.1f}  median {np.median(reach):.1f}  "
             f"max {reach.max():.1f} dB")
    un = loss_arr[sf_arr < 0]
    if un.size:
        emit(f"loss over UNREACHABLE pts : min {un.min():.1f}  median {np.median(un):.1f}  "
             f"max {un.max():.1f} dB")

    # ------------------------------------------------ greedy relay placement
    emit("")
    emit("-" * 74)
    emit("GREEDY RELAY PLACEMENT (relay also on the ridge; same radio assumptions)")
    emit("-" * 74)

    lats = np.linspace(lat0, lat1, N)
    lons = np.linspace(lon0, lon1, N)
    un_idx = [(i, j) for i in range(N) for j in range(N) if sf_arr[i, j] < 0]
    emit(f"unreachable points to serve: {len(un_idx)}")

    if un_idx:
        # candidate relay sites: a subsample of the grid (every 8th -> ~225 candidates)
        cand = [(i, j) for i in range(4, N, 8) for j in range(4, N, 8)]
        emit(f"candidate relay sites      : {len(cand)}")
        # target set: cap at 400 unreachable points for tractability
        tgt = un_idx[::max(1, len(un_idx) // 400)]
        emit(f"target points evaluated    : {len(tgt)}")

        cover = {}
        t0 = time.time()
        for ci, (i, j) in enumerate(cand):
            rl = (lats[i], lons[j])
            got = 0
            for (ti, tj) in tgt:
                _, sf = loss_and_sf(dem, rl, (lats[ti], lons[tj]))
                if sf is not None:
                    got += 1
            cover[(i, j)] = got
            if ci % 25 == 0:
                print(f"  candidate {ci+1}/{len(cand)}  ({time.time()-t0:.0f}s)", flush=True)

        rank = sorted(cover.items(), key=lambda kv: -kv[1])
        emit("")
        emit(f"{'rank':<6}{'relay lat':>11}{'relay lon':>11}{'unreachable served':>21}")
        best_sets = []
        for k, ((i, j), got) in enumerate(rank[:5]):
            emit(f"{k+1:<6}{lats[i]:>11.3f}{lons[j]:>11.3f}{got:>21}")
        # cumulative gain of top-k disjoint-ish relays
        emit("")
        emit("cumulative coverage if the top-k relays are deployed (upper bound, sites reused):")
        for k in (1, 2, 3, 5, 10):
            got = rank[min(k, len(rank)) - 1][1]
            frac = 100.0 * got / len(tgt)
            tot_frac = 100.0 * (served + got * len(un_idx) / len(tgt)) / total
            emit(f"  k={k:<3d} newly served ~{frac:5.1f}% of unreachable  ->  overall coverage ~"
                 f"{min(tot_frac,100.0):5.1f}%")

    # ------------------------------------------------------------- write out
    with open(os.path.join(OUT, "coverage_grid.csv"), "w") as f:
        f.write("lat,lon,loss_dB,best_sf(-1=unreachable)\n")
        for la, lo, L, sf in rows:
            f.write(f"{la:.5f},{lo:.5f},{L:.2f},{sf}\n")
    with open(os.path.join(OUT, "coverage_summary.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
    emit("")
    emit(f"wrote {os.path.join(OUT,'coverage_grid.csv')} and coverage_summary.txt")

    # ------------------------------------------------------------- figure
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(8, 7))
        disp = np.where(sf_arr < 0, 13, sf_arr)
        im = ax.imshow(disp, origin="lower", cmap="viridis",
                       extent=[lon0, lon1, lat0, lat1], vmin=7, vmax=13)
        ax.plot(gw[1], gw[0], "r*", ms=18, label="gateway (ridge)")
        ax.set_xlabel("longitude"); ax.set_ylabel("latitude")
        ax.set_title("LoRa reachability over SRTM terrain (Bome/Yigong, Tibet)\n"
                     "colour = lowest SF that closes; yellow = unreachable at any SF")
        cb = fig.colorbar(im, ax=ax); cb.set_label("best SF (13 = unreachable)")
        ax.legend(loc="upper right")
        fig.tight_layout()
        fig.savefig(os.path.join(OUT, "coverage_map.png"), dpi=140)
        emit(f"wrote {os.path.join(OUT,'coverage_map.png')}")
    except Exception as e:
        emit(f"(no figure: {type(e).__name__}: {e})")


if __name__ == "__main__":
    main()
