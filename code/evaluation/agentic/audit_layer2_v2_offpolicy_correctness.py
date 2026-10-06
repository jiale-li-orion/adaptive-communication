#!/usr/bin/env python3
"""Bounded off-policy correctness audit for Layer-2 v2 deterministic freeze.

Unlike the earlier exact-policy reachable-prefix audits, this runner enumerates
*all legal action branches* up to a bounded action depth, including actions the
winning policy would never choose. Observation branches do not consume action
depth and are also enumerated.

At every reached decision prefix it checks:

1. L/U soundness against exact continuation for every legal affordable action;
2. the conditional QxB continuation label against the same exact action label;
3. incremental conflict-frontier equality with a fresh full rebuild;
4. no realized world ID or future window ID leaks into model-facing contexts.

This is a bounded exhaustive audit, not a formal proof over the unbounded state
space.  It reads train/dev only; final test remains sealed.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Mapping

from causal_evidence_process_v0_1 import attach_causal_evidence
from compositional_recipe_generator_v0_1 import core_recipes
from dynamic_world_materializer_v0_1 import materialize_recipe
from exact_reference_oracle_v0_1 import (
    LocalState,
    _attempt_lattice,
    _expired,
    _normalize,
    _success,
)
from layer1_v02_exact_continuation import ExactContinuationReference
from layer2_v2_conditional_resource_frontier import ConditionalResourceFrontierRuntime
from layer2_v2_conflict_frontier import IncrementalConflictFrontier, canonical_snapshot
from layer2_v2_future_choice import future_choice_context, solve_minimal_resource_v2
from v8_policy_baselines_v0_1 import _legal_actions, _step


ROOT = Path(__file__).resolve().parents[3]
SPLIT = ROOT / "results/benchmark/layer1-structure-aware-split-v0.2-retry-legality.json"


def _representatives(split_name: str) -> list[dict[str, Any]]:
    frozen = json.loads(SPLIT.read_text(encoding="utf-8"))
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in frozen["rows"]:
        if (
            row.get("candidate_role") == "HARD_PRE_ADMISSION_SURVIVOR"
            and row.get("split") == split_name
        ):
            grouped[str(row["signature"])].append(row)
    return [min(rows, key=lambda row: str(row["recipe_id"])) for _, rows in sorted(grouped.items())]


def _initial(bundle: Mapping[str, Any], sat_budget: int) -> dict[str, LocalState]:
    return {
        str(world["world_id"]): LocalState(satellite_budget=sat_budget)
        for world in bundle["worlds"]
    }


def _action_key(action: tuple[str, str | None]) -> str:
    return f"{action[0]}:{action[1] if action[1] is not None else '-'}"


def _common_satellite_budget(states: Mapping[str, LocalState]) -> int:
    values = {int(state.satellite_budget) for state in states.values()}
    if len(values) != 1:
        raise AssertionError("off-policy support lost common satellite budget")
    return next(iter(values))


def _strings(value: Any):
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield str(key)
            yield from _strings(child)
    elif isinstance(value, (list, tuple, set)):
        for child in value:
            yield from _strings(child)
    elif value is not None:
        yield str(value)


def _forbidden_realization_tokens(bundle: Mapping[str, Any]) -> set[str]:
    tokens = {str(world["world_id"]) for world in bundle["worlds"]}
    for world in bundle["worlds"]:
        tokens.update(str(window["window_id"]) for window in world["terrestrial_windows"])
    # Public satellite-window IDs are not hidden realization identity and are
    # therefore intentionally excluded.
    return tokens


def _no_realization_leak(bundle: Mapping[str, Any], *contexts: Mapping[str, Any]) -> bool:
    forbidden = _forbidden_realization_tokens(bundle)
    for context in contexts:
        for text in _strings(context):
            if any(token and token in text for token in forbidden):
                return False
    return True


class CaseAudit:
    def __init__(
        self,
        bundle: Mapping[str, Any],
        *,
        query_budget: int,
        max_action_depth: int,
        max_prefixes: int,
    ):
        self.bundle = bundle
        self.process = attach_causal_evidence(bundle)
        self.query_budget = int(query_budget)
        self.max_action_depth = int(max_action_depth)
        self.max_prefixes = int(max_prefixes)
        self.exact = ExactContinuationReference(bundle)
        self.conditional = ConditionalResourceFrontierRuntime(bundle)
        self.rows: list[dict[str, Any]] = []
        self.observation_branch_count = 0
        self.action_branch_count = 0
        self.truncated = False

    def _visit(
        self,
        *,
        at_s: int,
        states: Mapping[str, LocalState],
        query_budget: int,
        action_depth: int,
        conflict: IncrementalConflictFrontier,
        history: tuple[str, ...],
    ) -> None:
        if len(self.rows) >= self.max_prefixes:
            self.truncated = True
            return

        branches = _normalize(self.bundle, self.process, at_s, states)
        if len(branches) != 1 or next(iter(branches)) != "same":
            self.observation_branch_count += len(branches)
            for observation, child in sorted(branches.items()):
                self._visit(
                    at_s=at_s,
                    states=child,
                    query_budget=query_budget,
                    action_depth=action_depth,
                    conflict=deepcopy(conflict),
                    history=(*history, f"OBS:{observation}"),
                )
            return

        support = next(iter(branches.values()))
        if any(_expired(self.bundle, state, at_s) for state in support.values()):
            return
        if all(_success(self.bundle, state) for state in support.values()):
            return

        incremental, delta = conflict.update(at_s=at_s, states=support)
        rebuilt = conflict.full_rebuild(at_s=at_s, states=support)
        conflict_match = canonical_snapshot(incremental) == canonical_snapshot(rebuilt)

        state_exact = self.exact.solve(at_s, support, query_budget=query_budget)
        if state_exact["status"] != "EXACT":
            raise RuntimeError("off-policy state exact continuation hit search limit")
        context = future_choice_context(
            self.bundle,
            at_s=at_s,
            states=support,
            query_budget=query_budget,
            witness_policy=state_exact["policy"] if state_exact["solvable"] else None,
        )
        by_key = {row["action_key"]: row for row in context["actions"]}
        conditional_context = None
        try:
            conditional_frontier = self.conditional.build_frontier(
                at_s=at_s,
                states=support,
                qmax=query_budget,
                bmax=_common_satellite_budget(support),
            )
            conditional_context = self.conditional.materialized_context(conditional_frontier)
        except ValueError:
            conditional_context = {
                "schema_version": "layer2-v2-conditional-resource-frontier-0.1",
                "unavailable": True,
            }
        conflict_context = conflict.materialized_context(incremental)
        no_leak = _no_realization_leak(
            self.bundle,
            context,
            conditional_context,
            conflict_context,
        )

        action_rows = []
        for action in _legal_actions(self.bundle, self.process, support, at_s):
            dq = int(action[0] == "ISSUE_QUERY")
            if dq > query_budget:
                continue
            stepped = _step(self.bundle, self.process, support, at_s, action)
            if stepped is None:
                continue
            child, next_t = stepped
            result = self.exact.solve(
                next_t,
                child,
                query_budget=query_budget - dq,
            )
            if result["status"] != "EXACT":
                raise RuntimeError("forced off-policy action exact continuation hit search limit")
            exact_solvable = bool(result["solvable"])
            bound = by_key[_action_key(action)]
            lower = int(bound["lower"])
            upper = int(bound["upper"])
            sat_after = _common_satellite_budget(child)
            conditional = self.conditional.evaluate_continuation_cell(
                at_s=next_t,
                states=child,
                query_budget=query_budget - dq,
                satellite_budget=sat_after,
            )
            action_rows.append(
                {
                    "action_key": _action_key(action),
                    "exact_solvable": exact_solvable,
                    "lower": lower,
                    "upper": upper,
                    "lower_sound": not lower or exact_solvable,
                    "upper_sound": upper or not exact_solvable,
                    "ordered": lower <= upper,
                    "conditional_solvable": bool(conditional["solvable"]),
                    "conditional_match": bool(conditional["solvable"]) == exact_solvable,
                }
            )

        self.rows.append(
            {
                "history": list(history),
                "time_s": int(at_s),
                "action_depth": int(action_depth),
                "query_budget": int(query_budget),
                "world_count": len(support),
                "state_exact_solvable": bool(state_exact["solvable"]),
                "conflict_incremental_match": conflict_match,
                "component_recomputes": int(delta["component_recomputes"]),
                "component_reuses": int(delta["component_reuses"]),
                "model_context_no_realization_leak": no_leak,
                "actions": action_rows,
            }
        )

        if action_depth >= self.max_action_depth:
            return
        for action in _legal_actions(self.bundle, self.process, support, at_s):
            dq = int(action[0] == "ISSUE_QUERY")
            if dq > query_budget:
                continue
            stepped = _step(self.bundle, self.process, support, at_s, action)
            if stepped is None:
                continue
            self.action_branch_count += 1
            child, next_t = stepped
            self._visit(
                at_s=next_t,
                states=child,
                query_budget=query_budget - dq,
                action_depth=action_depth + 1,
                conflict=deepcopy(conflict),
                history=(*history, _action_key(action)),
            )

    def run(self, initial_states: Mapping[str, LocalState], start_s: int) -> dict[str, Any]:
        self._visit(
            at_s=start_s,
            states=initial_states,
            query_budget=self.query_budget,
            action_depth=0,
            conflict=IncrementalConflictFrontier(self.bundle),
            history=(),
        )
        actions = [action for row in self.rows for action in row["actions"]]
        return {
            "prefix_count": len(self.rows),
            "action_check_count": len(actions),
            "observation_branch_count": self.observation_branch_count,
            "action_branch_count": self.action_branch_count,
            "truncated": self.truncated,
            "lower_sound_count": sum(action["lower_sound"] for action in actions),
            "upper_sound_count": sum(action["upper_sound"] for action in actions),
            "ordered_count": sum(action["ordered"] for action in actions),
            "conditional_match_count": sum(action["conditional_match"] for action in actions),
            "conflict_match_count": sum(row["conflict_incremental_match"] for row in self.rows),
            "no_realization_leak_count": sum(
                row["model_context_no_realization_leak"] for row in self.rows
            ),
            "component_recomputes": sum(row["component_recomputes"] for row in self.rows),
            "component_reuses": sum(row["component_reuses"] for row in self.rows),
            "rows": self.rows,
        }


def _case(bundle: Mapping[str, Any], *, max_action_depth: int, max_prefixes: int) -> dict[str, Any]:
    solved = solve_minimal_resource_v2(bundle, upper_mode="all_recursive")
    if solved["solvable"] is not True:
        raise AssertionError("hard case unexpectedly unsolved")
    q, sat = map(int, solved["minimal_resource_point"])
    audit = CaseAudit(
        bundle,
        query_budget=q,
        max_action_depth=max_action_depth,
        max_prefixes=max_prefixes,
    )
    result = audit.run(_initial(bundle, sat), min(_attempt_lattice(bundle)))
    return {"minimal_resource_point": [q, sat], **result}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["train", "dev"], default="dev")
    ap.add_argument("--limit", type=int, default=1)
    ap.add_argument("--max-action-depth", type=int, default=2)
    ap.add_argument("--max-prefixes", type=int, default=20_000)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    reps = _representatives(args.split)[: args.limit]
    recipes = {row.recipe_id: row for row in core_recipes()}
    cases = []
    for index, rep in enumerate(reps, 1):
        result = _case(
            materialize_recipe(recipes[str(rep["recipe_id"])]),
            max_action_depth=args.max_action_depth,
            max_prefixes=args.max_prefixes,
        )
        cases.append(
            {
                "signature": rep["signature"],
                "recipe_id": rep["recipe_id"],
                "result": result,
            }
        )
        print(
            index,
            str(rep["signature"])[:12],
            "prefixes",
            result["prefix_count"],
            "actions",
            result["action_check_count"],
            "truncated",
            result["truncated"],
            flush=True,
        )

    prefix_count = sum(case["result"]["prefix_count"] for case in cases)
    action_count = sum(case["result"]["action_check_count"] for case in cases)
    summary = {
        "signature_count": len(cases),
        "max_action_depth": int(args.max_action_depth),
        "prefix_count": prefix_count,
        "action_check_count": action_count,
        "observation_branch_count": sum(
            case["result"]["observation_branch_count"] for case in cases
        ),
        "action_branch_count": sum(case["result"]["action_branch_count"] for case in cases),
        "truncated_case_count": sum(case["result"]["truncated"] for case in cases),
        "lower_sound_count": sum(case["result"]["lower_sound_count"] for case in cases),
        "upper_sound_count": sum(case["result"]["upper_sound_count"] for case in cases),
        "ordered_count": sum(case["result"]["ordered_count"] for case in cases),
        "conditional_match_count": sum(
            case["result"]["conditional_match_count"] for case in cases
        ),
        "conflict_match_count": sum(case["result"]["conflict_match_count"] for case in cases),
        "no_realization_leak_count": sum(
            case["result"]["no_realization_leak_count"] for case in cases
        ),
        "component_recomputes": sum(case["result"]["component_recomputes"] for case in cases),
        "component_reuses": sum(case["result"]["component_reuses"] for case in cases),
    }
    passed = (
        bool(cases)
        and summary["truncated_case_count"] == 0
        and summary["lower_sound_count"] == action_count
        and summary["upper_sound_count"] == action_count
        and summary["ordered_count"] == action_count
        and summary["conditional_match_count"] == action_count
        and summary["conflict_match_count"] == prefix_count
        and summary["no_realization_leak_count"] == prefix_count
    )
    artifact = {
        "schema_version": "0.1",
        "status": "PASS" if passed else "FAIL",
        "experiment": "layer2-v2-bounded-offpolicy-correctness",
        "split": args.split,
        "scope": (
            f"all legal action/observation histories reachable within action depth "
            f"{args.max_action_depth}; bounded exhaustive, not an unbounded proof"
        ),
        "summary": summary,
        "rules": [
            "Every affordable legal action is enumerated, not only the exact winning action.",
            "Observation branches are exhaustive and do not consume action depth.",
            "L/U and conditional QxB labels are compared with same-information exact continuation after the forced action.",
            "Conflict-frontier incremental state is cloned per off-policy branch and compared with a fresh rebuild at every reached decision prefix.",
            "Model-facing future-choice/conditional/conflict contexts must not contain realized world IDs or hidden terrestrial-window IDs.",
            "Train/dev only; final test is not read.",
        ],
        "cases": cases,
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps({"status": artifact["status"], "summary": summary}, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
