#!/usr/bin/env python3
"""
fit_loss_model.py — fit a TEMPORALLY CORRELATED link-failure model to a real LoRa trace.

Why this matters: the pilot experiment assumed independent per-call loss
(P(success) = logistic in link margin). Real LoRa connectivity is BURSTY. Independent loss
cannot produce the clustered `outcome_unknown` events the paper is about, so the pilot's
failure distribution was not credible. This script replaces that assumption with statistics
measured from a real 4.5-month deployment.

Data: ChirpBox (Zenodo 10.5281/zenodo.5527877), 21 nodes, Shanghai, 2021-05-03..09-15,
hourly snapshots with a per-node adjacency list.

Method:
  - stream the CSV (562 MB) and reconstruct, per directed link, a binary up/down series
  - fit a Gilbert-Elliott two-state Markov chain (p_gb, p_bg) by transition counting
  - compare against an i.i.d. Bernoulli model with the SAME mean loss rate
  - report the burst-length distribution and the mean burst length

Output: a parameter set that the benchmark environment can sample from, plus the evidence
that the correlated model is required.

Deps: numpy only.
"""
from __future__ import annotations

import ast
import csv
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.normpath(os.path.join(HERE, "..", "..", "data", "downloads", "chirpbox.csv"))
OUT = os.path.normpath(os.path.join(HERE, "..", "..", "results", "loss_model.json"))

csv.field_size_limit(10 ** 9)


def stream_links(path: str):
    """Yield (utc, adjacency dict node->set(neighbours)) for each hourly snapshot."""
    with open(path, newline="") as f:
        r = csv.reader(f)
        header = next(r)
        i_utc = header.index("utc")
        # The adjacency list is the column NAMED node_degree_list. The similarly named
        # node_link_matrix is a 21x21 matrix of link-quality PERCENTAGES (0,5,...,100), not a
        # 0/1 adjacency. Reading the latter as `[set(a) for a in adj]` silently builds a series
        # of "does row i happen to contain the integer j", which yields a 7.44% "availability"
        # that is pure artifact. The two columns agree 100% once both are read correctly and
        # give 62.74% availability.
        i_adj = header.index("node_degree_list")
        for row in r:
            try:
                adj = ast.literal_eval(row[i_adj])
            except Exception:
                continue
            yield row[i_utc], [set(a) for a in adj]


def main() -> None:
    if not os.path.exists(CSV_PATH):
        raise SystemExit(f"missing {CSV_PATH}")

    # ---------- pass 1: accumulate per-link binary series ----------
    prev: list[set] | None = None
    trans = {}                      # (i,j) -> [n_00, n_01, n_10, n_11]
    n_snap = 0
    n_nodes = 0

    for utc, adj in stream_links(CSV_PATH):
        n_nodes = max(n_nodes, len(adj))
        if prev is None:
            prev = adj
            n_snap += 1
            continue
        n = min(len(prev), len(adj))
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                a = 1 if j in prev[i] else 0
                b = 1 if j in adj[i] else 0
                k = (i, j)
                t = trans.get(k)
                if t is None:
                    t = trans[k] = [0, 0, 0, 0]
                t[a * 2 + b] += 1
        prev = adj
        n_snap += 1
        if n_snap % 500 == 0:
            print(f"  {n_snap} snapshots...", flush=True)

    print(f"snapshots: {n_snap}, nodes: {n_nodes}, directed links: {len(trans)}")

    # ---------- aggregate the Markov parameters ----------
    T = np.array(list(trans.values()), dtype=float)          # columns: 00,01,10,11
    tot = T.sum(axis=0)
    n00, n01, n10, n11 = tot
    # column index a*2+b, with a=1 meaning the link existed. So n01 counts 0->1.
    p_bg = n01 / max(n01 + n00, 1)          # bad -> good
    p_gb = n10 / max(n10 + n11, 1)          # good -> bad

    # stationary distribution of the 2-state chain
    pi_bad = p_gb / max(p_gb + p_bg, 1e-12)
    mean_loss = pi_bad
    mean_burst_up = 1 / max(p_gb, 1e-12)
    mean_burst_down = 1 / max(p_bg, 1e-12)

    print()
    print("=" * 78)
    print("GILBERT-ELLIOTT FIT (real ChirpBox LoRa connectivity, hourly)")
    print("=" * 78)
    print(f"transitions counted      : {int(T.sum()):,}")
    print(f"p(up -> down)  p_gb      : {p_gb:.6f}")
    print(f"p(down -> up)  p_bg      : {p_bg:.6f}")
    print(f"stationary loss fraction : {mean_loss:.4f}  ({100*mean_loss:.2f} %)")
    print(f"mean UP burst (hours)    : {mean_burst_up:.2f}")
    print(f"mean DOWN burst (hours)  : {mean_burst_down:.2f}")
    print()
    print("Compare with an i.i.d. Bernoulli model at the SAME mean loss rate:")
    print(f"  i.i.d. mean DOWN burst : {1/max(1-mean_loss,1e-12):.2f} hour(s)")
    ratio = mean_burst_down / max(1 / max(1 - mean_loss, 1e-12), 1e-12)
    print(f"  => real down-bursts are {ratio:.1f}x longer than i.i.d. would predict")
    print()
    if mean_burst_down > 2.0:
        print("  VERDICT: connectivity loss is strongly BURSTY. An i.i.d. per-call model")
        print("           understates clustered outages and cannot reproduce the")
        print("           simultaneous outcome_unknown events the paper studies.")
    else:
        print("  VERDICT: bursts are short at hourly resolution; check sub-hourly structure.")

    out = {
        "source": "ChirpBox (Zenodo 10.5281/zenodo.5527877), Shanghai, hourly",
        "snapshots": n_snap,
        "nodes": n_nodes,
        "directed_links": len(trans),
        "transitions": int(T.sum()),
        "p_good_to_bad": p_gb,
        "p_bad_to_good": p_bg,
        "stationary_loss_fraction": mean_loss,
        "mean_up_burst_hours": mean_burst_up,
        "mean_down_burst_hours": mean_burst_down,
        "iid_mean_down_burst_hours": 1 / max(1 - mean_loss, 1e-12),
        "burstiness_ratio": ratio,
    }
    with open(OUT, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
