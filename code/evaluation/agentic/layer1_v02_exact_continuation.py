#!/usr/bin/env python3
"""Evaluation-only exact continuation helper for Layer-1 v0.2 prefixes.

This module does not redefine the benchmark oracle.  It reuses the frozen
Layer-1 transition/observation primitives and solves the same non-anticipative
AND/OR feasibility problem from an already-reached legal prefix.  It exists so
cross-layer Layer-2 audits can ask counterfactual questions such as "if v1
queries now, does any causal continuation remain?" without modifying Layer-1.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping

from causal_evidence_process_v0_1 import attach_causal_evidence
from exact_reference_oracle_v0_1 import LocalState, _expired, _normalize, _success
from v8_policy_baselines_v0_1 import _legal_actions, _step


class ContinuationExpansionLimit(RuntimeError):
    pass


@dataclass(frozen=True)
class ContinuationWitness:
    policy: dict[str, Any]


class ExactContinuationReference:
    """Exact same-information continuation feasibility from a reached prefix."""

    def __init__(self, bundle: Mapping[str, Any]):
        self.bundle = deepcopy(bundle)
        self.process = attach_causal_evidence(self.bundle)

    @staticmethod
    def _canon(states: Mapping[str, LocalState]) -> tuple[tuple[str, LocalState], ...]:
        return tuple(sorted(states.items()))

    def solve(
        self,
        at_s: int,
        states: Mapping[str, LocalState],
        *,
        query_budget: int,
        max_expansions: int = 200_000,
    ) -> dict[str, Any]:
        memo: dict[Any, ContinuationWitness | None] = {}
        expanded = 0

        def rec(t: int, support: dict[str, LocalState], qleft: int) -> ContinuationWitness | None:
            nonlocal expanded
            branches = _normalize(self.bundle, self.process, t, support)
            if len(branches) != 1 or next(iter(branches)) != "same":
                children = []
                for observation, child in sorted(branches.items()):
                    witness = rec(t, child, qleft)
                    if witness is None:
                        return None
                    children.append(
                        {
                            "observation": observation,
                            "worlds": sorted(child),
                            "subpolicy": witness.policy,
                        }
                    )
                return ContinuationWitness(
                    {"time_s": t, "event": "OBSERVATION", "children": children}
                )

            support = next(iter(branches.values()))
            key = (t, qleft, self._canon(support))
            if key in memo:
                return memo[key]
            if any(_expired(self.bundle, st, t) for st in support.values()):
                memo[key] = None
                return None
            if all(_success(self.bundle, st) for st in support.values()):
                witness = ContinuationWitness({"terminal": True})
                memo[key] = witness
                return witness
            if expanded >= max_expansions:
                raise ContinuationExpansionLimit(max_expansions)
            expanded += 1

            for action in _legal_actions(self.bundle, self.process, support, t):
                dq = int(action[0] == "ISSUE_QUERY")
                if dq > qleft:
                    continue
                stepped = _step(self.bundle, self.process, support, t, action)
                if stepped is None:
                    continue
                child, next_t = stepped
                continuation = rec(next_t, child, qleft - dq)
                if continuation is None:
                    continue
                witness = ContinuationWitness(
                    {
                        "time_s": t,
                        "action": action[0],
                        "arg": action[1],
                        "worlds": sorted(support),
                        "subpolicy": continuation.policy,
                    }
                )
                memo[key] = witness
                return witness

            memo[key] = None
            return None

        try:
            witness = rec(at_s, dict(states), query_budget)
            return {
                "status": "EXACT",
                "solvable": witness is not None,
                "policy": None if witness is None else deepcopy(witness.policy),
                "expanded": expanded,
                "memo_entries": len(memo),
            }
        except ContinuationExpansionLimit:
            return {
                "status": "SEARCH_LIMIT",
                "solvable": None,
                "policy": None,
                "expanded": expanded,
                "memo_entries": len(memo),
            }


def replay_continuation_policy(
    bundle: Mapping[str, Any],
    *,
    at_s: int,
    states: Mapping[str, LocalState],
    policy: Mapping[str, Any],
    query_budget: int,
) -> None:
    """Replay every observation branch against the frozen Layer-1 kernel."""

    process = attach_causal_evidence(bundle)

    def visit(t: int, support: dict[str, LocalState], node: Mapping[str, Any], qleft: int) -> None:
        branches = _normalize(bundle, process, t, support)
        if len(branches) != 1 or next(iter(branches)) != "same":
            assert node.get("event") == "OBSERVATION"
            assert int(node["time_s"]) == t
            children = {str(row["observation"]): row for row in node["children"]}
            assert set(children) == set(branches)
            for obs, child in branches.items():
                entry = children[obs]
                assert entry["worlds"] == sorted(child)
                visit(t, child, entry["subpolicy"], qleft)
            return

        support = next(iter(branches.values()))
        assert not any(_expired(bundle, st, t) for st in support.values())
        if node.get("terminal"):
            assert all(_success(bundle, st) for st in support.values())
            return

        action = (str(node["action"]), node.get("arg"))
        assert int(node["time_s"]) == t
        assert node["worlds"] == sorted(support)
        assert action in _legal_actions(bundle, process, support, t)
        dq = int(action[0] == "ISSUE_QUERY")
        assert dq <= qleft
        stepped = _step(bundle, process, support, t, action)
        assert stepped is not None
        child, next_t = stepped
        visit(next_t, child, node["subpolicy"], qleft - dq)

    visit(at_s, dict(states), policy, query_budget)
