#!/usr/bin/env python3
"""Extract reusable, resolved source primitives without sampling unresolved fields.

A source profile can be PARTIAL_SOURCE_GAP and still contribute a valid cache,
path, visibility or energy primitive to a compositional case.  This module keeps
those fragments while preserving any answer-relevant unresolved field as a
hard blocker for the semantics that depend on it.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
DEFAULT_REGISTRY=ROOT/'research/benchmark/profiles/v0.1/SOURCE-PROFILE-REGISTRY.v0.1.json'

# Template-specific dispositions where a profile-level gap should not erase a
# separately resolved operational primitive.
_TEMPLATE_OVERRIDES={
    ('DZT0450_2023_disconnect_recovery','retain_during_outage'):'TASK_AUTHORITY_RESOLVED',
    ('DZT0450_2023_disconnect_recovery','restore_after_reconnect'):'TASK_AUTHORITY_WITH_OBJECTIVE_GAP',
    ('DB11T1677_2019_rainfall_dual_path','rainfall_dry_monitoring'):'SUPPORT_ONLY_ACQUISITION_TIMING',
    ('DB11T1677_2019_rainfall_dual_path','rainfall_active_monitoring'):'SUPPORT_ONLY_ACQUISITION_TIMING',
}


def load_profiles(path:Path=DEFAULT_REGISTRY)->list[dict[str,Any]]:
    return json.loads(path.read_text(encoding='utf-8'))['profiles']


def resolved_variable_fragments(profile:Mapping[str,Any])->dict[str,Any]:
    out={}
    for name,meta in profile.get('variables',{}).items():
        if meta.get('provenance_class')=='UNRESOLVED':
            continue
        out[name]=meta
    return out


def unresolved_answer_fields(profile:Mapping[str,Any])->list[str]:
    return sorted(
        name for name,meta in profile.get('variables',{}).items()
        if meta.get('provenance_class')=='UNRESOLVED' and meta.get('answer_relevant',False)
    )


def template_disposition(profile:Mapping[str,Any],template:Mapping[str,Any])->str:
    key=(str(profile['profile_id']),str(template['template_id']))
    if key in _TEMPLATE_OVERRIDES:return _TEMPLATE_OVERRIDES[key]
    return 'TASK_AUTHORITY_RESOLVED' if profile.get('generator_status')=='READY' else 'BLOCKED_BY_PROFILE_GAP'


def catalog(path:Path=DEFAULT_REGISTRY)->dict[str,Any]:
    rows=[]
    for p in load_profiles(path):
        pid=str(p['profile_id'])
        gaps=unresolved_answer_fields(p)
        rows.append({
            'profile_id':pid,
            'families':list(p.get('families',[])),
            'generator_status':p.get('generator_status'),
            'unresolved_answer_fields':gaps,
            'resolved_variables':resolved_variable_fragments(p),
            'capabilities':list(p.get('capabilities',[])),
            'obligation_templates':[
                {**dict(t),'fragment_disposition':template_disposition(p,t)}
                for t in p.get('obligation_templates',[])
            ],
            'reuse_rule':(
                'READY_TASK_AUTHORITY_AND_PRIMITIVES' if not gaps
                else 'RESOLVED_PRIMITIVES_ONLY; UNRESOLVED_FIELDS_MUST_NOT_BE_SAMPLED'
            ),
        })
    return {
        'schema_version':'0.1',
        'rule':'Partial profiles may contribute resolved primitives; unresolved answer-relevant fields remain hard blockers and are never sampled.',
        'profiles':rows,
    }


if __name__=='__main__':
    print(json.dumps(catalog(),ensure_ascii=False,indent=2))
