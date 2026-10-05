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
from task_surface_registry import load_registry

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
AUTH=ROOT/'research/benchmark/LAYER1-AUTHORITY.md'
STATE=ROOT/'research/benchmark/LAYER1-CURRENT-STATE.v0.1.json'
README=ROOT/'README.md'
RESEARCH=ROOT/'research/README.md'
BENCH=ROOT/'research/benchmark/README.md'


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
    assert state['next_stage']=='DYNAMIC_WORLD_ALIAS_BUNDLE_MATERIALIZATION'

    authority=AUTH.read_text(encoding='utf-8')
    assert '58,752 个对象不是 benchmark cases' in authority
    assert 'receipt 188-grid' in authority
    assert '当前唯一主工程' in authority
    assert 'T1 — Monitoring Information Continuity' in authority
    assert 'T2 — Warning Delivery & Response Handoff' in authority

    for path in (README,RESEARCH,BENCH):
        text=path.read_text(encoding='utf-8')
        assert 'LAYER1-AUTHORITY.md' in text, f'{path} no longer points to Layer-1 authority'

    print('PASS Layer-1 authority: taxonomy/scope/generator snapshot/README entry points are aligned')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
