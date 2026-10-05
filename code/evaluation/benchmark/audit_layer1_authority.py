#!/usr/bin/env python3
"""Fail-fast guard against Layer-1 control-plane drift.

This is deliberately cheap: no simulator, oracle sweep or model call.  It only
checks that tracked authority projections remain derivable from the canonical
registries/generator and that public README entry points still point to the
Layer-1 authority instead of a versioned local experiment.
"""
from __future__ import annotations

import json
from pathlib import Path

from compositional_generator_scope import build_scope
from compositional_recipe_generator_v0_1 import manifest
from causal_evidence_process_v0_1 import causal_process_manifest
from dynamic_world_materializer_v0_1 import materialization_manifest
from task_surface_registry import load_registry

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
AUTH=ROOT/'research/benchmark/LAYER1-AUTHORITY.md'
STATE=ROOT/'research/benchmark/LAYER1-CURRENT-STATE.v0.1.json'
README=ROOT/'README.md'
RESEARCH=ROOT/'research/README.md'
BENCH=ROOT/'research/benchmark/README.md'
WORLD_MANIFEST=ROOT/'results/benchmark/layer1-world-materialization-v0.1.json'
WORLD_DOC=ROOT/'research/benchmark/DYNAMIC-WORLD-MATERIALIZATION.v0.1.md'
WORLD_SCHEMA=ROOT/'research/benchmark/WORLD-BUNDLE-SCHEMA.v0.1.json'
CAUSAL_MANIFEST=ROOT/'results/benchmark/layer1-causal-evidence-v0.1.json'
CAUSAL_DOC=ROOT/'research/benchmark/CAUSAL-EVIDENCE-PROCESS.v0.1.md'
CAUSAL_SCHEMA=ROOT/'research/benchmark/CAUSAL-EVIDENCE-SCHEMA.v0.1.json'
EXACT_AUDIT=ROOT/'results/benchmark/layer1-exact-reference-audit-v0.2-retry-legality.json'
EXACT_DOC=ROOT/'research/benchmark/EXACT-REFERENCE-ORACLE.v0.1.md'
EXACT_LABEL_MATERIALIZER=ROOT/'code/evaluation/benchmark/materialize_exact_labels_v0_1.py'
EXACT_LABEL_MANIFEST=ROOT/'results/benchmark/layer1-exact-labels-v0.2-retry-legality.json'
V8_PAID=ROOT/'results/benchmark/layer1-v8-ordinary-baselines-v0.1.json'
V8_ALL=ROOT/'results/benchmark/layer1-v8-all-structural-cells-v0.1.json'
V0V7_FULL=ROOT/'results/benchmark/layer1-v0-v7-full-v0.2-retry-legality.json'
V8_ALL_PASS=ROOT/'results/benchmark/layer1-v8-all-pass-v0.2-retry-legality.json'
V9_AUDIT=ROOT/'results/benchmark/layer1-v9-evaluator-soundness-v0.2-retry-legality.json'
SPLIT_MANIFEST=ROOT/'results/benchmark/layer1-structure-aware-split-v0.2-retry-legality.json'
SPLIT_COVERAGE=ROOT/'results/benchmark/layer1-split-coverage-v0.2-retry-legality.json'
PUBLIC_TEST=ROOT/'results/benchmark/layer1-public-test-freeze-v0.2-retry-legality.json'


def main()->int:
    reg=load_registry()
    assert set(reg['families'])=={
        'T1_MONITORING_INFORMATION_CONTINUITY',
        'T2_WARNING_DELIVERY_RESPONSE_HANDOFF',
    }
    t1=reg['families']['T1_MONITORING_INFORMATION_CONTINUITY']['task_surfaces']
    t2=reg['families']['T2_WARNING_DELIVERY_RESPONSE_HANDOFF']['task_surfaces']
    assert len(t1)==8, len(t1)
    assert len(t2)==3, len(t2)

    state=json.loads(STATE.read_text(encoding='utf-8'))
    assert state['status']=='LAYER1_CONSTRUCTION_IN_PROGRESS'
    assert state['release_status']=='NOT_BENCHMARK_ADMIT'
    assert state['main_family']=='T1_MONITORING_INFORMATION_CONTINUITY'
    assert state['boundary_family']=='T2_WARNING_DELIVERY_RESPONSE_HANDOFF'
    assert state['generator']==manifest(), 'tracked generator snapshot drifted from current generator'
    assert state['scope']==build_scope(), 'tracked scope snapshot drifted from current scope'
    assert state['generator']['core_recipe_count']==58752
    assert state['generator']['stage']=='PRE_WORLD_PRE_ORACLE'
    tracked_world=json.loads(WORLD_MANIFEST.read_text(encoding='utf-8'))
    current_world=materialization_manifest()
    assert tracked_world==current_world, 'tracked world-materialization manifest drifted from current materializer'
    assert state['world_materialization']==current_world, 'current-state world materialization drifted from materializer'
    assert current_world['bundle_count']==58752
    assert current_world['stage']=='WORLD_BUNDLE_PRE_EVIDENCE_PRE_ORACLE'
    tracked_causal=json.loads(CAUSAL_MANIFEST.read_text(encoding='utf-8'))
    current_causal=causal_process_manifest()
    assert tracked_causal==current_causal, 'tracked causal-evidence manifest drifted from current process compiler'
    assert state['causal_evidence_process']==current_causal, 'current-state causal evidence snapshot drifted from process compiler'
    assert current_causal['process_count']==58752
    assert current_causal['stage']=='CAUSAL_EVIDENCE_PRE_ORACLE'
    exact=json.loads(EXACT_AUDIT.read_text(encoding='utf-8'))
    phys=exact['physical_full_scan']
    strat=exact['stratified_validity_pilot']
    tracked_exact=state['exact_reference_oracle']
    assert tracked_exact['implementation_status']=='IMPLEMENTED_PRE_ADMISSION'
    assert tracked_exact['physical_full_scan']['bundle_count']==phys['bundle_count']==58752
    assert tracked_exact['physical_full_scan']['bundle_physical_class']==phys['bundle_physical_class']
    assert tracked_exact['hard_structure_audit']['outcome']==strat['outcome']
    assert tracked_exact['hard_structure_audit']['reference_counts']==strat['reference_counts']
    assert tracked_exact['hard_structure_audit']['search']==strat['search']
    labels=json.loads(EXACT_LABEL_MANIFEST.read_text(encoding='utf-8'))
    assert tracked_exact['full_universe_observation_label_status']=='COMPLETE'
    assert tracked_exact['full_universe_label_manifest']['status']==labels['status']=='COMPLETE'
    assert tracked_exact['full_universe_label_manifest']['unique_solver_signature_count']==labels['unique_solver_signature_count']==8064
    assert tracked_exact['full_universe_label_manifest']['signature_label_digest_sha256']==labels['signature_label_digest_sha256']
    vf=state['validity_filter_infrastructure']
    v0v7=json.loads(V0V7_FULL.read_text(encoding='utf-8'))
    v8=json.loads(V8_ALL_PASS.read_text(encoding='utf-8'))
    v9=json.loads(V9_AUDIT.read_text(encoding='utf-8'))
    split=json.loads(SPLIT_MANIFEST.read_text(encoding='utf-8'))
    coverage=json.loads(SPLIT_COVERAGE.read_text(encoding='utf-8'))
    public_test=json.loads(PUBLIC_TEST.read_text(encoding='utf-8'))
    assert vf['v0_v7']['status']=='DONE_FULL_UNIVERSE'
    assert vf['v0_v7']['signature_count']==v0v7['completed_signature_count']==8064
    assert v0v7['status']=='COMPLETE'
    assert vf['v8']['status']=='DONE_ALL_V0_V7_PASS_SIGNATURES'
    assert vf['v8']['input_signature_count']==v8['input_v0_v7_pass_signature_count']==1423
    assert vf['v8']['survivor_signature_count']==v8['survivor_signature_count']==41
    assert vf['v8']['projected_survivor_recipe_count']==v8['projected_survivor_recipe_count']==174
    assert v8['status']=='COMPLETE'
    assert vf['v9']['status']=='DONE'
    assert vf['v9']['passed'] is True and v9['passed'] is True
    assert state['structure_aware_split']['status']=='DONE'
    assert state['structure_aware_split']['candidate_count']==split['candidate_count']==30180
    assert state['structure_aware_split']['leakage_passed'] is True
    assert split['leakage_audit']['passed'] is True
    assert all(
        x['cross_split_neighbor_fingerprint_count']==0
        for x in coverage['near_duplicate_one_axis'].values()
    )
    assert state['structure_aware_split']['hard_signature_by_split']=={'train':16,'dev':18,'test':7}
    assert public_test['test_case_count']==3804
    assert state['quality_gates']['status']=='V02_RELEASE_GATES_REFRESHED_Q11_ONLY_BLOCKER'
    assert state['quality_gates']['gate_counts']=={'PASS':12,'BLOCKED':1}
    assert state['quality_gates']['llm_baseline']=='PASS_DEEPSEEK_FLASH_0_OF_7_HARD_SIGNATURES'
    assert state['quality_gates']['agentic_reducibility']=='PASS_41_OF_41_HARD_SIGNATURES'
    assert state['quality_gates']['communication_attribution']=='PASS_41_OF_41_HARD_SIGNATURES'
    assert state['quality_gates']['human_source_audit']=='MACHINE_PREAUDIT_23_OF_23_PASS_HUMAN_REVIEW_PENDING'
    assert state['next_stage']=='V02_Q11_HUMAN_REVIEW_ONLY_BEFORE_BENCHMARK_ADMIT'

    authority=AUTH.read_text(encoding='utf-8')
    assert '58,752 个 recipe 不是 benchmark cases' in authority
    assert 'receipt 188-grid' in authority
    assert '当前唯一主工程' in authority
    assert 'T1 — Monitoring Information Continuity' in authority
    assert 'T2 — Warning Delivery & Response Handoff' in authority
    assert 'retry legality / duplicate-free resend semantics       [DONE v0.2]' in authority
    assert 'regenerate exact labels + V0–V9' not in authority
    assert '41 个 signatures / 174 个 pre-admission recipes' in authority
    assert 'public-test identity v0.2 当前冻结 3,804 个 test cases' in authority
    assert 'frozen-split LLM baseline                              [DONE v0.2; DeepSeek 0/7]' in authority
    assert WORLD_DOC.exists()
    assert WORLD_SCHEMA.exists()
    assert CAUSAL_DOC.exists()
    assert CAUSAL_SCHEMA.exists()
    assert EXACT_DOC.exists()
    assert EXACT_LABEL_MATERIALIZER.exists()

    for path in (README,RESEARCH,BENCH):
        text=path.read_text(encoding='utf-8')
        assert 'LAYER1-AUTHORITY.md' in text, f'{path} no longer points to Layer-1 authority'

    print('PASS Layer-1 authority: retry-legality v0.2 exact/V0-V9/split/public-test/LLM/release audits are aligned; Q0-Q12=12 PASS / 1 BLOCKED and only real Q11 human review remains before BENCHMARK_ADMIT')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
