#!/usr/bin/env python3
"""Audit what actually makes the 41 Layer-1 V8 survivor signatures hard.

This is a benchmark-discovery audit, not a method benchmark.  It follows the
construction discipline frozen in cache06.md:

    generated candidate -> exact validity -> strong-baseline survivor
    -> explain the survivor before designing a new method.

For one deterministic representative of every V8 survivor signature, each
ordinary observation-matched baseline is executed causally.  At every reached
decision prefix we ask an *independent* exact continuation oracle whether the
prefix is still completable.  The first baseline action that changes a
completable prefix into a non-completable prefix is recorded as a first
irreversible loss.  At that same prefix we enumerate all legal actions and
record which alternatives still preserve an exact successful continuation.

The continuation check deliberately gives the diagnostic oracle a generous
future query allowance.  Therefore a recorded first-loss action is not merely
"the baseline used its query budget badly"; after the action, no completion
policy exists even when later evidence acquisition is not the bottleneck.

The audit also reports the structural coverage of the survivor set.  This is
important because recipe count is not structural coverage: 174 hard recipes
currently collapse to 41 exact signatures.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Callable, Mapping

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
from v8_policy_baselines_v0_1 import (
    _choose_always_query_then_plan,
    _choose_depth_k,
    _choose_least_slack,
    _choose_shallow,
    _fixed_query_times,
    _legal_actions,
    _step,
)


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
V8_ROWS = ROOT / "local_research/current/benchmark/generated/v8-all-pass-v0.2-retry-legality/signature-v8.jsonl"
SPLIT = ROOT / "results/benchmark/layer1-structure-aware-split-v0.2-retry-legality.json"

Action = tuple[str, str | None]
Chooser = Callable[[Mapping[str, Any], Mapping[str, Any], int, Mapping[str, LocalState]], Action | None]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _action_key(action: Action) -> str:
    return action[0] if action[1] is None else f"{action[0]}:{action[1]}"


def _canon(states: Mapping[str, LocalState]) -> tuple[tuple[str, LocalState], ...]:
    return tuple(sorted(states.items()))


def _initial(bundle: Mapping[str, Any]) -> dict[str, LocalState]:
    budget = int(bundle["public_environment"]["satellite_budget_units"])
    return {
        str(world["world_id"]): LocalState(satellite_budget=budget)
        for world in bundle["worlds"]
    }


def _fixed_query_chooser(mode: str) -> Chooser:
    def choose(bundle, process, at_s, states):
        schedule = _fixed_query_times(bundle, mode)
        actions = _legal_actions(bundle, process, states, at_s)
        if at_s in schedule:
            query = next((action for action in actions if action[0] == "ISSUE_QUERY"), None)
            if query is not None:
                return query
        return _choose_least_slack(bundle, process, at_s, states)

    return choose


def _baseline_choosers() -> dict[str, Chooser]:
    return {
        "always_query_then_plan": _choose_always_query_then_plan,
        "least_slack": _choose_least_slack,
        "shallow_rule": _choose_shallow,
        "myopic_flow_voi": lambda b, p, t, s: _choose_depth_k(b, p, t, s, 1, leaf="flow"),
        "true_depth_2_belief": lambda b, p, t, s: _choose_depth_k(b, p, t, s, 2),
        "true_depth_3_belief": lambda b, p, t, s: _choose_depth_k(b, p, t, s, 3),
        "receding_flow_terminal_4": lambda b, p, t, s: _choose_depth_k(b, p, t, s, 4, leaf="flow"),
        "receding_flow_terminal_6": lambda b, p, t, s: _choose_depth_k(b, p, t, s, 6, leaf="flow"),
        "fixed_query_every_release": _fixed_query_chooser("EVERY_RELEASE"),
    }


def _survivors() -> list[dict[str, Any]]:
    rows = _read_jsonl(V8_ROWS)
    survivors = [row for row in rows if row["v8_disposition"] == "SURVIVES_V8_LADDER_V0_1"]
    return sorted(survivors, key=lambda row: str(row["signature"]))


def _frontier(
    bundle: Mapping[str, Any],
    process: Mapping[str, Any],
    exact: ExactContinuationReference,
    cache: dict[Any, bool | None],
    *,
    at_s: int,
    states: Mapping[str, LocalState],
    generous_query_budget: int,
) -> list[dict[str, Any]]:
    out = []
    for action in _legal_actions(bundle, process, states, at_s):
        stepped = _step(bundle, process, states, at_s, action)
        if stepped is None:
            continue
        child, next_t = stepped
        key = (next_t, _canon(child))
        if key not in cache:
            cache[key] = exact.solve(
                next_t,
                deepcopy(child),
                query_budget=generous_query_budget,
            )["solvable"]
        out.append(
            {
                "action": _action_key(action),
                "kind": action[0],
                "preserves_completion": cache[key],
            }
        )
    return out


def _audit_baseline(bundle: Mapping[str, Any], chooser: Chooser) -> dict[str, Any]:
    process = attach_causal_evidence(bundle)
    exact = ExactContinuationReference(bundle)
    generous_query_budget = len(bundle["obligations"]) + 2
    exact_cache: dict[Any, bool | None] = {}
    first_losses: list[dict[str, Any]] = []
    endings: Counter[str] = Counter()
    visited_prefixes = 0

    def exact_solvable(t: int, states: Mapping[str, LocalState]) -> bool | None:
        key = (t, _canon(states))
        if key not in exact_cache:
            exact_cache[key] = exact.solve(
                t,
                deepcopy(dict(states)),
                query_budget=generous_query_budget,
            )["solvable"]
        return exact_cache[key]

    def rec(
        at_s: int,
        states: Mapping[str, LocalState],
        seen: frozenset[Any],
        depth: int,
        observation_path: tuple[str, ...],
    ) -> None:
        nonlocal visited_prefixes
        branches = _normalize(bundle, process, at_s, states)
        if len(branches) != 1 or next(iter(branches)) != "same":
            for observation, child in sorted(branches.items()):
                rec(at_s, child, seen, depth, observation_path + (str(observation),))
            return

        support = next(iter(branches.values()))
        visited_prefixes += 1
        if any(_expired(bundle, state, at_s) for state in support.values()):
            endings["DEADLINE_EXPIRED"] += 1
            return
        if all(_success(bundle, state) for state in support.values()):
            endings["SUCCESS"] += 1
            return

        key = (at_s, _canon(support))
        if key in seen:
            endings["LOOP"] += 1
            return
        if depth >= 128:
            endings["DEPTH_LIMIT"] += 1
            return

        action = chooser(bundle, process, at_s, support)
        if action is None:
            endings["NO_ACTION"] += 1
            return
        stepped = _step(bundle, process, support, at_s, action)
        if stepped is None:
            endings["ILLEGAL_OR_UNAVAILABLE_STEP"] += 1
            return
        child, next_t = stepped

        before = exact_solvable(at_s, support)
        after = exact_solvable(next_t, child)
        if before is True and after is False:
            frontier = _frontier(
                bundle,
                process,
                exact,
                exact_cache,
                at_s=at_s,
                states=support,
                generous_query_budget=generous_query_budget,
            )
            preserving = [row["action"] for row in frontier if row["preserves_completion"] is True]
            first_losses.append(
                {
                    "time_s": int(at_s),
                    "world_count": len(support),
                    "observation_path_digest": sha256(repr(observation_path).encode()).hexdigest()[:12],
                    "chosen_action": _action_key(action),
                    "chosen_action_kind": action[0],
                    "preserving_actions": preserving,
                    "legal_action_frontier": frontier,
                }
            )
            endings["FIRST_IRREVERSIBLE_LOSS"] += 1
            return

        rec(next_t, child, seen | {key}, depth + 1, observation_path)

    rec(min(_attempt_lattice(bundle)), _initial(bundle), frozenset(), 0, ())
    return {
        "visited_prefixes": visited_prefixes,
        "first_loss_count": len(first_losses),
        "first_loss_action_kind": dict(sorted(Counter(row["chosen_action_kind"] for row in first_losses).items())),
        "endings": dict(sorted(endings.items())),
        "first_losses": first_losses,
    }


def _axis_summary(survivors: list[dict[str, Any]], recipes: Mapping[str, Any]) -> dict[str, Any]:
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    hard_recipes = [row for row in split["rows"] if row["candidate_role"] == "HARD_PRE_ADMISSION_SURVIVOR"]

    rep_recipes = [recipes[str(row["representative_recipe_id"])] for row in survivors]
    rep_hardness = Counter(tag for recipe in rep_recipes for tag in recipe.hardness)

    def counts(values):
        return dict(sorted(Counter(values).items(), key=lambda item: str(item[0])))

    return {
        "hard_recipe_count": len(hard_recipes),
        "hard_signature_count": len(survivors),
        "signature_representative_axes": {
            "service_process": counts(row["service_process"] for row in survivors),
            "evidence_regime": counts(row["evidence_regime"] for row in survivors),
            "overlap_count": counts(int(row["overlap_count"]) for row in survivors),
            "recovery_regime": counts(row["recovery_regime"] for row in survivors),
            "resource_headroom": counts(recipe.resource_headroom for recipe in rep_recipes),
            "warning_state": counts(recipe.warning_state for recipe in rep_recipes),
            "report_interval_s": counts(int(recipe.report_interval_s) for recipe in rep_recipes),
            "geometry_signature_id": counts(recipe.geometry_signature_id for recipe in rep_recipes),
            "hardness_tags": dict(sorted(rep_hardness.items())),
            "task_contract_count": len({recipe.task_case_id for recipe in rep_recipes}),
        },
        "all_174_recipe_axes": {
            key: counts(row[key] for row in hard_recipes)
            for key in (
                "service_process",
                "evidence_regime",
                "overlap_count",
                "resource_headroom",
                "recovery_regime",
                "geometry_signature_id",
                "task_case_id",
            )
        },
        "coverage_interpretation": {
            "mechanism_core": "All current hard survivors lie in H2 evidence value × H3 shared-resource conflict × H4 coupled-sequential-commitment compositions.",
            "missing_as_independent_hard_survivors": [
                "PASSIVE_ACK_ONLY / H1-only partial-observation hard surface",
                "MIXED_PASSIVE_QUERY_PROBE / H5 competition hard surface",
                "MULTI_WINDOW_DYNAMIC hard survivors",
                "energy-pressure hard survivors (energy is intentionally after-core in the frozen contract)",
            ],
            "warning": "Parameter diversity across geometry, recovery, headroom and task contracts must not be reported as independent mechanism diversity.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "results/benchmark/layer1-hard-survivor-failure-atlas-v0.1.json")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    survivors = _survivors()
    if args.limit is not None:
        survivors = survivors[: args.limit]
    recipes = {row.recipe_id: row for row in core_recipes()}
    choosers = _baseline_choosers()

    cases = []
    summary_by_baseline: dict[str, Counter[str]] = {name: Counter() for name in choosers}
    for index, row in enumerate(survivors, 1):
        recipe_id = str(row["representative_recipe_id"])
        bundle = materialize_recipe(recipes[recipe_id])
        baseline_rows = {}
        for name, chooser in choosers.items():
            audit = _audit_baseline(bundle, chooser)
            baseline_rows[name] = audit
            counter = summary_by_baseline[name]
            counter["signature_count"] += 1
            counter["signature_with_first_loss"] += int(audit["first_loss_count"] > 0)
            counter["first_loss_branch_count"] += int(audit["first_loss_count"])
            for kind, count in audit["first_loss_action_kind"].items():
                counter[f"first_loss_action::{kind}"] += int(count)
        cases.append(
            {
                "signature": row["signature"],
                "representative_recipe_id": recipe_id,
                "service_process": row["service_process"],
                "evidence_regime": row["evidence_regime"],
                "overlap_count": row["overlap_count"],
                "recovery_regime": row["recovery_regime"],
                "baselines": baseline_rows,
            }
        )
        print(index, str(row["signature"])[:12], flush=True)

    artifact = {
        "schema_version": "0.1",
        "status": "COMPLETE" if survivors else "EMPTY",
        "purpose": "Explain the Layer-1 hard-survivor surface before any new method or learning work.",
        "diagnostic_contract": {
            "representative_rule": "one frozen V8 representative recipe per exact survivor signature",
            "first_irreversible_loss": "prefix exact-completable before the baseline action and exact-noncompletable after it",
            "future_query_allowance": "len(obligations)+2 at every diagnostic continuation; query-count scarcity is therefore not sufficient to create a first-loss label",
            "frontier": "all legal actions at the first-loss prefix are independently exact-checked; preserving alternatives are recorded",
            "claim_boundary": "This audit establishes failure structure inside the frozen Layer-1 simulator. It does not by itself prove field frequency or cross-domain universality.",
        },
        "coverage": _axis_summary(survivors, recipes),
        "summary_by_baseline": {
            name: dict(sorted(counter.items()))
            for name, counter in sorted(summary_by_baseline.items())
        },
        "cases": cases,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": artifact["status"],
        "coverage": artifact["coverage"],
        "summary_by_baseline": artifact["summary_by_baseline"],
    }, ensure_ascii=False, indent=2))
    return 0 if survivors else 1


if __name__ == "__main__":
    raise SystemExit(main())
