#!/usr/bin/env python3
from __future__ import annotations
import copy, hashlib, json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SRC=ROOT/'results'/'agentic'/'o5-context-transition-devset-v1'/'inputs'
OUT=ROOT/'results'/'agentic'/'o5-context-update-ablation-v1'

H8='backhaul_recovery_before_task_recovery'
H9='task_recovery_revision'
H10='post_revision_reconciliation'
MODE='action_conditioned_compact'

def load(event):
    return json.loads((SRC/event/f'{MODE}.json').read_text())

def dump(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=json.dumps(obj,ensure_ascii=False,indent=2)+'\n'
    path.write_text(raw,encoding='utf-8')
    return len(raw.encode()), hashlib.sha256(raw.encode()).hexdigest()

def phase_signature(env):
    c=env.get('candidate_action_context') or {}
    tc=env.get('task_contract') or {}
    desired=tc.get('desired_state') or {}
    return {
        'candidate_phase_index':c.get('phase_index'),
        'candidate_required_period_s':c.get('required_period_s'),
        'task_desired_state':desired,
        'task_policy_revision':tc.get('policy_revision'),
        'evidence_need_ids':[x.get('evidence_need_id') for x in env.get('evidence_needs',[])],
        'state_revision':(env.get('investigation_state') or {}).get('state_revision'),
    }

def stale_periods(obj):
    periods=[]
    if isinstance(obj,dict):
        if 'required_period_s' in obj and isinstance(obj['required_period_s'],(int,float)):
            periods.append(int(obj['required_period_s']))
        for v in obj.values(): periods.extend(stale_periods(v))
    elif isinstance(obj,list):
        for v in obj: periods.extend(stale_periods(v))
    return periods

def make_variants(prev,cur):
    variants={}
    variants['fresh_rebuild']=copy.deepcopy(cur)

    fh=copy.deepcopy(cur)
    fh['context_history']=[
        {
            'label':'previous_context_before_task_revision',
            'task_contract':copy.deepcopy(prev.get('task_contract')),
            'investigation_state':copy.deepcopy(prev.get('investigation_state')),
            'evidence_needs':copy.deepcopy(prev.get('evidence_needs')),
            'candidate_action_context':copy.deepcopy(prev.get('candidate_action_context')),
        }
    ]
    fh['planner_rules']=list(fh.get('planner_rules') or [])+[
        'context_history contains prior runtime context and may contain superseded Task-dependent state; resolve revision authority before acting.'
    ]
    variants['full_history']=fh

    naive=copy.deepcopy(cur)
    for key in ('investigation_state','evidence_needs','candidate_action_context'):
        naive[key]=copy.deepcopy(prev.get(key))
    naive['assembly']=copy.deepcopy(cur.get('assembly'))
    naive['planner_rules']=list(naive.get('planner_rules') or [])+[
        'This arm emulates an ordinary incremental cache that updates the TaskContract but retains prior cached reasoning/context objects until their independent refresh.'
    ]
    variants['naive_incremental_cache']=naive

    rev=copy.deepcopy(cur)
    # Stable surfaces are inherited from the previous turn; Task-dependent runtime state
    # is taken from the current revision.  This makes the invalidation rule explicit.
    for key in ('resource_inventory','capabilities','output_schema'):
        rev[key]=copy.deepcopy(prev.get(key))
    rev['context_update']= {
        'trigger':'TaskContract revision',
        'retained':['resource_inventory','capabilities','output_schema'],
        'invalidated':['investigation_state','evidence_needs','candidate_action_context'],
        'recomputed_from_current_revision':['investigation_state','evidence_needs','candidate_action_context'],
    }
    rev['planner_rules']=list(rev.get('planner_rules') or [])+[
        'context_update declares which cached surfaces survived this Task revision and which Task-dependent surfaces were recomputed.'
    ]
    variants['revision_aware_update']=rev
    return variants

def metrics(name,obj,current_period):
    allp=stale_periods(obj)
    stale=[p for p in allp if p!=current_period]
    c=obj.get('candidate_action_context') or {}
    history=obj.get('context_history') or []
    stale_candidate_periods=[]
    for h in history:
        hc=(h.get('candidate_action_context') or {})
        p=hc.get('required_period_s')
        if p is not None and int(p)!=current_period: stale_candidate_periods.append(int(p))
    cp=c.get('required_period_s')
    top_stale = cp is not None and int(cp)!=current_period
    return {
        'variant':name,
        'current_required_period_s':current_period,
        'top_candidate_required_period_s':cp,
        'top_candidate_stale':bool(top_stale),
        'historical_stale_candidate_periods':stale_candidate_periods,
        'all_required_period_values':sorted(set(allp)),
        'contains_conflicting_required_periods':len(set(allp))>1,
        'stale_required_period_occurrences':len(stale),
        'context_history_entries':len(history),
        'has_explicit_invalidation':bool(obj.get('context_update')),
    }

def main():
    transitions=[(H8,H9),(H9,H10)]
    manifest={'experiment':'o5-context-update-ablation-v1','mode':MODE,'transitions':[]}
    for prev_id,cur_id in transitions:
        prev,cur=load(prev_id),load(cur_id)
        current_period=int((cur.get('candidate_action_context') or {})['required_period_s'])
        entry={'from':prev_id,'to':cur_id,'from_signature':phase_signature(prev),'to_signature':phase_signature(cur),'variants':[]}
        for name,obj in make_variants(prev,cur).items():
            path=OUT/f'{prev_id}__to__{cur_id}'/f'{name}.json'
            n,h=dump(path,obj)
            row=metrics(name,obj,current_period)
            row.update({'protocol_like_json_bytes':n,'sha256':h,'input':str(path.relative_to(ROOT))})
            entry['variants'].append(row)
        manifest['transitions'].append(entry)
    manifest['source_devset']=str((SRC.parent/'manifest.json').relative_to(ROOT))
    manifest['claim_ceiling']=(
        'Structural pre-model ablation only. It measures stale Task-dependent context/conflict and input size; '
        'model decision quality requires the live-model R1/R3 experiment.'
    )
    dump(OUT/'manifest.json',manifest)
    print(json.dumps(manifest,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
