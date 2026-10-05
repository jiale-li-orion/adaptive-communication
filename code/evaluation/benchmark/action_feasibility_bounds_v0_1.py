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
    _world_map,
)
from v8_policy_baselines_v0_1 import _step
from structural_lower_certificate_v0_1 import satellite_only_certificate


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


class LazyActionFeasibility:
    def __init__(self, bundle: Mapping[str, Any], *, mode: str = "witness_domain",
                 use_upper: bool = True, use_lower: bool = False):
        self.bundle = deepcopy(bundle)
        self.planner = ContinuationPlanner(self.bundle, mode=mode)
        self.mode = mode
        self.use_upper = use_upper
        self.use_lower = use_lower
        self.counts = {
            "classified_actions": 0,
            "upper_prunes": 0,
            "structural_lower_hits": 0,
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

        if self.use_upper and not optimistic_upper(self.bundle, next_t, child):
            self.counts["upper_prunes"] += 1
            return {"lower": 0, "upper": 0, "solvable": False, "source": "STRUCTURAL_UPPER_PRUNE"}

        if self.use_lower:
            policy = satellite_only_certificate(self.bundle, next_t, child)
            if policy is not None:
                verify_witness(self.bundle, next_t, deepcopy(child), policy, query_budget=remaining_q)
                self.counts["structural_lower_hits"] += 1
                return {"lower": 1, "upper": 1, "solvable": True, "source": "STRUCTURAL_LOWER_SATELLITE"}

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

