#!/usr/bin/env python3
"""Conditional evidence selection over the asynchronous multi-evidence oracle."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Any

from multi_evidence_scenario_tree import Bundle, solve


@dataclass(frozen=True)
class QueryAssessment:
    query_ids: tuple[str, ...]
    solvable: bool
    memo_nodes: int
    critical_path_delay_s: int


@dataclass(frozen=True)
class EvidencePlan:
    mode: str
    selected_query_ids: tuple[str, ...]
    no_query_solvable: bool
    exact_solvable: bool
    reason: str


def _query_ids(bundle: Bundle) -> tuple[str, ...]:
    return tuple(q.query_id for q in bundle.queries)


def assess_query_subset(bundle: Bundle, query_ids: tuple[str, ...]) -> QueryAssessment:
    all_ids = set(_query_ids(bundle))
    enabled = set(query_ids)
    disabled = frozenset(all_ids - enabled)
    if not query_ids:
        result = solve(bundle, disabled_queries=frozenset(all_ids))
        delay = 0
    else:
        # Force the first selected query; the exact solver may issue the rest
        # asynchronously later if doing so is useful.
        first = query_ids[0]
        result = solve(
            bundle,
            forced_first_action=("ISSUE_QUERY", first),
            disabled_queries=disabled,
        )
        qmap = {q.query_id: q for q in bundle.queries}
        delay = max(qmap[q].delay_s for q in query_ids)
    return QueryAssessment(
        query_ids=tuple(query_ids),
        solvable=bool(result["solvable"]),
        memo_nodes=int(result["memo_nodes"]),
        critical_path_delay_s=delay,
    )


def choose_evidence_plan(bundle: Bundle) -> EvidencePlan:
    ids = _query_ids(bundle)
    no_query = assess_query_subset(bundle, ())
    exact = solve(bundle)

    if no_query.solvable:
        return EvidencePlan(
            mode="NO_PAID_QUERY",
            selected_query_ids=(),
            no_query_solvable=True,
            exact_solvable=bool(exact["solvable"]),
            reason="Passive/normal execution already admits an observation-matched winning policy.",
        )

    singles = [assess_query_subset(bundle, (qid,)) for qid in ids]
    winning_singles = [x for x in singles if x.solvable]
    if winning_singles:
        best = min(
            winning_singles,
            key=lambda x: (x.critical_path_delay_s, x.memo_nodes, x.query_ids),
        )
        return EvidencePlan(
            mode="SINGLE_QUERY",
            selected_query_ids=best.query_ids,
            no_query_solvable=False,
            exact_solvable=bool(exact["solvable"]),
            reason="One owner-scoped query is sufficient; choose the least-delay exact-resolving option.",
        )

    # Search the smallest resolving subset. This is exact for the current small
    # capability catalog and creates the target for later conflict-guided pruning.
    for width in range(2, len(ids) + 1):
        winners = []
        for subset in combinations(ids, width):
            assessed = assess_query_subset(bundle, tuple(subset))
            if assessed.solvable:
                winners.append(assessed)
        if winners:
            best = min(
                winners,
                key=lambda x: (x.critical_path_delay_s, x.memo_nodes, x.query_ids),
            )
            return EvidencePlan(
                mode="MULTI_QUERY",
                selected_query_ids=best.query_ids,
                no_query_solvable=False,
                exact_solvable=bool(exact["solvable"]),
                reason="No single query suffices; the smallest exact-resolving evidence subset is required.",
            )

    return EvidencePlan(
        mode="INFORMATION_INFEASIBLE",
        selected_query_ids=(),
        no_query_solvable=False,
        exact_solvable=bool(exact["solvable"]),
        reason="Available evidence capabilities do not recover a common successful policy.",
    )
