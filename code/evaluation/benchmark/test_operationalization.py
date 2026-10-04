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
from oracle_preflight import preflight_case
from source_derivation import expand_source_ranges

BASE=ROOT/'local_research/current/benchmark/task-design/operational-needs'

def load(name): return json.loads((BASE/name).read_text())

def main() -> int:
    tasks=load('SOURCE-PROFILE-REGISTRY.v0.1.json')['profiles']
    caps=load('CAPABILITY-PROFILE-REGISTRY.v0.1.json')['profiles']
    traces=load('TRACE-PROFILE-REGISTRY.v0.1.json')['profiles']
    payload=load('PAYLOAD-PROFILE-REGISTRY.v0.1.json')['profiles'][0]
    service=load('SERVICE-TRACE-PROFILE-REGISTRY.v0.1.json')['profiles'][0]
    mapping=load('T1-SIMULATOR-MAPPING.v0.1.json')
    cases=expand_source_ranges(compile_ready_registry(tasks))
    cap=next(p for p in caps if p['capability_profile_id']=='PLAN_S_CONNECTA_IOT_MODULE_D2S')
    trace=next(p for p in traces if p['trace_profile_id']=='CONNECTA_20260922_SIHUI_GEOMETRY_48H')
    worlds=augment_db44_universe(cases,capability_profile=cap,trace_profile=trace,trace_payload=json.loads((ROOT/trace['trace_ref']).read_text()))
    one=operationalize_upper_envelope(worlds[0],payload_profile=payload,service_profile=service)
    assert one['world']['report_payload_bytes']==32
    assert one['world']['selected_path_constraints']['max_payload_bytes']==51
    assert one['variable_provenance']['path_service_success_semantics']['class']=='CONTROLLED_STRESS'
    pf=preflight_case(one,mapping=mapping,capability_profiles=caps)
    assert pf['oracle_ready'], pf
    assert pf['blocking_fields']==[]
    print('PASS operationalization: 32 B source-example payload + controlled service upper envelope clears V1 preflight')
    return 0

if __name__=='__main__': raise SystemExit(main())
