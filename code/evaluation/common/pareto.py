#!/usr/bin/env python3
"""Generic Pareto-front helpers promoted from legacy communication analysis."""
from __future__ import annotations

from collections.abc import Mapping, Sequence


def dominates(left: Sequence[float], right: Sequence[float], *, directions: Sequence[int], eps: float = 1e-12) -> bool:
    if len(left) != len(right) or len(left) != len(directions):
        raise ValueError("Pareto vectors/directions must have equal length")
    not_worse = True
    strictly_better = False
    for x, y, sign in zip(left, right, directions):
        if sign * (y - x) > eps:
            not_worse = False
            break
        if sign * (x - y) > eps:
            strictly_better = True
    return not_worse and strictly_better


def frontier(points: Mapping[str, Sequence[float]], *, directions: Sequence[int], eps: float = 1e-12) -> tuple[str, ...]:
    labels = sorted(points)
    return tuple(
        label
        for label in labels
        if not any(
            other != label and dominates(points[other], points[label], directions=directions, eps=eps)
            for other in labels
        )
    )
