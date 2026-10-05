#!/usr/bin/env python3
"""Progressive placement-preserving V8 audit over all paid-evidence solver signatures."""
from __future__ import annotations

from collections import Counter
import json

from dynamic_world_materializer_v0_1 import iter_world_bundles
from ordinary_baselines_compositional_v0_1 import audit_bundle
from v8_policy_baselines_v0_1 import (
    solve_always_query_then_plan,
    solve_depth_k,
    solve_depth_k_flow_terminal,
    solve_latest_feasible_send,
    solve_least_slack,
    solve_myopic_flow_voi,
    solve_receding_horizon,
    solve_shallow_rule,
)


LABELS = 'local_research/current/benchmark/generated/exact-labels-v0.1/signature-labels.jsonl'


def _paid_representatives() -> dict[str, str]:
    out={}
    with open(LABELS,encoding='utf-8') as f:
        for line in f:
            row=json.loads(line)
            if row['classification']=='PAID_EVIDENCE_REQUIRED':
                out[str(row['representative_recipe_id'])]=str(row['signature'])
    return out


def _headroom(bundle) -> str:
    overlap=len(bundle['obligations'])
    budget=int(bundle['public_environment']['satellite_budget_units'])
    if budget==max(1,overlap-1): return 'TIGHT'
    if budget==overlap: return 'BALANCED'
    if budget==overlap+1: return 'SLACK'
    return f'OTHER:{budget}'


def _collect_bundles(ids:set[str]):
    out={}
    for b in iter_world_bundles():
        rid=str(b['recipe_id'])
        if rid in ids:
            out[rid]=b
            if len(out)==len(ids): break
    if set(out)!=ids:
        raise RuntimeError(f'missing paid signature representatives: {len(ids-set(out))}')
    return out


def _solve_progressive(bundle):
    ordinary=audit_bundle(bundle)
    ordinary_winners=sorted(
        name for name,row in ordinary.items()
        if row.get('legal') and row.get('robust_success') is True
        and row.get('comparison_role')=='SAME_INFORMATION_SHORTCUT'
    )
    if ordinary_winners:
        return 'ORDINARY_FIRST_LAYER', ordinary_winners, {}

    cheap={
        'shallow_rule_combiner':solve_shallow_rule(bundle),
        'least_slack':solve_least_slack(bundle),
        'always_query_then_plan':solve_always_query_then_plan(bundle),
        'latest_feasible_send':solve_latest_feasible_send(bundle),
        'myopic_flow_voi':solve_myopic_flow_voi(bundle),
    }
    winners=sorted(k for k,v in cheap.items() if v['solvable'])
    if winners:
        return 'CHEAP_POLICY_RULE', winners, {k:v['decisions'] for k,v in cheap.items()}

    finite={
        'true_depth_1_belief':solve_depth_k(bundle,depth=1),
        'true_depth_2_belief':solve_depth_k(bundle,depth=2),
        'receding_horizon_3':solve_receding_horizon(bundle,horizon_decisions=3),
    }
    winners=sorted(k for k,v in finite.items() if v['solvable'])
    if winners:
        return 'FINITE_HORIZON', winners, {k:v['decisions'] for k,v in finite.items()}

    flow={f'depth_{k}_flow_terminal':solve_depth_k_flow_terminal(bundle,depth=k) for k in (1,2,3,4)}
    winners=sorted(k for k,v in flow.items() if v['solvable'])
    if winners:
        return 'FLOW_TERMINAL_HORIZON', winners, {k:v['decisions'] for k,v in flow.items()}
    return 'SURVIVES_V8_PAID_SIGNATURE_LADDER_V0_1', [], {
        **{k:v['decisions'] for k,v in finite.items()},
        **{k:v['decisions'] for k,v in flow.items()},
    }


def audit() -> dict:
    reps=_paid_representatives()
    bundles=_collect_bundles(set(reps))
    stage=Counter(); coverage=Counter(); rows=[]
    for rid in sorted(reps):
        b=bundles[rid]
        cls,winners,meta=_solve_progressive(b)
        stage[cls]+=1
        for w in winners: coverage[w]+=1
        rows.append({
            'signature':reps[rid],
            'representative_recipe_id':rid,
            'service_process':b['public_environment']['terrestrial_process_class'],
            'evidence_regime':b['observation_projection']['evidence_regime'],
            'overlap_count':len(b['obligations']),
            'resource_headroom':_headroom(b),
            'recovery_regime':b['recovery']['regime'],
            'disposition':cls,
            'winning_baselines':winners,
            'decision_counts':meta,
        })
    survivors=[r for r in rows if r['disposition']=='SURVIVES_V8_PAID_SIGNATURE_LADDER_V0_1']
    return {
        'schema_version':'0.1',
        'status':'V8_PAID_SIGNATURE_PROGRESSIVE_AUDIT',
        'paid_signature_count':len(rows),
        'disposition':dict(sorted(stage.items())),
        'baseline_coverage':dict(sorted(coverage.items())),
        'survivor_signature_count':len(survivors),
        'survivor_signatures':[r['signature'] for r in survivors],
        'rows':rows,
    }


if __name__=='__main__':
    print(json.dumps(audit(),ensure_ascii=False,indent=2,sort_keys=True))
