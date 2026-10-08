#!/usr/bin/env python3
"""Formulation-level ASC transfer probe for future-choice feasibility.

Reference formulation:
  Agheli, Pappas, Kountouris, Pull-Based Query Scheduling for Goal-Oriented
  Semantic Communication, IEEE TCOM 2026 / arXiv:2503.06725.

The source work optimizes long-term semantic effectiveness (GoE/CPT-GoE) under
query cost constraints.  This probe deliberately does *not* reproduce their
numerical experiments.  Instead it preserves the interface that matters for
transfer -- current state, query action, scalar semantic value and query cost --
and asks whether an external hard operational-obligation layer can safely wrap
an unchanged scalar scheduler.

The paired construction uses identical current semantic scores and query costs.
Only the future hard-goal schedule differs.  A current high-value query is safe
in one state and destroys the only remaining feasible completion schedule in
the other.  A future-choice shield must distinguish the pair without changing
the scalar scheduler itself.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Goal:
    attribute: str
    release: int
    deadline: int


@dataclass(frozen=True)
class State:
    t: int
    remaining_queries: int
    current_scores: tuple[tuple[str, float], ...]
    future_goals: tuple[Goal, ...]

    def scores(self) -> dict[str, float]:
        return dict(self.current_scores)


def scalar_scheduler(state: State) -> str:
    """Unchanged semantic-value scheduler: choose highest current score."""

    return max(state.current_scores, key=lambda kv: (kv[1], kv[0]))[0]


def future_slots_after_action(state: State) -> list[int]:
    """The current action consumes slot t; later slots are t+1, t+2, ..."""

    horizon = max((goal.deadline for goal in state.future_goals), default=state.t)
    return list(range(state.t + 1, horizon + 1))


def action_query_cost(action: str) -> int:
    return 0 if action == "WAIT" else 1


def obligations_feasible_after(state: State, action: str) -> bool:
    """Exact tiny bipartite feasibility test for remaining hard query goals.

    Each query costs one unit and occupies one slot.  A goal is satisfied only
    by querying its required attribute no later than its deadline.  The current
    action is a scalar-policy action; future hard goals may require different
    attributes.  This is the finite-horizon hard-feasibility counterpart to a
    query-cost-constrained semantic scheduler.
    """

    remaining_budget = state.remaining_queries - action_query_cost(action)
    goals = list(state.future_goals)
    if remaining_budget < len(goals):
        return False
    slots = future_slots_after_action(state)
    if len(slots) < len(goals):
        return False

    # Unit-demand release/deadline scheduling is exact here by earliest deadline.
    available = list(slots)
    for goal in sorted(goals, key=lambda g: (g.deadline, g.attribute)):
        match = next(
            (slot for slot in available if goal.release <= slot <= goal.deadline),
            None,
        )
        if match is None:
            return False
        available.remove(match)
    return True


def shielded_scheduler(state: State) -> tuple[str | None, dict[str, bool]]:
    scores = state.scores()
    feasible = {
        action: obligations_feasible_after(state, action)
        for action in scores
    }
    candidates = [a for a, ok in feasible.items() if ok]
    if not candidates:
        return None, feasible
    return max(candidates, key=lambda a: (scores[a], a)), feasible


def run() -> dict:
    # Identical current semantic state in the two cases.
    current = (("A", 10.0), ("B", 4.0), ("C", 3.0), ("WAIT", 0.0))

    relaxed = State(
        t=0,
        remaining_queries=2,
        current_scores=current,
        future_goals=(Goal("B", 1, 2),),
    )
    tight = State(
        t=0,
        remaining_queries=2,
        current_scores=current,
        future_goals=(Goal("B", 1, 1), Goal("C", 2, 2)),
    )

    rows = []
    for name, state in (("relaxed_future", relaxed), ("tight_future", tight)):
        scalar = scalar_scheduler(state)
        shielded, mask = shielded_scheduler(state)
        rows.append(
            {
                "case": name,
                "current_scores": state.scores(),
                "remaining_queries": state.remaining_queries,
                "future_goals": [goal.__dict__ for goal in state.future_goals],
                "scalar_action": scalar,
                "scalar_action_future_feasible": mask[scalar],
                "shielded_action": shielded,
                "feasibility_mask": mask,
            }
        )

    payload = {
        "stage": "ASC_PULL_QUERY_FUTURE_CHOICE_FORMULATION_PROBE",
        "reference": {
            "title": "Pull-Based Query Scheduling for Goal-Oriented Semantic Communication",
            "arxiv": "2503.06725",
            "interface_used": "state -> query action -> scalar semantic effectiveness + query cost",
            "reproduction_claim": False,
        },
        "rows": rows,
        "checks": {
            "same_current_scores": rows[0]["current_scores"] == rows[1]["current_scores"],
            "scalar_policy_same_action": rows[0]["scalar_action"] == rows[1]["scalar_action"] == "A",
            "scalar_action_safe_in_relaxed": rows[0]["scalar_action_future_feasible"] is True,
            "scalar_action_unsafe_in_tight": rows[1]["scalar_action_future_feasible"] is False,
            "shield_changes_only_when_future_feasibility_changes": (
                rows[0]["shielded_action"] == "A" and rows[1]["shielded_action"] == "WAIT"
            ),
        },
        "claim_boundary": [
            "This is a formulation-level transfer counterexample, not reproduction of the source paper's numerical setup or CPT-GoE formula.",
            "The scalar scheduler is intentionally unchanged; only a hard operational-obligation feasibility layer is added.",
            "The probe establishes interface compatibility and non-equivalence of current scalar semantic value and future hard feasibility; it does not establish empirical gain on the source paper benchmark.",
        ],
    }
    return payload


def main() -> int:
    payload = run()
    assert all(payload["checks"].values()), payload["checks"]
    out = ROOT / "local_research/current/transfer/asc-pull-query-future-choice-probe.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"out": str(out), **payload["checks"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
