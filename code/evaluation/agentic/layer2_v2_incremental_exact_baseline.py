#!/usr/bin/env python3
"""Strong ordinary incremental AND/OR baseline for Layer-2 v2.

This baseline deliberately receives the same action ordering, persistent memo,
early stopping and exact transition semantics as the v2 planning kernel, but it
has no L/U structural bounds and no conditional certificate domains.  It is the
reviewer control required by cache06.md to separate future-choice structure
from ordinary incremental search engineering.
"""
from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any, Mapping

from causal_evidence_process_v0_1 import attach_causal_evidence
from exact_reference_oracle_v0_1 import LocalState, _expired, _normalize, _success
from v8_policy_baselines_v0_1 import _legal_actions, _step


Action = tuple[str, str | None]


@dataclass
class IncrementalExactMetrics:
    expanded: int = 0
    recursive_calls: int = 0
    memo_hits: int = 0
    action_steps: int = 0
    wall_s: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


class PersistentOrderedExact:
    """Persistent exact search with v2's deterministic action order, no L/U."""

    def __init__(self, bundle: Mapping[str, Any]):
        self.bundle = bundle
        self.process = attach_causal_evidence(bundle)
        self.memo: dict[Any, dict[str, Any] | None] = {}
        self.metrics = IncrementalExactMetrics()
        self.deadlines = {
            str(row["obligation_id"]): int(row["deadline_s"])
            for row in bundle["obligations"]
        }

    @staticmethod
    def _canon(states: Mapping[str, LocalState]):
        return tuple(sorted(states.items()))

    def _rank(self, at_s: int, actions: list[Action]) -> list[Action]:
        preference = {"SEND_TERR": 0, "SEND_SAT": 1, "WAIT": 2, "ISSUE_QUERY": 3}

        def key(action: Action):
            oid = str(action[1]) if action[1] is not None else ""
            slack = self.deadlines.get(oid, 10**18) - at_s
            return (preference.get(action[0], 9), slack, repr(action))

        return sorted(actions, key=key)

    def solve(
        self,
        at_s: int,
        states: Mapping[str, LocalState],
        *,
        query_budget: int,
        max_expansions: int = 200_000,
    ) -> dict[str, Any]:
        before = IncrementalExactMetrics(**self.metrics.as_dict())
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
            key = (t, qleft, self._canon(support))
            if key in self.memo:
                self.metrics.memo_hits += 1
                return self.memo[key]
            if any(_expired(self.bundle, state, t) for state in support.values()):
                self.memo[key] = None
                return None
            if all(_success(self.bundle, state) for state in support.values()):
                policy = {"terminal": True}
                self.memo[key] = policy
                return policy
            if self.metrics.expanded - before.expanded >= max_expansions:
                raise RuntimeError(f"incremental exact expansion limit {max_expansions}")
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
                self.memo[key] = policy
                return policy

            self.memo[key] = None
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
        elapsed = perf_counter() - started
        self.metrics.wall_s += elapsed
        after = self.metrics.as_dict()
        delta = {key: after[key] - before.as_dict()[key] for key in after}
        return {
            "status": status,
            "solvable": solvable,
            "policy": policy,
            "metrics": delta,
            "memo_entries": len(self.memo),
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
