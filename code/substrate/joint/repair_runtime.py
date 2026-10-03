#!/usr/bin/env python3
"""Ordinary, legal-information repair activation baselines.

These controllers are intentionally *not* the proposed positive method.  They are strong ordinary
baselines that decide whether the gateway should temporarily boost its backup backhaul.

Information contract: each controller receives only a `BackupRepairView` built from gateway-local
state at the current tick: primary-link status, samples already present in the gateway queue, their
public obligation deadlines, and the configured base backup profile.  No future outage duration,
node cache, future harvest, or simulator truth is exposed.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BackupDemand:
    deadline_s: int
    payload_bytes: int


@dataclass(frozen=True)
class BackupRepairView:
    now_s: int
    tick_s: int
    primary_available: bool
    live_demands: tuple[BackupDemand, ...]
    base_rate_s: int
    base_payload_bytes: int


@dataclass(frozen=True)
class AccessRepairView:
    now_s: int
    tick_s: int
    access_available: bool


class _BudgetedController:
    """Consumes activation time only while the boost is actually on."""

    kind = "budgeted"

    def __init__(self, budget_s: int):
        self.initial_budget_s = max(0, int(budget_s))
        self.remaining_s = self.initial_budget_s
        self.active_s = 0
        self.decisions = 0
        self.activation_episodes = 0
        self._was_active = False

    def wants_boost(self, view: BackupRepairView) -> bool:
        raise NotImplementedError

    def decide(self, view: BackupRepairView) -> bool:
        self.decisions += 1
        active = False
        if self.remaining_s >= view.tick_s and self.wants_boost(view):
            self.remaining_s -= view.tick_s
            self.active_s += view.tick_s
            active = True
        if active and not self._was_active:
            self.activation_episodes += 1
        self._was_active = active
        return active

    def summary(self) -> dict:
        return {
            "kind": self.kind,
            "initial_budget_s": self.initial_budget_s,
            "remaining_s": self.remaining_s,
            "active_s": self.active_s,
            "decisions": self.decisions,
            "activation_episodes": self.activation_episodes,
        }


class HealthFirstBudget(_BudgetedController):
    """Strong simple baseline: spend budget immediately whenever the primary path is down."""

    kind = "health_first"

    def wants_boost(self, view: BackupRepairView) -> bool:
        return not view.primary_available


class QueueAwareBudget(_BudgetedController):
    """Do not pay for a boosted path if the gateway has no still-live data to send."""

    kind = "queue_aware"

    def wants_boost(self, view: BackupRepairView) -> bool:
        return (not view.primary_available) and bool(view.live_demands)


class DeadlinePressureBudget(_BudgetedController):
    """EDF-style local feasibility gate for the *existing* gateway queue.

    For each distinct pending deadline, compare bytes that must be served by then with the payload
    capacity of ordinary backup opportunities from `now` through that deadline.  Boost only if the
    current queue cannot fit.  This is deliberately an ordinary deterministic-network baseline: it
    uses no task semantics beyond public per-record deadlines and no cross-stage inference.
    """

    kind = "deadline_pressure"

    @staticmethod
    def _opportunities(now_s: int, deadline_s: int, rate_s: int) -> int:
        if deadline_s < now_s or rate_s <= 0:
            return 0
        # Number of t in [now, deadline] with t % rate == 0.
        first = ((now_s + rate_s - 1) // rate_s) * rate_s
        if first > deadline_s:
            return 0
        return (deadline_s - first) // rate_s + 1

    def wants_boost(self, view: BackupRepairView) -> bool:
        if view.primary_available or not view.live_demands:
            return False
        ds = sorted(view.live_demands, key=lambda d: d.deadline_s)
        cumulative = 0
        for i, d in enumerate(ds):
            cumulative += max(0, int(d.payload_bytes))
            # Check only when the next item has a later deadline (or this is the last item).
            if i + 1 < len(ds) and ds[i + 1].deadline_s == d.deadline_s:
                continue
            cap = (self._opportunities(view.now_s, d.deadline_s, view.base_rate_s)
                   * max(0, int(view.base_payload_bytes)))
            if cumulative > cap:
                return True
        return False


class MinOnDeadlinePressureBudget(DeadlinePressureBudget):
    """Ordinary hold-down timer over :class:`DeadlinePressureBudget`.

    A boost episode, once triggered by the same legal EDF pressure predicate, remains active for at
    least `min_on_s`.  This models the standard engineering fact that repeatedly attaching,
    switching or waking an alternate backhaul is not free.  It adds no prediction and sees no new
    evidence; it is therefore a baseline, not a proposed method.
    """

    kind = "deadline_pressure_min_on"

    def __init__(self, budget_s: int, min_on_s: int = 600):
        super().__init__(budget_s)
        self.min_on_s = max(0, int(min_on_s))
        self._hold_ticks_left = 0

    def wants_boost(self, view: BackupRepairView) -> bool:
        pressure = super().wants_boost(view)
        if self._hold_ticks_left > 0:
            self._hold_ticks_left -= 1
            return True
        if pressure:
            n_ticks = max(1, (self.min_on_s + view.tick_s - 1) // view.tick_s)
            self._hold_ticks_left = n_ticks - 1
            return True
        return False

    def summary(self) -> dict:
        out = super().summary()
        out["min_on_s"] = self.min_on_s
        return out


class AccessHealthBudget(_BudgetedController):
    """Ordinary access-side baseline: spend assist budget whenever local link health is bad."""

    kind = "access_health"

    def wants_boost(self, view: AccessRepairView) -> bool:
        return not view.access_available
