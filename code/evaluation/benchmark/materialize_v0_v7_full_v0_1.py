#!/usr/bin/env python3
"""Materialize V0-V7 over the full 58,752-recipe Layer-1 universe.

Exact/full-current/no-paid-query labels are reused from the frozen exact-label
artifact.  We only solve the missing blind-open-loop reference for signatures
whose exact class is NO_PAID_QUERY_REQUIRED; PAID_EVIDENCE_REQUIRED already
implies blind failure because blind is a strict information subset of no-paid.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from causal_evidence_process_v0_1 import attach_causal_evidence
from exact_reference_oracle_v0_1 import solve_observation_matched
from materialize_exact_labels_v0_1 import _collect_universe
from validity_filters_v0_1 import _blind_process, count_physical_success_plans


HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
EXACT_SIGNATURE_LABELS=ROOT/'local_research/current/benchmark/generated/exact-labels-v0.1/signature-labels.jsonl'
DEFAULT_OUT=ROOT/'local_research/current/benchmark/generated/v0-v7-full-v0.1'


def _load_exact_labels() -> dict[str,dict[str,Any]]:
    out={}
    for line in EXACT_SIGNATURE_LABELS.read_text(encoding='utf-8').splitlines():
        if line.strip():
            row=json.loads(line); out[str(row['signature'])]=row
    return out


def _plan_stats(bundle:Mapping[str,Any],cap:int=10_000)->dict[str,Any]:
    plan={}; deadline={}; capacity={}; sat={}
    for world in bundle['worlds']:
        wid=str(world['world_id'])
        plan[wid]=count_physical_success_plans(bundle,world,cap=cap)
        deadline[wid]=count_physical_success_plans(bundle,world,cap=cap,relax_deadline=True)
        capacity[wid]=count_physical_success_plans(bundle,world,cap=cap,relax_capacity=True)
        sat[wid]=count_physical_success_plans(bundle,world,cap=cap,relax_satellite_budget=True)
    return {
        'plan':plan,'deadline':deadline,'capacity':capacity,'satellite_budget':sat,
        'multiple':any(v>=2 for v in plan.values()),
        'deadline_binding':any(deadline[w]>plan[w] for w in plan),
        'capacity_binding':any(capacity[w]>plan[w] for w in plan),
        'satellite_binding':any(sat[w]>plan[w] for w in plan),
    }


def _disposition(*,classification:str,v2:bool,v3:bool|None,v4:bool|None,v5:bool,v6:bool|None,v7:bool|None)->str:
    if classification in {'MIXED_WORLD_SOLVABILITY','NO_WORLD_SOLVABLE'}:
        return 'V1_PHYSICAL_INVALID'
    if classification in {'SEARCH_LIMIT','FULL_CURRENT_STATE_INFEASIBLE'}:
        return 'REFERENCE_UNRESOLVED'
    if classification=='INFORMATION_INFEASIBLE':
        return 'INFORMATION_INFEASIBLE_DIAGNOSTIC'
    if not v2: return 'UNIQUE_READY'
    if v3 is False: return 'COMMON_SAFE_ACTION'
    if v4 is False: return 'OBSERVATION_IRRELEVANT'
    if not v5: return 'NO_BINDING_CONSTRAINT'
    if v6 is False: return 'OUTCOME_EQUIVALENT'
    if v7 is not True: return 'OBJECTIVE_AMBIGUOUS'
    return 'V0_V7_PASS'


def _evaluate_one(args:tuple[str,dict[str,Any],dict[str,Any],int])->tuple[str,dict[str,Any]]:
    sig,bundle,label,max_memo_nodes=args
    cls=str(label['classification'])
    physical=label.get('physical') or {}
    all_worlds=bool(physical.get('all_worlds_solvable',False))
    stats=_plan_stats(bundle)
    v2=bool(stats['multiple'])
    v5=bool(stats['deadline_binding'] or stats['capacity_binding'] or stats['satellite_binding'])

    exact_solvable=(label.get('exact') or {}).get('solvable') is True
    no_paid_solvable=(label.get('no_paid_query') or {}).get('solvable') is True
    blind_solvable:bool|None=None
    blind_status='DERIVED_NOT_RUN'
    blind_memo_nodes=0
    if cls=='PAID_EVIDENCE_REQUIRED':
        blind_solvable=False
        blind_status='DERIVED_FROM_NO_PAID_INFEASIBLE'
    elif cls=='NO_PAID_QUERY_REQUIRED':
        process=attach_causal_evidence(bundle)
        blind=solve_observation_matched(
            bundle,_blind_process(process),disable_paid_query=True,max_memo_nodes=max_memo_nodes
        )
        blind_status=str(blind['status']); blind_solvable=blind['solvable']; blind_memo_nodes=int(blind['memo_nodes'])

    if cls=='INFORMATION_INFEASIBLE':
        v3=None; v4=None
    elif cls in {'MIXED_WORLD_SOLVABILITY','NO_WORLD_SOLVABLE','SEARCH_LIMIT','FULL_CURRENT_STATE_INFEASIBLE'}:
        v3=None; v4=None
    elif blind_status=='SEARCH_LIMIT':
        v3=None; v4=None
    else:
        v3=not bool(blind_solvable)
        v4=not bool(blind_solvable)

    if cls=='SEARCH_LIMIT' or blind_status=='SEARCH_LIMIT':
        v6=None
    else:
        v6=(bool(exact_solvable) and blind_solvable is False) or v2

    unresolved_priority=bundle.get('recovery',{}).get('unresolved_field')=='reconnect_backlog_priority'
    if all_worlds:
        v7=True
    else:
        v7=False if unresolved_priority else None

    disp=_disposition(classification=cls,v2=v2,v3=v3,v4=v4,v5=v5,v6=v6,v7=v7)
    row={
        'signature':sig,
        'representative_recipe_id':bundle['recipe_id'],
        'exact_classification':cls,
        'filters':{
            'V0_SOURCE_COMPLETE':True,
            'V1_SOLVABLE':all_worlds,
            'V2_MULTIPLE_LEGAL_OPTIONS':v2,
            'V3_COMMON_SAFE_ACTION':v3,
            'V4_OBSERVATION_RELEVANCE':v4,
            'V5_BINDING_CONSTRAINT':v5,
            'V6_OUTCOME_SEPARATION':v6,
            'V7_OBJECTIVE_DEFINED':v7,
        },
        'binding':{
            'source_deadline':stats['deadline_binding'],
            'controlled_capacity':stats['capacity_binding'],
            'controlled_satellite_budget':stats['satellite_binding'],
        },
        'blind':{'status':blind_status,'solvable':blind_solvable,'memo_nodes':blind_memo_nodes},
        'paid_evidence_required':cls=='PAID_EVIDENCE_REQUIRED',
        'no_paid_query_solvable':no_paid_solvable,
        'v0_v7_disposition':disp,
    }
    return sig,row


def _load_completed(path:Path)->dict[str,dict[str,Any]]:
    out={}
    if not path.exists(): return out
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.strip():
            r=json.loads(line); out[str(r['signature'])]=r
    return out


def materialize(*,out_dir:Path,workers:int,max_memo_nodes:int,resume:bool)->dict[str,Any]:
    out_dir.mkdir(parents=True,exist_ok=True)
    sig_path=out_dir/'signature-validity.jsonl'; recipe_path=out_dir/'recipe-validity.jsonl'
    representatives,recipes,multiplicity=_collect_universe()
    exact=_load_exact_labels()
    if set(representatives)!=set(exact):
        raise RuntimeError('exact-label signature universe drift')
    completed=_load_completed(sig_path) if resume else {}
    if not resume and sig_path.exists(): sig_path.unlink()
    todo=sorted(set(representatives)-set(completed))
    mode='a' if resume and sig_path.exists() else 'w'
    with sig_path.open(mode,encoding='utf-8',buffering=1) as f:
        if workers<=1:
            for sig in todo:
                _,row=_evaluate_one((sig,representatives[sig],exact[sig],max_memo_nodes))
                completed[sig]=row; f.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+'\n')
        else:
            with ProcessPoolExecutor(max_workers=workers) as ex:
                futs={ex.submit(_evaluate_one,(sig,representatives[sig],exact[sig],max_memo_nodes)):sig for sig in todo}
                for fut in as_completed(futs):
                    sig,row=fut.result(); completed[sig]=row; f.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+'\n')

    complete=len(completed)==len(representatives)
    sig_disp=Counter(r['v0_v7_disposition'] for r in completed.values())
    blind_status=Counter(r['blind']['status'] for r in completed.values())
    projected=Counter(); projected_pending=Counter(); filter_pass={f:Counter() for f in [
        'V0_SOURCE_COMPLETE','V1_SOLVABLE','V2_MULTIPLE_LEGAL_OPTIONS','V3_COMMON_SAFE_ACTION',
        'V4_OBSERVATION_RELEVANCE','V5_BINDING_CONSTRAINT','V6_OUTCOME_SEPARATION','V7_OBJECTIVE_DEFINED']}
    if complete:
        with recipe_path.open('w',encoding='utf-8') as f:
            for recipe in recipes:
                row=completed[recipe['signature']]; disp=str(row['v0_v7_disposition'])
                projected[disp]+=1
                if recipe['pre_oracle_disposition']=='VALIDITY_PENDING': projected_pending[disp]+=1
                for fid,val in row['filters'].items(): filter_pass[fid][str(val)]+=1
                f.write(json.dumps({**recipe,'v0_v7_disposition':disp,'filters':row['filters']},ensure_ascii=False,sort_keys=True)+'\n')
    digest=sha256()
    for sig in sorted(completed):
        digest.update(sig.encode()); digest.update(b':'); digest.update(str(completed[sig]['v0_v7_disposition']).encode()); digest.update(b'\n')
    return {
        'schema_version':'0.1','status':'COMPLETE' if complete else 'PARTIAL',
        'bundle_count':len(recipes),'unique_solver_signature_count':len(representatives),
        'completed_signature_count':len(completed),
        'signature_disposition':dict(sorted(sig_disp.items())),
        'blind_status':dict(sorted(blind_status.items())),
        'projected_recipe_disposition':dict(sorted(projected.items())) if complete else {},
        'projected_validity_pending_disposition':dict(sorted(projected_pending.items())) if complete else {},
        'projected_filter_values':{k:dict(sorted(v.items())) for k,v in sorted(filter_pass.items())} if complete else {},
        'projection_multiplicity':{'mean':len(recipes)/len(representatives),'max':max(multiplicity.values())},
        'validity_digest_sha256':digest.hexdigest(),
        'signature_labels_ref':str(sig_path.relative_to(ROOT)),
        'recipe_labels_ref':str(recipe_path.relative_to(ROOT)) if complete else None,
        'release_status':'NOT_BENCHMARK_ADMIT',
    }


def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--out-dir',type=Path,default=DEFAULT_OUT)
    ap.add_argument('--workers',type=int,default=8); ap.add_argument('--max-memo-nodes',type=int,default=200_000)
    ap.add_argument('--resume',action='store_true'); ap.add_argument('--manifest',type=Path)
    args=ap.parse_args()
    m=materialize(out_dir=args.out_dir,workers=args.workers,max_memo_nodes=args.max_memo_nodes,resume=args.resume)
    text=json.dumps(m,ensure_ascii=False,indent=2,sort_keys=True)+'\n'
    if args.manifest:
        args.manifest.parent.mkdir(parents=True,exist_ok=True); args.manifest.write_text(text,encoding='utf-8')
    print(text,end=''); return 0


if __name__=='__main__': raise SystemExit(main())
