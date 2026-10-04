#!/usr/bin/env python3
"""Fast admission gate for v0.5 dynamic process families.

Stage 1 is purely structural/physical and cheap. Exact policy search is only
allowed after a bundle passes physical feasibility and common-worst collapse.
"""
from __future__ import annotations
from dataclasses import asdict,dataclass
import json

from scenario_generator_v0_5 import build_bundle,build_receipt_race_bundle
from physical_admission_v0_5 import physical,sig


@dataclass(frozen=True)
class Admission:
    process_family:str
    phase_index:int
    per_world_physical:dict[str,bool]
    all_worlds_physical:bool
    common_worst_world:str|None
    exact_admit:bool
    status:str


def fast_audit(process_family:str,phase_index:int) -> Admission:
    b=build_bundle(process_family=process_family,phase_index=phase_index)
    per={w.world_id:physical(b,w) for w in b.worlds}
    ss={w.world_id:sig(b,w) for w in b.worlds}
    worst=next((wid for wid,s in ss.items() if all(s<=x for x in ss.values())),None)
    all_physical=all(per.values())
    if not all_physical:
        status='PHYSICAL_INFEASIBLE_SUPPORT'
    elif worst is not None:
        status='COMMON_WORST_COLLAPSE'
    else:
        status='EXACT_ADMIT_CANDIDATE'
    return Admission(process_family,phase_index,per,all_physical,worst,status=='EXACT_ADMIT_CANDIDATE',status)


def candidates(process_family:str='shifted-window',phase_count:int=4):
    return [fast_audit(process_family,i) for i in range(phase_count)]




def receipt_race_admission():
    from frontier_guided_planner_v0_5 import solve_frontier_guided
    from physical_admission_v0_5 import physical
    b=build_receipt_race_bundle()
    per={w.world_id:physical(b,w) for w in b.worlds}
    with_query=solve_frontier_guided(b)
    no_query=solve_frontier_guided(b,disabled_queries=frozenset(q.query_id for q in b.queries))
    info=all(per.values()) and bool(with_query['solvable']) and not bool(no_query['solvable'])
    return {
        'process_family':'receipt-race','phase_index':1,
        'per_world_physical':per,'all_worlds_physical':all(per.values()),
        'joint_with_query':bool(with_query['solvable']),
        'joint_no_query':bool(no_query['solvable']),
        'information_positive':info,
        'status':'INFORMATION_POSITIVE' if info else 'NOT_INFORMATION_POSITIVE',
    }

if __name__=='__main__':
    rows=[]
    rows.extend(candidates('independent-bits'))
    rows.extend(candidates('shifted-window'))
    print(json.dumps([asdict(x) for x in rows]+[receipt_race_admission()],indent=2,sort_keys=True))
