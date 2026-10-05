#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
import json

from dynamic_world_materializer_v0_1 import iter_world_bundles
from v8_policy_baselines_v0_1 import solve_depth_k_flow_terminal, solve_receding_horizon


SRC='results/benchmark/layer1-v8-paid-signatures-v0.1.json'


def audit() -> dict:
    src=json.load(open(SRC,encoding='utf-8'))
    rows0=[r for r in src['rows'] if r['disposition']=='SURVIVES_V8_PAID_SIGNATURE_LADDER_V0_1']
    rid_to_sig={str(r['representative_recipe_id']):str(r['signature']) for r in rows0}
    bundles={}
    for b in iter_world_bundles():
        rid=str(b['recipe_id'])
        if rid in rid_to_sig:
            bundles[rid]=b
            if len(bundles)==len(rid_to_sig): break
    if set(bundles)!=set(rid_to_sig):
        raise RuntimeError('missing paid-signature survivor bundles')

    disposition=Counter(); coverage=Counter(); rows=[]
    for rid in sorted(rid_to_sig):
        b=bundles[rid]
        winners=[]; results={}
        for k in (4,5,6):
            name=f'receding_horizon_{k}'
            out=solve_receding_horizon(b,horizon_decisions=k)
            results[name]={'solvable':out['solvable'],'decisions':out['decisions']}
            if out['solvable']:
                winners.append(name); break
        if not winners:
            for k in (5,6):
                name=f'depth_{k}_flow_terminal'
                out=solve_depth_k_flow_terminal(b,depth=k)
                results[name]={'solvable':out['solvable'],'decisions':out['decisions']}
                if out['solvable']:
                    winners.append(name); break
        if winners:
            cls='SHORTCUT_SOLVED_DEEP_PAID_SIGNATURE'
            for w in winners: coverage[w]+=1
        else:
            cls='SURVIVES_DEEP_PAID_SIGNATURE_V0_1'
        disposition[cls]+=1
        rows.append({
            'signature':rid_to_sig[rid],
            'representative_recipe_id':rid,
            'service_process':b['public_environment']['terrestrial_process_class'],
            'overlap_count':len(b['obligations']),
            'recovery_regime':b['recovery']['regime'],
            'disposition':cls,
            'winning_baselines':winners,
            'results':results,
        })
    survivors=[r['signature'] for r in rows if r['disposition']=='SURVIVES_DEEP_PAID_SIGNATURE_V0_1']
    return {
        'schema_version':'0.1',
        'status':'V8_PAID_SIGNATURE_DEEP_AUDIT',
        'input_signature_count':len(rows0),
        'disposition':dict(sorted(disposition.items())),
        'baseline_coverage':dict(sorted(coverage.items())),
        'survivor_signature_count':len(survivors),
        'survivor_signatures':survivors,
        'rows':rows,
    }


if __name__=='__main__':
    print(json.dumps(audit(),ensure_ascii=False,indent=2,sort_keys=True))
