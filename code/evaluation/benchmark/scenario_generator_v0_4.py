#!/usr/bin/env python3
"""Process-generated multi-conflict evidence bundles for Layer-1 method evaluation."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any
from hashlib import sha256
import json

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




def _queries(catalog_size:int=5) -> tuple[EvidenceQuery,...]:
    base=[
        EvidenceQuery('primary_health','communication.gateway.primary_health','gateway',40),
        EvidenceQuery('receipt_summary','communication.gateway.receipt_summary','gateway',20),
    ]
    for i in range(max(0,catalog_size-2)):
        base.append(EvidenceQuery(
            f'node_report:noise{i}',
            'communication.gateway.node_report',
            'gateway',
            60+10*i,
        ))
    return tuple(base[:catalog_size])


def _canonical_observation(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _current_gateway_state(missing: tuple[int, int]) -> dict[str, dict[str, Any]]:
    """Generate current/past gateway facts from the latent service regime.

    The returned values are observations that could already exist at decision
    time. They do not contain future opportunity times, obligation IDs, oracle
    labels or direct "which report needs satellite" answers.

    The correlation between these current facts and the later finite-service
    pattern is part of the declared CONTROLLED_STRESS process model.
    """
    a, b = missing
    primary = (
        {
            "last_forward_age_s": 300,
            "pending_depth": 1,
            "oldest_pending_age_s": 420,
            "query_path_reachable": True,
        }
        if a == 0
        else {
            "last_forward_age_s": 5400,
            "pending_depth": 3,
            "oldest_pending_age_s": 6000,
            "query_path_reachable": True,
        }
    )
    receipt = (
        {
            "recent_receipt_count": 3,
            "last_receipt_age_s": 240,
            "missing_receipt_count": 0,
        }
        if b == 2
        else {
            "recent_receipt_count": 0,
            "last_receipt_age_s": 4800,
            "missing_receipt_count": 2,
        }
    )
    node = {
        "soc_bucket": "nominal",
        "cache_bucket": "noncritical",
        "config_generation": 1,
    }
    return {"primary_health": primary, "receipt_summary": receipt, "node_report": node}


def _evidence_values(missing:tuple[int,int],profile:str,queries:tuple[EvidenceQuery,...]) -> tuple[tuple[str,str],...]:
    state=_current_gateway_state(missing)
    primary_live=profile in {'BOTH','PRIMARY_ONLY'}
    receipt_live=profile in {'BOTH','RECEIPT_ONLY'}
    vals={
        'primary_health': (
            _canonical_observation(state['primary_health']) if primary_live else 'same'
        ),
        'receipt_summary': (
            _canonical_observation(state['receipt_summary']) if receipt_live else 'same'
        ),
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
        worlds.append(World(
            world_id=f'missing-{missing[0]}-{missing[1]}-v{suffix}',
            terrestrial_slots=terrestrial,
            evidence_values=_evidence_values(missing,evidence_profile,queries),
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
