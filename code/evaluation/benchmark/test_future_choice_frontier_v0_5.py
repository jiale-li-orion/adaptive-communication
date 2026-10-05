#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))
from dynamic_scenario_tree_v0_5 import LocalState,_normalize,_step_action
from future_choice_frontier_v0_5 import build_future_choice_frontier
from scenario_generator_v0_5 import build_overlapping_receipt_chain_bundle


def main():
    b=build_overlapping_receipt_chain_bundle(); start=min(b.fixed_event_times)
    states={w.world_id:LocalState(sat_budget=b.satellite_budget) for w in b.worlds}
    stepped=_step_action(b,start,states,('WAIT',None)); assert stepped is not None
    branches,t=stepped; states=branches['same']; assert t in b.terrestrial_send_times
    stepped=_step_action(b,t,states,('SEND_TERR','A')); assert stepped is not None
    branches,t=stepped; states=branches['same']
    norm=_normalize(b,t,states); assert tuple(norm)==('same',)
    states=norm['same']
    f=build_future_choice_frontier(b,t,states)
    assert 'receipt_summary' in f.frontier_relevant_queries
    qp=next(x for x in f.query_partitions if x.query_id=='receipt_summary')
    assert qp.changes_choice_frontier and len(qp.outcomes)==2
    assert f.valid_until_s is not None and f.valid_until_s>t
    print('PASS future-choice frontier: executed gateway receipt changes the preserved backup-choice frontier before center final ACK')
    return 0

if __name__=='__main__':raise SystemExit(main())
