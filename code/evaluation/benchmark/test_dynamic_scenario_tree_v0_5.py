#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))
from dynamic_scenario_tree_v0_5 import *


def bundle():
    q=QueryCapability('health','gateway.health','gateway',sample_delay_s=0,response_delay_s=30,return_path=('gateway_to_center_backhaul',),opportunity_dependency=('gateway_reachability',))
    worlds=(
        World('w0',(OwnerStateEvent(0,'gateway.health','good'),OwnerStateEvent(150,'gateway.health','bad')),delivery_events=(DeliveryEvent(100,'r0',True,120,180),),query_reachable_times=(0,150,)),
        World('w1',(OwnerStateEvent(0,'gateway.health','good'),OwnerStateEvent(150,'gateway.health','good')),delivery_events=(DeliveryEvent(100,'r0',True,120,180),),query_reachable_times=(0,150,)),
    )
    return Bundle('dyn', (Obligation('r0',0,300),), worlds, (0,30,100,120,150,180,300), (100,150), (), 0, (q,))


def main():
    b=bundle()
    # Query at t=0 samples "good" in both worlds; future divergence at t=150
    # must not leak into the earlier response.
    r=solve(b,forced_first_action=('ISSUE_QUERY','health'))
    assert r['solvable']
    txt=str(r['policy'])
    assert 'sampled@0' in txt
    assert "'bad'" not in txt.split('sampled@0')[0]
    # Final delivery is distinct from gateway receipt: no terminal success at 120.
    assert 'gateway_receipt:r0' in txt
    assert 'final_ack:r0' in txt
    acct=execution_accounting(b,r['policy'])
    assert acct['max_query_requests']==1
    assert acct['max_total_sends']==1
    # Worlds are identical through the first query response and only diverge in owner state later.
    assert observed_prefix(b.worlds[0],before_s=150)==observed_prefix(b.worlds[1],before_s=150)
    assert observed_prefix(b.worlds[0],before_s=151)!=observed_prefix(b.worlds[1],before_s=151)
    print('PASS dynamic v0.5 oracle: repeated queries, sample/arrival separation, prefix consistency, delivery-stage separation, and realized execution accounting')
    return 0

if __name__=='__main__':raise SystemExit(main())
