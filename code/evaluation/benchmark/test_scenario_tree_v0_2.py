#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path: sys.path.insert(0,str(HERE))

from baseline_v0_2 import audit
from scenario_generator_v0_2 import generate

def main() -> int:
    rows=generate()
    assert len(rows)==72
    required=[r for r in rows if r['kind']=='QUERY_REQUIRED']
    harmful=[r for r in rows if r['kind']=='QUERY_HARMFUL']
    passive=[r for r in rows if r['kind']=='PASSIVE_BETTER']
    assert len(required)==len(harmful)==len(passive)==24

    assert all(all(r['hindsight'].values()) for r in required)
    assert all(r['query']['solvable'] for r in required)
    assert all(not r['no_query']['solvable'] for r in required)

    a=audit()
    assert a['baselines']['always_query_then_plan']['success']==24
    assert a['baselines']['always_query_then_plan']['fail']==48
    assert a['baselines']['never_query_exact']['success']==48
    assert a['baselines']['never_query_exact']['fail']==24
    assert a['baselines']['depth2_timing_rule']['success']==72

    # Deterministic IDs and ordering.
    ids=[r['bundle'].bundle_id for r in rows]
    ids2=[r['bundle'].bundle_id for r in generate()]
    assert ids==ids2
    assert len(ids)==len(set(ids))

    print(
        'PASS v0.2 alias-bundle mechanism: 24 genuine query-positive bundles; '
        'shortcut audit intentionally records depth-2 rule collapse 72/72'
    )
    return 0

if __name__=='__main__':
    raise SystemExit(main())
