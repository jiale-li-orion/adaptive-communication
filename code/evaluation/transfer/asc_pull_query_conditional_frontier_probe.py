#!/usr/bin/env python3
"""Conditional future-choice probe on a pull-based semantic-query interface.

This probe targets the part of Layer 2 that a static resource reservation cannot
represent: future obligations are conditional on information that has not yet
arrived.

Two hidden worlds share the same initial history.  Querying semantic attribute
``H`` at t=0 reveals which operational goal becomes relevant at t=1:

* H=0 -> query B by t=1;
* H=1 -> query C by t=1.

There are exactly two query units.  The causal policy

    QUERY H -> observe H -> QUERY B or QUERY C

is feasible in every world.  A static union-reserve approximation incorrectly
requires budget for both B and C after H and therefore rejects the only useful
information-gathering action.  Conversely, WAIT preserves raw budget but leaves
the two worlds aliased at t=1, where one common action cannot satisfy both.

The query/observation interface mirrors pull-based goal-oriented semantic
communication; the hard conditional goals are an explicit transfer extension,
not attributed to the source paper.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WORLDS = ("H0", "H1")
QUERY_BUDGET = 2


@dataclass(frozen=True)
class BranchState:
    t: int
    budget: int
    compatible_worlds: tuple[str, ...]
    h_observation: int | None = None


def required_attribute(world: str) -> str:
    return "B" if world == "H0" else "C"


def exact_causal_first_action(action: str) -> dict:
    """Evaluate one fixed t=0 action under non-anticipative continuation."""

    if action == "QUERY_H":
        # One query unit is spent, but the observation creates two legal histories.
        remaining = QUERY_BUDGET - 1
        branches = {
            "H=0": {
                "worlds": ["H0"],
                "remaining_budget": remaining,
                "t1_action": "QUERY_B",
                "success": remaining >= 1,
            },
            "H=1": {
                "worlds": ["H1"],
                "remaining_budget": remaining,
                "t1_action": "QUERY_C",
                "success": remaining >= 1,
            },
        }
        return {
            "action": action,
            "causal_success": all(row["success"] for row in branches.values()),
            "branches": branches,
        }

    # WAIT or querying B/C at t=0 does not reveal H.  At t=1 both worlds still
    # have the same legal history.  A non-anticipative policy must choose one
    # common query action; QUERY_B fails H1, QUERY_C fails H0.
    remaining = QUERY_BUDGET - (0 if action == "WAIT" else 1)
    candidates = []
    for t1_action in ("QUERY_B", "QUERY_C"):
        successes = {
            world: (
                remaining >= 1 and t1_action.removeprefix("QUERY_") == required_attribute(world)
            )
            for world in WORLDS
        }
        candidates.append({
            "t1_action": t1_action,
            "world_success": successes,
            "common_success": all(successes.values()),
        })
    return {
        "action": action,
        "causal_success": any(row["common_success"] for row in candidates),
        "aliased_worlds_at_t1": list(WORLDS),
        "candidate_common_continuations": candidates,
    }


def static_union_reserve_after_h() -> dict:
    """Ordinary over-conservative approximation that unions branch obligations."""

    remaining_budget = QUERY_BUDGET - 1
    union_goals = {required_attribute(world) for world in WORLDS}
    return {
        "remaining_budget": remaining_budget,
        "union_future_goals": sorted(union_goals),
        "required_units": len(union_goals),
        "declared_feasible": remaining_budget >= len(union_goals),
    }


def full_current_upper(action: str) -> bool:
    """Optimistic upper bound: evaluator reveals H before t=1 continuation."""

    remaining = QUERY_BUDGET - (0 if action == "WAIT" else 1)
    # If H were magically known, one t=1 query suffices in either world.
    return remaining >= 1


def main() -> int:
    actions = ("WAIT", "QUERY_H", "QUERY_B", "QUERY_C")
    rows = {}
    for action in actions:
        exact = exact_causal_first_action(action)
        rows[action] = {
            "exact_causal": exact,
            "L": 1 if exact["causal_success"] else 0,
            "U": 1 if full_current_upper(action) else 0,
        }

    union = static_union_reserve_after_h()
    h = rows["QUERY_H"]
    wait = rows["WAIT"]
    payload = {
        "stage": "ASC_PULL_QUERY_CONDITIONAL_FRONTIER_PROBE",
        "reference_interface": {
            "domain": "pull-based goal-oriented semantic query scheduling",
            "initial_query_budget": QUERY_BUDGET,
            "hidden_worlds": list(WORLDS),
            "query_result": "QUERY_H reveals branch-relevant semantic attribute H",
            "transfer_extension": "branch-conditional hard operational query goal at t=1",
        },
        "rows": rows,
        "static_union_reserve": union,
        "conditional_certificate": {
            "action": "QUERY_H",
            "valid_domain": "budget>=2 and H observation arrives before t=1 decision",
            "branches": {
                "H=0": "remaining budget 1 -> QUERY_B",
                "H=1": "remaining budget 1 -> QUERY_C",
            },
            "causal_success_witness": True,
        },
        "checks": {
            "query_h_has_executable_lower_bound": h["L"] == 1,
            "wait_is_information_unresolved_not_physically_impossible": (
                wait["L"] == 0 and wait["U"] == 1
            ),
            "static_union_reserve_false_negative": (
                union["declared_feasible"] is False and h["L"] == 1
            ),
            "observation_conditioned_continuation_is_nonanticipative": all(
                len(branch["worlds"]) == 1
                for branch in h["exact_causal"]["branches"].values()
            ),
        },
        "claim_boundary": [
            "The hard branch-conditional operational goals are a transfer extension; the source Pull-Based paper is not claimed to contain these deadlines.",
            "The result isolates conditional feasibility: a static union of possible future goals is over-conservative, while a causal observation-conditioned policy succeeds with the same budget.",
            "An exact belief-space AND-OR solver also represents this structure; the probe motivates the conditional-frontier representation but does not by itself establish a computational advantage over a strong exact solver.",
        ],
    }
    assert all(payload["checks"].values()), payload["checks"]
    out = ROOT / "local_research/current/transfer/asc-pull-query-conditional-frontier.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"out": str(out), **payload["checks"], "rows": rows}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
