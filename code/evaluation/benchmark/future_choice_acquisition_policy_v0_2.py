#!/usr/bin/env python3
"""Closed-loop acquisition policies with a shared exact non-query task selector.

The experiment isolates acquisition timing: all variants use the same exact
future-choice frontier to choose among non-query task actions.  They differ only
in whether/when they spend the paid owner query.
"""
from __future__ import annotations

from copy import deepcopy
from time import perf_counter
from typing import Any, Mapping

from causal_evidence_process_v0_1 import attach_causal_evidence
from conditional_action_frontier_v0_1 import build_action_frontier
from continuation_resource_domains_v0_1 import verify_witness
from exact_reference_oracle_v0_1 import LocalState, _expired, _normalize, _success
from future_choice_bound_controller_v0_1 import bound_future_choice_context
from v8_policy_baselines_v0_1 import _legal_actions, _step


QUERY = ("ISSUE_QUERY", "gateway_state_summary")
POLICIES = (
    "NO_QUERY",
    "EARLIEST_LEGAL_QUERY",
    "EXACT_FUTURE_CHOICE",
    "BOUND_FUTURE_CHOICE",
)


def _akey(action) -> str:
    return f"{action[0]}:{action[1] if action[1] is not None else '-'}"


def _action_from_key(key: str):
    kind, arg = key.split(":", 1)
    return kind, None if arg == "-" else arg


class AcquisitionPolicyBuilder:
    def __init__(self, bundle: Mapping[str, Any], *, policy: str,
                 choice_upper_depth: int = 4, choice_lower_depth: int = 6,
                 max_expansions: int = 200_000):
        if policy not in POLICIES:
            raise ValueError(policy)
        self.bundle = deepcopy(bundle)
        self.process = attach_causal_evidence(self.bundle)
        self.policy = policy
        self.choice_upper_depth = choice_upper_depth
        self.choice_lower_depth = choice_lower_depth
        self.max_expansions = max_expansions
        self.metrics = {
            "decision_boundaries": 0,
            "query_actions": 0,
            "harmful_query_actions": 0,
            "controller_unresolved": 0,
            "controller_soundness_errors": 0,
            "task_selector_wall_s": 0.0,
            "acquisition_controller_wall_s": 0.0,
        }
        self.query_times_s: list[int] = []

    def _choose(self, t: int, support: Mapping[str, LocalState], qleft: int):
        self.metrics["decision_boundaries"] += 1
        exact_t0 = perf_counter()
        frontier = build_action_frontier(
            self.bundle, at_s=t, states=deepcopy(support), query_budget=qleft,
            max_expansions=self.max_expansions,
        )
        self.metrics["task_selector_wall_s"] += perf_counter() - exact_t0
        legal = _legal_actions(self.bundle, self.process, support, t)
        cert = set(frontier["certified_action_keys"])
        qkey = _akey(QUERY)
        non_query = [a for a in legal if a != QUERY and _akey(a) in cert]

        def first_non_query():
            return non_query[0] if non_query else None

        if self.policy == "NO_QUERY":
            return first_non_query(), frontier, None

        if self.policy == "EARLIEST_LEGAL_QUERY":
            if QUERY in legal and qleft > 0:
                return QUERY, frontier, None
            return first_non_query(), frontier, None

        if self.policy == "EXACT_FUTURE_CHOICE":
            if frontier["context"]["query_is_only_certified_next_action"]:
                return QUERY, frontier, None
            action = first_non_query()
            if action is not None:
                return action, frontier, None
            if qkey in cert:
                return QUERY, frontier, None
            return None, frontier, "NO_CERTIFIED_ACTION"

        ctrl_t0 = perf_counter()
        bounded = bound_future_choice_context(
            self.bundle,
            at_s=t,
            states=deepcopy(support),
            query_budget=qleft,
            choice_upper_depth=self.choice_upper_depth,
            choice_lower_depth=self.choice_lower_depth,
        )
        self.metrics["acquisition_controller_wall_s"] += perf_counter() - ctrl_t0
        labels = set(bounded["labels"])

        # Evaluation-only soundness checks. They do not alter the bound policy.
        if "QUERY_HARMFUL_NOW" in labels and qkey in cert:
            self.metrics["controller_soundness_errors"] += 1
        if "CAN_DEFER_QUERY" in labels and not non_query:
            self.metrics["controller_soundness_errors"] += 1
        if "QUERY_REQUIRED_NOW" in labels and (qkey not in cert or non_query):
            self.metrics["controller_soundness_errors"] += 1
        if "STOP_ACQUISITION_CERTIFIED" in labels and not frontier["context"]["query_free_completion"]:
            self.metrics["controller_soundness_errors"] += 1

        if "QUERY_REQUIRED_NOW" in labels:
            return QUERY if QUERY in legal and qleft > 0 else None, frontier, None
        if "QUERY_HARMFUL_NOW" in labels or "CAN_DEFER_QUERY" in labels or "STOP_ACQUISITION_CERTIFIED" in labels:
            action = first_non_query()
            if action is not None:
                return action, frontier, None
        self.metrics["controller_unresolved"] += 1
        return None, frontier, "CONTROLLER_UNRESOLVED"

    def build(self, *, at_s: int, states: Mapping[str, LocalState], query_budget: int):
        seen = set()

        def rec(t: int, support: Mapping[str, LocalState], qleft: int, depth: int):
            if depth > 1024:
                return None, "STEP_LIMIT"
            branches = _normalize(self.bundle, self.process, t, support)
            if len(branches) != 1 or next(iter(branches)) != "same":
                children = []
                for obs, child in sorted(branches.items()):
                    sub, err = rec(t, child, qleft, depth + 1)
                    if sub is None:
                        return None, err
                    children.append({"observation": obs, "worlds": sorted(child), "subpolicy": sub})
                return {"time_s": t, "event": "OBSERVATION", "children": children}, None
            support = next(iter(branches.values()))
            if any(_expired(self.bundle, st, t) for st in support.values()):
                return None, "EXPIRED"
            if all(_success(self.bundle, st) for st in support.values()):
                return {"terminal": True}, None

            state_key = (t, qleft, tuple(sorted(support.items())))
            if state_key in seen:
                return None, "POLICY_CYCLE"
            seen.add(state_key)
            action, frontier, err = self._choose(t, support, qleft)
            if action is None:
                return None, err or "NO_ACTION"
            if action == QUERY:
                self.metrics["query_actions"] += 1
                self.query_times_s.append(t)
                if _akey(QUERY) not in set(frontier["certified_action_keys"]):
                    self.metrics["harmful_query_actions"] += 1
            dq = int(action == QUERY)
            if dq > qleft:
                return None, "QUERY_BUDGET_EXHAUSTED"
            stepped = _step(self.bundle, self.process, support, t, action)
            if stepped is None:
                return None, "STEP_NOT_EXECUTABLE"
            child, nt = stepped
            sub, sub_err = rec(nt, child, qleft - dq, depth + 1)
            if sub is None:
                return None, sub_err
            return {
                "time_s": t,
                "action": action[0],
                "arg": action[1],
                "worlds": sorted(support),
                "subpolicy": sub,
            }, None

        policy, error = rec(at_s, dict(states), query_budget, 0)
        requirement = None
        if policy is not None:
            requirement = verify_witness(
                self.bundle, at_s, dict(states), policy, query_budget=query_budget,
            )
        return {
            "status": "SUCCESS" if policy is not None else "FAIL",
            "failure_reason": error,
            "policy": policy,
            "requirement": requirement,
            "query_times_s": list(self.query_times_s),
            "metrics": dict(self.metrics),
        }
