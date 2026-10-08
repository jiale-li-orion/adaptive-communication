#!/usr/bin/env python3
"""Scale the ASC conditional-future-choice counterexample into a family.

The frozen Layer-2 v2 implementation assumes a globally fixed obligation set.
The Pull-Based ASC transfer exposes a strictly richer interface: a semantic
query can reveal *which future operational obligations become active*.  This
file therefore does not modify Layer-2 v2.  It provides an isolated exact
reference for observation-conditioned future obligations and measures the
representation/computation gap before integrating that semantic extension.

Family
------
There are K hidden worlds sharing the same initial history.  At t=0 the agent
has exactly D+1 query units.  QUERY_H costs one unit and reveals the world at
t=1.  In world w, D branch-specific hard query goals then arrive one per slot:

    QUERY_G{w}_0 at t=1, ..., QUERY_G{w}_{D-1} at t=D.

Hence QUERY_H followed by the observed branch has an exact causal completion
using D+1 units.  WAIT is too late to reveal H before the first goal.  Any
non-H query spends one unit and leaves insufficient budget for H + D branch
queries.

This gives three useful controls:

* static union reserve: unions all K*D possible future goals and falsely rejects
  QUERY_H when K>1;
* generic belief-space exact: correct but searches the full causal action
  frontier;
* conditional certificate: stores K branch-specific D-query continuations and
  proves QUERY_H without unioning mutually exclusive future obligations.

The construction is a controlled transfer stress family, not a reproduction
of the source paper's task distribution.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
from time import perf_counter
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
WAIT = "WAIT"
QUERY_H = "QUERY_H"
QUERY_A = "QUERY_A"  # high-current-value distractor; irrelevant to hard goals


@dataclass(frozen=True)
class Family:
    branches: int
    depth: int

    @property
    def budget(self) -> int:
        return self.depth + 1

    @property
    def last_deadline(self) -> int:
        return self.depth

    def goal_attr(self, world: int, step: int) -> str:
        return f"QUERY_G{world}_{step}"

    def actions(self, h_queried: bool) -> tuple[str, ...]:
        rows = [WAIT, QUERY_A]
        if not h_queried:
            rows.append(QUERY_H)
        rows.extend(
            self.goal_attr(world, step)
            for world in range(self.branches)
            for step in range(self.depth)
        )
        return tuple(rows)


@dataclass
class Metrics:
    expanded: int = 0
    recursive_calls: int = 0
    memo_hits: int = 0
    action_steps: int = 0
    observation_branches: int = 0
    wall_s: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


class ExactSolver:
    def __init__(self, family: Family):
        self.family = family
        self.metrics = Metrics()
        self.memo: dict[Any, dict[str, Any] | None] = {}

    def _expired(self, t: int, states: tuple[tuple[int, int], ...]) -> bool:
        # Each world's step j goal has release=deadline=1+j.
        for _world, mask in states:
            for step in range(self.family.depth):
                deadline = 1 + step
                if deadline < t and not (mask & (1 << step)):
                    return True
        return False

    def _success(self, t: int, states: tuple[tuple[int, int], ...]) -> bool:
        if t <= self.family.last_deadline:
            return False
        full = (1 << self.family.depth) - 1
        return all(mask == full for _world, mask in states)

    def _step_goal(
        self, t: int, action: str, states: tuple[tuple[int, int], ...]
    ) -> tuple[tuple[int, int], ...]:
        out = []
        for world, mask in states:
            new_mask = mask
            for step in range(self.family.depth):
                if action != self.family.goal_attr(world, step):
                    continue
                if t == 1 + step:
                    new_mask |= 1 << step
            out.append((world, new_mask))
        return tuple(out)

    def solve(
        self,
        *,
        t: int = 0,
        budget: int | None = None,
        states: tuple[tuple[int, int], ...] | None = None,
        h_queried: bool = False,
        pending_reveal: bool = False,
        forced_first_action: str | None = None,
    ) -> dict[str, Any]:
        if budget is None:
            budget = self.family.budget
        if states is None:
            states = tuple((world, 0) for world in range(self.family.branches))
        before = Metrics(**self.metrics.as_dict())
        started = perf_counter()

        def rec(
            now: int,
            left: int,
            support: tuple[tuple[int, int], ...],
            queried_h: bool,
            reveal: bool,
        ):
            self.metrics.recursive_calls += 1
            key = (now, left, support, queried_h, reveal)
            if key in self.memo:
                self.metrics.memo_hits += 1
                return self.memo[key]

            if reveal:
                children = []
                for world, mask in support:
                    self.metrics.observation_branches += 1
                    sub = rec(now, left, ((world, mask),), True, False)
                    if sub is None:
                        self.memo[key] = None
                        return None
                    children.append({
                        "observation": f"H={world}",
                        "world": world,
                        "subpolicy": sub,
                    })
                policy = {"time": now, "event": "OBSERVATION", "children": children}
                self.memo[key] = policy
                return policy

            if self._expired(now, support):
                self.memo[key] = None
                return None
            if self._success(now, support):
                policy = {"terminal": True}
                self.memo[key] = policy
                return policy
            if now > self.family.last_deadline:
                self.memo[key] = None
                return None

            self.metrics.expanded += 1
            available = self.family.actions(queried_h)
            for action in available:
                cost = int(action != WAIT)
                if cost > left:
                    continue
                self.metrics.action_steps += 1
                if action == QUERY_H:
                    sub = rec(now + 1, left - 1, support, True, True)
                else:
                    next_support = self._step_goal(now, action, support)
                    sub = rec(now + 1, left - cost, next_support, queried_h, False)
                if sub is None:
                    continue
                policy = {"time": now, "action": action, "subpolicy": sub}
                self.memo[key] = policy
                return policy
            self.memo[key] = None
            return None

        if forced_first_action is None:
            policy = rec(t, budget, states, h_queried, pending_reveal)
        else:
            action = forced_first_action
            if action not in self.family.actions(h_queried):
                policy = None
            else:
                cost = int(action != WAIT)
                if cost > budget:
                    policy = None
                elif action == QUERY_H:
                    sub = rec(t + 1, budget - 1, states, True, True)
                    policy = None if sub is None else {"time": t, "action": action, "subpolicy": sub}
                else:
                    stepped = self._step_goal(t, action, states)
                    sub = rec(t + 1, budget - cost, stepped, h_queried, False)
                    policy = None if sub is None else {"time": t, "action": action, "subpolicy": sub}

        self.metrics.wall_s += perf_counter() - started
        after = self.metrics.as_dict()
        delta = {k: after[k] - before.as_dict()[k] for k in after}
        return {
            "solvable": policy is not None,
            "policy": policy,
            "metrics": delta,
            "memo_entries": len(self.memo),
        }


def fresh_exact_action_frontier(family: Family) -> dict[str, Any]:
    rows = {}
    aggregate = Metrics()
    for action in family.actions(False):
        solver = ExactSolver(family)
        result = solver.solve(forced_first_action=action)
        rows[action] = bool(result["solvable"])
        for key, value in result["metrics"].items():
            setattr(aggregate, key, getattr(aggregate, key) + value)
    return {"actions": rows, "metrics": aggregate.as_dict()}


def persistent_exact_action_frontier(family: Family) -> dict[str, Any]:
    solver = ExactSolver(family)
    rows = {}
    before = solver.metrics.as_dict()
    started = perf_counter()
    for action in family.actions(False):
        rows[action] = bool(solver.solve(forced_first_action=action)["solvable"])
    elapsed = perf_counter() - started
    after = solver.metrics.as_dict()
    delta = {k: after[k] - before[k] for k in after}
    delta["frontier_wall_s"] = elapsed
    return {"actions": rows, "metrics": delta, "memo_entries": len(solver.memo)}


def conditional_certificate_frontier(family: Family) -> dict[str, Any]:
    """Sound root frontier from branch-conditional resource/timing certificates."""

    actions = {}
    reasons = {}
    checked_branch_steps = 0
    for action in family.actions(False):
        if family.branches == 1:
            # No aliasing exists. H is informationally unnecessary and the
            # D+1 budget leaves enough units for the D branch goals even after
            # any single t=0 query. WAIT also preserves all D+1 units.
            actions[action] = True
            reasons[action] = {
                "L": 1,
                "U": 1,
                "reason": "single-world no-aliasing control; D future goals remain schedulable",
            }
            continue
        if action == QUERY_H:
            # After QUERY_H each observation branch has exactly D budget units
            # and D one-slot goals.  Build one executable branch certificate.
            branches = {}
            for world in range(family.branches):
                policy = [family.goal_attr(world, step) for step in range(family.depth)]
                checked_branch_steps += len(policy)
                branches[f"H={world}"] = policy
            actions[action] = True
            reasons[action] = {
                "L": 1,
                "U": 1,
                "certificate": branches,
                "remaining_budget": family.depth,
                "worst_branch_query_requirement": family.depth,
            }
            continue

        if action == WAIT:
            # H queried at t>=1 can only reveal at t>=2, after the first
            # branch-specific t=1 deadline. This is a sound timing U=0 proof.
            actions[action] = False
            reasons[action] = {"L": 0, "U": 0, "reason": "reveal arrives after first branch deadline"}
            continue

        # Any other query at t=0 consumes one of D+1 units. A still-unqueried H
        # plus D branch goals require D+1 additional units, but only D remain.
        actions[action] = False
        reasons[action] = {"L": 0, "U": 0, "reason": "insufficient budget for H plus branch chain"}

    return {
        "actions": actions,
        "reasons": reasons,
        "metrics": {
            "branch_certificate_steps": checked_branch_steps,
            "root_actions_classified": len(actions),
            "exact_fallback_calls": 0,
        },
    }


def static_union_reserve(family: Family) -> dict[str, Any]:
    remaining = family.budget - 1
    union_requirement = family.branches * family.depth
    return {
        "query_h_declared_feasible": remaining >= union_requirement,
        "remaining_budget_after_h": remaining,
        "union_future_goal_count": union_requirement,
        "false_negative": family.branches > 1 and remaining < union_requirement,
    }


def run_grid() -> dict[str, Any]:
    cells = []
    for branches in (1, 2, 4, 8, 16):
        for depth in (1, 2, 3, 4):
            family = Family(branches=branches, depth=depth)
            fresh = fresh_exact_action_frontier(family)
            persistent = persistent_exact_action_frontier(family)
            conditional = conditional_certificate_frontier(family)
            union = static_union_reserve(family)
            assert fresh["actions"] == persistent["actions"] == conditional["actions"]
            assert fresh["actions"][QUERY_H] is True
            if branches == 1:
                assert all(bool(v) for v in fresh["actions"].values())
            else:
                assert sum(bool(v) for v in fresh["actions"].values()) == 1
            cells.append({
                "branches": branches,
                "depth": depth,
                "budget": family.budget,
                "root_action_count": len(fresh["actions"]),
                "static_union_reserve": union,
                "fresh_exact": fresh,
                "persistent_exact": persistent,
                "conditional_frontier": conditional,
                "compute": {
                    "fresh_expanded": fresh["metrics"]["expanded"],
                    "persistent_expanded": persistent["metrics"]["expanded"],
                    "conditional_certificate_steps": conditional["metrics"]["branch_certificate_steps"],
                    "conditional_over_fresh_expansion_proxy": (
                        conditional["metrics"]["branch_certificate_steps"] / fresh["metrics"]["expanded"]
                        if fresh["metrics"]["expanded"] else None
                    ),
                    "conditional_over_persistent_expansion_proxy": (
                        conditional["metrics"]["branch_certificate_steps"] / persistent["metrics"]["expanded"]
                        if persistent["metrics"]["expanded"] else None
                    ),
                },
            })

    nontrivial = [row for row in cells if row["branches"] > 1]
    payload = {
        "stage": "ASC_PULL_QUERY_OBSERVATION_CONDITIONED_OBLIGATION_FAMILY",
        "family_axes": {
            "branches": [1, 2, 4, 8, 16],
            "branch_goal_depth": [1, 2, 3, 4],
            "budget_rule": "D+1: one H query plus D branch-specific goal queries",
        },
        "cells": cells,
        "summary": {
            "cell_count": len(cells),
            "nontrivial_multibranch_cells": len(nontrivial),
            "static_union_false_negative_cells": sum(row["static_union_reserve"]["false_negative"] for row in cells),
            "conditional_exact_frontier_match_cells": len(cells),
            "mean_fresh_expanded": sum(row["compute"]["fresh_expanded"] for row in cells) / len(cells),
            "mean_persistent_expanded": sum(row["compute"]["persistent_expanded"] for row in cells) / len(cells),
            "mean_conditional_certificate_steps": sum(row["compute"]["conditional_certificate_steps"] for row in cells) / len(cells),
            "max_fresh_expanded": max(row["compute"]["fresh_expanded"] for row in cells),
            "max_persistent_expanded": max(row["compute"]["persistent_expanded"] for row in cells),
            "max_conditional_certificate_steps": max(row["compute"]["conditional_certificate_steps"] for row in cells),
        },
        "claim_boundary": [
            "This is a controlled transfer stress family, not the source Pull-Based paper's empirical task distribution.",
            "It validates observation-conditioned future-obligation semantics and static-union failure before extending the frozen Layer-2 v2 implementation.",
            "Branch-certificate steps and exact state expansions are different operation types; their ratio is a search-work proxy, not a wall-time theorem.",
            "The current conditional certificate is specialized to unit query goals. Full Layer-2 novelty still requires shared-resource/delayed-feedback structure beyond this family."
        ],
    }
    return payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "results/transfer/asc-pull-query-conditional-family.json")
    args = ap.parse_args()
    payload = run_grid()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(args.out), **payload["summary"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
