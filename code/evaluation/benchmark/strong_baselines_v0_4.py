#!/usr/bin/env python3
from __future__ import annotations
from itertools import combinations
from typing import Any
import json

from delivery_constraint_graph import world_resource_signatures
from multi_evidence_conflict_planner import assess_query_subset
from scenario_generator_v0_4 import generate


def _conflict_score(bundle, qid: str) -> int:
    sig=world_resource_signatures(bundle)
    worlds=list(bundle.worlds)
    vals={w.world_id:dict(w.evidence_values)[qid] for w in worlds}
    score=0
    for i,a in enumerate(worlds):
        for b in worlds[i+1:]:
            if sig[a.world_id] != sig[b.world_id] and vals[a.world_id] != vals[b.world_id]:
                score += 1
    return score


def myopic_conflict_latency(bundle) -> bool:
    if assess_query_subset(bundle,()).solvable:
        return True
    ranked=[]
    for q in bundle.queries:
        ranked.append((-( _conflict_score(bundle,q.query_id) / max(1,q.delay_s)), q.delay_s, q.query_id))
    if not ranked:
        return False
    ranked.sort()
    chosen=ranked[0][2]
    return assess_query_subset(bundle,(chosen,)).solvable


def depth2_belief(bundle) -> bool:
    if assess_query_subset(bundle,()).solvable:
        return True
    ids=tuple(q.query_id for q in bundle.queries)
    for width in (1,2):
        for subset in combinations(ids,width):
            if assess_query_subset(bundle,tuple(subset)).solvable:
                return True
    return False


def audit(*,phase_limit:int=4,catalog_size:int=5) -> dict[str,Any]:
    rows=[r for r in generate(phase_limit=phase_limit,catalog_size=catalog_size) if r.exact_solvable]
    return {
        'denominator_exact_solvable':len(rows),
        'no_paid_query_exact_success':sum(assess_query_subset(r.bundle,()).solvable for r in rows),
        'myopic_conflict_latency_success':sum(myopic_conflict_latency(r.bundle) for r in rows),
        'depth2_belief_success':sum(depth2_belief(r.bundle) for r in rows),
        'interpretation':{
            'myopic_conflict_latency':'one query chosen only from current delivery-conflict separation per unit delay; no future query composition',
            'depth2_belief':'exact observation-matched continuation with at most two enabled paid evidence capabilities',
        },
    }


if __name__=='__main__':
    print(json.dumps(audit(),indent=2,sort_keys=True))
