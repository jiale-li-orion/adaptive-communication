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
from v2_v3_dual_path_audit import audit_phase_surface

BASE=ROOT/'local_research/current/benchmark/task-design/operational-needs'

def load(name): return json.loads((BASE/name).read_text())

def main() -> int:
    tasks=load('SOURCE-PROFILE-REGISTRY.v0.1.json')['profiles']
    caps=load('CAPABILITY-PROFILE-REGISTRY.v0.1.json')['profiles']
    traces=load('TRACE-PROFILE-REGISTRY.v0.1.json')['profiles']
    payload=load('PAYLOAD-PROFILE-REGISTRY.v0.1.json')['profiles'][0]
    service=load('SERVICE-TRACE-PROFILE-REGISTRY.v0.1.json')['profiles'][0]
    outage=load('OUTAGE-STRESS-PROFILE-REGISTRY.v0.1.json')['profiles'][0]
    source=expand_source_ranges(compile_ready_registry(tasks))
    cap=next(p for p in caps if p['capability_profile_id']=='PLAN_S_CONNECTA_IOT_MODULE_D2S')
    trace=next(p for p in traces if p['trace_profile_id']=='CONNECTA_20260922_SIHUI_GEOMETRY_48H')
    trace_payload=json.loads((ROOT/trace['trace_ref']).read_text())
    worlds=augment_db44_universe(source,capability_profile=cap,trace_profile=trace,trace_payload=trace_payload)
    worlds=[operationalize_upper_envelope(w,payload_profile=payload,service_profile=service) for w in worlds]

    rows=[]
    for w in worlds:
        for ratio in outage['duration_over_deadline_cells']:
            rows.append(audit_phase_surface(w,trace_payload=trace_payload,outage_duration_over_deadline=ratio))

    audited=[r for r in rows if r['status']=='AUDITED']
    assert audited
    assert all(r['common_safe_violation_count']==0 for r in audited)
    assert all(r['ordinary_matches_oracle'] for r in audited)
    assert any(r['v2_multiple_legal_options_observed'] for r in audited)
    assert all(not r['v3_no_common_safe_policy'] for r in audited)
    assert all(r['disposition']=='COMMON_SAFE_POLICY' for r in audited)

    print(
        'PASS V2/V3 dual-path audit: multiple legal success plans exist, but ordinary '
        'earliest-available fallback matches any-path oracle in every solvable audited phase'
    )
    return 0

if __name__=='__main__': raise SystemExit(main())
