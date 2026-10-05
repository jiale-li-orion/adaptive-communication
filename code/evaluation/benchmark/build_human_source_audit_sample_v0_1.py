#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from compositional_recipe_generator_v0_1 import core_recipes

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SPLIT=ROOT/'results/benchmark/layer1-structure-aware-split-v0.1.json'


def _rank(recipe_id:str)->str:
    return sha256(recipe_id.encode()).hexdigest()


def main()->int:
    split=json.loads(SPLIT.read_text(encoding='utf-8'))
    idx={r.recipe_id:r for r in core_recipes()}
    candidates=[]
    for row in split['rows']:
        r=idx[row['recipe_id']]
        hardness=list(r.hardness) or ['NONE']
        tokens={
            f"split:{row['split']}",
            f"role:{row['candidate_role']}",
            f"split-role:{row['split']}|{row['candidate_role']}",
        }
        for p in r.source_profiles:
            tokens.add(f'profile:{p}')
            tokens.add(f"split-profile:{row['split']}|{p}")
            tokens.add(f"role-profile:{row['candidate_role']}|{p}")
        for h in hardness:
            tokens.add(f'hardness:{h}')
            tokens.add(f"split-hardness:{row['split']}|{h}")
            tokens.add(f"role-hardness:{row['candidate_role']}|{h}")
        for p in r.source_profiles:
            for h in hardness:
                tokens.add(f'profile-hardness:{p}|{h}')
        candidates.append((row,r,tokens))

    uncovered=set().union(*(tokens for _row,_r,tokens in candidates))
    chosen=[]; chosen_ids=set()
    while uncovered:
        scored=[]
        for row,r,tokens in candidates:
            if row['recipe_id'] in chosen_ids: continue
            gain=len(tokens & uncovered)
            if gain<=0: continue
            hard_bonus=3 if row['candidate_role']=='HARD_PRE_ADMISSION_SURVIVOR' else 0
            scored.append((-(gain+hard_bonus),_rank(row['recipe_id']),row,r,tokens))
        if not scored:
            break
        _score,_hash,row,r,tokens=min(scored,key=lambda x:(x[0],x[1]))
        chosen.append((row,r));chosen_ids.add(row['recipe_id']);uncovered-=tokens

    # Human audit should not hinge on a single hard example per split.  Keep
    # four stable hard survivors in each split when available.
    hard_counts=Counter(row['split'] for row,_r in chosen if row['candidate_role']=='HARD_PRE_ADMISSION_SURVIVOR')
    for split_name in ('train','dev','test'):
        need=max(0,4-hard_counts[split_name])
        pool=sorted(
            [(row,r) for row,r,_tokens in candidates if row['split']==split_name and row['candidate_role']=='HARD_PRE_ADMISSION_SURVIVOR' and row['recipe_id'] not in chosen_ids],
            key=lambda x:_rank(x[0]['recipe_id'])
        )
        for row,r in pool[:need]:
            chosen.append((row,r));chosen_ids.add(row['recipe_id'])

    samples=[]
    for row,r in sorted(chosen,key=lambda x:(x[0]['split'],x[0]['candidate_role'],_rank(x[0]['recipe_id']))):
        samples.append({
            'sample_id':f'HSA-{len(samples):04d}',
            'recipe_id':row['recipe_id'],
            'split':row['split'],
            'candidate_role':row['candidate_role'],
            'source_profiles':list(r.source_profiles),
            'hardness':list(r.hardness),
            'task_case_id':row['task_case_id'],
            'geometry_shape_cluster':row['geometry_shape_cluster'],
            'review':{
                'source_extraction_semantics':'PENDING',
                'authority_priority_time_semantics':'PENDING',
                'task_family_identity':'PENDING',
                'oracle_success_set':'PENDING',
                'evaluator_trace':'PENDING',
                'reviewer':None,
                'notes':None,
            },
        })
    artifact={
        'schema_version':'0.1',
        'status':'PENDING_HUMAN_REVIEW',
        'sampling_rule':'stable greedy pairwise-stratified cover over split, candidate role, source profile and hardness interactions; plus four hard-survivor examples per split when available',
        'sample_count':len(samples),
        'coverage_token_count':len(set().union(*(tokens for _row,_r,tokens in candidates))),
        'uncovered_token_count':len(uncovered),
        'samples':samples,
        'pass_rule':'Every sampled item must have all five review fields PASS and a named reviewer; any FAIL blocks Q11 until corrected and re-audited.',
    }
    print(json.dumps(artifact,ensure_ascii=False,indent=2,sort_keys=True))
    return 0


if __name__=='__main__': raise SystemExit(main())
