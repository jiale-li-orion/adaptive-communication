#!/usr/bin/env python3
"""Lower/upper action-feasibility bounds with exact fallback."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from continuation_resource_domains_v0_1 import ContinuationPlanner, verify_witness
from exact_reference_oracle_v0_1 import (
    FINAL_ACK_DELAY_S,
    SATELLITE_COMPLETION_DELAY_S,
    LocalState,
    _expired,
    _maxflow,
    _normalize,
    _success,
    _world_map,
)
from v8_policy_baselines_v0_1 import _legal_actions, _step
from structural_lower_certificate_v0_1 import satellite_only_certificate
from structural_common_certificate_v0_1 import common_opportunity_certificate


Action = tuple[str, str | None]


def _world_residual_feasible(bundle: Mapping[str, Any], at_s: int, wid: str, st: LocalState) -> bool:
    if _expired(bundle, st, at_s):
        return False
    world = _world_map(bundle)[wid]
    secured = set(st.delivered)
    for d in st.pending_deliveries:
        if not d.accepted or d.final_ack_at_s is None:
            continue
        deadline = next(
            int(o["deadline_s"])
            for o in bundle["obligations"]
            if str(o["obligation_id"]) == d.obligation_id
        )
        if d.final_ack_at_s <= deadline:
            secured.add(d.obligation_id)
    obligations = [o for o in bundle["obligations"] if str(o["obligation_id"]) not in secured]
    if not obligations:
        return True

    source = "SRC"; sink = "SNK"; sat_pool = "SAT_POOL"; graph: dict[str, dict[str, int]] = {}
    def add(u: str, v: str, cap: int) -> None:
        if cap <= 0:
            return
        graph.setdefault(u, {})[v] = graph.setdefault(u, {}).get(v, 0) + cap
        graph.setdefault(v, {}).setdefault(u, 0)

    terr_used = dict(st.terrestrial_used)
    sat_used = dict(st.satellite_used)
    for o in obligations:
        oid = str(o["obligation_id"]); on = f"O::{oid}"; add(source, on, 1)
        for w in world["terrestrial_windows"]:
            cap = max(0, int(w["capacity_units"]) - terr_used.get(str(w["window_id"]), 0))
            t = max(at_s, int(o["release_s"]), int(w["start_s"]))
            if cap > 0 and t < int(w["end_s"]) and t + FINAL_ACK_DELAY_S <= int(o["deadline_s"]):
                add(on, f"T::{w['window_id']}", 1)
        for w in bundle["public_environment"]["satellite_windows"]:
            cap = max(0, int(w["capacity_units"]) - sat_used.get(str(w["window_id"]), 0))
            t = max(at_s, int(o["release_s"]), int(w["start_s"]))
            if cap > 0 and t < int(w["end_s"]) and t + SATELLITE_COMPLETION_DELAY_S <= int(o["deadline_s"]):
                add(on, f"S::{w['window_id']}", 1)
    for w in world["terrestrial_windows"]:
        add(f"T::{w['window_id']}", sink, max(0, int(w["capacity_units"]) - terr_used.get(str(w["window_id"]), 0)))
    for w in bundle["public_environment"]["satellite_windows"]:
        add(f"S::{w['window_id']}", sat_pool, max(0, int(w["capacity_units"]) - sat_used.get(str(w["window_id"]), 0)))
    add(sat_pool, sink, max(0, st.satellite_budget))
    return _maxflow(graph, source, sink) >= len(obligations)


def optimistic_upper(bundle: Mapping[str, Any], at_s: int, states: Mapping[str, LocalState]) -> bool:
    return all(_world_residual_feasible(bundle, at_s, wid, st) for wid, st in states.items())


def causal_upper(bundle: Mapping[str, Any], process: Mapping[str, Any], at_s: int,
                 states: Mapping[str, LocalState], query_budget: int, depth: int,
                 *, metrics: dict[str, int] | None = None, memo=None) -> bool:
    """Safe depth-k non-anticipative upper bound with per-world flow leaves."""
    if memo is None:
        memo = {}
    branches = _normalize(bundle, process, at_s, states)
    if len(branches) != 1 or next(iter(branches)) != "same":
        return all(
            causal_upper(bundle, process, at_s, child, query_budget, depth, metrics=metrics, memo=memo)
            for child in branches.values()
        )
    support = next(iter(branches.values()))
    key = (at_s, query_budget, depth, tuple(sorted(support.items())))
    if key in memo:
        return memo[key]
    if metrics is not None:
        metrics["upper_nodes"] = metrics.get("upper_nodes", 0) + 1
    if any(_expired(bundle, st, at_s) for st in support.values()):
        memo[key] = False; return False
    if all(_success(bundle, st) for st in support.values()):
        memo[key] = True; return True
    if depth <= 0:
        memo[key] = optimistic_upper(bundle, at_s, support)
        return memo[key]
    for action in _legal_actions(bundle, process, support, at_s):
        dq = int(action[0] == "ISSUE_QUERY")
        if dq > query_budget:
            continue
        stepped = _step(bundle, process, support, at_s, action)
        if stepped is None:
            continue
        child, next_t = stepped
        if causal_upper(
            bundle, process, next_t, child, query_budget - dq, depth - 1,
            metrics=metrics, memo=memo,
        ):
            memo[key] = True; return True
    memo[key] = False
    return False


def choice_depth_upper(
    bundle: Mapping[str, Any],
    process: Mapping[str, Any],
    at_s: int,
    states: Mapping[str, LocalState],
    query_budget: int,
    choice_depth: int,
    *,
    metrics: dict[str, int] | None = None,
    memo=None,
) -> bool:
    """Safe non-anticipative upper bound measured in deliberate choice depth.

    WAIT transitions and observation splits do not consume the choice horizon.
    When the horizon is exhausted, per-world optimistic residual flow is used as
    the leaf relaxation. Returning False is therefore still a sound
    infeasibility certificate; returning True is only an upper bound.
    """
    if memo is None:
        memo = {}
    branches = _normalize(bundle, process, at_s, states)
    if len(branches) != 1 or next(iter(branches)) != "same":
        return all(
            choice_depth_upper(
                bundle, process, at_s, child, query_budget, choice_depth,
                metrics=metrics, memo=memo,
            )
            for child in branches.values()
        )
    support = next(iter(branches.values()))
    key = ("choice_upper", at_s, query_budget, choice_depth, tuple(sorted(support.items())))
    if key in memo:
        return memo[key]
    if metrics is not None:
        metrics["choice_upper_nodes"] = metrics.get("choice_upper_nodes", 0) + 1
    if any(_expired(bundle, st, at_s) for st in support.values()):
        memo[key] = False
        return False
    if all(_success(bundle, st) for st in support.values()):
        memo[key] = True
        return True

    # At zero deliberate-choice horizon we still allow passive time progress;
    # only non-WAIT actions are disallowed.  If WAIT is unavailable, fall back
    # to the per-world optimistic flow leaf.
    actions = _legal_actions(bundle, process, support, at_s)
    for action in actions:
        dq = int(action[0] == "ISSUE_QUERY")
        if dq > query_budget:
            continue
        choice_cost = 0 if action[0] == "WAIT" else 1
        if choice_cost > choice_depth:
            continue
        stepped = _step(bundle, process, support, at_s, action)
        if stepped is None:
            continue
        child, next_t = stepped
        if choice_depth_upper(
            bundle,
            process,
            next_t,
            child,
            query_budget - dq,
            choice_depth - choice_cost,
            metrics=metrics,
            memo=memo,
        ):
            memo[key] = True
            return True

    if choice_depth <= 0:
        memo[key] = optimistic_upper(bundle, at_s, support)
        return memo[key]
    memo[key] = False
    return False


def causal_lower_certificate(
    bundle: Mapping[str, Any],
    process: Mapping[str, Any],
    at_s: int,
    states: Mapping[str, LocalState],
    query_budget: int,
    depth: int,
    *,
    metrics: dict[str, int] | None = None,
    memo=None,
) -> dict[str, Any] | None:
    """Sound depth-k causal lower bound with replayable structural leaves.

    OR nodes choose one legal action; observation nodes require a certificate
    for every compatible branch.  Leaves accept only the existing satellite or
    common-opportunity completion certificates.  Failure to find a certificate
    is unresolved, never an infeasibility claim.
    """
    if memo is None:
        memo = {}
    branches = _normalize(bundle, process, at_s, states)
    if len(branches) != 1 or next(iter(branches)) != "same":
        children = []
        for observation, child in sorted(branches.items()):
            sub = causal_lower_certificate(
                bundle, process, at_s, child, query_budget, depth,
                metrics=metrics, memo=memo,
            )
            if sub is None:
                return None
            children.append({
                "observation": observation,
                "worlds": sorted(child),
                "subpolicy": sub,
            })
        return {"time_s": at_s, "event": "OBSERVATION", "children": children}

    support = next(iter(branches.values()))
    key = (at_s, query_budget, depth, tuple(sorted(support.items())))
    if key in memo:
        return deepcopy(memo[key])
    if metrics is not None:
        metrics["lower_nodes"] = metrics.get("lower_nodes", 0) + 1
    if any(_expired(bundle, st, at_s) for st in support.values()):
        memo[key] = None
        return None
    if all(_success(bundle, st) for st in support.values()):
        policy = {"terminal": True}
        memo[key] = policy
        return deepcopy(policy)

    # Cheap complete-tail certificates are valid at every depth, including 0.
    for leaf_name, leaf_fn in (
        ("satellite", satellite_only_certificate),
        ("common", common_opportunity_certificate),
    ):
        if metrics is not None:
            metrics[f"lower_{leaf_name}_attempts"] = metrics.get(f"lower_{leaf_name}_attempts", 0) + 1
        policy = leaf_fn(bundle, at_s, support)
        if policy is not None:
            if metrics is not None:
                metrics[f"lower_{leaf_name}_hits"] = metrics.get(f"lower_{leaf_name}_hits", 0) + 1
            memo[key] = policy
            return deepcopy(policy)

    if depth <= 0:
        memo[key] = None
        return None

    for action in _legal_actions(bundle, process, support, at_s):
        dq = int(action[0] == "ISSUE_QUERY")
        if dq > query_budget:
            continue
        stepped = _step(bundle, process, support, at_s, action)
        if stepped is None:
            continue
        child, next_t = stepped
        sub = causal_lower_certificate(
            bundle, process, next_t, child, query_budget - dq, depth - 1,
            metrics=metrics, memo=memo,
        )
        if sub is None:
            continue
        policy = {
            "time_s": at_s,
            "action": action[0],
            "arg": action[1],
            "worlds": sorted(support),
            "subpolicy": sub,
        }
        memo[key] = policy
        return deepcopy(policy)

    memo[key] = None
    return None


def choice_depth_lower_certificate(
    bundle: Mapping[str, Any],
    process: Mapping[str, Any],
    at_s: int,
    states: Mapping[str, LocalState],
    query_budget: int,
    choice_depth: int,
    *,
    metrics: dict[str, int] | None = None,
    memo=None,
) -> dict[str, Any] | None:
    """Sound causal lower bound where passive WAIT transitions cost zero depth.

    The budget counts deliberate future choices (send/query) rather than raw
    event-lattice depth. Observation splits are AND nodes and likewise do not
    consume choice depth. WAIT must advance time through `_step`, so the search
    remains finite even when depth is unchanged.
    """
    if memo is None:
        memo = {}
    branches = _normalize(bundle, process, at_s, states)
    if len(branches) != 1 or next(iter(branches)) != "same":
        children = []
        for observation, child in sorted(branches.items()):
            sub = choice_depth_lower_certificate(
                bundle, process, at_s, child, query_budget, choice_depth,
                metrics=metrics, memo=memo,
            )
            if sub is None:
                return None
            children.append({
                "observation": observation,
                "worlds": sorted(child),
                "subpolicy": sub,
            })
        return {"time_s": at_s, "event": "OBSERVATION", "children": children}

    support = next(iter(branches.values()))
    key = ("choice", at_s, query_budget, choice_depth, tuple(sorted(support.items())))
    if key in memo:
        return deepcopy(memo[key])
    if metrics is not None:
        metrics["choice_lower_nodes"] = metrics.get("choice_lower_nodes", 0) + 1
    if any(_expired(bundle, st, at_s) for st in support.values()):
        memo[key] = None
        return None
    if all(_success(bundle, st) for st in support.values()):
        policy = {"terminal": True}
        memo[key] = policy
        return deepcopy(policy)

    for leaf_name, leaf_fn in (
        ("satellite", satellite_only_certificate),
        ("common", common_opportunity_certificate),
    ):
        if metrics is not None:
            metrics[f"choice_lower_{leaf_name}_attempts"] = metrics.get(
                f"choice_lower_{leaf_name}_attempts", 0
            ) + 1
        policy = leaf_fn(bundle, at_s, support)
        if policy is not None:
            if metrics is not None:
                metrics[f"choice_lower_{leaf_name}_hits"] = metrics.get(
                    f"choice_lower_{leaf_name}_hits", 0
                ) + 1
            memo[key] = policy
            return deepcopy(policy)

    for action in _legal_actions(bundle, process, support, at_s):
        dq = int(action[0] == "ISSUE_QUERY")
        if dq > query_budget:
            continue
        choice_cost = 0 if action[0] == "WAIT" else 1
        if choice_cost > choice_depth:
            continue
        stepped = _step(bundle, process, support, at_s, action)
        if stepped is None:
            continue
        child, next_t = stepped
        sub = choice_depth_lower_certificate(
            bundle,
            process,
            next_t,
            child,
            query_budget - dq,
            choice_depth - choice_cost,
            metrics=metrics,
            memo=memo,
        )
        if sub is None:
            continue
        policy = {
            "time_s": at_s,
            "action": action[0],
            "arg": action[1],
            "worlds": sorted(support),
            "subpolicy": sub,
        }
        memo[key] = policy
        return deepcopy(policy)

    memo[key] = None
    return None


class LazyActionFeasibility:
    def __init__(self, bundle: Mapping[str, Any], *, mode: str = "witness_domain",
                 use_upper: bool = True, use_lower: bool = False,
                 use_common_lower: bool = False, upper_depth: int = 0,
                 causal_lower_depth: int | None = None,
                 choice_lower_depth: int | None = None,
                 choice_upper_depth: int | None = None,
                 cache_first: bool = False):
        self.bundle = deepcopy(bundle)
        self.planner = ContinuationPlanner(self.bundle, mode=mode)
        self.mode = mode
        self.use_upper = use_upper
        self.use_lower = use_lower
        self.use_common_lower = use_common_lower
        self.upper_depth = upper_depth
        self.causal_lower_depth = causal_lower_depth
        self.choice_lower_depth = choice_lower_depth
        self.choice_upper_depth = choice_upper_depth
        self.cache_first = cache_first
        self.counts = {
            "classified_actions": 0,
            "upper_prunes": 0,
            "upper_nodes": 0,
            "choice_upper_nodes": 0,
            "structural_lower_hits": 0,
            "common_lower_hits": 0,
            "causal_lower_hits": 0,
            "lower_nodes": 0,
            "choice_lower_hits": 0,
            "choice_lower_nodes": 0,
            "certificate_hits": 0,
            "known_failure_hits": 0,
            "exact_fallback_calls": 0,
            "exact_fallback_expanded": 0,
            "search_limits": 0,
        }

    def classify(self, *, at_s: int, states: Mapping[str, LocalState], query_budget: int,
                 action: Action, max_expansions: int = 200_000) -> dict[str, Any]:
        self.counts["classified_actions"] += 1
        dq = int(action[0] == "ISSUE_QUERY")
        if dq > query_budget:
            return {"lower": 0, "upper": 0, "solvable": False, "source": "QUERY_BUDGET_EXHAUSTED"}
        stepped = _step(self.bundle, self.planner.process, states, at_s, action)
        if stepped is None:
            return {"lower": 0, "upper": 0, "solvable": False, "source": "STEP_NOT_EXECUTABLE"}
        child, next_t = stepped
        remaining_q = query_budget - dq

        if self.cache_first:
            probe = self.planner.solve(
                next_t, deepcopy(child), query_budget=remaining_q, max_expansions=0,
            )
            if probe["solvable"] is True:
                verify_witness(self.bundle, next_t, deepcopy(child), probe["policy"], query_budget=remaining_q)
                self.counts["certificate_hits"] += 1
                return {"lower": 1, "upper": 1, "solvable": True, "source": "CERTIFICATE_HIT"}
            if probe["solvable"] is False:
                self.counts["known_failure_hits"] += 1
                return {"lower": 0, "upper": 0, "solvable": False, "source": "KNOWN_FAILURE_HIT"}

        if self.use_upper:
            upper_metrics: dict[str, int] = {}
            if self.choice_upper_depth is not None:
                upper_ok = choice_depth_upper(
                    self.bundle, self.planner.process, next_t, child, remaining_q,
                    self.choice_upper_depth, metrics=upper_metrics,
                )
                self.counts["choice_upper_nodes"] += upper_metrics.get("choice_upper_nodes", 0)
                upper_source = f"CHOICE_UPPER_D{self.choice_upper_depth}"
            else:
                upper_ok = causal_upper(
                    self.bundle, self.planner.process, next_t, child, remaining_q,
                    self.upper_depth, metrics=upper_metrics,
                )
                self.counts["upper_nodes"] += upper_metrics.get("upper_nodes", 0)
                upper_source = f"STRUCTURAL_UPPER_PRUNE_D{self.upper_depth}"
            if not upper_ok:
                self.counts["upper_prunes"] += 1
                return {
                    "lower": 0, "upper": 0, "solvable": False,
                    "source": upper_source,
                }

        if self.use_lower:
            policy = satellite_only_certificate(self.bundle, next_t, child)
            if policy is not None:
                verify_witness(self.bundle, next_t, deepcopy(child), policy, query_budget=remaining_q)
                self.counts["structural_lower_hits"] += 1
                return {"lower": 1, "upper": 1, "solvable": True, "source": "STRUCTURAL_LOWER_SATELLITE"}

        if self.use_common_lower:
            policy = common_opportunity_certificate(self.bundle, next_t, child)
            if policy is not None:
                verify_witness(self.bundle, next_t, deepcopy(child), policy, query_budget=remaining_q)
                self.counts["common_lower_hits"] += 1
                return {"lower": 1, "upper": 1, "solvable": True, "source": "STRUCTURAL_LOWER_COMMON_OPPORTUNITY"}

        if self.causal_lower_depth is not None:
            lower_metrics: dict[str, int] = {}
            policy = causal_lower_certificate(
                self.bundle, self.planner.process, next_t, child, remaining_q,
                self.causal_lower_depth, metrics=lower_metrics,
            )
            self.counts["lower_nodes"] += lower_metrics.get("lower_nodes", 0)
            if policy is not None:
                verify_witness(self.bundle, next_t, deepcopy(child), policy, query_budget=remaining_q)
                self.counts["causal_lower_hits"] += 1
                return {
                    "lower": 1, "upper": 1, "solvable": True,
                    "source": f"CAUSAL_LOWER_D{self.causal_lower_depth}",
                }

        if self.choice_lower_depth is not None:
            choice_metrics: dict[str, int] = {}
            policy = choice_depth_lower_certificate(
                self.bundle,
                self.planner.process,
                next_t,
                child,
                remaining_q,
                self.choice_lower_depth,
                metrics=choice_metrics,
            )
            self.counts["choice_lower_nodes"] += choice_metrics.get("choice_lower_nodes", 0)
            if policy is not None:
                verify_witness(self.bundle, next_t, deepcopy(child), policy, query_budget=remaining_q)
                self.counts["choice_lower_hits"] += 1
                return {
                    "lower": 1, "upper": 1, "solvable": True,
                    "source": f"CHOICE_LOWER_D{self.choice_lower_depth}",
                }

        if not self.cache_first:
            probe = self.planner.solve(next_t, deepcopy(child), query_budget=remaining_q, max_expansions=0)
            if probe["solvable"] is True:
                verify_witness(self.bundle, next_t, deepcopy(child), probe["policy"], query_budget=remaining_q)
                self.counts["certificate_hits"] += 1
                return {"lower": 1, "upper": 1, "solvable": True, "source": "CERTIFICATE_HIT"}
            if probe["solvable"] is False:
                self.counts["known_failure_hits"] += 1
                return {"lower": 0, "upper": 0, "solvable": False, "source": "KNOWN_FAILURE_HIT"}

        self.counts["exact_fallback_calls"] += 1
        exact = self.planner.solve(next_t, deepcopy(child), query_budget=remaining_q, max_expansions=max_expansions)
        self.counts["exact_fallback_expanded"] += int(exact["metrics"]["expanded"])
        if exact["solvable"] is True:
            verify_witness(self.bundle, next_t, deepcopy(child), exact["policy"], query_budget=remaining_q)
            return {"lower": 0, "upper": 1, "solvable": True, "source": "EXACT_FALLBACK_SUCCESS"}
        if exact["solvable"] is False:
            return {"lower": 0, "upper": 1, "solvable": False, "source": "EXACT_FALLBACK_FAILURE"}
        self.counts["search_limits"] += 1
        return {"lower": 0, "upper": 1, "solvable": None, "source": "EXACT_FALLBACK_SEARCH_LIMIT"}

