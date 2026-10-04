#!/usr/bin/env python3
"""Fast admission gate for v0.5 dynamic process families.

Stage 1 is purely structural/physical and cheap. Exact policy search is only
allowed after a bundle passes physical feasibility and common-worst collapse.
"""
from __future__ import annotations
from dataclasses import asdict,dataclass
import json

from scenario_generator_v0_5 import build_bundle
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


if __name__=='__main__':
    rows=[]
    rows.extend(candidates('independent-bits'))
    rows.extend(candidates('shifted-window'))
    print(json.dumps([asdict(x) for x in rows],indent=2,sort_keys=True))
