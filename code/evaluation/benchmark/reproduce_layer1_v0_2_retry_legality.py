#!/usr/bin/env python3
"""Validate or refresh the frozen Layer-1 v0.2 retry-legality release evidence.

The expensive exact/V0-V9/split generation is already frozen.  This entry
validates the release manifest by digest and can refresh only release-layer
evidence (Q11 sample/preaudit, Q0-Q12 audit and pre-release manifest).
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
R = ROOT / 'results/benchmark'
MANIFEST = R / 'layer1-release-manifest-v0.2-retry-legality.json'


def validate() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    bad = []
    for row in manifest['files']:
        path = ROOT / row['path']
        if not path.exists() or sha256(path.read_bytes()).hexdigest() != row['sha256']:
            bad.append(row['path'])
    if bad:
        print(json.dumps({'status': 'FAIL', 'digest_mismatch': bad}, indent=2))
        return 1
    print(json.dumps({
        'status': 'PASS',
        'benchmark_version': manifest['benchmark_version'],
        'validated_file_count': len(manifest['files']),
        'known_release_blockers': manifest['known_release_blockers'],
    }, ensure_ascii=False, indent=2))
    return 0


def run_shell(command: str, *, stdout: Path | None = None) -> None:
    proc = subprocess.run(
        ['bash', '-lc', f'PYTHONPATH=code/evaluation/benchmark {command}'],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=stdout is not None,
    )
    if stdout is not None:
        stdout.write_text(proc.stdout, encoding='utf-8')


def refresh_release_evidence() -> None:
    py = sys.executable
    run_shell(
        f'{py} code/evaluation/benchmark/build_human_source_audit_sample_v0_1.py '
        '--split results/benchmark/layer1-structure-aware-split-v0.2-retry-legality.json',
        stdout=R / 'layer1-human-source-audit-v0.2-retry-legality.json',
    )
    run_shell(
        f'{py} code/evaluation/benchmark/preaudit_human_source_sample_v0_1.py '
        '--audit results/benchmark/layer1-human-source-audit-v0.2-retry-legality.json '
        '--split results/benchmark/layer1-structure-aware-split-v0.2-retry-legality.json '
        '--exact-recipe local_research/current/benchmark/generated/exact-labels-v0.2-retry-legality/recipe-labels.jsonl '
        '--validity-recipe local_research/current/benchmark/generated/v0-v7-full-v0.2-retry-legality/recipe-validity.jsonl '
        '--v8-signature local_research/current/benchmark/generated/v8-all-pass-v0.2-retry-legality/signature-v8.jsonl',
        stdout=R / 'layer1-human-source-machine-preaudit-v0.2-retry-legality.json',
    )
    run_shell(
        f'{py} code/evaluation/benchmark/audit_agentic_reducibility_v0_2.py',
        stdout=R / 'layer1-agentic-reducibility-v0.2-retry-legality.json',
    )
    run_shell(
        f'{py} code/evaluation/benchmark/audit_communication_attribution_v0_2.py',
        stdout=R / 'layer1-communication-attribution-v0.2-retry-legality.json',
    )
    run_shell(
        f'{py} code/evaluation/benchmark/freeze_release_manifest_v0_2_retry_legality.py',
        stdout=R / 'layer1-release-manifest-v0.2-retry-legality.json',
    )
    run_shell(
        f'{py} code/evaluation/benchmark/audit_quality_gates_v0_1.py '
        '--v0-v7 results/benchmark/layer1-v0-v7-full-v0.2-retry-legality.json '
        '--v8 results/benchmark/layer1-v8-all-pass-v0.2-retry-legality.json '
        '--v9 results/benchmark/layer1-v9-evaluator-soundness-v0.2-retry-legality.json '
        '--split results/benchmark/layer1-structure-aware-split-v0.2-retry-legality.json '
        '--coverage results/benchmark/layer1-split-coverage-v0.2-retry-legality.json '
        '--public-test results/benchmark/layer1-public-test-freeze-v0.2-retry-legality.json '
        '--llm results/benchmark/layer1-llm-baseline-v0.2-retry-legality.json '
        '--human results/benchmark/layer1-human-source-audit-v0.2-retry-legality.json '
        '--release-manifest results/benchmark/layer1-release-manifest-v0.2-retry-legality.json '
        '--reproduction-entry code/evaluation/benchmark/reproduce_layer1_v0_2_retry_legality.py '
        '--agentic-reducibility results/benchmark/layer1-agentic-reducibility-v0.2-retry-legality.json '
        '--communication-attribution results/benchmark/layer1-communication-attribution-v0.2-retry-legality.json',
        stdout=R / 'layer1-quality-gates-v0.2-retry-legality.json',
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--refresh-release-evidence', action='store_true')
    args = ap.parse_args()
    if args.refresh_release_evidence:
        refresh_release_evidence()
    return validate()


if __name__ == '__main__':
    raise SystemExit(main())
