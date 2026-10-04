#!/usr/bin/env python3
"""Structural lower/upper feasibility bounds for irreversible satellite commits.

Bounds are intentionally conservative:
- U=1 only if every alias world remains max-flow feasible after the commit.
- L=1 only if the remaining obligations are feasible using terrestrial
  opportunities common to every alias world plus the shared satellite schedule.

Thus L <= true observation-matched feasibility <= U. Exact policy search is
reserved for actions with L=0,U=1.
"""
from __future__ import annotations

from dataclasses import dataclass

from delivery_constraint_graph import world_feasibility_witness
from multi_evidence_scenario_tree import Bundle, Obligation, World


@dataclass(frozen=True)
class CommitBound:
    action: tuple[str,str]
    lower: int
    upper: int
    prunable: bool
    reason: str


def _reduced_bundle_after_satellite(
    bundle: Bundle,
    *,
    time_s: int,
    obligation_id: str,
    worlds: tuple[World,...] | None=None,
) -> Bundle | None:
    if time_s not in bundle.satellite_slots or bundle.satellite_budget <= 0:
        return None
    target=next((o for o in bundle.obligations if o.oid==obligation_id),None)
    if target is None or not (target.release_s <= time_s <= target.deadline_s):
        return None
    # Any other obligation already expired by the commitment point makes the
    # commit structurally infeasible in this no-prior-delivery relaxation.
    if any(o.oid!=obligation_id and o.deadline_s < time_s for o in bundle.obligations):
        return None
    remaining=tuple(o for o in bundle.obligations if o.oid!=obligation_id)
    use_worlds=worlds if worlds is not None else bundle.worlds
    clipped=tuple(
        World(
            world_id=w.world_id,
            terrestrial_slots=tuple(t for t in w.terrestrial_slots if t>=time_s),
            evidence_values=w.evidence_values,
            query_reachable=w.query_reachable,
            prehistory_events=w.prehistory_events,
            passive_events=tuple(e for e in w.passive_events if e[0]>=time_s),
        )
        for w in use_worlds
    )
    return Bundle(
        bundle_id=f"{bundle.bundle_id}::sat@{time_s}:{obligation_id}",
        fixed_event_times=tuple(t for t in bundle.fixed_event_times if t>=time_s),
        obligations=remaining,
        satellite_slots=tuple(t for t in bundle.satellite_slots if t>time_s),
        worlds=clipped,
        satellite_budget=bundle.satellite_budget-1,
        queries=bundle.queries,
        initial_public_observation=bundle.initial_public_observation,
    )


def satellite_commit_bounds(bundle: Bundle, *, time_s:int) -> tuple[CommitBound,...]:
    released=[o for o in bundle.obligations if o.release_s<=time_s<=o.deadline_s]
    rows=[]
    for obligation in released:
        reduced=_reduced_bundle_after_satellite(
            bundle,time_s=time_s,obligation_id=obligation.oid
        )
        if reduced is None:
            rows.append(CommitBound(("SEND_SAT",obligation.oid),0,0,True,"illegal or already structurally expired"))
            continue
        world_ok=[world_feasibility_witness(reduced,w).feasible for w in reduced.worlds]
        upper=int(all(world_ok))

        common_terr=set(reduced.worlds[0].terrestrial_slots) if reduced.worlds else set()
        for w in reduced.worlds[1:]:
            common_terr &= set(w.terrestrial_slots)
        common_world=World(
            world_id="common-relaxation",
            terrestrial_slots=tuple(sorted(common_terr)),
            evidence_values=(),
        )
        common_bundle=_reduced_bundle_after_satellite(
            bundle,time_s=time_s,obligation_id=obligation.oid,worlds=(common_world,)
        )
        lower=0
        if common_bundle is not None:
            lower=int(world_feasibility_witness(common_bundle,common_bundle.worlds[0]).feasible)
        if lower>upper:
            raise AssertionError("invalid feasibility bound")
        rows.append(CommitBound(
            action=("SEND_SAT",obligation.oid),
            lower=lower,
            upper=upper,
            prunable=(upper==0),
            reason=(
                "common-opportunity schedule remains feasible" if lower
                else "some alias remains feasible but common schedule not proven" if upper
                else "commit destroys feasibility in at least one alias world"
            ),
        ))
    return tuple(rows)
