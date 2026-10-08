#!/usr/bin/env python3
"""Paper-structured finite-horizon replay for Pull-Based Query Scheduling.

This is deliberately *not* a numerical reproduction of Agheli et al.  It uses
the source paper's core decision structure:

* state contains per-attribute AoI / usefulness;
* at most one sensing attribute is queried per slot (or no query);
* a successful query refreshes that attribute while unrefreshed AoI grows;
* query actions consume a communication/query budget;
* semantic reward is a monotone freshness/usefulness GoE composition.

To test transfer, we add an explicit finite set of hard operational query goals
with release/deadline windows.  Those goals are *not* claimed to be part of the
source paper.  The question is whether the existing scalar-GoE scheduler can be
wrapped by the same future-choice feasibility layer used in this repository.

Three policies are compared on the identical replay:

1. value-only dynamic programming (source-style objective, no hard goals),
2. generic hard-goal exact DP that discovers infeasible branches only when they
   expire or exhaust the finite query budget,
3. the same exact DP plus an action-level future-choice certificate that prunes
   an action iff the remaining unit query goals no longer admit a release/deadline
   matching under the remaining slots and budget.

The shield is required to preserve the exact constrained optimum.  Its search
reduction is only a transfer/correctness result; an ordinary scheduling-aware
constrained DP is a strong baseline and can implement the same unit-demand
certificate, so this file does not claim Layer-2 novelty by itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
from math import inf
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[3]
ATTRS = ("A", "B", "C")
WAIT = "WAIT"
HORIZON = 5
MAX_AOI = 8
INITIAL_AOI = (1, 1, 1)
USEFULNESS = (6.0, 2.0, 1.0)
QUERY_BUDGET = 2


@dataclass(frozen=True)
class Goal:
    attribute: str
    release: int
    deadline: int


@dataclass
class Stats:
    states: int = 0
    action_evaluations: int = 0
    feasibility_checks: int = 0
    actions_pruned_by_future_choice: int = 0


def goe(ages: tuple[int, ...]) -> float:
    """Valid monotone GoE subclass: usefulness weighted inverse freshness."""

    return sum(u / float(age) for u, age in zip(USEFULNESS, ages))


def transition(
    ages: tuple[int, ...], budget: int, action: str
) -> tuple[tuple[int, ...], int] | None:
    if action != WAIT and budget <= 0:
        return None
    nxt = [min(MAX_AOI, x + 1) for x in ages]
    nb = budget
    if action != WAIT:
        idx = ATTRS.index(action)
        # Deterministic-success subcase of the paper's query/update dynamics.
        nxt[idx] = 1
        nb -= 1
    return tuple(nxt), nb


def actions(budget: int) -> tuple[str, ...]:
    return (WAIT,) if budget <= 0 else (WAIT, *ATTRS)


def value_only_dp() -> dict:
    stats = Stats()

    @lru_cache(maxsize=None)
    def rec(t: int, ages: tuple[int, ...], budget: int):
        stats.states += 1
        if t >= HORIZON:
            return 0.0, ()
        best = (-inf, ())
        for action in actions(budget):
            stats.action_evaluations += 1
            stepped = transition(ages, budget, action)
            if stepped is None:
                continue
            na, nb = stepped
            future, policy = rec(t + 1, na, nb)
            candidate = (goe(na) + future, (action, *policy))
            if candidate[0] > best[0] + 1e-12 or (
                abs(candidate[0] - best[0]) <= 1e-12
                and candidate[1] < best[1]
            ):
                best = candidate
        return best

    value, policy = rec(0, INITIAL_AOI, QUERY_BUDGET)
    return {"value": value, "policy": list(policy), "stats": stats.__dict__}


def _apply_goal_action(
    t: int,
    action: str,
    goals: tuple[Goal, ...],
    satisfied_mask: int,
) -> int:
    if action == WAIT:
        return satisfied_mask
    candidates = [
        i for i, goal in enumerate(goals)
        if not (satisfied_mask & (1 << i))
        and goal.attribute == action
        and goal.release <= t <= goal.deadline
    ]
    if not candidates:
        return satisfied_mask
    # One query can discharge one unit goal; earliest deadline first is exact.
    i = min(candidates, key=lambda j: (goals[j].deadline, goals[j].release, j))
    return satisfied_mask | (1 << i)


def _expired(t: int, goals: tuple[Goal, ...], mask: int) -> bool:
    return any(
        not (mask & (1 << i)) and goal.deadline < t
        for i, goal in enumerate(goals)
    )


def _remaining_goals(goals: tuple[Goal, ...], mask: int) -> list[Goal]:
    return [goal for i, goal in enumerate(goals) if not (mask & (1 << i))]


def future_choice_feasible(
    *,
    next_t: int,
    remaining_budget: int,
    goals: tuple[Goal, ...],
    satisfied_mask: int,
) -> bool:
    """Exact unit-demand release/deadline feasibility certificate.

    Each remaining goal requires one future query slot.  Attribute identity does
    not consume a shared per-attribute resource, so the exact feasibility test
    is earliest-deadline matching of released unit jobs to slots, plus budget.
    """

    pending = _remaining_goals(goals, satisfied_mask)
    if len(pending) > remaining_budget:
        return False
    if any(goal.deadline < next_t for goal in pending):
        return False
    available = list(range(next_t, HORIZON))
    if len(available) < len(pending):
        return False
    for goal in sorted(pending, key=lambda g: (g.deadline, g.release, g.attribute)):
        slot = next(
            (s for s in available if goal.release <= s <= goal.deadline),
            None,
        )
        if slot is None:
            return False
        available.remove(slot)
    return True


def constrained_dp(goals: Iterable[Goal], *, shield: bool) -> dict:
    goals = tuple(goals)
    all_satisfied = (1 << len(goals)) - 1
    stats = Stats()

    @lru_cache(maxsize=None)
    def rec(t: int, ages: tuple[int, ...], budget: int, mask: int):
        stats.states += 1
        if _expired(t, goals, mask):
            return -inf, ()
        if t >= HORIZON:
            return (0.0, ()) if mask == all_satisfied else (-inf, ())

        best = (-inf, ())
        for action in actions(budget):
            stats.action_evaluations += 1
            stepped = transition(ages, budget, action)
            if stepped is None:
                continue
            na, nb = stepped
            nm = _apply_goal_action(t, action, goals, mask)
            if shield:
                stats.feasibility_checks += 1
                if not future_choice_feasible(
                    next_t=t + 1,
                    remaining_budget=nb,
                    goals=goals,
                    satisfied_mask=nm,
                ):
                    stats.actions_pruned_by_future_choice += 1
                    continue
            future, policy = rec(t + 1, na, nb, nm)
            if future == -inf:
                continue
            candidate = (goe(na) + future, (action, *policy))
            if candidate[0] > best[0] + 1e-12 or (
                abs(candidate[0] - best[0]) <= 1e-12
                and candidate[1] < best[1]
            ):
                best = candidate
        return best

    value, policy = rec(0, INITIAL_AOI, QUERY_BUDGET, 0)
    return {
        "value": None if value == -inf else value,
        "policy": list(policy),
        "solvable": value != -inf,
        "stats": stats.__dict__,
    }


def hard_feasible_policy(policy: list[str], goals: tuple[Goal, ...]) -> bool:
    mask = 0
    budget = QUERY_BUDGET
    ages = INITIAL_AOI
    for t, action in enumerate(policy[:HORIZON]):
        stepped = transition(ages, budget, action)
        if stepped is None:
            return False
        ages, budget = stepped
        mask = _apply_goal_action(t, action, goals, mask)
        if _expired(t + 1, goals, mask):
            return False
    return mask == (1 << len(goals)) - 1


def run() -> dict:
    # Control case: the unchanged value-only DP naturally refreshes A at t=1,
    # so this future hard goal is compatible with its preferred semantic-value
    # schedule.  The tight case keeps the same current AoI/usefulness/budget but
    # changes only the future operational-goal geometry.
    relaxed = (Goal("A", 1, 2),)
    tight = (Goal("B", 1, 1), Goal("C", 2, 2))
    value_only = value_only_dp()

    rows = {}
    for name, goals in (("relaxed", relaxed), ("tight", tight)):
        exact = constrained_dp(goals, shield=False)
        shielded = constrained_dp(goals, shield=True)
        rows[name] = {
            "goals": [g.__dict__ for g in goals],
            "value_only_policy": value_only["policy"],
            "value_only_hard_feasible": hard_feasible_policy(value_only["policy"], goals),
            "generic_constrained_exact": exact,
            "future_choice_shielded_exact": shielded,
            "same_constrained_optimum": (
                exact["solvable"] == shielded["solvable"]
                and exact["policy"] == shielded["policy"]
                and (
                    exact["value"] is None
                    or abs(float(exact["value"]) - float(shielded["value"])) <= 1e-9
                )
            ),
        }

    tight_exact = rows["tight"]["generic_constrained_exact"]
    tight_shield = rows["tight"]["future_choice_shielded_exact"]
    payload = {
        "stage": "ASC_PULL_QUERY_PAPER_STRUCTURED_REPLAY",
        "reference": {
            "title": "Pull-Based Query Scheduling for Goal-Oriented Semantic Communication",
            "arxiv": "2503.06725",
            "preserved_structure": [
                "per-attribute AoI state",
                "query-one-attribute-or-wait action",
                "query refresh / unqueried age growth",
                "finite query-cost constraint",
                "monotone freshness/usefulness GoE objective",
            ],
            "simplifications": [
                "deterministic successful query subcase",
                "finite horizon instead of infinite discounted horizon",
                "inverse-AoI weighted usefulness GoE subclass instead of reproducing CPT numerical parameters",
            ],
            "transfer_extension": "release/deadline hard operational query goals",
            "numerical_reproduction_claim": False,
        },
        "model": {
            "attributes": list(ATTRS),
            "horizon": HORIZON,
            "initial_aoi": list(INITIAL_AOI),
            "usefulness": list(USEFULNESS),
            "query_budget": QUERY_BUDGET,
            "goe": "sum_m usefulness_m / AoI_m",
        },
        "value_only": value_only,
        "rows": rows,
        "checks": {
            "value_only_safe_when_future_relaxed": rows["relaxed"]["value_only_hard_feasible"],
            "value_only_breaks_tight_future_goals": not rows["tight"]["value_only_hard_feasible"],
            "generic_constrained_exact_solves_tight": tight_exact["solvable"],
            "shield_preserves_exact_tight_optimum": rows["tight"]["same_constrained_optimum"],
            "shield_prunes_doomed_tight_actions": (
                tight_shield["stats"]["actions_pruned_by_future_choice"] > 0
            ),
            "shield_reduces_tight_state_expansions": (
                tight_shield["stats"]["states"] < tight_exact["stats"]["states"]
            ),
        },
        "claim_boundary": [
            "Hard operational goals are an explicit transfer extension and are not attributed to the source paper.",
            "This replay preserves the paper's query/AoI/value scheduling structure but does not reproduce its CPT parameterization or published numerical curves.",
            "The unit-demand feasibility certificate is also available to an ordinary scheduling-aware constrained DP; this probe establishes correctness/interface compatibility and search headroom, not standalone Layer-2 novelty.",
            "Any paper claim requires a stronger dynamic/shared-resource domain where the full conditional frontier is not reducible to this unit-job certificate.",
        ],
    }
    return payload


def main() -> int:
    payload = run()
    assert all(payload["checks"].values()), payload["checks"]
    out = ROOT / "local_research/current/transfer/asc-pull-query-paper-structured-replay.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"out": str(out), **payload["checks"], "tight": payload["rows"]["tight"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
