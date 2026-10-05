#!/usr/bin/env python3
"""Dependency-separator projection for causal continuation states.

The v0.1 separator removes only history that the declared future transition
kernel cannot read again.  It is intentionally conservative: current/future
resource usage, delivered obligations, pending operations and query-history
state remain explicit.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping

from exact_reference_oracle_v0_1 import LocalState


def _future_terrestrial_ids(bundle: Mapping[str, Any], wid: str, at_s: int) -> set[str]:
    world = next(w for w in bundle['worlds'] if str(w['world_id']) == wid)
    return {
        str(w['window_id'])
        for w in world['terrestrial_windows']
        if int(w['end_s']) > at_s
    }


class DependencySeparator:
    """Cached separator projector for one immutable bundle/process session."""

    def __init__(self, bundle: Mapping[str, Any], process: Mapping[str, Any]):
        self.bundle = bundle
        self.process = process
        self._worlds = {str(w['world_id']): w for w in bundle['worlds']}
        self._terr_keep_cache: dict[tuple[str, int], frozenset[str]] = {}
        self._sat_keep_cache: dict[int, frozenset[str]] = {}
        self.passive = bool(process.get('passive_observation_rules'))
        self.direct = bool(process.get('direct_observation'))

    def _terr_keep(self, wid: str, at_s: int) -> frozenset[str]:
        key = (wid, int(at_s))
        hit = self._terr_keep_cache.get(key)
        if hit is not None:
            return hit
        hit = frozenset(
            str(w['window_id'])
            for w in self._worlds[wid]['terrestrial_windows']
            if int(w['end_s']) > at_s
        )
        self._terr_keep_cache[key] = hit
        return hit

    def _sat_keep(self, at_s: int) -> frozenset[str]:
        at_s = int(at_s)
        hit = self._sat_keep_cache.get(at_s)
        if hit is not None:
            return hit
        hit = frozenset(
            str(w['window_id'])
            for w in self.bundle['public_environment']['satellite_windows']
            if int(w['end_s']) > at_s
        )
        self._sat_keep_cache[at_s] = hit
        return hit

    def state(self, wid: str, at_s: int, state: LocalState) -> LocalState:
        pending = tuple(state.pending_deliveries)
        if not self.passive:
            pending = tuple(replace(d, gateway_receipt_seen=False) for d in pending)
        return LocalState(
            delivered=state.delivered,
            terrestrial_used=_filtered_usage(state.terrestrial_used, set(self._terr_keep(wid, at_s))),
            satellite_used=_filtered_usage(state.satellite_used, set(self._sat_keep(at_s))),
            satellite_budget=0,
            pending_query=state.pending_query,
            last_query_signature=state.last_query_signature,
            last_direct_signature=state.last_direct_signature if self.direct else None,
            pending_deliveries=pending,
        )

    def key(self, at_s: int, states: Mapping[str, LocalState]) -> tuple[Any, ...]:
        return (
            int(at_s),
            tuple(sorted((str(wid), self.state(str(wid), at_s, st)) for wid, st in states.items())),
        )


def _future_satellite_ids(bundle: Mapping[str, Any], at_s: int) -> set[str]:
    return {
        str(w['window_id'])
        for w in bundle['public_environment']['satellite_windows']
        if int(w['end_s']) > at_s
    }


def _filtered_usage(rows, keep: set[str]):
    return tuple(sorted((str(k), int(v)) for k, v in rows if str(k) in keep))


def _canonical_pending(process: Mapping[str, Any], pending):
    passive = bool(process.get('passive_observation_rules'))
    if passive:
        return tuple(pending)
    # In a process with no passive ACK/receipt surface, receipt_seen is never
    # consulted by future decision semantics after normalization.  Keep every
    # timing/acceptance field and erase only that dead bookkeeping bit.
    return tuple(replace(d, gateway_receipt_seen=False) for d in pending)


def separator_state(
    bundle: Mapping[str, Any],
    process: Mapping[str, Any],
    *,
    wid: str,
    at_s: int,
    state: LocalState,
    normalize_satellite_budget: bool = True,
) -> LocalState:
    """Project one normalized LocalState onto future-readable dependencies."""
    terr_keep = _future_terrestrial_ids(bundle, wid, at_s)
    sat_keep = _future_satellite_ids(bundle, at_s)
    direct = bool(process.get('direct_observation'))
    return LocalState(
        delivered=state.delivered,
        terrestrial_used=_filtered_usage(state.terrestrial_used, terr_keep),
        satellite_used=_filtered_usage(state.satellite_used, sat_keep),
        satellite_budget=0 if normalize_satellite_budget else state.satellite_budget,
        pending_query=state.pending_query,
        last_query_signature=state.last_query_signature,
        last_direct_signature=state.last_direct_signature if direct else None,
        pending_deliveries=_canonical_pending(process, state.pending_deliveries),
    )


def dependency_separator_key(
    bundle: Mapping[str, Any],
    process: Mapping[str, Any],
    at_s: int,
    states: Mapping[str, LocalState],
) -> tuple[Any, ...]:
    """A conservative interface state for future continuation semantics.

    Time and compatible world support remain explicit.  Satellite budget is a
    separate monotone resource coordinate in the continuation-domain planner.
    """
    return (
        int(at_s),
        tuple(
            sorted(
                (
                    str(wid),
                    separator_state(
                        bundle, process, wid=str(wid), at_s=at_s, state=st,
                        normalize_satellite_budget=True,
                    ),
                )
                for wid, st in states.items()
            )
        ),
    )


def separator_explanation() -> dict[str, Any]:
    return {
        'retained': [
            'time', 'compatible world support', 'delivered obligations',
            'current/future terrestrial capacity use',
            'current/future satellite-window capacity use',
            'pending query', 'last query signature', 'pending deliveries',
        ],
        'resource_coordinate': 'remaining satellite budget is excluded from z and kept as an explicit monotone resource coordinate',
        'removed_v0_1': [
            'usage entries belonging only to windows whose end <= current time',
            'last_direct_signature when direct-current-state observation is disabled',
            'gateway_receipt_seen bookkeeping when the process exposes no passive receipt/ACK surface',
        ],
        'not_removed': [
            'last_query_signature',
            'pending operation timing or acceptance',
            'future opportunity identity/capacity',
            'world support',
        ],
    }
