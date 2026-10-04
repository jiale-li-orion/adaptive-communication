#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
if str(HERE) not in sys.path: sys.path.insert(0,str(HERE))
if str(ROOT/'code') not in sys.path: sys.path.insert(0,str(ROOT/'code'))
from placement_ledger_v0_4 import placement_ledger


def main() -> int:
    r=placement_ledger(phase_limit=1,catalog_size=5)
    g=r['planner_placements']['gateway']
    c=r['planner_placements']['center']
    assert g['conflict_guided']['selected_query_count']==c['conflict_guided']['selected_query_count']
    assert g['conflict_guided']['ledger']['remote_acquisition']['request_count']==0
    assert g['conflict_guided']['ledger']['local_context']['read_count']>0
    assert c['conflict_guided']['ledger']['remote_acquisition']['request_count']>0
    assert c['conflict_guided']['ledger']['local_context']['read_count']==0
    assert c['conflict_guided']['ledger']['remote_acquisition']['unknown_transport_cost_count']==c['conflict_guided']['selected_query_count']
    assert g['conflict_guided']['mean_selected_query_count'] < g['fixed_pair']['mean_selected_query_count'] < g['always_all']['mean_selected_query_count']
    print('PASS placement ledger: gateway-local context selection and center-remote acquisition are accounted separately')
    return 0


if __name__=='__main__': raise SystemExit(main())
