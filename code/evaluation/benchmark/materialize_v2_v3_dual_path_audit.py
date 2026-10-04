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
from source_derivation import expand_source_ranges
from v2_v3_dual_path_audit import audit_phase_surface

BASE=ROOT/'local_research/current/benchmark/task-design/operational-needs'
OUT=ROOT/'local_research/current/benchmark/generated/v2-v3-dual-path-audit-v0.1'

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
    tp=json.loads((ROOT/trace['trace_ref']).read_text())
    worlds=augment_db44_universe(source,capability_profile=cap,trace_profile=trace,trace_payload=tp)
    worlds=[operationalize_upper_envelope(w,payload_profile=payload,service_profile=service) for w in worlds]

    rows=[]
    for w in worlds:
        for ratio in outage['duration_over_deadline_cells']:
            r=audit_phase_surface(w,trace_payload=tp,outage_duration_over_deadline=ratio)
            rows.append({
                'case_id':w['case_id'],
                'warning_state':w['world']['warning_state'],
                'monitoring_grade':w['world']['monitoring_grade'],
                **r,
            })

    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'ROWS.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    audited=[r for r in rows if r['status']=='AUDITED']
    by_ratio=defaultdict(list)
    for r in audited: by_ratio[str(r['outage_duration_over_deadline'])].append(r)

    manifest={
      'schema_version':'0.1',
      'stage':'V2_V3_DUAL_PATH_DECISION_VALIDITY_AUDIT',
      'row_count':len(rows),
      'audited_row_count':len(audited),
      'horizon_insufficient_row_count':sum(r['status']=='TRACE_HORIZON_INSUFFICIENT' for r in rows),
      'rows_with_multiple_legal_success_plans':sum(r.get('v2_multiple_legal_options_observed') is True for r in audited),
      'rows_with_common_safe_violation':sum(r.get('common_safe_violation_count',0)>0 for r in audited),
      'ordinary_matches_oracle_rows':sum(r.get('ordinary_matches_oracle') is True for r in audited),
      'disposition_counts':dict(Counter(r.get('disposition','NA') for r in audited)),
      'by_outage_ratio':{
        k:{
          'rows':len(v),
          'multiple_option_rows':sum(x['v2_multiple_legal_options_observed'] for x in v),
          'common_safe_violation_rows':sum(x['common_safe_violation_count']>0 for x in v),
          'ordinary_matches_oracle_rows':sum(x['ordinary_matches_oracle'] for x in v)
        }
        for k,v in sorted(by_ratio.items(),key=lambda x:float(x[0]))
      },
      'conclusion':'This candidate dual-path family passes the existence-of-multiple-legal-options check in some cells but fails V3: an ordinary earliest-available/automatic-fallback policy is common-safe whenever any path can satisfy the single-report obligation.',
      'next_required_structure':[
        'source-backed cross-report resource coupling, quota, energy, capacity, or another constraint that makes using one path now change later obligation feasibility',
        'or a different operational task where waiting/querying changes the legal/feasible plan set'
      ],
      'claim_boundary':[
        'outage ratios are controlled stress, not field frequency',
        'service success uses the same upper-envelope sanity semantics as V1',
        'this is a degeneracy audit, not a benchmark admission result'
      ]
    }
    (OUT/'MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(manifest,ensure_ascii=False,indent=2))
    return 0

if __name__=='__main__': raise SystemExit(main())
