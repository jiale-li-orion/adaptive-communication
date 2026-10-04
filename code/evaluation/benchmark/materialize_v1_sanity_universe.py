#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import json, sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
if str(HERE) not in sys.path: sys.path.insert(0,str(HERE))

from case_augmentation import augment_db44_universe
from case_generation import compile_ready_registry
from case_operationalization import operationalize_upper_envelope
from oracle_preflight import preflight_universe
from source_derivation import expand_source_ranges
from v1_upper_envelope_oracle import solve_phase_surface

BASE=ROOT/'local_research/current/benchmark/task-design/operational-needs'
OUT=ROOT/'local_research/current/benchmark/generated/case-universe-v0.4-v1-sanity'

def load(name): return json.loads((BASE/name).read_text())

def main() -> int:
    tasks=load('SOURCE-PROFILE-REGISTRY.v0.1.json')['profiles']
    caps=load('CAPABILITY-PROFILE-REGISTRY.v0.1.json')['profiles']
    traces=load('TRACE-PROFILE-REGISTRY.v0.1.json')['profiles']
    payload=load('PAYLOAD-PROFILE-REGISTRY.v0.1.json')['profiles'][0]
    service=load('SERVICE-TRACE-PROFILE-REGISTRY.v0.1.json')['profiles'][0]
    mapping=load('T1-SIMULATOR-MAPPING.v0.1.json')
    source=expand_source_ranges(compile_ready_registry(tasks))
    cap=next(p for p in caps if p['capability_profile_id']=='PLAN_S_CONNECTA_IOT_MODULE_D2S')
    trace=next(p for p in traces if p['trace_profile_id']=='CONNECTA_20260922_SIHUI_GEOMETRY_48H')
    trace_payload=json.loads((ROOT/trace['trace_ref']).read_text())

    worlds=augment_db44_universe(source,capability_profile=cap,trace_profile=trace,trace_payload=trace_payload)
    worlds=[
        operationalize_upper_envelope(w,payload_profile=payload,service_profile=service)
        for w in worlds
    ]
    preflight=preflight_universe(worlds,mapping=mapping,capability_profiles=caps)
    assert all(row['oracle_ready'] for row in preflight)
    oracle=[solve_phase_surface(w,trace_payload=trace_payload) for w in worlds]

    OUT.mkdir(parents=True,exist_ok=True)
    case_dir=OUT/'cases'; case_dir.mkdir(exist_ok=True)
    for old in case_dir.glob('*.json'): old.unlink()

    for w,pf,orow in zip(worlds,preflight,oracle):
        out=dict(w)
        out['pre_oracle']=pf
        out['v1_sanity_oracle']=orow
        safe=w['case_id'].replace('::','__').replace('/','_')
        (case_dir/f'{safe}.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')

    by_status=Counter(r['status'] for r in oracle)
    by_mask=defaultdict(list)
    by_interval=defaultdict(list)
    for w,r in zip(worlds,oracle):
        if r['horizon_sufficient']:
            by_mask[str(r['elevation_mask_deg'])].append(r['solvable_phase_fraction'])
            by_interval[str(r['report_interval_s'])].append(r['solvable_phase_fraction'])

    manifest={
      'schema_version':'0.4',
      'stage':'V1_UPPER_ENVELOPE_PHASE_SOLVABILITY_SANITY',
      'world_count':len(worlds),
      'preflight_ready_count':sum(x['oracle_ready'] for x in preflight),
      'oracle_status_counts':dict(sorted(by_status.items())),
      'horizon_evaluable_count':sum(r['horizon_sufficient'] for r in oracle),
      'horizon_insufficient_count':sum(not r['horizon_sufficient'] for r in oracle),
      'phase_binding_world_count':sum(r.get('phase_binding') is True for r in oracle),
      'all_phase_solvable_world_count':sum(r.get('all_phase_solvable') is True for r in oracle),
      'mean_solvable_phase_fraction_by_mask':{
        k:sum(v)/len(v) for k,v in sorted(by_mask.items(),key=lambda x:int(x[0]))
      },
      'mean_solvable_phase_fraction_by_interval_s':{
        k:sum(v)/len(v) for k,v in sorted(by_interval.items(),key=lambda x:int(x[0]))
      },
      'task_profile':'DB44T2457_2024_warning_reporting',
      'site_profile':'GUANGDONG_SIHUI_HIGH_SCHOOL_LANDSLIDE',
      'capability_profile':cap['capability_profile_id'],
      'geometry_trace_profile':trace['trace_profile_id'],
      'payload_profile':payload['payload_profile_id'],
      'service_profile':service['service_trace_profile_id'],
      'claim_boundary':[
        'V1 sanity only; no decision-benchmark admission.',
        'Service success is an explicit upper-envelope controlled stress profile.',
        'Release phase is exhaustively evaluated at the 60 s trace resolution; no arbitrary phase is selected.',
        'TRACE_HORIZON_INSUFFICIENT is not treated as unsolvable.',
        'Payload is one exact 32 B DZ/T 0450 Type-1 source example, not a payload distribution.'
      ]
    }
    (OUT/'MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(manifest,ensure_ascii=False,indent=2))
    return 0

if __name__=='__main__': raise SystemExit(main())
