#!/usr/bin/env python3
"""V9 evaluator-soundness audit over structural representatives.

The audit replays exact physical witnesses through the independent execution
evaluator and attacks the success predicate with concrete trace mutations.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import json

from audit_v8_baselines_v0_1 import _representatives
from exact_reference_oracle_v0_1 import hindsight_bundle_reference
from execution_trace_evaluator_v0_1 import evaluate_execution_trace, witness_to_execution_trace


def audit() -> dict:
    counters=Counter(); mutation_reasons=Counter(); rows=[]
    for cell,(_rank,bundle) in sorted(_representatives().items()):
        physical=hindsight_bundle_reference(bundle)
        if not physical['all_worlds_solvable']:
            counters['SKIP_NOT_ALL_WORLD_SOLVABLE']+=1
            continue
        bundle_ok=True
        for wr in physical['worlds']:
            wid=str(wr['world_id'])
            trace=witness_to_execution_trace(bundle,wr['witness'])
            good=evaluate_execution_trace(bundle,world_id=wid,actions=trace)
            if not good['success']:
                bundle_ok=False; counters['VALID_WITNESS_REJECTED']+=1; break

            # No-op / incomplete execution must not inherit success from planner text.
            noop=evaluate_execution_trace(bundle,world_id=wid,actions=[])
            mutation_reasons[noop['reason_code']]+=1
            if noop['success']:
                bundle_ok=False; counters['NOOP_EXPLOIT']+=1; break

            if trace:
                bad=deepcopy(trace); bad[0]['actor']='unauthorized-controller'
                r=evaluate_execution_trace(bundle,world_id=wid,actions=bad)
                mutation_reasons[r['reason_code']]+=1
                if r['success']:
                    bundle_ok=False; counters['AUTHORITY_EXPLOIT']+=1; break

                bad=deepcopy(trace); bad[0]['resource_id']='nonexistent-window'
                r=evaluate_execution_trace(bundle,world_id=wid,actions=bad)
                mutation_reasons[r['reason_code']]+=1
                if r['success']:
                    bundle_ok=False; counters['PHYSICS_EXPLOIT']+=1; break

                bad=deepcopy(trace); bad[0]['protected_subject']='irrelevant-state'
                r=evaluate_execution_trace(bundle,world_id=wid,actions=bad)
                mutation_reasons[r['reason_code']]+=1
                if r['success']:
                    bundle_ok=False; counters['SUBJECT_EXPLOIT']+=1; break

                if len(trace)>1:
                    bad=deepcopy(trace[:-1])
                    r=evaluate_execution_trace(bundle,world_id=wid,actions=bad)
                    mutation_reasons[r['reason_code']]+=1
                    if r['success']:
                        bundle_ok=False; counters['MISSING_COMPLETION_EXPLOIT']+=1; break

        counters['PASS_BUNDLE' if bundle_ok else 'FAIL_BUNDLE']+=1
        rows.append({'cell':list(cell),'recipe_id':bundle['recipe_id'],'passed':bundle_ok})
    return {
        'schema_version':'0.1',
        'status':'V9_EVALUATOR_SOUNDNESS_AUDIT',
        'structural_representative_count':len(rows),
        'counts':dict(sorted(counters.items())),
        'mutation_reasons':dict(sorted(mutation_reasons.items())),
        'passed':counters['FAIL_BUNDLE']==0 and counters['VALID_WITNESS_REJECTED']==0,
        'rows':rows,
    }


if __name__=='__main__':
    print(json.dumps(audit(),ensure_ascii=False,indent=2,sort_keys=True))
