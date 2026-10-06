#!/usr/bin/env python3
"""Dynamic conditional Q×B future-choice frontier for Layer-2 v2.

Q is remaining paid owner-query budget; B is remaining satellite fallback
budget.  For one reached causal execution/evidence boundary the frontier stores
which integer resource cells still admit a non-anticipative completion policy.

The representation is monotone and certificate-backed:

* a replayable successful policy at (q,b) certifies every (q'>=q,b'>=b);
* an exact failure at (q,b) certifies every (q'<=q,b'<=b) as failure;
* cells not covered by either antichain fall back to the same-information exact
  L/U kernel and immediately extend the corresponding validity domain.

This is the information-resource layer that the purely physical conflict
frontier cannot express: a query can leave perfect-information delivery
feasible while exhausting the only paid-query opportunity needed later.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from typing import Any, Mapping

from causal_evidence_process_v0_1 import attach_causal_evidence
from exact_reference_oracle_v0_1 import LocalState, _normalize
from layer2_v2_persistent_frontier import (
    ConditionalCertificate,
    PersistentFutureChoiceFrontier,
    _boundary_core,
    _boundary_digest,
)
from v8_policy_baselines_v0_1 import _legal_actions, _step


Action = tuple[str, str | None]


def _common_satellite_budget(states: Mapping[str, LocalState]) -> int:
    values = {int(state.satellite_budget) for state in states.values()}
    if not states or len(values) != 1:
        raise ValueError("conditional frontier requires one common remaining satellite budget")
    return next(iter(values))


def _with_satellite_budget(
    states: Mapping[str, LocalState],
    satellite_budget: int,
) -> dict[str, LocalState]:
    return {
        str(world_id): replace(state, satellite_budget=int(satellite_budget))
        for world_id, state in states.items()
    }


@dataclass(frozen=True)
class ResourceCell:
    query_budget: int
    satellite_budget: int
    solvable: bool
    source: str
    certificate_id: str | None = None


@dataclass(frozen=True)
class ConditionalResourceFrontier:
    boundary_digest: str
    at_s: int
    qmax: int
    bmax: int
    cells: tuple[ResourceCell, ...]
    pareto_success: tuple[tuple[int, int], ...]
    maximal_failure: tuple[tuple[int, int], ...]
    minimum_query_budget_for_any_success: int | None
    minimum_satellite_budget_without_paid_query: int | None
    minimum_satellite_budget_with_query_allowed: int | None
    evidence_gain_type: str

    def feasible(self, query_budget: int, satellite_budget: int) -> bool:
        row = next(
            cell
            for cell in self.cells
            if cell.query_budget == int(query_budget)
            and cell.satellite_budget == int(satellite_budget)
        )
        return row.solvable


def _pareto_minimal(points: list[tuple[int, int]]) -> tuple[tuple[int, int], ...]:
    rows = []
    for q, b in sorted(set(points)):
        if any(q2 <= q and b2 <= b and (q2 < q or b2 < b) for q2, b2 in points):
            continue
        rows.append((q, b))
    return tuple(rows)


def _maximal_failures(points: list[tuple[int, int]]) -> tuple[tuple[int, int], ...]:
    rows = []
    for q, b in sorted(set(points)):
        if any(q2 >= q and b2 >= b and (q2 > q or b2 > b) for q2, b2 in points):
            continue
        rows.append((q, b))
    return tuple(rows)


class ConditionalResourceFrontierRuntime:
    """Persistent Q×B antichain runtime over causal decision boundaries."""

    def __init__(
        self,
        bundle: Mapping[str, Any],
        *,
        upper_mode: str = "all_recursive",
        use_lower: bool = True,
    ):
        self.bundle = deepcopy(bundle)
        self.process = attach_causal_evidence(self.bundle)
        self.success = PersistentFutureChoiceFrontier(
            self.bundle,
            upper_mode=upper_mode,
            use_lower=use_lower,
        )
        # Maximal exact-failure points indexed by the non-resource boundary.
        self._failure_domains: dict[str, list[tuple[int, int]]] = {}
        self.metrics = {
            "cell_queries": 0,
            "success_domain_hits": 0,
            "failure_domain_hits": 0,
            "exact_cell_fallbacks": 0,
            "exact_fallback_expanded": 0,
            "exact_fallback_wall_s": 0.0,
            "success_cells_learned": 0,
            "failure_cells_learned": 0,
        }

    def _normalized_support(
        self,
        *,
        at_s: int,
        states: Mapping[str, LocalState],
    ) -> dict[str, LocalState]:
        branches = _normalize(self.bundle, self.process, at_s, states)
        if len(branches) != 1 or next(iter(branches)) != "same":
            raise ValueError("conditional resource frontier requires a normalized decision boundary")
        return dict(next(iter(branches.values())))

    def _key(self, *, at_s: int, states: Mapping[str, LocalState]) -> tuple[str, tuple[Any, ...]]:
        core = _boundary_core(at_s, states)
        return _boundary_digest(core), core

    def _failure_hit(self, digest: str, q: int, b: int) -> bool:
        return any(q <= q0 and b <= b0 for q0, b0 in self._failure_domains.get(digest, ()))

    def _record_failure(self, digest: str, q: int, b: int) -> None:
        rows = self._failure_domains.setdefault(digest, [])
        if any(q <= q0 and b <= b0 for q0, b0 in rows):
            return
        rows[:] = [
            (q0, b0)
            for q0, b0 in rows
            if not (q0 <= q and b0 <= b)
        ]
        rows.append((int(q), int(b)))
        self.metrics["failure_cells_learned"] += 1

    def evaluate_cell(
        self,
        *,
        at_s: int,
        states: Mapping[str, LocalState],
        query_budget: int,
        satellite_budget: int,
        max_expansions: int = 200_000,
    ) -> ResourceCell:
        if query_budget < 0 or satellite_budget < 0:
            return ResourceCell(query_budget, satellite_budget, False, "negative-resource")
        support = self._normalized_support(at_s=at_s, states=states)
        cell_states = _with_satellite_budget(support, satellite_budget)
        digest, _core = self._key(at_s=at_s, states=cell_states)
        self.metrics["cell_queries"] += 1

        certificate = self.success.lookup_certificate(
            at_s=at_s,
            states=cell_states,
            query_budget=query_budget,
        )
        if certificate is not None:
            self.metrics["success_domain_hits"] += 1
            return ResourceCell(
                int(query_budget),
                int(satellite_budget),
                True,
                "success-domain",
                certificate.certificate_id,
            )

        if self._failure_hit(digest, int(query_budget), int(satellite_budget)):
            self.metrics["failure_domain_hits"] += 1
            return ResourceCell(
                int(query_budget),
                int(satellite_budget),
                False,
                "failure-domain",
            )

        self.metrics["exact_cell_fallbacks"] += 1
        result = self.success.ensure(
            at_s=at_s,
            states=cell_states,
            query_budget=query_budget,
            max_expansions=max_expansions,
        )
        kernel = result.get("kernel")
        if kernel is not None:
            km = kernel.get("metrics", {})
            self.metrics["exact_fallback_expanded"] += int(km.get("expanded", 0))
            self.metrics["exact_fallback_wall_s"] += float(km.get("wall_s", 0.0))
        if result["solvable"] is True:
            self.metrics["success_cells_learned"] += 1
            certificate = result["certificate"]
            return ResourceCell(
                int(query_budget),
                int(satellite_budget),
                True,
                "exact-success",
                None if certificate is None else certificate.certificate_id,
            )
        if result["solvable"] is False:
            self._record_failure(digest, int(query_budget), int(satellite_budget))
            return ResourceCell(
                int(query_budget),
                int(satellite_budget),
                False,
                "exact-failure",
            )
        raise RuntimeError("conditional frontier cell hit exact search limit")

    def evaluate_continuation_cell(
        self,
        *,
        at_s: int,
        states: Mapping[str, LocalState],
        query_budget: int,
        satellite_budget: int,
    ) -> dict[str, Any]:
        """Evaluate a resource cell even when an observation arrives immediately.

        A post-action boundary may normalize directly into multiple observable
        branches.  The causal continuation is feasible only when every branch
        is feasible with the same remaining resource coordinates.
        """

        branches = _normalize(self.bundle, self.process, at_s, states)
        if len(branches) == 1 and next(iter(branches)) == "same":
            cell = self.evaluate_cell(
                at_s=at_s,
                states=next(iter(branches.values())),
                query_budget=query_budget,
                satellite_budget=satellite_budget,
            )
            return {
                "solvable": cell.solvable,
                "source": cell.source,
                "branch_count": 1,
            }

        rows = []
        for observation, child in sorted(branches.items()):
            cell = self.evaluate_cell(
                at_s=at_s,
                states=child,
                query_budget=query_budget,
                satellite_budget=satellite_budget,
            )
            rows.append((observation, cell))
        solvable = all(cell.solvable for _observation, cell in rows)
        sources = sorted({cell.source for _observation, cell in rows})
        return {
            "solvable": solvable,
            "source": "observation-and:" + "+".join(sources),
            "branch_count": len(rows),
        }

    def build_frontier(
        self,
        *,
        at_s: int,
        states: Mapping[str, LocalState],
        qmax: int,
        bmax: int | None = None,
    ) -> ConditionalResourceFrontier:
        support = self._normalized_support(at_s=at_s, states=states)
        if bmax is None:
            bmax = _common_satellite_budget(support)
        if qmax < 0 or bmax < 0:
            raise ValueError("negative frontier rectangle")
        digest, _ = self._key(at_s=at_s, states=support)

        # Search from resource-rich to poor.  A rich exact success immediately
        # yields an upward success domain; later poorer successes tighten the
        # Pareto frontier.  Exact failures create downward antichains.
        cells: dict[tuple[int, int], ResourceCell] = {}
        for q in range(int(qmax), -1, -1):
            for b in range(int(bmax), -1, -1):
                cells[(q, b)] = self.evaluate_cell(
                    at_s=at_s,
                    states=support,
                    query_budget=q,
                    satellite_budget=b,
                )

        success_points = [point for point, row in cells.items() if row.solvable]
        failure_points = [point for point, row in cells.items() if not row.solvable]
        pareto = _pareto_minimal(success_points)
        failures = _maximal_failures(failure_points)
        no_query_sat = min((b for q, b in success_points if q == 0), default=None)
        any_sat = min((b for _q, b in success_points), default=None)
        min_query = min((q for q, _b in success_points), default=None)
        if not success_points:
            gain = "UNSOLVABLE_IN_RECTANGLE"
        elif no_query_sat is None:
            gain = "INFORMATION_FEASIBILITY_GAIN"
        elif any_sat is not None and any_sat < no_query_sat:
            gain = "INFORMATION_RESOURCE_GAIN"
        else:
            gain = "NO_INFORMATION_GAIN_IN_RECTANGLE"

        return ConditionalResourceFrontier(
            boundary_digest=digest,
            at_s=int(at_s),
            qmax=int(qmax),
            bmax=int(bmax),
            cells=tuple(cells[key] for key in sorted(cells)),
            pareto_success=pareto,
            maximal_failure=failures,
            minimum_query_budget_for_any_success=min_query,
            minimum_satellite_budget_without_paid_query=no_query_sat,
            minimum_satellite_budget_with_query_allowed=any_sat,
            evidence_gain_type=gain,
        )

    def classify_acquisition(
        self,
        *,
        at_s: int,
        states: Mapping[str, LocalState],
        query_budget: int,
    ) -> dict[str, Any]:
        """Classify the current gateway query relative to future feasibility."""

        support = self._normalized_support(at_s=at_s, states=states)
        sat_budget = _common_satellite_budget(support)
        current = self.evaluate_cell(
            at_s=at_s,
            states=support,
            query_budget=query_budget,
            satellite_budget=sat_budget,
        )
        no_more_query = self.evaluate_cell(
            at_s=at_s,
            states=support,
            query_budget=0,
            satellite_budget=sat_budget,
        )

        query: Action = ("ISSUE_QUERY", "gateway_state_summary")
        legal = query in _legal_actions(self.bundle, self.process, support, at_s)
        query_safe = None
        child_source = None
        if legal and query_budget > 0:
            stepped = _step(self.bundle, self.process, support, at_s, query)
            if stepped is None:
                raise AssertionError("legal query cannot be stepped")
            child, next_t = stepped
            child_cell = self.evaluate_continuation_cell(
                at_s=next_t,
                states=child,
                query_budget=query_budget - 1,
                satellite_budget=sat_budget,
            )
            query_safe = bool(child_cell["solvable"])
            child_source = str(child_cell["source"])

        non_query_safe_actions: list[str] = []
        for action in _legal_actions(self.bundle, self.process, support, at_s):
            if action[0] == "ISSUE_QUERY":
                continue
            stepped = _step(self.bundle, self.process, support, at_s, action)
            if stepped is None:
                continue
            child, next_t = stepped
            cell = self.evaluate_continuation_cell(
                at_s=next_t,
                states=child,
                query_budget=query_budget,
                satellite_budget=sat_budget - int(action[0] == "SEND_SAT"),
            )
            if cell["solvable"]:
                non_query_safe_actions.append(
                    f"{action[0]}:{action[1] if action[1] is not None else '-'}"
                )

        labels: list[str] = []
        if no_more_query.solvable:
            labels.append("STOP_ACQUISITION_FOR_FEASIBILITY")
        if legal and query_safe is False:
            labels.append("QUERY_HARMFUL_NOW")
        if legal and query_safe is True and not non_query_safe_actions:
            labels.append("QUERY_REQUIRED_NOW")
        if non_query_safe_actions:
            labels.append("CAN_DEFER_QUERY")
        if not labels:
            labels.append("UNRESOLVED")
        return {
            "time_s": int(at_s),
            "query_budget": int(query_budget),
            "satellite_budget": int(sat_budget),
            "current_feasible": current.solvable,
            "query_legal": legal,
            "query_safe": query_safe,
            "query_child_source": child_source,
            "non_query_safe_actions": non_query_safe_actions,
            "labels": labels,
        }

    def materialized_context(
        self,
        frontier: ConditionalResourceFrontier,
    ) -> dict[str, Any]:
        """Model-facing resource frontier without hidden world/window identity."""

        return {
            "schema_version": "layer2-v2-conditional-resource-frontier-0.1",
            "time_s": frontier.at_s,
            "pareto_success": [list(row) for row in frontier.pareto_success],
            "maximal_failure": [list(row) for row in frontier.maximal_failure],
            "minimum_query_budget_for_any_success": frontier.minimum_query_budget_for_any_success,
            "minimum_satellite_budget_without_paid_query": frontier.minimum_satellite_budget_without_paid_query,
            "minimum_satellite_budget_with_query_allowed": frontier.minimum_satellite_budget_with_query_allowed,
            "evidence_gain_type": frontier.evidence_gain_type,
            "hidden_future_world_or_window_identity_exposed": False,
        }
