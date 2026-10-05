#!/usr/bin/env python3
"""Compose the current placement-aware V8 audit state into one compact manifest."""
from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
RESULTS=ROOT/'results/benchmark'
RECIPE_LABELS=ROOT/'local_research/current/benchmark/generated/exact-labels-v0.1/recipe-labels.jsonl'


def _load(name:str):
    p=RESULTS/name
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() and p.stat().st_size else None


def manifest() -> dict:
    ordinary=_load('layer1-v8-ordinary-baselines-v0.1.json')
    all_cells=_load('layer1-v8-all-structural-cells-v0.1.json')
    policy=_load('layer1-v8-policy-ladder-v0.1.json')
    deep=_load('layer1-v8-deep-horizon-v0.1.json')
    flow=_load('layer1-v8-flow-terminal-v0.1.json')
    tail=_load('layer1-v8-rule-tail-v0.1.json')
    comp=_load('layer1-v8-computation-reference-v0.1.json')
    paid=_load('layer1-v8-paid-signatures-v0.1.json')
    paid_deep=_load('layer1-v8-paid-signature-deep-v0.1.json')
    fixed_tail=_load('layer1-v8-fixed-query-tail-v0.1.json')
    survivor_signatures=(
        set(fixed_tail['survivor_signatures']) if fixed_tail is not None
        else set(paid_deep['survivor_signatures']) if paid_deep is not None
        else set(paid['survivor_signatures']) if paid is not None
        else set()
    )
    projected_survivor_recipes=0
    if survivor_signatures and RECIPE_LABELS.exists():
        with RECIPE_LABELS.open(encoding='utf-8') as f:
            for line in f:
                if json.loads(line)['signature'] in survivor_signatures:
                    projected_survivor_recipes+=1
    return {
        'schema_version':'0.1',
        'status':'V8_PLACEMENT_AWARE_IN_PROGRESS',
        'contract':'research/benchmark/V8-BASELINE-CONTRACT.v0.1.md',
        'placement_boundary':{
            'same_information_shortcuts_drive_hardness_verdict':True,
            'gateway_local_autonomy_role':'DEPLOYMENT_ALTERNATIVE',
            'generic_exact_role':'COMPUTATION_REFERENCE_NOT_ADMISSION_VERDICT',
        },
        'structural_first_layer':None if all_cells is None else {
            'cell_count':all_cells['cell_count'],
            'disposition':all_cells['disposition'],
            'same_information_shortcut_coverage':all_cells['same_information_shortcut_coverage'],
            'deployment_alternative_coverage':all_cells['deployment_alternative_coverage'],
        },
        'paid_evidence_first_layer':None if ordinary is None else {
            'cell_count':ordinary['selection']['paid_evidence_required_cells'],
            'disposition':ordinary['disposition'],
            'same_information_shortcut_coverage':ordinary['same_information_shortcut_coverage'],
            'deployment_alternative_coverage':ordinary['deployment_alternative_coverage'],
        },
        'policy_ladder':None if policy is None else {
            'input_survivor_count':policy['input_survivor_count'],
            'disposition':policy['disposition'],
            'baseline_coverage':policy['baseline_coverage'],
        },
        'deep_horizon':None if deep is None else {
            'input_survivor_count':deep['input_survivor_count'],
            'disposition':deep['disposition'],
            'baseline_coverage':deep['baseline_coverage'],
        },
        'flow_terminal':None if flow is None else {
            'input_survivor_count':flow['input_survivor_count'],
            'disposition':flow['disposition'],
            'baseline_coverage':flow['baseline_coverage'],
        },
        'rule_tail':None if tail is None else {
            'input_survivor_count':tail['input_survivor_count'],
            'disposition':tail['disposition'],
            'baseline_coverage':tail['baseline_coverage'],
        },
        'generic_exact_computation_reference':None if comp is None else {
            'survivor_count':comp['survivor_count'],
            'summary':comp['summary'],
            'role':comp['role'],
        },
        'paid_signature_progressive_audit':None if paid is None else {
            'paid_signature_count':paid['paid_signature_count'],
            'disposition':paid['disposition'],
            'baseline_coverage':paid['baseline_coverage'],
            'survivor_signature_count':paid['survivor_signature_count'],
        },
        'paid_signature_deep_audit':None if paid_deep is None else {
            'input_signature_count':paid_deep['input_signature_count'],
            'disposition':paid_deep['disposition'],
            'baseline_coverage':paid_deep['baseline_coverage'],
            'survivor_signature_count':paid_deep['survivor_signature_count'],
        },
        'fixed_query_tail':None if fixed_tail is None else {
            'input_signature_count':fixed_tail['input_signature_count'],
            'disposition':fixed_tail['disposition'],
            'baseline_coverage':fixed_tail['baseline_coverage'],
            'survivor_signature_count':fixed_tail['survivor_signature_count'],
        },
        'current_paid_survivor_projection':{
            'signature_count':len(survivor_signatures),
            'projected_recipe_count':projected_survivor_recipes,
            'interpretation':'pre-admission V8 survivor projection; not benchmark case count',
        },
        'release_status':'NOT_BENCHMARK_ADMIT',
    }


if __name__=='__main__':
    print(json.dumps(manifest(),ensure_ascii=False,indent=2,sort_keys=True))
