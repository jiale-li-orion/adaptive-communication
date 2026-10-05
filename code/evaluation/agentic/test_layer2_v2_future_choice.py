#!/usr/bin/env python3
"""Soundness smoke for Layer-2 v2 future-choice L/U semantics."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from causal_evidence_process_v0_1 import attach_causal_evidence
from compositional_recipe_generator_v0_1 import core_recipes
from dynamic_world_materializer_v0_1 import materialize_recipe
from exact_reference_oracle_v0_1 import LocalState, _attempt_lattice, _normalize
from layer1_v02_exact_continuation import ExactContinuationReference, replay_continuation_policy
from layer2_v2_future_choice import (
    common_opportunity_certificate,
    optimistic_upper,
    solve_minimal_resource_v2,
)
from v8_policy_baselines_v0_1 import _legal_actions, _step


ROOT = Path(__file__).resolve().parents[3]
SPLIT = ROOT / "results/benchmark/layer1-structure-aware-split-v0.2-retry-legality.json"
QUERY = ("ISSUE_QUERY", "gateway_state_summary")


def _bundle():
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    rep = next(
        row
        for row in split["rows"]
        if row.get("candidate_role") == "HARD_PRE_ADMISSION_SURVIVOR"
        and row.get("split") == "dev"
    )
    recipes = {row.recipe_id: row for row in core_recipes()}
    return materialize_recipe(recipes[str(rep["recipe_id"])])


def _initial(bundle, sat_budget: int):
    return {
        str(world["world_id"]): LocalState(satellite_budget=sat_budget)
        for world in bundle["worlds"]
    }


def _exact_minimal(bundle):
    start = min(_attempt_lattice(bundle))
    for q in range(len(bundle["obligations"]) + 1):
        for b in range(int(bundle["public_environment"]["satellite_budget_units"]) + 1):
            states = _initial(bundle, b)
            result = ExactContinuationReference(bundle).solve(start, states, query_budget=q)
            if result["solvable"] is True:
                replay_continuation_policy(
                    bundle,
                    at_s=start,
                    states=states,
                    policy=result["policy"],
                    query_budget=q,
                )
                return q, b, result
    raise AssertionError("hard dev representative unexpectedly infeasible")


def _find_replayable_lower(bundle, *, at_s, states, policy, qleft: int):
    process = attach_causal_evidence(bundle)
    node = policy
    support = dict(states)
    t = at_s
    while node and not node.get("terminal"):
        branches = _normalize(bundle, process, t, support)
        if len(branches) != 1 or next(iter(branches)) != "same":
            # Follow one lawful observation branch only to locate a candidate L;
            # replay later validates the certificate across its full support.
            obs, child = sorted(branches.items())[0]
            entry = next(row for row in node["children"] if row["observation"] == obs)
            support = child
            node = entry["subpolicy"]
            continue
        support = next(iter(branches.values()))
        cert = common_opportunity_certificate(bundle, at_s=t, states=support, process=process)
        if cert is not None:
            replay_continuation_policy(
                bundle,
                at_s=t,
                states=support,
                policy=cert,
                query_budget=qleft,
            )
            return True
        action = (str(node["action"]), node.get("arg"))
        if action[0] == "ISSUE_QUERY":
            qleft -= 1
        stepped = _step(bundle, process, support, t, action)
        assert stepped is not None
        support, t = stepped
        node = node["subpolicy"]
    return False


def main() -> int:
    bundle = _bundle()
    q, b, exact = _exact_minimal(bundle)
    v2 = solve_minimal_resource_v2(bundle, upper_mode="all_recursive")
    assert v2["solvable"] is True
    assert v2["minimal_resource_point"] == [q, b]

    start = min(_attempt_lattice(bundle))
    states = _initial(bundle, b)
    process = attach_causal_evidence(bundle)
    branches = _normalize(bundle, process, start, states)
    assert len(branches) == 1 and next(iter(branches)) == "same"
    support = next(iter(branches.values()))

    # U soundness: whenever the optimistic query upper says impossible, exact
    # continuation after the same forced query must also be impossible.
    if QUERY in _legal_actions(bundle, process, support, start):
        stepped = _step(bundle, process, support, start, QUERY)
        assert stepped is not None
        child, next_t = stepped
        upper = optimistic_upper(bundle, at_s=next_t, states=child)
        if not upper:
            forced = ExactContinuationReference(bundle).solve(
                next_t,
                deepcopy(child),
                query_budget=max(0, q - 1),
            )
            assert forced["status"] == "EXACT"
            assert forced["solvable"] is False

    # L soundness: locate at least one reachable structural tail certificate
    # and replay it against the frozen Layer-1 transition kernel.
    assert _find_replayable_lower(
        bundle,
        at_s=start,
        states=states,
        policy=exact["policy"],
        qleft=q,
    )
    print("PASS Layer-2 v2 future-choice: exact resource match + U soundness + replayable L")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
