#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))
from dynamic_scenario_tree_v0_5 import *
from dynamic_feasibility_frontier_v0_5 import DynamicFeasibilityFrontier
from scenario_generator_v0_5 import build_bundle


def main():
    # P0: late final ACK cannot repair a missed deadline.
    b=Bundle('late',(Obligation('r',0,100),),(
        World('w',(),delivery_events=(DeliveryEvent(90,'r',True,95,120),)),
    ),(0,90,95,100,120),(90,),(),0,())
    assert not solve(b,forced_first_action=('SEND_TERR','r'))['solvable']

    # P0: query observation obeys sample/arrival and timeout contract.
    g=build_bundle();f=DynamicFeasibilityFrontier(g);start=min(g.fixed_event_times)
    n=f.apply_query_observation(query_id='primary_health',sampled_at_s=start,arrival_at_s=start+120,value='healthy')
    assert n==len(g.worlds)
    ref,_=f.reference_rebuild();assert f.snapshot()==ref

    # P0: gateway receipt prevents double-counting the same in-flight report as needing backup.
    oid='A0';f.apply_gateway_receipt(oid,at_s=start+1000)
    assert oid in f.snapshot().pending_cover
    assert all(oid not in c.obligations for c in f.snapshot().certificates)

    # P0: crossing an opportunity outside the current deficiency set still forces rebuild.
    before=f.flow_solves
    target=next(t for t in sorted(set(g.terrestrial_send_times)|set(g.satellite_send_times)) if t>f.at_s)
    f.advance_time(target)
    assert f.flow_solves>before
    ref,_=f.reference_rebuild();assert f.snapshot()==ref
    print('PASS v0.5 P0 blockers: late ACK deadline, timed query/timeout semantics, in-flight cover, and safe opportunity invalidation')
    return 0

if __name__=='__main__':raise SystemExit(main())
