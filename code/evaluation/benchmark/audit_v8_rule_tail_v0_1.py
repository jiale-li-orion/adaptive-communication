#!/usr/bin/env python3
"""Cheap V8 tail rules on survivors after the first policy ladder."""
from __future__ import annotations

from collections import Counter
import json

from audit_v8_baselines_v0_1 import _representatives
from v8_policy_baselines_v0_1 import (
    solve_always_query_then_plan,
    solve_latest_feasible_send,
    solve_least_slack,
    solve_myopic_flow_voi,
)


def audit() -> dict:
    deep=json.load(open('results/benchmark/layer1-v8-deep-horizon-v0.1.json',encoding='utf-8'))
    ids={str(r['recipe_id']) for r in deep['rows'] if r['disposition']=='SURVIVES_DEEP_HORIZON_V0_1'}
    reps={str(b['recipe_id']):(cell,b) for cell,(_rank,b) in _representatives().items() if str(b['recipe_id']) in ids}
    coverage=Counter(); disposition=Counter(); rows=[]
    for rid in sorted(ids):
        cell,bundle=reps[rid]
        results={
            'always_query_then_plan':solve_always_query_then_plan(bundle),
            'latest_feasible_send':solve_latest_feasible_send(bundle),
            'least_slack':solve_least_slack(bundle),
            'myopic_flow_voi':solve_myopic_flow_voi(bundle),
        }
        winners=sorted(k for k,v in results.items() if v['solvable'])
        for w in winners: coverage[w]+=1
        cls='SHORTCUT_SOLVED_RULE_TAIL' if winners else 'SURVIVES_RULE_TAIL_V0_1'
        disposition[cls]+=1
        rows.append({'recipe_id':rid,'cell':list(cell),'disposition':cls,'winning_baselines':winners})
    return {
        'schema_version':'0.1',
        'status':'V8_RULE_TAIL_AUDIT',
        'input_survivor_count':len(ids),
        'disposition':dict(sorted(disposition.items())),
        'baseline_coverage':dict(sorted(coverage.items())),
        'rows':rows,
    }


if __name__=='__main__':
    print(json.dumps(audit(),ensure_ascii=False,indent=2,sort_keys=True))
