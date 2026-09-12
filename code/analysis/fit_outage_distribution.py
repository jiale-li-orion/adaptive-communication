#!/usr/bin/env python3
"""
fit_outage_distribution.py — fit the DISTRIBUTION of link-outage durations, not just its mean.

fit_loss_model.py reports the mean down-burst (6.38 h). A mean is not usable in a system model:
the reliability of a monitoring mission, the buffer depth needed to ride out an outage, and the
value of a store-and-forward relay all depend on the tail, and a Weibull and an exponential with
the same mean have very different tails.

Data: ChirpBox (Zenodo 10.5281/zenodo.5527877), 21 nodes, hourly snapshots, 2021-05-03..09-15.
A link is "down" at hour t when node j is absent from node i's adjacency list. A down-burst is a
maximal run of down hours. Runs touching the start or end of the series are right- or
left-censored and are excluded, since their true length is unknown.

Three candidate laws are fitted by maximum likelihood, and compared by KS distance and AIC:
  exponential  f(x) = (1/b) exp(-x/b)
  lognormal    f(x) = 1/(x s sqrt(2 pi)) exp(-(ln x - m)^2 / (2 s^2))
  weibull      f(x) = (k/b) (x/b)^(k-1) exp(-(x/b)^k)

scipy is not available in this environment, so every estimator and the KS test are implemented
directly. The Weibull shape has no closed form; it is found by maximising the profile likelihood
on a grid refined by golden-section search.

Deps: numpy only.
"""
from __future__ import annotations

import ast
import csv
import json
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.normpath(os.path.join(HERE, "..", "..", "data", "downloads", "chirpbox.csv"))
OUT = os.path.normpath(os.path.join(HERE, "..", "..", "results", "outage_distribution.json"))

csv.field_size_limit(10 ** 9)


# ------------------------------------------------------------------ load series
def load_series(path: str) -> tuple[np.ndarray, list[str]]:
    """Boolean matrix S[link, time]; True means the link exists (node reachable)."""
    with open(path, newline="") as f:
        r = csv.reader(f)
        header = next(r)
        i_utc = header.index("utc")
        # node_degree_list is the adjacency list; node_link_matrix is a matrix of
        # link-quality percentages and must NOT be read as an adjacency (see
        # fit_loss_model.py for the artifact that mistake produces).
        i_adj = header.index("node_degree_list")
        snaps = []
        times = []
        for row in r:
            try:
                adj = ast.literal_eval(row[i_adj])
            except Exception:
                continue
            snaps.append([set(a) for a in adj])
            times.append(row[i_utc])

    n_nodes = max(len(s) for s in snaps)
    n_t = len(snaps)
    links = [(i, j) for i in range(n_nodes) for j in range(n_nodes) if i != j]
    S = np.zeros((len(links), n_t), dtype=bool)
    for t, adj in enumerate(snaps):
        m = len(adj)
        for k, (i, j) in enumerate(links):
            if i < m and j < m:
                S[k, t] = j in adj[i]
    return S, times


# ------------------------------------------------------------------- run lengths
def run_lengths(series: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Lengths of maximal runs of False (down) and True (up), excluding censored ends."""
    down, up = [], []
    for row in series:
        # locate boundaries by diff on the boolean series
        idx = np.flatnonzero(np.diff(row.astype(np.int8)))
        starts = np.concatenate(([0], idx + 1))
        ends = np.concatenate((idx, [len(row) - 1]))
        for s, e in zip(starts, ends):
            if s == 0 or e == len(row) - 1:
                continue                      # touches an end: censored, true length unknown
            (up if row[s] else down).append(e - s + 1)
    return np.asarray(down, dtype=float), np.asarray(up, dtype=float)


# -------------------------------------------------------------------- fitting
def fit_exponential(x: np.ndarray) -> dict:
    b = float(x.mean())
    ll = float(np.sum(-np.log(b) - x / b))
    return {"name": "exponential", "params": {"scale_hours": b}, "loglik": ll, "k": 1}


def fit_lognormal(x: np.ndarray) -> dict:
    lx = np.log(x)
    m = float(lx.mean())
    s = float(lx.std(ddof=0))
    ll = float(np.sum(-np.log(x) - np.log(s) - 0.5 * np.log(2 * np.pi)
                      - (lx - m) ** 2 / (2 * s * s)))
    return {"name": "lognormal", "params": {"mu_log_hours": m, "sigma_log": s},
            "loglik": ll, "k": 2}


def _weibull_profile(k: float, x: np.ndarray, lx_mean: float) -> float:
    """Profile log-likelihood per observation, with the scale concentrated out."""
    xk = np.power(x, k)
    b = float(xk.mean()) ** (1.0 / k)
    return math.log(k) - k * math.log(b) + (k - 1.0) * lx_mean - 1.0


def fit_weibull(x: np.ndarray) -> dict:
    lx_mean = float(np.log(x).mean())
    # coarse grid then golden-section refinement; the profile is unimodal in k
    ks = np.exp(np.linspace(math.log(0.15), math.log(8.0), 240))
    vals = [_weibull_profile(k, x, lx_mean) for k in ks]
    i = int(np.argmax(vals))
    lo = ks[max(0, i - 1)]
    hi = ks[min(len(ks) - 1, i + 1)]
    gr = (math.sqrt(5.0) - 1.0) / 2.0
    a, b = lo, hi
    c, d = b - gr * (b - a), a + gr * (b - a)
    for _ in range(80):
        if _weibull_profile(c, x, lx_mean) > _weibull_profile(d, x, lx_mean):
            b, d = d, c
            c = b - gr * (b - a)
        else:
            a, c = c, d
            d = a + gr * (b - a)
    k = 0.5 * (a + b)
    scale = float(np.power(np.power(x, k).mean(), 1.0 / k))
    n = len(x)
    ll = n * _weibull_profile(k, x, lx_mean)
    return {"name": "weibull", "params": {"shape_k": k, "scale_hours": scale},
            "loglik": ll, "k": 2}


# ------------------------------------------------------------------- goodness
def cdf(model: dict, x: np.ndarray) -> np.ndarray:
    p = model["params"]
    if model["name"] == "exponential":
        return 1.0 - np.exp(-x / p["scale_hours"])
    if model["name"] == "lognormal":
        m, s = p["mu_log_hours"], p["sigma_log"]
        return 0.5 * (1.0 + _erf((np.log(x) - m) / (s * math.sqrt(2.0))))
    k, b = p["shape_k"], p["scale_hours"]
    return 1.0 - np.exp(-np.power(x / b, k))


def _erf(z: np.ndarray) -> np.ndarray:
    """Abramowitz-Stegun 7.1.26; |error| < 1.5e-7, enough for a KS statistic."""
    s = np.sign(z)
    az = np.abs(z)
    t = 1.0 / (1.0 + 0.3275911 * az)
    y = 1.0 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t
                - 0.284496736) * t + 0.254829592) * t * np.exp(-az * az)
    return s * y


def ks_statistic(model: dict, x: np.ndarray) -> tuple[float, float]:
    xs = np.sort(x)
    n = len(xs)
    F = cdf(model, xs)
    i = np.arange(1, n + 1)
    D = float(np.max(np.maximum(i / n - F, F - (i - 1) / n)))
    lam = (math.sqrt(n) + 0.12 + 0.11 / math.sqrt(n)) * D
    # Kolmogorov limiting distribution
    q = 2.0 * sum((-1) ** (j - 1) * math.exp(-2.0 * j * j * lam * lam) for j in range(1, 101))
    return D, float(min(max(q, 0.0), 1.0))


def main() -> None:
    if not os.path.exists(CSV_PATH):
        raise SystemExit(f"missing {CSV_PATH}")

    print(f"reading {CSV_PATH} ...", flush=True)
    S, times = load_series(CSV_PATH)
    print(f"links {S.shape[0]}, snapshots {S.shape[1]} ({times[0]} .. {times[-1]})")
    print(f"mean link availability {100*S.mean():.2f} %")

    down, up = run_lengths(S)
    print(f"uncensored down-runs {len(down)}, up-runs {len(up)}")

    rep = {"source": "ChirpBox (Zenodo 10.5281/zenodo.5527877), hourly",
           "links": int(S.shape[0]), "snapshots": int(S.shape[1]),
           "mean_availability": float(S.mean()),
           "down_runs": int(len(down)), "up_runs": int(len(up))}

    for label, x in (("DOWN (outage)", down), ("UP (connected)", up)):
        if len(x) < 50:
            continue
        print()
        print("=" * 76)
        print(f"{label} DURATION DISTRIBUTION  (n = {len(x)}, hourly resolution)")
        print("=" * 76)
        qs = [0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99, 1.0]
        emp = np.quantile(x, qs)
        print("empirical quantiles (h): " + "  ".join(f"p{int(q*100)}={v:.2f}"
                                                      for q, v in zip(qs, emp)))
        print(f"mean {x.mean():.2f} h   std {x.std():.2f} h   max {x.max():.0f} h")
        print(f"share of runs <= 1 h: {100*np.mean(x <= 1):.1f} %    "
              f"share >= 24 h: {100*np.mean(x >= 24):.1f} %")
        print()
        print(f"{'model':13s} {'params':44s} {'KS D':>7s} {'p':>8s} {'AIC':>10s}")
        print("-" * 76)
        fits = []
        for fit in (fit_exponential(x), fit_lognormal(x), fit_weibull(x)):
            D, p = ks_statistic(fit, x)
            aic = 2 * fit["k"] - 2 * fit["loglik"]
            ps = "  ".join(f"{k}={v:.4f}" for k, v in fit["params"].items())
            print(f"{fit['name']:13s} {ps:44s} {D:7.4f} {p:8.4f} {aic:10.1f}")
            fits.append({**fit, "ks_D": D, "ks_p": p, "aic": aic})
        best = min(fits, key=lambda f: f["aic"])
        print()
        print(f"best by AIC: {best['name']}   "
              f"(exponential is rejected as a model of the tail if its p is small)")
        key = "down" if label.startswith("DOWN") else "up"
        rep[key] = {"n": int(len(x)), "mean_hours": float(x.mean()),
                    "quantiles_hours": {f"p{int(q*100)}": float(v) for q, v in zip(qs, emp)},
                    "fits": fits, "best_by_aic": best["name"]}

    with open(OUT, "w") as f:
        json.dump(rep, f, indent=2)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
