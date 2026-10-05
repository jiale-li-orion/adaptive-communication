#!/usr/bin/env python3
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
MANIFEST=ROOT/'results/benchmark/layer1-release-manifest-v0.1.json'


def validate()->int:
    m=json.loads(MANIFEST.read_text(encoding='utf-8'))
    bad=[]
    for row in m['files']:
        p=ROOT/row['path']
        if not p.exists() or sha256(p.read_bytes()).hexdigest()!=row['sha256']:
            bad.append(row['path'])
    if bad:
        print(json.dumps({'status':'FAIL','digest_mismatch':bad},indent=2)); return 1
    print(json.dumps({'status':'PASS','benchmark_version':m['benchmark_version'],'validated_file_count':len(m['files'])},indent=2)); return 0


def run(cmd:list[str])->None:
    subprocess.run(cmd,cwd=ROOT,check=True)


def rebuild_light()->None:
    py=sys.executable
    env={'PYTHONPATH':'code/evaluation/benchmark'}
    commands=[
        f'{py} code/evaluation/benchmark/build_structure_aware_split_v0_1.py > results/benchmark/layer1-structure-aware-split-v0.1.json',
        f'{py} code/evaluation/benchmark/audit_split_coverage_v0_1.py > results/benchmark/layer1-split-coverage-v0.1.json',
        f'{py} code/evaluation/benchmark/freeze_public_test_v0_1.py > results/benchmark/layer1-public-test-freeze-v0.1.json',
        f'{py} code/evaluation/benchmark/build_human_source_audit_sample_v0_1.py > results/benchmark/layer1-human-source-audit-v0.1.json',
        f'{py} code/evaluation/benchmark/freeze_release_manifest_v0_1.py > results/benchmark/layer1-release-manifest-v0.1.json',
        f'{py} code/evaluation/benchmark/audit_quality_gates_v0_1.py > results/benchmark/layer1-quality-gates-v0.1.json',
    ]
    for command in commands:
        subprocess.run(['bash','-lc',f'PYTHONPATH={env["PYTHONPATH"]} {command}'],cwd=ROOT,check=True)


def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--rebuild-light',action='store_true')
    args=ap.parse_args()
    if args.rebuild_light: rebuild_light()
    return validate()


if __name__=='__main__': raise SystemExit(main())
