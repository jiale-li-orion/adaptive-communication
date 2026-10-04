#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
if str(HERE) not in sys.path: sys.path.insert(0,str(HERE))

from case_augmentation import augment_db44_universe
from case_generation import compile_ready_registry
from case_operationalization import operationalize_upper_envelope
from source_derivation import expand_source_ranges
from v1_upper_envelope_oracle import solve_phase_surface

BASE=ROOT/'local_research/current/benchmark/task-design/operational-needs'

def load(name): return json.loads((BASE/name).read_text())

def main() -> int:
    tasks=load('SOURCE-PROFILE-REGISTRY.v0.1.json')['profiles']
    caps=load('CAPABILITY-PROFILE-REGISTRY.v0.1.json')['profiles']
    traces=load('TRACE-PROFILE-REGISTRY.v0.1.json')['profiles']
    payload=load('PAYLOAD-PROFILE-REGISTRY.v0.1.json')['profiles'][0]
    service=load('SERVICE-TRACE-PROFILE-REGISTRY.v0.1.json')['profiles'][0]
    source=expand_source_ranges(compile_ready_registry(tasks))
    cap=next(p for p in caps if p['capability_profile_id']=='PLAN_S_CONNECTA_IOT_MODULE_D2S')
    trace=next(p for p in traces if p['trace_profile_id']=='CONNECTA_20260922_SIHUI_GEOMETRY_48H')
    trace_payload=json.loads((ROOT/trace['trace_ref']).read_text())
    worlds=augment_db44_universe(source,capability_profile=cap,trace_profile=trace,trace_payload=trace_payload)
    worlds=[operationalize_upper_envelope(w,payload_profile=payload,service_profile=service) for w in worlds]
    rows=[solve_phase_surface(w,trace_payload=trace_payload) for w in worlds]

    assert len(rows)==135
    assert all(r['payload_fit'] for r in rows)
    assert sum(r['status']=='TRACE_HORIZON_INSUFFICIENT' for r in rows)==35
    evaluated=[r for r in rows if r['horizon_sufficient']]
    assert len(evaluated)==100
    assert all(r['solvable_phase_count']>0 for r in evaluated)
    assert any(r['status']=='SOLVABLE_SOME_PHASES' for r in evaluated)
    assert any(r['status']=='SOLVABLE_ALL_PHASES' for r in evaluated)
    assert all(r['field_reliability_claim'] is False for r in rows)

    red=[
        (w,r) for w,r in zip(worlds,rows)
        if w['world']['warning_state']=='red'
    ]
    assert len(red)==15
    assert all(r['phase_binding'] for _,r in red)

    print(
        'PASS V1 upper-envelope oracle: 135 worlds -> 100 horizon-evaluable, '
        '35 horizon-insufficient; short-cadence phases bind without reliability overclaim'
    )
    return 0

if __name__=='__main__': raise SystemExit(main())
