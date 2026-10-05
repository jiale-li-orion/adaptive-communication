#!/usr/bin/env python3
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

FILES = [
    'spec/benchmark/LAYER1-DECISION-BENCHMARK-v0.2.md',
    'research/benchmark/LAYER1-AUTHORITY.md',
    'research/benchmark/BENCHMARK-QUALITY-GATE.v0.1.md',
    'research/benchmark/V8-BASELINE-CONTRACT.v0.1.md',
    'research/benchmark/TASK-SURFACE-REGISTRY.v0.1.json',
    'research/benchmark/profiles/v0.1/SOURCE-PROFILE-REGISTRY.v0.1.json',
    'research/benchmark/source-evidence/DB44T2457_2024-landslide-table11.md',
    'code/evaluation/benchmark/compositional_recipe_generator_v0_1.py',
    'code/evaluation/benchmark/dynamic_world_materializer_v0_1.py',
    'code/evaluation/benchmark/causal_evidence_process_v0_1.py',
    'code/evaluation/benchmark/exact_reference_oracle_v0_1.py',
    'code/evaluation/benchmark/validity_filters_v0_1.py',
    'code/evaluation/benchmark/v8_policy_baselines_v0_1.py',
    'code/evaluation/benchmark/execution_trace_evaluator_v0_1.py',
    'code/evaluation/benchmark/llm_reasoning_baseline_v0_1.py',
    'code/evaluation/benchmark/audit_agentic_reducibility_v0_2.py',
    'code/evaluation/benchmark/audit_communication_attribution_v0_2.py',
    'results/benchmark/layer1-exact-labels-v0.2-retry-legality.json',
    'results/benchmark/layer1-v0-v7-full-v0.2-retry-legality.json',
    'results/benchmark/layer1-v8-all-pass-v0.2-retry-legality.json',
    'results/benchmark/layer1-v9-evaluator-soundness-v0.2-retry-legality.json',
    'results/benchmark/layer1-structure-aware-split-v0.2-retry-legality.json',
    'results/benchmark/layer1-split-coverage-v0.2-retry-legality.json',
    'results/benchmark/layer1-public-test-freeze-v0.2-retry-legality.json',
    'results/benchmark/layer1-public-test-cases-v0.2-retry-legality.jsonl',
    'results/benchmark/layer1-llm-baseline-v0.2-retry-legality.json',
    'results/benchmark/layer1-agentic-reducibility-v0.2-retry-legality.json',
    'results/benchmark/layer1-communication-attribution-v0.2-retry-legality.json',
    'results/benchmark/layer1-human-source-audit-v0.2-retry-legality.json',
    'results/benchmark/layer1-human-source-machine-preaudit-v0.2-retry-legality.json',
    'research/benchmark/HUMAN-SOURCE-AUDIT-PACKET.v0.2-retry-legality.md',
    'research/benchmark/HUMAN-SOURCE-AUDIT-WORKSHEET.v0.2-retry-legality.md',
    'research/benchmark/STATISTICAL-REPORTING.v0.1.md',
    'research/benchmark/BENCHMARK-MAINTENANCE.v0.1.md',
    'code/evaluation/benchmark/reproduce_layer1_v0_2_retry_legality.py',
]


def main() -> int:
    rows = []
    for rel in FILES:
        path = ROOT / rel
        if not path.exists():
            raise FileNotFoundError(rel)
        rows.append({'path': rel, 'sha256': sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size})
    try:
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    except Exception:
        commit = None
    human = json.loads((ROOT / 'results/benchmark/layer1-human-source-audit-v0.2-retry-legality.json').read_text(encoding='utf-8'))
    blockers = []
    if human.get('status') != 'PASS':
        blockers.append('Q11 human/source audit')
    artifact = {
        'schema_version': '0.2',
        'status': 'PRE_RELEASE_FROZEN_INPUTS',
        'benchmark_version': 'layer1-v0.2-retry-legality',
        'base_git_commit_at_freeze': commit,
        'workspace_tree_frozen_by_file_sha256': True,
        'files': rows,
        'known_release_blockers': blockers,
        'immutability_rule': 'Any digest change after BENCHMARK_ADMIT requires a new benchmark version or a disclosed evaluator-flaw migration.',
    }
    print(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
