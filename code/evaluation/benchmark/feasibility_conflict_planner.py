#!/usr/bin/env python3
"""Feasibility-conflict-guided evidence planning for Layer-1 alias bundles.

This module is intentionally solver-backed and method-facing:
- discover which direct commitments remain jointly winning across alias worlds;
- turn empty action intersections into an explicit feasibility conflict;
- test whether an owner-scoped evidence query partitions the aliases into
  groups with executable winning continuations;
- materialize only decision-relevant conflict/evidence facts into a compact
  context object.

It does not use model scores or hidden-world hindsight labels as policy input.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from scenario_tree_oracle import Bundle, World, solve


DirectAction = tuple[str, str | None]


@dataclass(frozen=True)
class ActionSupport:
    action: DirectAction
    winning_worlds: tuple[str, ...]
    losing_worlds: tuple[str, ...]


@dataclass(frozen=True)
class FeasibilityConflict:
    conflict_id: str
    world_ids: tuple[str, ...]
    direct_actions: tuple[ActionSupport, ...]
    common_winning_actions: tuple[DirectAction, ...]
    reason: str


@dataclass(frozen=True)
class EvidenceNeed:
    need_id: str
    proposition: str
    owner: str
    query_delay_s: int
    partitions: tuple[tuple[str, tuple[str, ...]], ...]
    resolves_conflict: bool
    reason: str


@dataclass(frozen=True)
class DecisionContext:
    bundle_id: str
    world_count: int
    obligation_rows: tuple[tuple[str, int, int], ...]
    satellite_budget: int
    satellite_slots: tuple[int, ...]
    conflict: FeasibilityConflict | None
    evidence_needs: tuple[EvidenceNeed, ...]
    retained_fields: tuple[str, ...]


def _single_world_bundle(bundle: Bundle, world: World) -> Bundle:
    return Bundle(
        bundle_id=f"{bundle.bundle_id}::{world.world_id}",
        decision_times=bundle.decision_times,
        obligations=bundle.obligations,
        satellite_slots=bundle.satellite_slots,
        worlds=(world,),
        satellite_budget=bundle.satellite_budget,
        query_legal=bundle.query_legal,
        query_delay_s=bundle.query_delay_s,
        initial_public_observation=bundle.initial_public_observation,
    )


def _candidate_direct_actions(bundle: Bundle) -> tuple[DirectAction, ...]:
    start = bundle.decision_times[0]
    released = sorted(
        o.oid for o in bundle.obligations if o.release_s <= start <= o.deadline_s
    )
    actions: list[DirectAction] = [("WAIT", None)]
    if start in bundle.satellite_slots and bundle.satellite_budget > 0:
        actions.extend(("SEND_SAT", oid) for oid in released)
    actions.extend(("SEND_TERR", oid) for oid in released)
    return tuple(actions)


def action_support_matrix(bundle: Bundle) -> tuple[ActionSupport, ...]:
    """Compute exact winning support for every direct first action.

    The action is forced only at the shared initial history. Each single-world
    continuation then receives the same future observation/action interface as
    the original bundle.
    """

    supports: list[ActionSupport] = []
    for action in _candidate_direct_actions(bundle):
        winning: list[str] = []
        losing: list[str] = []
        for world in bundle.worlds:
            single = _single_world_bundle(bundle, world)
            result = solve(
                single,
                allow_query=False,
                forced_first_action=action,
            )
            (winning if result["solvable"] else losing).append(world.world_id)
        supports.append(
            ActionSupport(
                action=action,
                winning_worlds=tuple(sorted(winning)),
                losing_worlds=tuple(sorted(losing)),
            )
        )
    return tuple(supports)


def detect_feasibility_conflict(bundle: Bundle) -> FeasibilityConflict | None:
    supports = action_support_matrix(bundle)
    world_ids = tuple(sorted(w.world_id for w in bundle.worlds))
    # A direct action is common-safe only if the *same observation-matched
    # continuation policy* exists after forcing it on the whole alias bundle.
    # Per-world solvability alone would illegally let the continuation branch
    # on hidden world identity.
    common = tuple(
        row.action
        for row in supports
        if solve(
            bundle,
            allow_query=False,
            forced_first_action=row.action,
        )["solvable"]
    )
    if common:
        return None

    differentiating = tuple(
        row for row in supports
        if row.winning_worlds and row.losing_worlds
    )
    if not differentiating:
        reason = (
            "No direct first action is jointly winning, but the observed split "
            "is not attributable to an action whose success differs across aliases."
        )
    else:
        reason = (
            "Alias worlds disagree on which direct commitment preserves full "
            "obligation feasibility; no common winning direct action exists."
        )
    return FeasibilityConflict(
        conflict_id=f"{bundle.bundle_id}::initial-action-conflict",
        world_ids=world_ids,
        direct_actions=supports,
        common_winning_actions=common,
        reason=reason,
    )


def _query_partitions(bundle: Bundle) -> tuple[tuple[str, tuple[str, ...]], ...]:
    groups: dict[str, list[str]] = {}
    for world in bundle.worlds:
        groups.setdefault(world.query_value, []).append(world.world_id)
    return tuple(
        (value, tuple(sorted(ids)))
        for value, ids in sorted(groups.items())
    )


def derive_evidence_need(
    bundle: Bundle,
    conflict: FeasibilityConflict | None,
) -> EvidenceNeed | None:
    if conflict is None or not bundle.query_legal:
        return None

    partitions = _query_partitions(bundle)
    distinguishes = len(partitions) > 1
    query_policy = solve(
        bundle,
        allow_query=True,
        forced_first_action=("QUERY", None),
    )
    resolves = bool(distinguishes and query_policy["solvable"])
    return EvidenceNeed(
        need_id=f"{bundle.bundle_id}::gateway-primary-health",
        proposition="communication.gateway.primary_health",
        owner="gateway",
        query_delay_s=bundle.query_delay_s,
        partitions=partitions,
        resolves_conflict=resolves,
        reason=(
            "Current gateway-owner evidence partitions alias worlds into "
            "different feasibility regimes before the irreversible resource "
            "commitment."
            if resolves
            else "The available owner-scoped query does not produce a timely winning policy."
        ),
    )


def build_decision_context(bundle: Bundle) -> DecisionContext:
    conflict = detect_feasibility_conflict(bundle)
    need = derive_evidence_need(bundle, conflict)

    retained = [
        "operational_obligations",
        "satellite_budget",
        "satellite_opportunity_schedule",
    ]
    if conflict is not None:
        retained.append("feasibility_conflict")
    if need is not None:
        retained.extend(
            [
                "gateway_owner_evidence_contract",
                "query_delay",
            ]
        )

    return DecisionContext(
        bundle_id=bundle.bundle_id,
        world_count=len(bundle.worlds),
        obligation_rows=tuple(
            (o.oid, o.release_s, o.deadline_s) for o in bundle.obligations
        ),
        satellite_budget=bundle.satellite_budget,
        satellite_slots=bundle.satellite_slots,
        conflict=conflict,
        evidence_needs=(() if need is None else (need,)),
        retained_fields=tuple(retained),
    )


def compact_context_dict(ctx: DecisionContext) -> dict[str, Any]:
    """Stable JSON-ready context for later planner/model experiments."""

    conflict = None
    if ctx.conflict is not None:
        conflict = {
            "conflict_id": ctx.conflict.conflict_id,
            "world_count": len(ctx.conflict.world_ids),
            "common_winning_actions": [
                [a, arg] for a, arg in ctx.conflict.common_winning_actions
            ],
            "action_support": [
                {
                    "action": [row.action[0], row.action[1]],
                    "winning_world_count": len(row.winning_worlds),
                    "losing_world_count": len(row.losing_worlds),
                }
                for row in ctx.conflict.direct_actions
            ],
            "reason": ctx.conflict.reason,
        }

    return {
        "bundle_id": ctx.bundle_id,
        "obligations": [
            {"obligation_id": oid, "release_s": rel, "deadline_s": ddl}
            for oid, rel, ddl in ctx.obligation_rows
        ],
        "satellite_budget": ctx.satellite_budget,
        "satellite_slots": list(ctx.satellite_slots),
        "conflict": conflict,
        "evidence_needs": [
            {
                "need_id": n.need_id,
                "proposition": n.proposition,
                "owner": n.owner,
                "query_delay_s": n.query_delay_s,
                "partition_count": len(n.partitions),
                "resolves_conflict": n.resolves_conflict,
                "reason": n.reason,
            }
            for n in ctx.evidence_needs
        ],
        "retained_fields": list(ctx.retained_fields),
    }


@dataclass(frozen=True)
class ActionBound:
    action: DirectAction
    lower: int
    upper: int
    prunable: bool
    reason: str


@dataclass(frozen=True)
class UpdatedContext:
    observation: str
    remaining_world_ids: tuple[str, ...]
    context: DecisionContext


def action_feasibility_bounds(bundle: Bundle) -> tuple[ActionBound, ...]:
    """Compute sound binary lower/upper bounds for direct first actions.

    lower=1:
        the action has an observation-matched winning continuation on the
        whole current alias set.

    upper=1:
        the action is winning in every world if hidden identity were revealed
        immediately after the action (perfect-information relaxation).

    Therefore lower <= true value <= upper. Any action with upper below the
    best lower can be safely pruned.
    """

    supports = action_support_matrix(bundle)
    world_ids = tuple(sorted(w.world_id for w in bundle.worlds))
    raw: list[tuple[DirectAction, int, int, str]] = []
    for row in supports:
        joint = solve(
            bundle,
            allow_query=False,
            forced_first_action=row.action,
        )["solvable"]
        lower = int(bool(joint))
        upper = int(row.winning_worlds == world_ids)
        if lower > upper:
            raise AssertionError("invalid feasibility bound: lower > upper")
        raw.append(
            (
                row.action,
                lower,
                upper,
                (
                    "observation-matched continuation exists"
                    if lower
                    else (
                        "perfect-information relaxation still permits success"
                        if upper
                        else "at least one alias world makes the action infeasible"
                    )
                ),
            )
        )

    best_lower = max((x[1] for x in raw), default=0)
    return tuple(
        ActionBound(
            action=action,
            lower=lower,
            upper=upper,
            prunable=upper < best_lower,
            reason=reason,
        )
        for action, lower, upper, reason in raw
    )


def _restricted_bundle(bundle: Bundle, world_ids: Iterable[str]) -> Bundle:
    wanted = set(world_ids)
    worlds = tuple(w for w in bundle.worlds if w.world_id in wanted)
    if not worlds:
        raise ValueError("evidence update removed all alias worlds")
    return Bundle(
        bundle_id=bundle.bundle_id,
        decision_times=bundle.decision_times,
        obligations=bundle.obligations,
        satellite_slots=bundle.satellite_slots,
        worlds=worlds,
        satellite_budget=bundle.satellite_budget,
        query_legal=bundle.query_legal,
        query_delay_s=bundle.query_delay_s,
        initial_public_observation=bundle.initial_public_observation,
    )


def update_context_after_gateway_evidence(
    bundle: Bundle,
    *,
    observed_value: str,
) -> UpdatedContext:
    """Incrementally narrow aliases after a legal gateway-owner observation.

    The update does not rebuild or expose hidden world state. It filters the
    alias set by the evidence proposition's returned value, then recomputes
    only the feasibility conflict/evidence slice for the surviving aliases.
    """

    ids = tuple(
        sorted(w.world_id for w in bundle.worlds if w.query_value == observed_value)
    )
    if not ids:
        raise ValueError(f"evidence value {observed_value!r} is incompatible with bundle")
    restricted = _restricted_bundle(bundle, ids)
    return UpdatedContext(
        observation=observed_value,
        remaining_world_ids=ids,
        context=build_decision_context(restricted),
    )


@dataclass(frozen=True)
class PlannerDecision:
    action: DirectAction
    reason_code: str
    conflict_id: str | None
    evidence_need_id: str | None


def choose_first_step(bundle: Bundle) -> PlannerDecision:
    """Choose the first step from feasibility structure, not hidden labels.

    Priority:
    1. execute any direct action with an observation-matched winning
       continuation;
    2. wait if passive feedback alone preserves a winning no-paid-query policy;
    3. issue a resolving owner query;
    4. report information infeasibility by returning WAIT with an explicit
       reason code (caller should not treat it as a winning plan).
    """

    bounds = action_feasibility_bounds(bundle)
    direct = [b for b in bounds if b.lower == 1]
    if direct:
        # Prefer WAIT when it is already sufficient; otherwise avoid satellite
        # use when an equally valid terrestrial action exists.
        order = {"WAIT": 0, "SEND_TERR": 1, "SEND_SAT": 2}
        chosen = min(
            direct,
            key=lambda b: (order.get(b.action[0], 9), b.action[1] or ""),
        )
        return PlannerDecision(
            action=chosen.action,
            reason_code="COMMON_WINNING_DIRECT_ACTION",
            conflict_id=None,
            evidence_need_id=None,
        )

    conflict = detect_feasibility_conflict(bundle)
    if conflict is None:
        return PlannerDecision(
            action=("WAIT", None),
            reason_code="NO_WINNING_DIRECT_ACTION_NO_ALIAS_CONFLICT",
            conflict_id=None,
            evidence_need_id=None,
        )

    # If waiting without paid queries already yields a valid common policy,
    # preserve the free/passive feedback path.
    passive = solve(
        bundle,
        allow_query=False,
        forced_first_action=("WAIT", None),
    )
    if passive["solvable"]:
        return PlannerDecision(
            action=("WAIT", None),
            reason_code="WAIT_FOR_PASSIVE_EVIDENCE",
            conflict_id=conflict.conflict_id,
            evidence_need_id=None,
        )

    need = derive_evidence_need(bundle, conflict)
    if need is not None and need.resolves_conflict:
        return PlannerDecision(
            action=("QUERY", None),
            reason_code="RESOLVE_FEASIBILITY_CONFLICT",
            conflict_id=conflict.conflict_id,
            evidence_need_id=need.need_id,
        )

    return PlannerDecision(
        action=("WAIT", None),
        reason_code="INFORMATION_INFEASIBLE_OR_UNRESOLVED",
        conflict_id=conflict.conflict_id,
        evidence_need_id=(None if need is None else need.need_id),
    )
