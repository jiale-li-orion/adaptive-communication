#!/usr/bin/env python3
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]

FILES=[
    'research/benchmark/LAYER1-AUTHORITY.md',
    'research/benchmark/BENCHMARK-QUALITY-GATE.v0.1.md',
    'research/benchmark/V8-BASELINE-CONTRACT.v0.1.md',
    'research/benchmark/TASK-SURFACE-REGISTRY.v0.1.json',
    'research/benchmark/profiles/v0.1/SOURCE-PROFILE-REGISTRY.v0.1.json',
    'code/evaluation/benchmark/compositional_recipe_generator_v0_1.py',
    'code/evaluation/benchmark/dynamic_world_materializer_v0_1.py',
    'code/evaluation/benchmark/causal_evidence_process_v0_1.py',
    'code/evaluation/benchmark/exact_reference_oracle_v0_1.py',
    'code/evaluation/benchmark/validity_filters_v0_1.py',
    'code/evaluation/benchmark/v8_policy_baselines_v0_1.py',
    'code/evaluation/benchmark/execution_trace_evaluator_v0_1.py',
    'results/benchmark/layer1-exact-label-manifest-v0.1.json',
    'results/benchmark/layer1-v0-v7-full-v0.1.json',
    'results/benchmark/layer1-v8-all-pass-v0.1.json',
    'results/benchmark/layer1-v9-evaluator-soundness-v0.1.json',
    'results/benchmark/layer1-structure-aware-split-v0.1.json',
    'results/benchmark/layer1-split-coverage-v0.1.json',
    'results/benchmark/layer1-public-test-freeze-v0.1.json',
    'results/benchmark/layer1-public-test-cases-v0.1.jsonl',
    'results/benchmark/layer1-human-source-audit-v0.1.json',
    'research/benchmark/STATISTICAL-REPORTING.v0.1.md',
    'research/benchmark/BENCHMARK-MAINTENANCE.v0.1.md',
    'code/evaluation/benchmark/reproduce_layer1_v0_1.py',
]


def main()->int:
    files=list(FILES)
    llm=ROOT/'results/benchmark/layer1-llm-baseline-v0.1.json'
    if llm.exists():
        files.append('results/benchmark/layer1-llm-baseline-v0.1.json')
    rows=[]
    for rel in files:
        p=ROOT/rel
        if not p.exists():
            raise FileNotFoundError(rel)
        rows.append({'path':rel,'sha256':sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size})
    try:
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    except Exception:
        commit=None
    blockers=[]
    if not llm.exists(): blockers.append('Q6 frozen-split LLM/reasoning-agent baseline')
    human=json.loads((ROOT/'results/benchmark/layer1-human-source-audit-v0.1.json').read_text(encoding='utf-8'))
    if human.get('status')!='PASS': blockers.append('Q11 human/source audit')
    artifact={
        'schema_version':'0.1',
        'status':'PRE_RELEASE_FROZEN_INPUTS',
        'benchmark_version':'layer1-v0.1',
        'base_git_commit_at_freeze':commit,
        'workspace_tree_frozen_by_file_sha256':True,
        'files':rows,
        'known_release_blockers':blockers,
        'immutability_rule':'Any digest change after BENCHMARK_ADMIT requires a new benchmark version or a disclosed evaluator-flaw migration.',
    }
    print(json.dumps(artifact,ensure_ascii=False,indent=2,sort_keys=True))
    return 0


if __name__=='__main__': raise SystemExit(main())
