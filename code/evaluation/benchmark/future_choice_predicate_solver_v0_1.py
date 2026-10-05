#!/usr/bin/env python3
"""Demand-driven future-choice predicate solvers.

Two solvers answer the same predicate on the same causal boundary:

* ``ExactPredicateSolver`` uses the generic exact continuation search with
  early stop for the requested proposition only.
* ``BoundPredicateSolver`` schedules sound L/U proofs on demand and returns
  UNKNOWN when the requested proposition is not proved within the configured
  structural horizons.

Neither solver constructs the full action frontier unless the predicate itself
requires all alternatives to be ruled out.
"""
from __future__ import annotations

from copy import deepcopy
from time import perf_counter
from typing import Any, Mapping

from action_feasibility_bounds_v0_1 import choice_depth_lower_certificate, choice_depth_upper
from causal_evidence_process_v0_1 import attach_causal_evidence
from continuation_resource_domains_v0_1 import ContinuationPlanner, verify_witness
from exact_reference_oracle_v0_1 import LocalState, _normalize
from future_choice_context_compiler_v0_1 import FutureChoiceContextCompiler
from v8_policy_baselines_v0_1 import _legal_actions, _step


Action = tuple[str, str | None]
QUERY: Action = ("ISSUE_QUERY", "gateway_state_summary")
PREDICATES = (
    "CAN_DEFER_QUERY",
    "QUERY_HARMFUL_NOW",
    "QUERY_REQUIRED_NOW",
    "STOP_ACQUISITION",
)


def _akey(action: Action) -> str:
    return f"{action[0]}:{action[1] if action[1] is not None else '-'}"


def _support(bundle, process, at_s: int, states: Mapping[str, LocalState]):
    normalized = _normalize(bundle, process, at_s, states)
    if len(normalized) != 1 or next(iter(normalized)) != "same":
        raise ValueError("predicate solver requires a decision boundary without immediate observation split")
    return next(iter(normalized.values()))


class ExactPredicateSolver:
    """Generic exact search answering one requested predicate at a time."""

    def __init__(self, bundle):
        self.bundle = deepcopy(bundle)
        self.planner = ContinuationPlanner(self.bundle, mode="exact_memo")
        self.process = self.planner.process
        self.totals = {
            "predicate_calls": 0,
            "action_checks": 0,
            "continuation_calls": 0,
            "expanded": 0,
            "wall_s": 0.0,
        }

    def _action_feasible(self, at_s: int, support, query_budget: int, action: Action,
                         max_expansions: int) -> bool | None:
        self.totals["action_checks"] += 1
        dq = int(action[0] == "ISSUE_QUERY")
        if dq > query_budget:
            return False
        stepped = _step(self.bundle, self.process, support, at_s, action)
        if stepped is None:
            return False
        child, next_t = stepped
        self.totals["continuation_calls"] += 1
        result = self.planner.solve(
            next_t, deepcopy(child), query_budget=query_budget - dq,
            max_expansions=max_expansions,
        )
        self.totals["expanded"] += int(result["metrics"]["expanded"])
        if result["solvable"] is True:
            verify_witness(
                self.bundle, next_t, deepcopy(child), result["policy"],
                query_budget=query_budget - dq,
            )
        return result["solvable"]

    def prove(self, predicate: str, *, at_s: int, states: Mapping[str, LocalState],
              query_budget: int, max_expansions: int = 200_000) -> dict[str, Any]:
        if predicate not in PREDICATES:
            raise ValueError(predicate)
        started = perf_counter(); self.totals["predicate_calls"] += 1
        before_actions = self.totals["action_checks"]
        before = dict(self.totals)
        support = _support(self.bundle, self.process, at_s, states)
        actions = _legal_actions(self.bundle, self.process, support, at_s)
        query = QUERY if QUERY in actions else None
        non_query = [a for a in actions if a != QUERY]
        checked: list[str] = []

        def check(action: Action) -> bool | None:
            checked.append(_akey(action))
            return self._action_feasible(at_s, support, query_budget, action, max_expansions)

        value: bool | None
        if predicate == "CAN_DEFER_QUERY":
            unresolved = False; value = False
            for action in non_query:
                ok = check(action)
                if ok is True:
                    value = True; break
                if ok is None:
                    unresolved = True
            else:
                if unresolved:
                    value = None
        elif predicate == "QUERY_HARMFUL_NOW":
            if query is None:
                value = False
            else:
                ok = check(query)
                value = None if ok is None else (not ok)
        elif predicate == "QUERY_REQUIRED_NOW":
            # Cheapest disproof on this distribution is usually a feasible
            # non-query action.  Only when none exists do we prove query itself.
            unresolved_nonquery = False; value = None
            for action in non_query:
                ok = check(action)
                if ok is True:
                    value = False; break
                if ok is None:
                    unresolved_nonquery = True
            else:
                if query is None:
                    value = False
                else:
                    qok = check(query)
                    if qok is False:
                        value = False
                    elif qok is True and not unresolved_nonquery:
                        value = True
                    else:
                        value = None
        else:  # STOP_ACQUISITION
            self.totals["continuation_calls"] += 1
            result = self.planner.solve(
                at_s, deepcopy(support), query_budget=0,
                max_expansions=max_expansions,
            )
            self.totals["expanded"] += int(result["metrics"]["expanded"])
            if result["solvable"] is True:
                verify_witness(self.bundle, at_s, deepcopy(support), result["policy"], query_budget=0)
            value = result["solvable"]

        elapsed = perf_counter() - started; self.totals["wall_s"] += elapsed
        return {
            "predicate": predicate,
            "value": value,
            "status": "PROVED" if value is not None else "UNRESOLVED",
            "checked_action_keys": checked,
            "action_checks": self.totals["action_checks"] - before["action_checks"],
            "continuation_calls": self.totals["continuation_calls"] - before["continuation_calls"],
            "expanded": self.totals["expanded"] - before["expanded"],
            "wall_s": elapsed,
        }


class ProgressiveBoundPredicateSolver:
    """Predicate-aware iterative proof scheduler.

    The previous bound solver immediately pays the configured maximum U/L
    horizon for every checked action.  This scheduler instead asks for the
    cheapest proof of the requested proposition and deepens only while the
    result remains unresolved.  Upper and lower proof memos persist across
    successive boundaries of the same case.
    """

    def __init__(
        self,
        bundle,
        *,
        upper_depths: tuple[int, ...] = (0, 1, 2, 3, 4),
        lower_depths: tuple[int, ...] = (0, 1, 2, 3, 4, 6),
    ):
        self.bundle = deepcopy(bundle)
        self.process = attach_causal_evidence(self.bundle)
        self.upper_depths = upper_depths
        self.lower_depths = lower_depths
        self.upper_memo: dict[Any, bool] = {}
        self.lower_memo: dict[Any, dict[str, Any] | None] = {}
        self.totals = {
            "predicate_calls": 0,
            "action_checks": 0,
            "upper_nodes": 0,
            "lower_nodes": 0,
            "wall_s": 0.0,
        }

    def _child(self, at_s: int, states, query_budget: int, action: Action):
        self.totals["action_checks"] += 1
        dq = int(action[0] == "ISSUE_QUERY")
        if dq > query_budget:
            return None, None, None
        stepped = _step(self.bundle, self.process, states, at_s, action)
        if stepped is None:
            return None, None, None
        child, next_t = stepped
        return child, next_t, query_budget - dq

    def _prove_impossible(self, next_t: int, child, qleft: int) -> tuple[bool | None, dict[str, Any]]:
        nodes = 0; tried = []
        for depth in self.upper_depths:
            metrics: dict[str, int] = {}
            upper_ok = choice_depth_upper(
                self.bundle, self.process, next_t, deepcopy(child), qleft, depth,
                metrics=metrics, memo=self.upper_memo,
            )
            n = int(metrics.get("choice_upper_nodes", 0)); nodes += n
            self.totals["upper_nodes"] += n; tried.append(depth)
            if not upper_ok:
                return True, {"upper_nodes": nodes, "upper_depths_tried": tried, "proof_depth": depth}
        return None, {"upper_nodes": nodes, "upper_depths_tried": tried, "proof_depth": None}

    def _prove_feasible(self, next_t: int, child, qleft: int) -> tuple[bool | None, dict[str, Any]]:
        nodes = 0; tried = []
        for depth in self.lower_depths:
            metrics: dict[str, int] = {}
            policy = choice_depth_lower_certificate(
                self.bundle, self.process, next_t, deepcopy(child), qleft, depth,
                metrics=metrics, memo=self.lower_memo,
            )
            n = int(metrics.get("choice_lower_nodes", 0)); nodes += n
            self.totals["lower_nodes"] += n; tried.append(depth)
            if policy is not None:
                verify_witness(self.bundle, next_t, deepcopy(child), policy, query_budget=qleft)
                return True, {"lower_nodes": nodes, "lower_depths_tried": tried, "proof_depth": depth}
        return None, {"lower_nodes": nodes, "lower_depths_tried": tried, "proof_depth": None}

    def _action_impossible(self, at_s: int, support, query_budget: int, action: Action):
        child, next_t, qleft = self._child(at_s, support, query_budget, action)
        if child is None:
            return True, {"upper_nodes": 0, "upper_depths_tried": [], "proof_depth": "LEGALITY"}
        return self._prove_impossible(next_t, child, qleft)

    def _action_feasible(self, at_s: int, support, query_budget: int, action: Action):
        child, next_t, qleft = self._child(at_s, support, query_budget, action)
        if child is None:
            return False, {"lower_nodes": 0, "lower_depths_tried": [], "proof_depth": "LEGALITY"}
        return self._prove_feasible(next_t, child, qleft)

    def _stop_impossible(self, at_s: int, support):
        return self._prove_impossible(at_s, support, 0)

    def _stop_feasible(self, at_s: int, support):
        return self._prove_feasible(at_s, support, 0)

    def prove(self, predicate: str, *, at_s: int, states: Mapping[str, LocalState],
              query_budget: int) -> dict[str, Any]:
        if predicate not in PREDICATES:
            raise ValueError(predicate)
        started = perf_counter(); self.totals["predicate_calls"] += 1
        before_actions = self.totals["action_checks"]
        before_upper = self.totals["upper_nodes"]
        before_lower = self.totals["lower_nodes"]
        support = _support(self.bundle, self.process, at_s, states)
        actions = _legal_actions(self.bundle, self.process, support, at_s)
        query = QUERY if QUERY in actions else None
        non_query = [a for a in actions if a != QUERY]
        checked: list[str] = []
        proof_trace: list[dict[str, Any]] = []

        value: bool | None = None
        if predicate == "CAN_DEFER_QUERY":
            # Existential positive: search shallow replayable witnesses first.
            for action in non_query:
                checked.append(_akey(action))
                ok, meta = self._action_feasible(at_s, support, query_budget, action)
                proof_trace.append({"action_key": _akey(action), "direction": "LOWER", **meta})
                if ok is True:
                    value = True; break
            else:
                # To prove False every legal non-query alternative must be impossible.
                all_impossible = True
                for action in non_query:
                    ok, meta = self._action_impossible(at_s, support, query_budget, action)
                    proof_trace.append({"action_key": _akey(action), "direction": "UPPER", **meta})
                    if ok is not True:
                        all_impossible = False; break
                if all_impossible:
                    value = False

        elif predicate == "QUERY_HARMFUL_NOW":
            if query is None:
                value = False
            else:
                checked.append(_akey(query))
                bad, meta = self._action_impossible(at_s, support, query_budget, query)
                proof_trace.append({"action_key": _akey(query), "direction": "UPPER", **meta})
                if bad is True:
                    value = True
                else:
                    good, meta = self._action_feasible(at_s, support, query_budget, query)
                    proof_trace.append({"action_key": _akey(query), "direction": "LOWER", **meta})
                    if good is True:
                        value = False

        elif predicate == "QUERY_REQUIRED_NOW":
            # Cheapest disproof is a single certified non-query action.
            for action in non_query:
                checked.append(_akey(action))
                good, meta = self._action_feasible(at_s, support, query_budget, action)
                proof_trace.append({"action_key": _akey(action), "direction": "LOWER", **meta})
                if good is True:
                    value = False; break
            else:
                all_impossible = True
                for action in non_query:
                    bad, meta = self._action_impossible(at_s, support, query_budget, action)
                    proof_trace.append({"action_key": _akey(action), "direction": "UPPER", **meta})
                    if bad is not True:
                        all_impossible = False; break
                if all_impossible:
                    if query is None:
                        value = False
                    else:
                        checked.append(_akey(query))
                        good, meta = self._action_feasible(at_s, support, query_budget, query)
                        proof_trace.append({"action_key": _akey(query), "direction": "LOWER", **meta})
                        if good is True:
                            value = True
                        else:
                            bad, meta = self._action_impossible(at_s, support, query_budget, query)
                            proof_trace.append({"action_key": _akey(query), "direction": "UPPER", **meta})
                            if bad is True:
                                value = False

        else:  # STOP_ACQUISITION
            # On the current hard-test distribution stop=False dominates, so
            # prove impossibility first; only then search a zero-query witness.
            bad, meta = self._stop_impossible(at_s, support)
            proof_trace.append({"direction": "UPPER", **meta})
            if bad is True:
                value = False
            else:
                good, meta = self._stop_feasible(at_s, support)
                proof_trace.append({"direction": "LOWER", **meta})
                if good is True:
                    value = True

        elapsed = perf_counter() - started; self.totals["wall_s"] += elapsed
        return {
            "predicate": predicate,
            "value": value,
            "status": "PROVED" if value is not None else "UNRESOLVED",
            "checked_action_keys": checked,
            "action_checks": self.totals["action_checks"] - before_actions,
            "upper_nodes": self.totals["upper_nodes"] - before_upper,
            "lower_nodes": self.totals["lower_nodes"] - before_lower,
            "proof_trace": proof_trace,
            "wall_s": elapsed,
        }


class BoundPredicateSolver:
    """Demand-driven structural L/U proof scheduler with persistent memos."""

    def __init__(self, bundle, *, choice_upper_depth: int = 4, choice_lower_depth: int = 6):
        self.bundle = deepcopy(bundle)
        self.compiler = FutureChoiceContextCompiler(
            self.bundle,
            choice_upper_depth=choice_upper_depth,
            choice_lower_depth=choice_lower_depth,
        )
        self.process = self.compiler.process
        self.choice_upper_depth = choice_upper_depth
        self.choice_lower_depth = choice_lower_depth
        self.totals = {
            "predicate_calls": 0,
            "action_checks": 0,
            "upper_nodes": 0,
            "lower_nodes": 0,
            "wall_s": 0.0,
        }

    def _bound(self, at_s: int, support, query_budget: int, action: Action) -> dict[str, Any]:
        self.totals["action_checks"] += 1
        row = self.compiler._bound_action(  # shared proof memos are intentional
            at_s=at_s, states=support, query_budget=query_budget, action=action,
        )
        self.totals["upper_nodes"] += int(row.get("upper_nodes", 0))
        self.totals["lower_nodes"] += int(row.get("lower_nodes", 0))
        return row

    def _stop_bound(self, at_s: int, support) -> tuple[bool | None, dict[str, int]]:
        lm: dict[str, int] = {}
        policy = choice_depth_lower_certificate(
            self.bundle, self.process, at_s, deepcopy(support), 0,
            self.choice_lower_depth, metrics=lm, memo=self.compiler.lower_memo,
        )
        lnodes = int(lm.get("choice_lower_nodes", 0)); self.totals["lower_nodes"] += lnodes
        if policy is not None:
            verify_witness(self.bundle, at_s, deepcopy(support), policy, query_budget=0)
            return True, {"upper_nodes": 0, "lower_nodes": lnodes}
        um: dict[str, int] = {}
        upper = choice_depth_upper(
            self.bundle, self.process, at_s, deepcopy(support), 0,
            self.choice_upper_depth, metrics=um, memo=self.compiler.upper_memo,
        )
        unodes = int(um.get("choice_upper_nodes", 0)); self.totals["upper_nodes"] += unodes
        return (None if upper else False), {"upper_nodes": unodes, "lower_nodes": lnodes}

    def prove(self, predicate: str, *, at_s: int, states: Mapping[str, LocalState],
              query_budget: int) -> dict[str, Any]:
        if predicate not in PREDICATES:
            raise ValueError(predicate)
        started = perf_counter(); self.totals["predicate_calls"] += 1
        before_actions = self.totals["action_checks"]
        support = _support(self.bundle, self.process, at_s, states)
        actions = _legal_actions(self.bundle, self.process, support, at_s)
        query = QUERY if QUERY in actions else None
        non_query = [a for a in actions if a != QUERY]
        checked: list[str] = []; local_u = 0; local_l = 0

        def bound(action: Action) -> dict[str, Any]:
            nonlocal local_u, local_l
            checked.append(_akey(action)); row = self._bound(at_s, support, query_budget, action)
            local_u += int(row.get("upper_nodes", 0)); local_l += int(row.get("lower_nodes", 0))
            return row

        value: bool | None
        if predicate == "CAN_DEFER_QUERY":
            unknown = False; value = False
            for action in non_query:
                row = bound(action)
                if row["status"] == "CERTIFIED": value = True; break
                if row["status"] == "UNKNOWN": unknown = True
            else:
                if unknown: value = None
        elif predicate == "QUERY_HARMFUL_NOW":
            if query is None: value = False
            else:
                row = bound(query)
                value = True if row["status"] == "IMPOSSIBLE" else False if row["status"] == "CERTIFIED" else None
        elif predicate == "QUERY_REQUIRED_NOW":
            unknown_nonquery = False; value = None
            for action in non_query:
                row = bound(action)
                if row["status"] == "CERTIFIED": value = False; break
                if row["status"] == "UNKNOWN": unknown_nonquery = True
            else:
                if query is None: value = False
                else:
                    qrow = bound(query)
                    if qrow["status"] == "IMPOSSIBLE": value = False
                    elif qrow["status"] == "CERTIFIED" and not unknown_nonquery: value = True
                    else: value = None
        else:
            value, cost = self._stop_bound(at_s, support)
            local_u += cost["upper_nodes"]; local_l += cost["lower_nodes"]

        elapsed = perf_counter() - started; self.totals["wall_s"] += elapsed
        return {
            "predicate": predicate,
            "value": value,
            "status": "PROVED" if value is not None else "UNRESOLVED",
            "checked_action_keys": checked,
            "action_checks": self.totals["action_checks"] - before_actions,
            "upper_nodes": local_u,
            "lower_nodes": local_l,
            "wall_s": elapsed,
        }
