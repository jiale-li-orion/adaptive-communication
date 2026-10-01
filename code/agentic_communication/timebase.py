"""Deterministic simulator-time -> timezone-aware runtime timestamps."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta


SIM_EPOCH = datetime(2026, 1, 1, tzinfo=UTC)


def sim_datetime(t_s: int) -> datetime:
    return SIM_EPOCH + timedelta(seconds=int(t_s))
