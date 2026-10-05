#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
import json

from dynamic_world_materializer_v0_1 import iter_world_bundles
from v8_policy_baselines_v0_1 import solve_fixed_query_schedule


SRC='results/benchmark/layer1-v8-paid-signature-deep-v0.1.json'


def audit() -> dict:
    src=json.load(open(SRC,encoding='utf-8'))
    rows0=[r for r in src['rows'] if r['disposition']=='SURVIVES_DEEP_PAID_SIGNATURE_V0_1']
    rid_to_sig={str(r['representative_recipe_id']):str(r['signature']) for r in rows0}
    bundles={}
    for b in iter_world_bundles():
        rid=str(b['recipe_id'])
        if rid in rid_to_sig:
            bundles[rid]=b
            if len(bundles)==len(rid_to_sig): break
    modes=('FIRST_RELEASE','EVERY_RELEASE','SATELLITE_START','EVERY_SECOND_EVENT')
    disposition=Counter(); coverage=Counter(); rows=[]
    for rid in sorted(rid_to_sig):
        b=bundles[rid]; winners=[]; results={}
        for mode in modes:
            out=solve_fixed_query_schedule(b,mode=mode)
            name=out['baseline']; results[name]={'solvable':out['solvable'],'decisions':out['decisions']}
            if out['solvable']: winners.append(name)
        if winners:
            cls='SHORTCUT_SOLVED_FIXED_QUERY_TAIL'
            for w in winners: coverage[w]+=1
        else:
            cls='SURVIVES_FIXED_QUERY_TAIL_V0_1'
        disposition[cls]+=1
        rows.append({'signature':rid_to_sig[rid],'representative_recipe_id':rid,
                     'disposition':cls,'winning_baselines':sorted(winners),'results':results})
    survivors=[r['signature'] for r in rows if r['disposition']=='SURVIVES_FIXED_QUERY_TAIL_V0_1']
    return {'schema_version':'0.1','status':'V8_FIXED_QUERY_TAIL_AUDIT','input_signature_count':len(rows0),
            'disposition':dict(sorted(disposition.items())),'baseline_coverage':dict(sorted(coverage.items())),
            'survivor_signature_count':len(survivors),'survivor_signatures':survivors,'rows':rows}


if __name__=='__main__':
    print(json.dumps(audit(),ensure_ascii=False,indent=2,sort_keys=True))
