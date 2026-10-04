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
    print('PASS dynamic frontier v0.5: incremental query updates equal full rebuild while avoiding unaffected flow recomputation')
    return 0

if __name__=='__main__':raise SystemExit(main())
