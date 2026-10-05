#!/usr/bin/env python3
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import argparse

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SPLIT=ROOT/'results/benchmark/layer1-structure-aware-split-v0.1.json'
CASES_PATH=ROOT/'results/benchmark/layer1-public-test-cases-v0.1.jsonl'


def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--split',type=Path,default=SPLIT); ap.add_argument('--cases-path',type=Path,default=CASES_PATH); args=ap.parse_args()
    split_path=args.split if args.split.is_absolute() else ROOT/args.split
    cases_path=args.cases_path if args.cases_path.is_absolute() else ROOT/args.cases_path
    split=json.loads(split_path.read_text(encoding='utf-8'))
    cases_path.parent.mkdir(parents=True,exist_ok=True)
    digest=sha256()
    count=0
    with cases_path.open('w',encoding='utf-8') as f:
        for r in split['rows']:
            if r['split']!='test':
                continue
            public={
                'recipe_id':r['recipe_id'],
                'bundle_id':r['bundle_id'],
                'task_case_id':r['task_case_id'],
                'geometry_signature_id':r['geometry_signature_id'],
                'geometry_shape_cluster':r['geometry_shape_cluster'],
                'service_process':r['service_process'],
                'evidence_regime':r['evidence_regime'],
                'overlap_count':r['overlap_count'],
                'resource_headroom':r['resource_headroom'],
                'recovery_regime':r['recovery_regime'],
            }
            line=json.dumps(public,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n'
            f.write(line); digest.update(line.encode('utf-8')); count+=1
    split_digest=sha256(split_path.read_bytes()).hexdigest()
    manifest={
        'schema_version':'0.1',
        'status':'FROZEN_PUBLIC_TEST_IDENTITY',
        'benchmark_version':'layer1-v0.1',
        'test_case_count':count,
        'public_cases_ref':str(cases_path.relative_to(ROOT)) if cases_path.is_relative_to(ROOT) else str(cases_path),
        'public_cases_sha256':digest.hexdigest(),
        'source_split_sha256':split_digest,
        'labels_withheld':['candidate_role','exact_classification','v0_v7_disposition','solver_signature','oracle/reference labels'],
        'mutation_policy':'Any change to case identity/order/content requires a new benchmark version.',
        'release_status':'PRE_RELEASE_FROZEN_TEST',
    }
    print(json.dumps(manifest,ensure_ascii=False,indent=2,sort_keys=True))
    return 0


if __name__=='__main__': raise SystemExit(main())
