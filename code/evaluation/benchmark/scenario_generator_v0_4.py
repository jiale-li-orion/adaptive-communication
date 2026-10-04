#!/usr/bin/env python3
"""Process-generated multi-conflict evidence bundles for Layer-1 method evaluation."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any
from hashlib import sha256
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
if str(ROOT/'code') not in sys.path:
    sys.path.insert(0,str(ROOT/'code'))

from agentic_communication.capabilities import CommunicationCapabilityCatalog

from multi_evidence_conflict_planner import (
    assess_query_subset,
    conflict_guided_query_search,
    exhaustive_query_search,
)
from multi_evidence_scenario_tree import Bundle, EvidenceQuery, Obligation, World, solve
from structural_scaling_v0_3 import CADENCE_S, phase_groups


EVIDENCE_PROFILES=("BOTH","PRIMARY_ONLY","RECEIPT_ONLY","NONE")
ALIAS_SETS=(
    ((0,2),(0,2)),          # duplicate aliases / no decision information needed
    ((0,2),(1,2)),          # first conflict only
    ((0,2),(0,3)),          # second conflict only
    ((0,2),(0,3),(1,2),(1,3)),  # two independent conflicts
)


@dataclass(frozen=True)
class GeneratedBundle:
    bundle: Bundle
    coordinates: dict[str,Any]
    outcome_class: str
    selected_query_ids: tuple[str,...]
    no_query_solvable: bool
    exact_solvable: bool


def _stable_id(payload: Any) -> str:
    raw=json.dumps(payload,sort_keys=True,separators=(",",":")).encode()
    return sha256(raw).hexdigest()[:16]




_CATALOG=CommunicationCapabilityCatalog()


def _query_from_capability(query_id:str, capability_id:str, delay_s:int) -> EvidenceQuery:
    binding=_CATALOG.binding(capability_id)
    contract=_CATALOG.get(capability_id)
    if binding.owner_location not in contract.authority_semantics:
        raise ValueError(f'owner/authority mismatch for {capability_id}')
    return EvidenceQuery(
        query_id=query_id,
        proposition=capability_id,
        owner=binding.owner_location,
        delay_s=delay_s,
        capability_id=capability_id,
        required_path=tuple(binding.required_path),
        return_path=tuple(binding.return_path),
        opportunity_dependency=tuple(binding.opportunity_dependency),
    )


def _queries(catalog_size:int=5) -> tuple[EvidenceQuery,...]:
    base=[
        _query_from_capability('primary_health','communication.gateway.primary_health',40),
        _query_from_capability('receipt_summary','communication.gateway.receipt_summary',20),
    ]
    for i in range(max(0,catalog_size-2)):
        base.append(_query_from_capability(
            f'node_report:noise{i}',
            'communication.gateway.node_report',
            60+10*i,
        ))
    return tuple(base[:catalog_size])


def _canonical_observation(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _prehistory_events(missing:tuple[int,int], *, decision_t:int) -> tuple[tuple[int,str,str],...]:
    """Generate already-happened gateway execution/receipt events.

    These events exist before the policy's initial decision. Evidence values are
    aggregated from them; no future opportunity or obligation label is returned.
    Their correlation with later service patterns is CONTROLLED_STRESS.
    """
    a,b=missing
    events:list[tuple[int,str,str]]=[]
    if a==0:
        events += [
            (decision_t-300,'forward_ok','gw0'),
            (decision_t-420,'queue_add','q0'),
        ]
    else:
        events += [
            (decision_t-5400,'forward_ok','gw0'),
            (decision_t-6000,'queue_add','q0'),
            (decision_t-5700,'queue_add','q1'),
            (decision_t-5400,'queue_add','q2'),
        ]
    if b==2:
        events += [
            (decision_t-600,'receipt_ok','r0'),
            (decision_t-400,'receipt_ok','r1'),
            (decision_t-240,'receipt_ok','r2'),
        ]
    else:
        events += [
            (decision_t-4800,'receipt_ok','r-old'),
            (decision_t-1200,'receipt_missing','r1'),
            (decision_t-900,'receipt_missing','r2'),
        ]
    events += [
        (decision_t-180,'node_soc','nominal'),
        (decision_t-180,'node_cache','noncritical'),
        (decision_t-180,'config_generation','1'),
    ]
    return tuple(sorted(events))


def _aggregate_gateway_state(events:tuple[tuple[int,str,str],...], *, decision_t:int) -> dict[str,dict[str,Any]]:
    forwards=[t for t,k,_ in events if k=='forward_ok']
    adds=[(t,v) for t,k,v in events if k=='queue_add']
    removes={v for _t,k,v in events if k=='queue_remove'}
    outstanding=[(t,v) for t,v in adds if v not in removes]
    receipts=[t for t,k,_ in events if k=='receipt_ok']
    missing=[1 for _t,k,_ in events if k=='receipt_missing']
    node={k:v for _t,k,v in events if k in {'node_soc','node_cache','config_generation'}}
    return {
        'primary_health':{
            'last_forward_age_s': None if not forwards else decision_t-max(forwards),
            'pending_depth':len(outstanding),
            'oldest_pending_age_s': None if not outstanding else decision_t-min(t for t,_ in outstanding),
            'query_path_reachable':True,
        },
        'receipt_summary':{
            'recent_receipt_count':sum(decision_t-t<=900 for t in receipts),
            'last_receipt_age_s':None if not receipts else decision_t-max(receipts),
            'missing_receipt_count':sum(missing),
        },
        'node_report':{
            'soc_bucket':node.get('node_soc','unknown'),
            'cache_bucket':node.get('node_cache','unknown'),
            'config_generation':int(node.get('config_generation','0')),
        },
    }


def _evidence_values(
    *,
    events:tuple[tuple[int,str,str],...],
    decision_t:int,
    profile:str,
    queries:tuple[EvidenceQuery,...],
) -> tuple[tuple[str,str],...]:
    state=_aggregate_gateway_state(events,decision_t=decision_t)
    primary_live=profile in {'BOTH','PRIMARY_ONLY'}
    receipt_live=profile in {'BOTH','RECEIPT_ONLY'}
    vals={
        'primary_health':_canonical_observation(state['primary_health']) if primary_live else 'same',
        'receipt_summary':_canonical_observation(state['receipt_summary']) if receipt_live else 'same',
    }
    node_value=_canonical_observation(state['node_report'])
    for q in queries:
        if q.query_id.startswith('node_report:'):
            vals[q.query_id]=node_value
    return tuple((q.query_id,vals[q.query_id]) for q in queries)

def build_bundle(*,phase_index:int,start:int,sats:tuple[int,...],alias_set:tuple[tuple[int,int],...],evidence_profile:str,catalog_size:int=5) -> Bundle:
    if len(sats)!=4:
        raise ValueError('v0.4 requires four consecutive source-shaped obligations')
    queries=_queries(catalog_size)
    obligations=tuple(
        Obligation(f'report_{i}',start+i*CADENCE_S,start+(i+1)*CADENCE_S)
        for i in range(4)
    )
    rescue=[]
    for i,sat in enumerate(sats):
        r=min(sat+600,obligations[i].deadline_s-60)
        if r<=sat:
            raise ValueError('invalid rescue slot')
        rescue.append(r)

    worlds=[]
    seen=Counter()
    for missing in alias_set:
        if missing[0] not in {0,1} or missing[1] not in {2,3}:
            raise ValueError(missing)
        suffix=seen[missing]; seen[missing]+=1
        terrestrial=tuple(rescue[i] for i in range(4) if i not in set(missing))
        prehistory=_prehistory_events(missing,decision_t=start)
        state=_aggregate_gateway_state(prehistory,decision_t=start)
        worlds.append(World(
            world_id=f'missing-{missing[0]}-{missing[1]}-v{suffix}',
            terrestrial_slots=terrestrial,
            evidence_values=_evidence_values(
                events=prehistory,decision_t=start,profile=evidence_profile,queries=queries
            ),
            query_reachable=bool(state['primary_health']['query_path_reachable']),
            prehistory_events=prehistory,
        ))

    fixed={start,*sats,*rescue}
    for o in obligations:
        fixed.add(o.release_s); fixed.add(o.deadline_s)
    return Bundle(
        bundle_id='v04-'+_stable_id({'phase_index':phase_index,'start':start,'sats':sats,'alias_set':alias_set,'evidence_profile':evidence_profile,'catalog_size':catalog_size}),
        fixed_event_times=tuple(sorted(fixed)),
        obligations=obligations,
        satellite_slots=sats,
        worlds=tuple(worlds),
        satellite_budget=2,
        queries=queries,
        initial_public_observation=(
            ('warning','orange'),
            ('report_period_s',str(CADENCE_S)),
            ('satellite_budget','2'),
            ('gateway_health','stale'),
            ('receipt_state','stale'),
        ),
    )


def label(bundle:Bundle) -> tuple[str,tuple[str,...],bool,bool]:
    all_q=frozenset(q.query_id for q in bundle.queries)
    no_query=solve(bundle,disabled_queries=all_q)
    exact=solve(bundle)
    if no_query['solvable']:
        return 'NO_PAID_QUERY',(),True,True
    if not exact['solvable']:
        return 'INFORMATION_INFEASIBLE',(),False,False
    plan,_=exhaustive_query_search(bundle)
    return plan.mode,plan.selected_query_ids,False,True


def generate(*,phase_limit:int=4,catalog_size:int=5) -> list[GeneratedBundle]:
    rows=[]
    for phase_index,(start,sats) in enumerate(phase_groups(4,phase_limit)):
        for alias_set in ALIAS_SETS:
            for profile in EVIDENCE_PROFILES:
                b=build_bundle(
                    phase_index=phase_index,start=start,sats=sats,
                    alias_set=alias_set,evidence_profile=profile,catalog_size=catalog_size,
                )
                outcome,selected,noq,exact=label(b)
                rows.append(GeneratedBundle(
                    bundle=b,
                    coordinates={
                        'phase_index':phase_index,
                        'alias_set':[list(x) for x in alias_set],
                        'evidence_profile':profile,
                        'catalog_size':catalog_size,
                        'conflict_count':int(len({x[0] for x in alias_set})>1)+int(len({x[1] for x in alias_set})>1),
                    },
                    outcome_class=outcome,
                    selected_query_ids=selected,
                    no_query_solvable=noq,
                    exact_solvable=exact,
                ))
    return rows


def summarize(rows:list[GeneratedBundle]) -> dict[str,Any]:
    return {
        'bundle_count':len(rows),
        'outcome_counts':dict(sorted(Counter(r.outcome_class for r in rows).items())),
        'mean_selected_query_count':(
            sum(len(r.selected_query_ids) for r in rows if r.exact_solvable)/
            max(1,sum(r.exact_solvable for r in rows))
        ),
        'exact_solvable_count':sum(r.exact_solvable for r in rows),
        'no_query_solvable_count':sum(r.no_query_solvable for r in rows),
    }


if __name__=='__main__':
    print(json.dumps(summarize(generate()),indent=2,sort_keys=True))
