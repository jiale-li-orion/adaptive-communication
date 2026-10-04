#!/usr/bin/env python3
"""Time-expanded delivery-constraint graph for Layer-1 evidence planning.

The graph is a deterministic relaxation/reference over the current finite
opportunity model.  It exposes which obligations depend on which terrestrial
or satellite service opportunities and which obligations are forced to consume
the shared satellite budget in a given hidden world.

It is deliberately independent of evidence labels and model scores.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any

from multi_evidence_scenario_tree import Bundle, Obligation, World


@dataclass(frozen=True)
class Opportunity:
    opportunity_id: str
    kind: str
    time_s: int
    capacity: int = 1


@dataclass(frozen=True)
class WorldFeasibilityWitness:
    world_id: str
    feasible: bool
    delivered_count: int
    obligation_count: int
    flow_solve_count: int
    mandatory_satellite_obligations: tuple[str, ...]
    obligation_opportunities: tuple[tuple[str, tuple[str, ...]], ...]


@dataclass(frozen=True)
class AliasConflictWitness:
    world_witnesses: tuple[WorldFeasibilityWitness, ...]
    flow_solve_count: int
    mandatory_satellite_union: tuple[str, ...]
    mandatory_satellite_intersection: tuple[str, ...]
    differing_obligations: tuple[str, ...]
    shared_satellite_budget: int
    resource_conflict_present: bool


class _Flow:
    def __init__(self) -> None:
        self.cap: dict[str, dict[str, int]] = {}

    def add_edge(self, u: str, v: str, c: int) -> None:
        self.cap.setdefault(u, {})
        self.cap.setdefault(v, {})
        self.cap[u][v] = self.cap[u].get(v, 0) + c
        self.cap[v].setdefault(u, 0)

    def max_flow(self, source: str, sink: str) -> int:
        residual = {u: dict(vs) for u, vs in self.cap.items()}
        total = 0
        while True:
            parent: dict[str, str | None] = {source: None}
            q = deque([source])
            while q and sink not in parent:
                u = q.popleft()
                for v, c in residual.get(u, {}).items():
                    if c > 0 and v not in parent:
                        parent[v] = u
                        q.append(v)
            if sink not in parent:
                break
            aug = 10**9
            v = sink
            while parent[v] is not None:
                u = parent[v]
                aug = min(aug, residual[u][v])
                v = u
            v = sink
            while parent[v] is not None:
                u = parent[v]
                residual[u][v] -= aug
                residual[v][u] = residual[v].get(u, 0) + aug
                v = u
            total += aug
        return total


def _opportunities(bundle: Bundle, world: World) -> tuple[Opportunity, ...]:
    terr = tuple(
        Opportunity(f"terr@{t}", "terrestrial", int(t))
        for t in sorted(set(world.terrestrial_slots))
    )
    sat = tuple(
        Opportunity(f"sat@{t}", "satellite", int(t))
        for t in sorted(set(bundle.satellite_slots))
    )
    return terr + sat


def _edge_allowed(obligation: Obligation, opportunity: Opportunity) -> bool:
    return obligation.release_s <= opportunity.time_s <= obligation.deadline_s


def _max_deliverable(
    bundle: Bundle,
    world: World,
    *,
    forbid_satellite_for: frozenset[str] = frozenset(),
) -> tuple[int, dict[str, tuple[str, ...]]]:
    source = "SRC"
    sink = "SNK"
    sat_budget_node = "SAT_BUDGET"
    flow = _Flow()
    opps = _opportunities(bundle, world)

    by_obligation: dict[str, list[str]] = {o.oid: [] for o in bundle.obligations}
    for obligation in bundle.obligations:
        onode = f"obl:{obligation.oid}"
        flow.add_edge(source, onode, 1)
        for opportunity in opps:
            if not _edge_allowed(obligation, opportunity):
                continue
            if opportunity.kind == "satellite" and obligation.oid in forbid_satellite_for:
                continue
            pnode = f"opp:{opportunity.opportunity_id}"
            flow.add_edge(onode, pnode, 1)
            by_obligation[obligation.oid].append(opportunity.opportunity_id)

    for opportunity in opps:
        pnode = f"opp:{opportunity.opportunity_id}"
        if opportunity.kind == "terrestrial":
            flow.add_edge(pnode, sink, opportunity.capacity)
        else:
            flow.add_edge(pnode, sat_budget_node, opportunity.capacity)
    flow.add_edge(sat_budget_node, sink, int(bundle.satellite_budget))

    delivered = flow.max_flow(source, sink)
    return delivered, {
        oid: tuple(sorted(values)) for oid, values in sorted(by_obligation.items())
    }


def world_feasibility_witness(bundle: Bundle, world: World) -> WorldFeasibilityWitness:
    delivered, edges = _max_deliverable(bundle, world)
    target = len(bundle.obligations)
    feasible = delivered == target

    mandatory: list[str] = []
    if feasible:
        for obligation in bundle.obligations:
            without_sat, _ = _max_deliverable(
                bundle,
                world,
                forbid_satellite_for=frozenset({obligation.oid}),
            )
            if without_sat < target:
                mandatory.append(obligation.oid)

    return WorldFeasibilityWitness(
        world_id=world.world_id,
        feasible=feasible,
        delivered_count=delivered,
        obligation_count=target,
        flow_solve_count=(1 + len(bundle.obligations)) if feasible else 1,
        mandatory_satellite_obligations=tuple(sorted(mandatory)),
        obligation_opportunities=tuple(sorted(edges.items())),
    )


def aggregate_world_witnesses(
    witnesses: tuple[WorldFeasibilityWitness, ...],
    *,
    satellite_budget: int,
    inherited_flow_solve_count: int | None = None,
) -> AliasConflictWitness:
    mandatory_sets = [set(w.mandatory_satellite_obligations) for w in witnesses]
    union = set().union(*mandatory_sets) if mandatory_sets else set()
    intersection = set.intersection(*mandatory_sets) if mandatory_sets else set()

    differing = {
        oid
        for oid in union
        if any(oid in s for s in mandatory_sets)
        and not all(oid in s for s in mandatory_sets)
    }

    resource_conflict = bool(
        witnesses
        and all(w.feasible for w in witnesses)
        and differing
        and len(union) > int(satellite_budget)
    )

    return AliasConflictWitness(
        world_witnesses=witnesses,
        flow_solve_count=(
            sum(w.flow_solve_count for w in witnesses)
            if inherited_flow_solve_count is None
            else int(inherited_flow_solve_count)
        ),
        mandatory_satellite_union=tuple(sorted(union)),
        mandatory_satellite_intersection=tuple(sorted(intersection)),
        differing_obligations=tuple(sorted(differing)),
        shared_satellite_budget=int(satellite_budget),
        resource_conflict_present=resource_conflict,
    )


def alias_conflict_witness(bundle: Bundle) -> AliasConflictWitness:
    witnesses = tuple(world_feasibility_witness(bundle, w) for w in bundle.worlds)
    return aggregate_world_witnesses(
        witnesses,
        satellite_budget=int(bundle.satellite_budget),
    )


def world_resource_signatures(bundle: Bundle) -> dict[str, frozenset[str]]:
    """Compact conflict signatures used to rank evidence without exact policy solves."""
    return world_resource_signatures_with_cost(bundle)[0]


def world_resource_signatures_with_cost(
    bundle: Bundle,
) -> tuple[dict[str, frozenset[str]], int]:
    witness = alias_conflict_witness(bundle)
    return (
        {
            row.world_id: frozenset(row.mandatory_satellite_obligations)
            for row in witness.world_witnesses
        },
        witness.flow_solve_count,
    )


def witness_dict(witness: AliasConflictWitness) -> dict[str, Any]:
    return {
        "shared_satellite_budget": witness.shared_satellite_budget,
        "flow_solve_count": witness.flow_solve_count,
        "resource_conflict_present": witness.resource_conflict_present,
        "mandatory_satellite_union": list(witness.mandatory_satellite_union),
        "mandatory_satellite_intersection": list(witness.mandatory_satellite_intersection),
        "differing_obligations": list(witness.differing_obligations),
        "worlds": [
            {
                "world_id": row.world_id,
                "feasible": row.feasible,
                "delivered_count": row.delivered_count,
                "obligation_count": row.obligation_count,
                "flow_solve_count": row.flow_solve_count,
                "mandatory_satellite_obligations": list(row.mandatory_satellite_obligations),
                "obligation_opportunities": {
                    oid: list(opps) for oid, opps in row.obligation_opportunities
                },
            }
            for row in witness.world_witnesses
        ],
    }
