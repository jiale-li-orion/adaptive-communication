#!/usr/bin/env python3
"""Generate the Layer-1 T1 compositional candidate-recipe universe.

This is the corpus-first pre-world stage described in cache06:
source-grounded task authority + resolved source primitives + declared
MODEL_DERIVED_TRACE / CONTROLLED_STRESS coordinates.  It intentionally stops
before dynamic world materialization and V0-V9 oracle filtering.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from itertools import product
from pathlib import Path
from typing import Any, Iterable

from case_generation import compile_ready_profile
from source_derivation import expand_source_ranges
from structural_scaling_v0_3 import _slots
from task_surface_registry import task_surface_ids_for_profile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SOURCE_REGISTRY=ROOT/'research/benchmark/profiles/v0.1/SOURCE-PROFILE-REGISTRY.v0.1.json'
TRACE_HORIZON_S=48*3600
HARD_CORE_MAX_INTERVAL_S=12*3600

SERVICE_PROCESS_CLASSES=(
    'STEADY_AVAILABLE_CONTROL',
    'MONOTONE_RECOVERY_NEGATIVE',
    'FINITE_CROSSING_WINDOWS',
    'MULTI_WINDOW_DYNAMIC',
)
OVERLAP_COUNTS=(2,3,4)
RESOURCE_HEADROOM=('TIGHT','BALANCED','SLACK')
EVIDENCE_REGIMES=(
    'FULL_OBSERVATION_CONTROL',
    'PASSIVE_ACK_ONLY',
    'GATEWAY_SUMMARY_QUERY',
    'MIXED_PASSIVE_QUERY_PROBE',
)
RECOVERY_REGIMES=(
    'NO_RECOVERY_STATE',
    'OUTAGE_CACHE_RETAIN',
    'RECONNECT_RECONCILE_OBJECTIVE_CHECK',
)


@dataclass(frozen=True)
class GeometrySignature:
    signature_id:str
    start_s:int
    relative_slots_s:tuple[int,...]
    bin_counts:tuple[int,int,int]


@dataclass(frozen=True)
class CandidateRecipe:
    recipe_id:str
    family:str
    task_case_id:str
    task_surface_ids:tuple[str,...]
    report_interval_s:int
    monitoring_grade:int
    warning_state:str
    geometry_signature_id:str
    geometry_start_s:int
    service_process_class:str
    overlap_count:int
    resource_headroom:str
    evidence_regime:str
    recovery_regime:str
    hardness:tuple[str,...]
    source_profiles:tuple[str,...]
    variable_provenance:dict[str,dict[str,Any]]
    pre_oracle_disposition:str
    blockers:tuple[str,...]


def _load_profiles()->list[dict[str,Any]]:
    return json.loads(SOURCE_REGISTRY.read_text(encoding='utf-8'))['profiles']


def _db44_resolved_cases()->list[dict[str,Any]]:
    p=next(x for x in _load_profiles() if x['profile_id']=='DB44T2457_2024_warning_reporting')
    return expand_source_ranges(compile_ready_profile(p))


def geometry_signatures(limit:int=8,horizon_s:int=12*3600)->tuple[GeometrySignature,...]:
    slots=tuple(_slots())
    max_start=max(slots)-horizon_s
    seen=set();out=[]
    for start in range(0,max_start+1,1800):
        rel=tuple(t-start for t in slots if start<=t<=start+horizon_s)
        if not rel:continue
        bins=(
            sum(0<=x<4*3600 for x in rel),
            sum(4*3600<=x<8*3600 for x in rel),
            sum(8*3600<=x<=12*3600 for x in rel),
        )
        # Keep timing shape, not merely total count, so held-out signatures can
        # later be structural rather than seed/id splits.
        coarse=tuple(round(x/300) for x in rel)
        sig=(bins,coarse)
        if sig in seen:continue
        seen.add(sig)
        out.append(GeometrySignature(f'G{len(out):02d}',start,rel,bins))
        if len(out)>=limit:break
    if len(out)<limit:
        raise RuntimeError(f'only {len(out)} unique geometry signatures')
    return tuple(out)


def _budget_for(overlap:int,headroom:str)->int:
    if headroom=='TIGHT':return max(1,overlap-1)
    if headroom=='BALANCED':return overlap
    if headroom=='SLACK':return overlap+1
    raise ValueError(headroom)


def _hardness(service:str,overlap:int,evidence:str,recovery:str)->tuple[str,...]:
    hs=[]
    if service=='STEADY_AVAILABLE_CONTROL':hs.append('H0_CONFORMANCE')
    elif service=='MONOTONE_RECOVERY_NEGATIVE':hs.append('H0_NEGATIVE_SHORTCUT_REGRESSION')
    else:
        hs += ['H3_SHARED_RESOURCE_CONFLICT']
        if overlap>=3:hs.append('H4_COUPLED_SEQUENTIAL_COMMITMENT')
    if evidence=='GATEWAY_SUMMARY_QUERY':hs.append('H2_EVIDENCE_VALUE')
    elif evidence=='MIXED_PASSIVE_QUERY_PROBE':hs += ['H2_EVIDENCE_VALUE','H5_PASSIVE_PROBE_QUERY_COMPETITION']
    elif evidence=='PASSIVE_ACK_ONLY':hs.append('H1_PARTIAL_OBSERVATION')
    if recovery=='RECONNECT_RECONCILE_OBJECTIVE_CHECK':hs.append('H_RECOVERY_OBJECTIVE_CHECK')
    return tuple(sorted(set(hs)))


def _surfaces(base_case:dict[str,Any],service:str,recovery:str)->tuple[str,...]:
    out=set(base_case.get('task_surfaces',[]))
    if service!='STEADY_AVAILABLE_CONTROL':
        out.update({'T1.S2_INTERMITTENT_BACKHAUL_FALLBACK','T1.S6_HETEROGENEOUS_PATH_PRIORITY'})
    if recovery=='OUTAGE_CACHE_RETAIN':out.add('T1.S4_OUTAGE_CACHE_RETENTION')
    elif recovery=='RECONNECT_RECONCILE_OBJECTIVE_CHECK':
        out.update({'T1.S4_OUTAGE_CACHE_RETENTION','T1.S5_RECOVERY_RECONCILIATION'})
    if len(out)>=2:out.add('T1.S7_COMPOUND_CONTINUITY')
    return tuple(sorted(out))


def _disposition(service:str,recovery:str)->tuple[str,tuple[str,...]]:
    blockers=[]
    if service=='STEADY_AVAILABLE_CONTROL':return 'EASY_CONFORMANCE',()
    if service=='MONOTONE_RECOVERY_NEGATIVE':return 'NEGATIVE_REGRESSION',()
    if recovery=='RECONNECT_RECONCILE_OBJECTIVE_CHECK':
        blockers.append('V7_OBJECTIVE_DEFINED must reject any case requiring an invented backlog-vs-fresh sacrifice priority')
    return 'VALIDITY_PENDING',tuple(blockers)


def _digest(payload:dict[str,Any])->str:
    raw=json.dumps(payload,sort_keys=True,separators=(',',':'))
    return sha256(raw.encode()).hexdigest()[:14]


def core_recipes()->Iterable[CandidateRecipe]:
    task_cases=[x for x in _db44_resolved_cases() if x['world']['report_interval_s']<=HARD_CORE_MAX_INTERVAL_S]
    geoms=geometry_signatures()
    for case,g,service,overlap,headroom,evidence,recovery in product(
        task_cases,geoms,SERVICE_PROCESS_CLASSES,OVERLAP_COUNTS,RESOURCE_HEADROOM,EVIDENCE_REGIMES,RECOVERY_REGIMES
    ):
        surfaces=_surfaces(case,service,recovery)
        disp,blockers=_disposition(service,recovery)
        budget=_budget_for(overlap,headroom)
        support_profiles={'DB44T2457_2024_warning_reporting'}
        if service!='STEADY_AVAILABLE_CONTROL':support_profiles.update({'DZT0450_2023_disconnect_recovery','JIAOZUO_2024_geohazard_monitoring_deployment'})
        if recovery!='NO_RECOVERY_STATE':support_profiles.add('DZT0450_2023_disconnect_recovery')
        if headroom=='TIGHT':support_profiles.add('DB11T1677_2019_rainfall_dual_path')
        key={
            'task':case['case_id'],'geometry':g.signature_id,'service':service,'overlap':overlap,
            'headroom':headroom,'evidence':evidence,'recovery':recovery,
        }
        yield CandidateRecipe(
            recipe_id='T1R-'+_digest(key),
            family='T1_MONITORING_INFORMATION_CONTINUITY',
            task_case_id=case['case_id'],
            task_surface_ids=surfaces,
            report_interval_s=int(case['world']['report_interval_s']),
            monitoring_grade=int(case['world']['monitoring_grade']),
            warning_state=str(case['world']['warning_state']),
            geometry_signature_id=g.signature_id,
            geometry_start_s=g.start_s,
            service_process_class=service,
            overlap_count=overlap,
            resource_headroom=headroom,
            evidence_regime=evidence,
            recovery_regime=recovery,
            hardness=_hardness(service,overlap,evidence,recovery),
            source_profiles=tuple(sorted(support_profiles)),
            variable_provenance={
                'report_interval_s':dict(case['variable_provenance']['report_interval_s']),
                'geometry_signature':{
                    'class':'MODEL_DERIVED_TRACE','source_ref_ids':[],
                    'trace_ref':'CONNECTA_20260922_SIHUI_GEOMETRY_48H',
                    'sampling_rule':'enumerate distinct 12h opportunity signatures',
                },
                'service_process_class':{
                    'class':'CONTROLLED_STRESS','source_ref_ids':['DZT0450_2023','JIAOZUO_2024'],
                    'stress_rationale':'cover finite/non-nested intermittent service processes without claiming a field outage distribution',
                },
                'overlap_count':{
                    'class':'CONTROLLED_STRESS','source_ref_ids':['DB44T2457_2024'],
                    'stress_rationale':'controlled workload density over source-valid recurring reporting obligations',
                },
                'satellite_budget':{
                    'class':'CONTROLLED_STRESS','source_ref_ids':[],
                    'value':budget,
                    'stress_rationale':'normalized rescue capacity for binding-resource coverage; not battery energy',
                },
                'evidence_regime':{
                    'class':'CONTROLLED_STRESS','source_ref_ids':['JIAOZUO_2024','DZT0450_2023'],
                    'stress_rationale':'compare legal full/passive/query/probe observation processes using existing owners/capabilities',
                },
                'recovery_regime':{
                    'class':'CONTROLLED_STRESS','source_ref_ids':['DZT0450_2023'],
                    'stress_rationale':'cover outage retention/reconnect lifecycle while preserving unresolved priority blockers',
                },
            },
            pre_oracle_disposition=disp,
            blockers=blockers,
        )


def long_cadence_anchors()->list[dict[str,Any]]:
    rows=[]
    for case in _db44_resolved_cases():
        interval=int(case['world']['report_interval_s'])
        if interval<=HARD_CORE_MAX_INTERVAL_S:continue
        rows.append({
            'case_id':case['case_id'],
            'family':case['family'],
            'task_surfaces':case.get('task_surfaces',[]),
            'report_interval_s':interval,
            'warning_state':case['world']['warning_state'],
            'monitoring_grade':case['world']['monitoring_grade'],
            'disposition':'EASY_COVERAGE_OR_TRACE_HORIZON_GAP',
            'reason':'source-valid long-cadence task retained; current 48h geometry trace is insufficient for multi-obligation hard composition when interval exceeds 12h',
        })
    return rows


def manifest()->dict[str,Any]:
    recipes=list(core_recipes())
    from collections import Counter
    return {
        'schema_version':'0.1',
        'generator':'T1-compositional-recipe-v0.1',
        'stage':'PRE_WORLD_PRE_ORACLE',
        'core_recipe_count':len(recipes),
        'long_cadence_anchor_count':len(long_cadence_anchors()),
        'db44_source_resolved_contract_count':len(_db44_resolved_cases()),
        'core_task_contract_count':len({x.task_case_id for x in recipes}),
        'geometry_signature_count':len(geometry_signatures()),
        'by_pre_oracle_disposition':dict(sorted(Counter(x.pre_oracle_disposition for x in recipes).items())),
        'by_warning_state':dict(sorted(Counter(x.warning_state for x in recipes).items())),
        'by_service_process':dict(sorted(Counter(x.service_process_class for x in recipes).items())),
        'rules':[
            'Recipes are not benchmark cases until dynamic world materialization and V0-V9.',
            'UNRESOLVED source fields are absent from sampled axes.',
            'Easy and negative-regression structures are intentionally retained.',
            'T2 is excluded from this T1 universe until its actor-chain environment closes SIMULATOR_GAP.',
        ],
    }


if __name__=='__main__':
    print(json.dumps(manifest(),ensure_ascii=False,indent=2))
