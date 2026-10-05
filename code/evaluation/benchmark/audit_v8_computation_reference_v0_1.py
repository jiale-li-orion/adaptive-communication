#!/usr/bin/env python3
"""Generic computation reference on current V8 survivors.

This audit is deliberately not a shortcut/admission verdict.  Exact success is
expected; the output is a computation floor for later incremental/context work.
"""
from __future__ import annotations

import json
from statistics import mean
from time import perf_counter

from audit_v8_baselines_v0_1 import _representatives
from causal_evidence_process_v0_1 import attach_causal_evidence
from exact_reference_oracle_v0_1 import solve_observation_matched


def _survivor_ids() -> set[str]:
    for path, label in (
        ('results/benchmark/layer1-v8-flow-terminal-v0.1.json', 'SURVIVES_FLOW_TERMINAL_V0_1'),
        ('results/benchmark/layer1-v8-deep-horizon-v0.1.json', 'SURVIVES_DEEP_HORIZON_V0_1'),
    ):
        try:
            d=json.load(open(path,encoding='utf-8'))
        except FileNotFoundError:
            continue
        return {str(r['recipe_id']) for r in d['rows'] if r['disposition']==label}
    raise FileNotFoundError('no V8 survivor audit available')


def audit() -> dict:
    ids=_survivor_ids()
    reps={str(b['recipe_id']):(cell,b) for cell,(_rank,b) in _representatives().items() if str(b['recipe_id']) in ids}
    rows=[]
    for rid in sorted(ids):
        cell,bundle=reps[rid]
        process=attach_causal_evidence(bundle)
        t0=perf_counter()
        exact=solve_observation_matched(bundle,process,max_memo_nodes=500_000)
        exact_ms=(perf_counter()-t0)*1000.0
        t0=perf_counter()
        no_query=solve_observation_matched(bundle,process,disable_paid_query=True,max_memo_nodes=500_000)
        no_query_ms=(perf_counter()-t0)*1000.0
        rows.append({
            'recipe_id':rid,
            'cell':list(cell),
            'exact':{
                'status':exact['status'],'solvable':exact['solvable'],
                'memo_nodes':exact['memo_nodes'],'attempt_lattice_size':exact['attempt_lattice_size'],
                'wall_ms':exact_ms,
            },
            'no_paid_query':{
                'status':no_query['status'],'solvable':no_query['solvable'],
                'memo_nodes':no_query['memo_nodes'],'attempt_lattice_size':no_query['attempt_lattice_size'],
                'wall_ms':no_query_ms,
            },
        })
    return {
        'schema_version':'0.1',
        'status':'V8_GENERIC_MEMOIZED_EXACT_COMPUTATION_REFERENCE',
        'role':'COMPUTATION_REFERENCE_NOT_ADMISSION_VERDICT',
        'survivor_count':len(rows),
        'summary':{
            'exact_mean_wall_ms':mean(r['exact']['wall_ms'] for r in rows) if rows else 0.0,
            'exact_max_wall_ms':max((r['exact']['wall_ms'] for r in rows),default=0.0),
            'exact_mean_memo_nodes':mean(r['exact']['memo_nodes'] for r in rows) if rows else 0.0,
            'exact_max_memo_nodes':max((r['exact']['memo_nodes'] for r in rows),default=0),
            'no_query_mean_wall_ms':mean(r['no_paid_query']['wall_ms'] for r in rows) if rows else 0.0,
            'no_query_max_wall_ms':max((r['no_paid_query']['wall_ms'] for r in rows),default=0.0),
        },
        'rows':rows,
    }


if __name__=='__main__':
    print(json.dumps(audit(),ensure_ascii=False,indent=2,sort_keys=True))
