#!/usr/bin/env python3
"""Future-choice frontier for dynamic Layer-1 planning.

Unlike the earlier matching-deficit cache, this object exposes which future
backup commitments have not yet been disproved by the communication constraints,
and which legal evidence reads would change that remaining choice set.

The frontier is deliberately optimistic.  Membership means "still potentially
preservable", not "certified successful".  It may rank exact search but may not
hard-prune an unresolved action.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from dynamic_scenario_tree_v0_5 import (
    Action,Bundle,LocalState,_sample_query_value,_query_partitions,
)
from dynamic_feasibility_frontier_v0_5 import _world_certificate


@dataclass(frozen=True)
class ChoiceSupport:
    obligation_id:str
    supporting_world_ids:tuple[str,...]
    common_to_all_worlds:bool


@dataclass(frozen=True)
class QueryChoicePartition:
    query_id:str
    outcomes:tuple[tuple[str,tuple[str,...],tuple[str,...]],...]
    changes_choice_frontier:bool


@dataclass(frozen=True)
class FutureChoiceFrontier:
    at_s:int
    active_world_ids:tuple[str,...]
    satellite_budget_min:int
    backup_choices:tuple[ChoiceSupport,...]
    common_backup_choices:tuple[str,...]
    query_partitions:tuple[QueryChoicePartition,...]
    frontier_relevant_queries:tuple[str,...]
    valid_until_s:int|None


def _pending_cover(bundle:Bundle,t:int,st:LocalState) -> set[str]:
    out=set()
    for d in st.pending_deliveries:
        if not d.accepted or d.final_ack_at_s is None or d.final_ack_at_s<=t:
            continue
        deadline=next(o.deadline_s for o in bundle.obligations if o.oid==d.oid)
        if d.final_ack_at_s<=deadline:
            out.add(d.oid)
    return out


def _world_backup_choices(bundle:Bundle,t:int,wid:str,st:LocalState) -> set[str]:
    if st.sat_budget<=0 or st.violated_obligations:
        return set()
    world=next(w for w in bundle.worlds if w.world_id==wid)
    covered=_pending_cover(bundle,t,st)
    choices=set()
    for o in bundle.obligations:
        if o.oid in st.final_delivered or o.oid in covered or o.oid in st.violated_obligations:
            continue
        if not any(max(t,o.release_s)<=sat<=o.deadline_s for sat in bundle.satellite_send_times):
            continue
        cert,_=_world_certificate(
            bundle,world,
            delivered=set(st.final_delivered)|{o.oid},
            violated=set(st.violated_obligations),
            pending_cover=covered,
            at_s=t,
            satellite_budget=st.sat_budget-1,
        )
        if cert.optimistic_backup_feasible:
            choices.add(o.oid)
    return choices


def _group_common_choices(bundle:Bundle,t:int,states:dict[str,LocalState],world_ids:set[str]) -> tuple[str,...]:
    rows=[_world_backup_choices(bundle,t,wid,states[wid]) for wid in sorted(world_ids)]
    if not rows:return ()
    return tuple(sorted(set.intersection(*rows)))


def _valid_until(bundle:Bundle,t:int,states:dict[str,LocalState]) -> int|None:
    c=[]
    c.extend(x for x in bundle.terrestrial_send_times if x>t)
    c.extend(x for x in bundle.satellite_send_times if x>t)
    for o in bundle.obligations:
        if o.release_s>t:c.append(o.release_s)
        if o.deadline_s>t:c.append(o.deadline_s)
    for st in states.values():
        c.extend(q.arrive_at_s for q in st.pending_queries if q.arrive_at_s>t)
        for d in st.pending_deliveries:
            if d.gateway_receipt_at_s is not None and d.gateway_receipt_at_s>t:c.append(d.gateway_receipt_at_s)
            if d.final_ack_at_s is not None and d.final_ack_at_s>t:c.append(d.final_ack_at_s)
    return min(c) if c else None


def build_future_choice_frontier(bundle:Bundle,t:int,states:dict[str,LocalState]) -> FutureChoiceFrontier:
    world_choices={wid:_world_backup_choices(bundle,t,wid,st) for wid,st in states.items()}
    all_oids=sorted(set().union(*world_choices.values()) if world_choices else set())
    supports=[]
    active=set(states)
    for oid in all_oids:
        ws=tuple(sorted(wid for wid,choices in world_choices.items() if oid in choices))
        supports.append(ChoiceSupport(oid,ws,set(ws)==active))
    common=tuple(sorted(set.intersection(*world_choices.values()))) if world_choices else ()

    qparts=[]; relevant=[]
    world_map={w.world_id:w for w in bundle.worlds}
    for q in bundle.queries:
        if not _query_partitions(bundle,t,states,q.query_id):
            continue
        sample=t+q.sample_delay_s
        groups:dict[str,set[str]]={}
        for wid,st in states.items():
            w=world_map[wid]
            outcome=_sample_query_value(w,st,q,sample) if w.query_reachable(sample) else '__TIMEOUT__'
            groups.setdefault(outcome,set()).add(wid)
        rows=[]
        fronts=set()
        for outcome,wids in sorted(groups.items()):
            choices=_group_common_choices(bundle,t,states,wids)
            fronts.add(choices)
            rows.append((outcome,tuple(sorted(wids)),choices))
        changes=len(fronts)>1
        qparts.append(QueryChoicePartition(q.query_id,tuple(rows),changes))
        if changes:relevant.append(q.query_id)

    return FutureChoiceFrontier(
        at_s=t,
        active_world_ids=tuple(sorted(states)),
        satellite_budget_min=min((st.sat_budget for st in states.values()),default=0),
        backup_choices=tuple(supports),
        common_backup_choices=common,
        query_partitions=tuple(qparts),
        frontier_relevant_queries=tuple(sorted(relevant)),
        valid_until_s=_valid_until(bundle,t,states),
    )


def frontier_action_order(bundle:Bundle,t:int,states:dict[str,LocalState],actions:list[Action]) -> list[Action]:
    """Completeness-preserving ordering only; never removes an action."""
    frontier=build_future_choice_frontier(bundle,t,states)
    relevant=set(frontier.frontier_relevant_queries)
    common=set(frontier.common_backup_choices)
    def score(a:Action):
        kind,arg=a
        if kind=='SEND_TERR': return (5,0,repr(a))  # task progress + potential feedback
        if kind=='ISSUE_QUERY' and arg in relevant:return (4,0,repr(a))
        if kind=='SEND_SAT' and arg in common:return (3,0,repr(a))
        if kind=='WAIT':return (1,0,repr(a))
        return (2,0,repr(a))
    return sorted(actions,key=score,reverse=True)
