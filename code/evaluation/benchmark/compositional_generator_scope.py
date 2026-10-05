#!/usr/bin/env python3
"""Freeze the Layer-1 compositional generator scope before scenario sampling."""
from __future__ import annotations

import json
from typing import Any

from source_primitive_catalog import catalog
from task_surface_registry import load_registry


def build_scope()->dict[str,Any]:
    reg=load_registry(); primitives=catalog()
    by_id={x['profile_id']:x for x in primitives['profiles']}
    t1=reg['families']['T1_MONITORING_INFORMATION_CONTINUITY']['task_surfaces']
    t2=reg['families']['T2_WARNING_DELIVERY_RESPONSE_HANDOFF']['task_surfaces']

    active=[]; closed=[]; blocked=[]
    for row in t1:
        role=row['generator_role']; disp=row['standalone_disposition']
        item={
            'surface_id':row['surface_id'],
            'generator_role':role,
            'standalone_disposition':disp,
            'source_profiles':row['source_profiles'],
            'profile_gaps':{
                pid:by_id[pid]['unresolved_answer_fields']
                for pid in row['source_profiles'] if pid in by_id and by_id[pid]['unresolved_answer_fields']
            },
        }
        if role in {'KEEP_EASY_ANCHOR'}:closed.append(item)
        elif role=='ACTIVE_ONLY_WHEN_OBJECTIVE_DEFINED':active.append(item)
        else:active.append(item)
    for row in t2:
        blocked.append({
            'surface_id':row['surface_id'],
            'generator_role':row['generator_role'],
            'standalone_disposition':row['standalone_disposition'],
            'source_profiles':row['source_profiles'],
        })

    return {
        'schema_version':'0.1',
        'main_family':'T1_MONITORING_INFORMATION_CONTINUITY',
        'boundary_family':'T2_WARNING_DELIVERY_RESPONSE_HANDOFF',
        't1_active_or_compositional_surfaces':active,
        't1_easy_conformance_anchors':closed,
        't2_blocked_until_environment':blocked,
        'required_composition_dimensions':[
            'multi_obligation_release_and_deadline',
            'warning_driven_workload_transition',
            'finite_non_nested_terrestrial_service_opportunities',
            'intermittent_satellite_opportunities',
            'shared_real_resource_or_capacity',
            'outage_cache_and_recovery_state',
            'legal_partial_evidence_and_async_feedback',
        ],
        'optional_after_core_dimensions':[
            'source_or_trace_grounded_energy_pressure',
            'future_authority_published_warning_transition',
        ],
        'forbidden_shortcuts':[
            'one_shot_permanent_recovery_as_only_uncertainty',
            'invented_backlog_vs_fresh_priority',
            'artificially_reduced_source_required_cache',
            'hidden_public_geometry',
            'future_truth_encoded_in_current_query',
            'capability_or_tool_name_promoted_to_task_family',
            'receipt_race_promoted_to_task_family',
        ],
        'historical_closure_policy':'Do not rerun closed standalone forms. Reuse them as easy/conformance/regression cells; only new compositions re-enter V0-V9 hardness mining.',
    }


if __name__=='__main__':
    print(json.dumps(build_scope(),ensure_ascii=False,indent=2))
