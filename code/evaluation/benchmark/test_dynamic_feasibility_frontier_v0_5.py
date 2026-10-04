#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))
from dynamic_feasibility_frontier_v0_5 import DynamicFeasibilityFrontier
from scenario_generator_v0_5 import build_bundle


def canonical(s):
    return (s.active_world_ids,s.delivered,s.at_s,s.satellite_budget,tuple((c.world_ids,c.obligations,c.usable_terrestrial_times,c.required_backup) for c in s.certificates))


def main():
    b=build_bundle();f=DynamicFeasibilityFrontier(b);start=min(b.fixed_event_times)
    # Shared-prefix query gives identical value in all worlds and costs zero flow recomputation.
    n=f.apply_query_observation(query_id='primary_health',sampled_at_s=start,value='healthy')
    assert n==0
    ref,flows=f.reference_rebuild();assert canonical(f.snapshot())==canonical(ref)
    assert flows==len(b.worlds)
    # At first future transition, query narrows worlds; incremental filtering again avoids flow recompute.
    n=f.apply_query_observation(query_id='primary_health',sampled_at_s=start+7200,value='healthy')
    assert n==0
    ref,_=f.reference_rebuild();assert canonical(f.snapshot())==canonical(ref)
    assert len(f.snapshot().active_world_ids)==2

    # Final ACK changes the remaining obligation set: incremental rebuild must
    # match a clean rebuild on the same legal prefix.
    ack_t=start+8100+180
    n=f.apply_final_ack('A1',at_s=ack_t)
    assert n==len(f.snapshot().active_world_ids)
    ref,_=f.reference_rebuild();assert canonical(f.snapshot())==canonical(ref)

    # An irreversible satellite commit changes both completion state and shared budget.
    sat_t=next(t for t in b.satellite_send_times if t>=ack_t)
    candidate=next(o.oid for o in b.obligations if o.oid not in f.delivered and o.release_s<=sat_t<=o.deadline_s)
    n=f.apply_satellite_commit(candidate,at_s=sat_t)
    assert n==len(f.snapshot().active_world_ids)
    ref,_=f.reference_rebuild();assert canonical(f.snapshot())==canonical(ref)

    # Time movement inside a certificate-valid interval reuses the frontier;
    # crossing a represented terrestrial opportunity triggers recomputation.
    n=f.advance_time(sat_t+1)
    assert n==0
    ref,_=f.reference_rebuild();assert canonical(f.snapshot())==canonical(ref)
    future=sorted({t for c in f.snapshot().certificates for t in c.usable_terrestrial_times if t>=f.at_s})
    if future:
        n=f.advance_time(future[0]+1)
        assert n==len(f.snapshot().active_world_ids)
        ref,_=f.reference_rebuild();assert canonical(f.snapshot())==canonical(ref)

    print('PASS dynamic frontier v0.5: query/ACK/budget/time incremental updates match full rebuild; unaffected prefixes reuse certificates')
    return 0

if __name__=='__main__':raise SystemExit(main())
