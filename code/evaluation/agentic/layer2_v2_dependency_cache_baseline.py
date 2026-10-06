#!/usr/bin/env python3
"""Ordinary dependency/cache exact baseline for Layer-2 v2.

This is the strong structural control required by ``cache06.md``.  It performs
only transition-kernel-dead history projection plus persistent exact memoization.
It does **not** maintain conditional future-choice frontiers, Hall conflicts,
certificate validity domains, or event-local component invalidation.

The projection is intentionally conservative and follows the frozen historical
dependency-separator result: only state that no future transition can read is
removed from the memo key.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from time import perf_counter
from typing import Any, Mapping

from causal_evidence_process_v0_1 import attach_causal_evidence
from exact_reference_oracle_v0_1 import LocalState, _expired, _normalize, _success
from layer1_v02_exact_continuation import replay_continuation_policy
from v8_policy_baselines_v0_1 import _legal_actions, _step


Action = tuple[str, str | None]


def _future_terr_ids(bundle: Mapping[str, Any], world_id: str, at_s: int) -> set[str]:
    world = next(row for row in bundle["worlds"] if str(row["world_id"]) == world_id)
    return {
        str(window["window_id"])
        for window in world["terrestrial_windows"]
        if int(window["end_s"]) > at_s
    }


def _future_sat_ids(bundle: Mapping[str, Any], at_s: int) -> set[str]:
    return {
        str(window["window_id"])
        for window in bundle["public_environment"]["satellite_windows"]
        if int(window["end_s"]) > at_s
    }


def _filtered_usage(rows, keep: set[str]):
    return tuple(sorted((str(key), int(value)) for key, value in rows if str(key) in keep))


class DependencyProjector:
    def __init__(self, bundle: Mapping[str, Any], process: Mapping[str, Any]):
        self.bundle = bundle
        self.process = process
        self.passive = bool(process.get("passive_observation_rules"))
        self.direct = bool(process.get("direct_observation"))
        self._terr_cache: dict[tuple[str, int], frozenset[str]] = {}
        self._sat_cache: dict[int, frozenset[str]] = {}

    def _terr_keep(self, world_id: str, at_s: int) -> frozenset[str]:
        key = (world_id, int(at_s))
        if key not in self._terr_cache:
            self._terr_cache[key] = frozenset(_future_terr_ids(self.bundle, world_id, at_s))
        return self._terr_cache[key]

    def _sat_keep(self, at_s: int) -> frozenset[str]:
        at_s = int(at_s)
        if at_s not in self._sat_cache:
            self._sat_cache[at_s] = frozenset(_future_sat_ids(self.bundle, at_s))
        return self._sat_cache[at_s]

    def state(self, world_id: str, at_s: int, state: LocalState) -> LocalState:
        pending = tuple(state.pending_deliveries)
        if not self.passive:
            pending = tuple(replace(row, gateway_receipt_seen=False) for row in pending)
        return LocalState(
            delivered=state.delivered,
            terrestrial_used=_filtered_usage(state.terrestrial_used, set(self._terr_keep(world_id, at_s))),
            satellite_used=_filtered_usage(state.satellite_used, set(self._sat_keep(at_s))),
            satellite_budget=state.satellite_budget,
            pending_query=state.pending_query,
            last_query_signature=state.last_query_signature,
            last_direct_signature=state.last_direct_signature if self.direct else None,
            pending_deliveries=pending,
        )

    def key(self, at_s: int, states: Mapping[str, LocalState]) -> tuple[Any, ...]:
        return (
            int(at_s),
            tuple(
                sorted(
                    (str(world_id), self.state(str(world_id), at_s, state))
                    for world_id, state in states.items()
                )
            ),
        )


@dataclass
class Metrics:
    expanded: int = 0
    recursive_calls: int = 0
    memo_hits: int = 0
    separator_hits: int = 0
    separator_replay_success: int = 0
    separator_replay_fail: int = 0
    action_steps: int = 0
    wall_s: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


class PersistentDependencyExact:
    """Exact persistent AND/OR search with dead-history dependency projection."""

    def __init__(self, bundle: Mapping[str, Any]):
        self.bundle = bundle
        self.process = attach_causal_evidence(bundle)
        self.projector = DependencyProjector(bundle, self.process)
        self.memo: dict[Any, list[tuple[Any, dict[str, Any] | None]]] = {}
        self.metrics = Metrics()
        self.deadlines = {
            str(row["obligation_id"]): int(row["deadline_s"])
            for row in bundle["obligations"]
        }

    def _rank(self, at_s: int, actions: list[Action]) -> list[Action]:
        preference = {"SEND_TERR": 0, "SEND_SAT": 1, "WAIT": 2, "ISSUE_QUERY": 3}

        def key(action: Action):
            oid = str(action[1]) if action[1] is not None else ""
            return (
                preference.get(action[0], 9),
                self.deadlines.get(oid, 10**18) - at_s,
                repr(action),
            )

        return sorted(actions, key=key)

    def solve(
        self,
        at_s: int,
        states: Mapping[str, LocalState],
        *,
        query_budget: int,
        max_expansions: int = 200_000,
    ) -> dict[str, Any]:
        before = Metrics(**self.metrics.as_dict())
        started = perf_counter()

        def rec(t: int, support: Mapping[str, LocalState], qleft: int):
            self.metrics.recursive_calls += 1
            branches = _normalize(self.bundle, self.process, t, support)
            if len(branches) != 1 or next(iter(branches)) != "same":
                children = []
                for observation, child in sorted(branches.items()):
                    sub = rec(t, child, qleft)
                    if sub is None:
                        return None
                    children.append(
                        {"observation": observation, "worlds": sorted(child), "subpolicy": sub}
                    )
                return {"time_s": t, "event": "OBSERVATION", "children": children}

            support = next(iter(branches.values()))
            key = (qleft, self.projector.key(t, support))
            full_key = (t, qleft, tuple(sorted(support.items())))
            entries = self.memo.get(key, ())
            for stored_full_key, stored_policy in entries:
                if stored_full_key == full_key:
                    self.metrics.memo_hits += 1
                    return stored_policy
                if stored_policy is None:
                    # Projected failure reuse is deliberately forbidden.
                    continue
                self.metrics.separator_hits += 1
                try:
                    replay_continuation_policy(
                        self.bundle,
                        at_s=t,
                        states=support,
                        policy=stored_policy,
                        query_budget=qleft,
                    )
                except (AssertionError, ValueError, KeyError):
                    self.metrics.separator_replay_fail += 1
                    continue
                self.metrics.separator_replay_success += 1
                return stored_policy
            if any(_expired(self.bundle, state, t) for state in support.values()):
                self.memo.setdefault(key, []).append((full_key, None))
                return None
            if all(_success(self.bundle, state) for state in support.values()):
                policy = {"terminal": True}
                self.memo.setdefault(key, []).append((full_key, policy))
                return policy
            if self.metrics.expanded - before.expanded >= max_expansions:
                raise RuntimeError(f"dependency exact expansion limit {max_expansions}")
            self.metrics.expanded += 1
            for action in self._rank(
                t,
                _legal_actions(self.bundle, self.process, support, t),
            ):
                dq = int(action[0] == "ISSUE_QUERY")
                if dq > qleft:
                    continue
                stepped = _step(self.bundle, self.process, support, t, action)
                if stepped is None:
                    continue
                self.metrics.action_steps += 1
                child, next_t = stepped
                sub = rec(next_t, child, qleft - dq)
                if sub is None:
                    continue
                policy = {
                    "time_s": t,
                    "action": action[0],
                    "arg": action[1],
                    "worlds": sorted(support),
                    "subpolicy": sub,
                }
                self.memo.setdefault(key, []).append((full_key, policy))
                return policy
            self.memo.setdefault(key, []).append((full_key, None))
            return None

        try:
            policy = rec(at_s, dict(states), query_budget)
            status = "EXACT"
            solvable = policy is not None
        except RuntimeError as exc:
            if "expansion limit" not in str(exc):
                raise
            policy = None
            status = "SEARCH_LIMIT"
            solvable = None
        self.metrics.wall_s += perf_counter() - started
        after = self.metrics.as_dict()
        return {
            "status": status,
            "solvable": solvable,
            "policy": policy,
            "metrics": {key: after[key] - before.as_dict()[key] for key in after},
            "memo_entries": sum(len(rows) for rows in self.memo.values()),
        }

    def build_frontier(
        self,
        *,
        at_s: int,
        states: Mapping[str, LocalState],
        query_budget: int,
    ) -> dict[str, Any]:
        branches = _normalize(self.bundle, self.process, at_s, states)
        if len(branches) != 1 or next(iter(branches)) != "same":
            raise ValueError("frontier requires normalized decision boundary")
        support = next(iter(branches.values()))
        before = self.metrics.as_dict()
        started = perf_counter()
        actions: dict[str, bool | None] = {}
        for action in _legal_actions(self.bundle, self.process, support, at_s):
            dq = int(action[0] == "ISSUE_QUERY")
            key = f"{action[0]}:{action[1] if action[1] is not None else '-'}"
            if dq > query_budget:
                actions[key] = False
                continue
            stepped = _step(self.bundle, self.process, support, at_s, action)
            if stepped is None:
                actions[key] = False
                continue
            child, next_t = stepped
            result = self.solve(next_t, child, query_budget=query_budget - dq)
            actions[key] = result["solvable"]
        elapsed = perf_counter() - started
        after = self.metrics.as_dict()
        return {
            "actions": actions,
            "wall_s": elapsed,
            "metrics": {key: after[key] - before[key] for key in after},
        }
