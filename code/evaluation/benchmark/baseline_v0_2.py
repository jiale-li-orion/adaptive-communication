#!/usr/bin/env python3
"""Strong non-learning baseline audit for the minimal v0.2 prototype."""
from __future__ import annotations
from collections import Counter
from typing import Any
from scenario_generator_v0_2 import generate
from scenario_tree_oracle import solve


def always_query(row: dict[str,Any]) -> bool:
    return solve(
        row['bundle'],
        allow_query=True,
        forced_first_action=('QUERY',None),
    )['solvable']


def never_query_exact(row: dict[str,Any]) -> bool:
    return solve(row['bundle'],allow_query=False)['solvable']


def shallow_rule(row: dict[str,Any]) -> bool:
    """Depth-2 timing rule, followed by exact no-query continuation.

    1. If free passive evidence arrives before the first satellite slot, wait.
    2. Else if paid query completes before the first satellite slot, query.
    3. Else use no-paid-query exact continuation.

    This is deliberately strong as a shortcut detector.
    """
    b=row['bundle']
    start=b.decision_times[0]
    first_sat=min(b.satellite_slots)
    passive_times=[
        w.passive_evidence_at_s for w in b.worlds
        if w.passive_evidence_at_s is not None
    ]
    if passive_times and max(passive_times)<first_sat:
        return solve(b,allow_query=False,forced_first_action=('WAIT',None))['solvable']
    if start+b.query_delay_s<first_sat:
        return always_query(row)
    return never_query_exact(row)


def audit():
    rows=generate()
    result={}
    for name,fn in [
        ('always_query_then_plan',always_query),
        ('never_query_exact',never_query_exact),
        ('depth2_timing_rule',shallow_rule),
    ]:
        c=Counter()
        for r in rows:
            ok=fn(r)
            c['success' if ok else 'fail']+=1
            c[r['kind']+('_success' if ok else '_fail')]+=1
        result[name]=dict(c)
    return {'bundles':len(rows),'baselines':result}


if __name__=='__main__':
    import json
    print(json.dumps(audit(),indent=2,sort_keys=True))
