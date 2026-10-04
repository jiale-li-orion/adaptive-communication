#!/usr/bin/env python3
"""Conditional evidence selection over the asynchronous multi-evidence oracle."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Any

from multi_evidence_scenario_tree import Bundle, solve
from delivery_constraint_graph import world_resource_signatures_with_cost


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


@dataclass(frozen=True)
class QuerySearchDiagnostics:
    catalog_size: int
    constant_pruned: tuple[str, ...]
    dominated_pruned: tuple[str, ...]
    candidate_query_ids: tuple[str, ...]
    subset_solves: int
    preprocessing_solves: int
    structural_flow_solves: int
    total_memo_nodes: int
    selected_query_ids: tuple[str, ...]
    selected_mode: str


def _partition(bundle: Bundle, query_id: str) -> tuple[frozenset[str], ...]:
    groups: dict[str, set[str]] = {}
    for world in bundle.worlds:
        value = dict(world.evidence_values)[query_id]
        groups.setdefault(value, set()).add(world.world_id)
    return tuple(
        sorted(
            (frozenset(ids) for ids in groups.values()),
            key=lambda x: tuple(sorted(x)),
        )
    )


def _partition_refines(
    finer: tuple[frozenset[str], ...],
    coarser: tuple[frozenset[str], ...],
) -> bool:
    return all(any(cell <= parent for parent in coarser) for cell in finer)


def _safe_static_prune(bundle: Bundle) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    qmap = {q.query_id: q for q in bundle.queries}
    partitions = {qid: _partition(bundle, qid) for qid in qmap}

    constant = {
        qid for qid, part in partitions.items()
        if len(part) <= 1
    }
    live = [qid for qid in qmap if qid not in constant]

    dominated: set[str] = set()
    for victim in live:
        if victim in dominated:
            continue
        for winner in live:
            if winner == victim:
                continue
            qv = qmap[victim]
            qw = qmap[winner]
            # Dominance is claimed only inside the current abstract cost model:
            # same owner, no explicit query resource cost, and winner returns no
            # later while providing a partition at least as informative.
            if (
                qv.owner == qw.owner
                and qw.delay_s <= qv.delay_s
                and _partition_refines(partitions[winner], partitions[victim])
                and (
                    qw.delay_s < qv.delay_s
                    or partitions[winner] != partitions[victim]
                    or winner < victim
                )
            ):
                dominated.add(victim)
                break

    candidates = tuple(sorted(qid for qid in live if qid not in dominated))
    return tuple(sorted(constant)), tuple(sorted(dominated)), candidates


def _direct_action_signatures(
    bundle: Bundle,
) -> tuple[dict[str, frozenset[str]], int, int]:
    """Perfect-information first-action signatures plus exact preprocessing cost."""
    from multi_evidence_scenario_tree import Bundle as MBundle

    start = bundle.fixed_event_times[0]
    released = sorted(
        o.oid for o in bundle.obligations
        if o.release_s <= start <= o.deadline_s
    )
    actions: list[tuple[str, str | None]] = [("WAIT", None)]
    if start in bundle.satellite_slots and bundle.satellite_budget > 0:
        actions.extend(("SEND_SAT", oid) for oid in released)
    actions.extend(("SEND_TERR", oid) for oid in released)

    all_q = frozenset(_query_ids(bundle))
    out: dict[str, frozenset[str]] = {}
    solve_count = 0
    memo_nodes = 0
    for world in bundle.worlds:
        single = MBundle(
            bundle_id=f"{bundle.bundle_id}::{world.world_id}",
            fixed_event_times=bundle.fixed_event_times,
            obligations=bundle.obligations,
            satellite_slots=bundle.satellite_slots,
            worlds=(world,),
            satellite_budget=bundle.satellite_budget,
            queries=bundle.queries,
            initial_public_observation=bundle.initial_public_observation,
        )
        winning = []
        for action in actions:
            result = solve(
                single,
                forced_first_action=action,
                disabled_queries=all_q,
            )
            solve_count += 1
            memo_nodes += int(result["memo_nodes"])
            if result["solvable"]:
                winning.append(f"{action[0]}:{action[1] or ''}")
        out[world.world_id] = frozenset(winning)
    return out, solve_count, memo_nodes

def _conflict_pair_score(
    bundle: Bundle,
    query_id: str,
    signatures: dict[str, frozenset[str]],
) -> int:
    worlds = list(bundle.worlds)
    values = {
        w.world_id: dict(w.evidence_values)[query_id]
        for w in worlds
    }
    score = 0
    for i, wa in enumerate(worlds):
        for wb in worlds[i + 1 :]:
            if signatures[wa.world_id] == signatures[wb.world_id]:
                continue
            if values[wa.world_id] != values[wb.world_id]:
                score += 1
    return score

def conflict_guided_query_search(
    bundle: Bundle,
) -> tuple[EvidencePlan, QuerySearchDiagnostics]:
    """Exact evidence-subset search with sound static pruning and conflict order."""

    ids = _query_ids(bundle)
    no_query = assess_query_subset(bundle, ())
    if no_query.solvable:
        plan = EvidencePlan(
            mode="NO_PAID_QUERY",
            selected_query_ids=(),
            no_query_solvable=True,
            exact_solvable=True,
            reason="No paid evidence is required.",
        )
        return plan, QuerySearchDiagnostics(
            catalog_size=len(ids),
            constant_pruned=(),
            dominated_pruned=(),
            candidate_query_ids=(),
            subset_solves=0,
            preprocessing_solves=0,
            structural_flow_solves=0,
            total_memo_nodes=no_query.memo_nodes,
            selected_query_ids=(),
            selected_mode=plan.mode,
        )

    constant, dominated, candidates = _safe_static_prune(bundle)
    qmap = {q.query_id: q for q in bundle.queries}
    # Structural preprocessing: derive per-world shared-resource signatures
    # from the time-expanded delivery constraint graph.  Exact policy solves
    # remain only in subset verification, so correctness is still solver-backed.
    signatures, structural_flow_solves = world_resource_signatures_with_cost(bundle)
    preprocessing_solves = 0
    preprocessing_memo_nodes = 0
    scores = {
        qid: _conflict_pair_score(bundle, qid, signatures)
        for qid in candidates
    }
    subset_solves = 0
    total_memo_nodes = no_query.memo_nodes

    for width in range(1, len(candidates) + 1):
        subsets = list(combinations(candidates, width))
        subsets.sort(
            key=lambda subset: (
                max(qmap[q].delay_s for q in subset),
                -sum(scores[q] for q in subset),
                subset,
            )
        )
        for subset in subsets:
            subset_solves += 1
            assessed = assess_query_subset(bundle, tuple(subset))
            total_memo_nodes += assessed.memo_nodes
            if assessed.solvable:
                mode = "SINGLE_QUERY" if width == 1 else "MULTI_QUERY"
                plan = EvidencePlan(
                    mode=mode,
                    selected_query_ids=tuple(subset),
                    no_query_solvable=False,
                    exact_solvable=True,
                    reason=(
                        "Conflict-guided exact subset search found the smallest "
                        "non-dominated resolving evidence set."
                    ),
                )
                return plan, QuerySearchDiagnostics(
                    catalog_size=len(ids),
                    constant_pruned=constant,
                    dominated_pruned=dominated,
                    candidate_query_ids=candidates,
                    subset_solves=subset_solves,
                    preprocessing_solves=preprocessing_solves,
                    structural_flow_solves=structural_flow_solves,
                    total_memo_nodes=total_memo_nodes,
                    selected_query_ids=tuple(subset),
                    selected_mode=mode,
                )

    plan = EvidencePlan(
        mode="INFORMATION_INFEASIBLE",
        selected_query_ids=(),
        no_query_solvable=False,
        exact_solvable=bool(solve(bundle)["solvable"]),
        reason="No non-dominated evidence subset restores a common successful policy.",
    )
    return plan, QuerySearchDiagnostics(
        catalog_size=len(ids),
        constant_pruned=constant,
        dominated_pruned=dominated,
        candidate_query_ids=candidates,
        subset_solves=subset_solves,
        preprocessing_solves=preprocessing_solves,
        structural_flow_solves=structural_flow_solves,
        total_memo_nodes=total_memo_nodes,
        selected_query_ids=(),
        selected_mode=plan.mode,
    )


def exhaustive_query_search(
    bundle: Bundle,
) -> tuple[EvidencePlan, QuerySearchDiagnostics]:
    """Exact minimum-cardinality evidence search without structural pruning.

    This is the computation reference for the conflict-guided selector. It
    evaluates every subset at a cardinality before choosing the least-delay
    resolving set, so result quality is directly comparable.
    """

    ids = _query_ids(bundle)
    no_query = assess_query_subset(bundle, ())
    total_memo_nodes = no_query.memo_nodes
    if no_query.solvable:
        plan = EvidencePlan(
            mode="NO_PAID_QUERY",
            selected_query_ids=(),
            no_query_solvable=True,
            exact_solvable=True,
            reason="No paid evidence is required.",
        )
        return plan, QuerySearchDiagnostics(
            catalog_size=len(ids),
            constant_pruned=(),
            dominated_pruned=(),
            candidate_query_ids=ids,
            subset_solves=0,
            preprocessing_solves=0,
            structural_flow_solves=0,
            total_memo_nodes=total_memo_nodes,
            selected_query_ids=(),
            selected_mode=plan.mode,
        )

    qmap = {q.query_id: q for q in bundle.queries}
    subset_solves = 0
    for width in range(1, len(ids) + 1):
        winners: list[QueryAssessment] = []
        for subset in combinations(ids, width):
            subset_solves += 1
            assessed = assess_query_subset(bundle, tuple(subset))
            total_memo_nodes += assessed.memo_nodes
            if assessed.solvable:
                winners.append(assessed)
        if winners:
            best = min(
                winners,
                key=lambda x: (
                    x.critical_path_delay_s,
                    x.memo_nodes,
                    x.query_ids,
                ),
            )
            mode = "SINGLE_QUERY" if width == 1 else "MULTI_QUERY"
            plan = EvidencePlan(
                mode=mode,
                selected_query_ids=best.query_ids,
                no_query_solvable=False,
                exact_solvable=True,
                reason="Unstructured exact subset enumeration reference.",
            )
            return plan, QuerySearchDiagnostics(
                catalog_size=len(ids),
                constant_pruned=(),
                dominated_pruned=(),
                candidate_query_ids=ids,
                subset_solves=subset_solves,
                preprocessing_solves=0,
                structural_flow_solves=0,
                total_memo_nodes=total_memo_nodes,
                selected_query_ids=best.query_ids,
                selected_mode=mode,
            )

    plan = EvidencePlan(
        mode="INFORMATION_INFEASIBLE",
        selected_query_ids=(),
        no_query_solvable=False,
        exact_solvable=bool(solve(bundle)["solvable"]),
        reason="No evidence subset restores a common successful policy.",
    )
    return plan, QuerySearchDiagnostics(
        catalog_size=len(ids),
        constant_pruned=(),
        dominated_pruned=(),
        candidate_query_ids=ids,
        subset_solves=subset_solves,
        preprocessing_solves=0,
        structural_flow_solves=0,
        total_memo_nodes=total_memo_nodes,
        selected_query_ids=(),
        selected_mode=plan.mode,
    )
