#!/usr/bin/env python3
"""Shared paper statistics with frozen deterministic semantics."""
from __future__ import annotations

import math
import random
import statistics


def quantile_linear(values: list[float], p: float) -> float:
    xs = sorted(values)
    if not xs:
        return float("nan")
    pos = (len(xs) - 1) * p
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return xs[lo]
    w = pos - lo
    return xs[lo] * (1 - w) + xs[hi] * w


def bootstrap_mean_ci_linear(values: list[float], *, seed: int, resamples: int) -> dict[str, float]:
    if not values:
        return {"mean": float("nan"), "lo": float("nan"), "hi": float("nan")}
    rng = random.Random(seed)
    n = len(values)
    means = [sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(resamples)]
    return {
        "mean": statistics.fmean(values),
        "lo": quantile_linear(means, 0.025),
        "hi": quantile_linear(means, 0.975),
    }


def bootstrap_mean_ci_order(values: list[float], *, seed: int, resamples: int) -> dict[str, float] | None:
    if not values:
        return None
    rng = random.Random(seed)
    samples = []
    for _ in range(resamples):
        draw = [values[rng.randrange(len(values))] for _ in values]
        samples.append(statistics.fmean(draw))
    samples.sort()
    return {
        "mean": float(statistics.fmean(values)),
        "lo": float(samples[int(0.025 * (resamples - 1))]),
        "hi": float(samples[int(0.975 * (resamples - 1))]),
    }


def wilson_interval(success: int, n: int, z: float = 1.959963984540054) -> dict[str, float | int]:
    if n <= 0:
        return {"success": success, "n": n, "rate": float("nan"), "lo": float("nan"), "hi": float("nan")}
    phat = success / n
    denom = 1 + z * z / n
    center = (phat + z * z / (2 * n)) / denom
    half = z * math.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n) / denom
    return {
        "success": success,
        "n": n,
        "rate": phat,
        "lo": max(0.0, center - half),
        "hi": min(1.0, center + half),
    }


def paired_differences(left: list[float], right: list[float]) -> list[float]:
    if len(left) != len(right):
        raise ValueError(f"paired samples differ in length: {len(left)} != {len(right)}")
    return [a - b for a, b in zip(left, right)]


def zero_check(values: list[float]) -> dict[str, float | int | bool]:
    nonzero = [v for v in values if v != 0]
    return {
        "all_zero": not nonzero,
        "nonzero_count": len(nonzero),
        "max_abs": max((abs(v) for v in values), default=0.0),
    }
