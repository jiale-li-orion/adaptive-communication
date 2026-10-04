#!/usr/bin/env python3
"""Unified information / algorithm / computation ledger for Layer-1 v0.4."""
from __future__ import annotations

from collections import Counter,defaultdict
from typing import Any
import json

from multi_evidence_conflict_planner import (
    assess_query_subset,
    conflict_guided_query_search,
    exhaustive_query_search,
)
from scenario_generator_v0_4 import generate


def _best_single_success(bundle) -> bool:
    for q in bundle.queries:
        if assess_query_subset(bundle,(q.query_id,)).solvable:
            return True
    return False


def _fixed_pair_success(bundle) -> bool:
    ids={q.query_id for q in bundle.queries}
    pair=tuple(q for q in ('primary_health','receipt_summary') if q in ids)
    return assess_query_subset(bundle,pair).solvable if pair else False


def build_ledger(*,phase_limit:int=4,catalog_size:int=5) -> dict[str,Any]:
    rows=generate(phase_limit=phase_limit,catalog_size=catalog_size)

    exact_solvable=[r for r in rows if r.exact_solvable]
    query_positive=[r for r in exact_solvable if not r.no_query_solvable]

    best_single=0
    fixed_pair=0
    conflict_guided=0
    guided_queries=[]
    fixed_pair_queries=[]
    always_all_queries=[]

    exhaustive_subset_solves=[]
    guided_subset_solves=[]
    exhaustive_memo=[]
    guided_memo=[]
    guided_preprocessing=[]

    by_outcome=defaultdict(lambda:Counter())

    for r in rows:
        b=r.bundle
        if r.exact_solvable:
            one=_best_single_success(b)
            pair=_fixed_pair_success(b)
            guided,gdiag=conflict_guided_query_search(b)
            exhaustive,ediag=exhaustive_query_search(b)

            best_single += int(one)
            fixed_pair += int(pair)
            conflict_guided += int(guided.exact_solvable and guided.mode!='INFORMATION_INFEASIBLE')

            guided_queries.append(len(guided.selected_query_ids))
            fixed_pair_queries.append(2)
            always_all_queries.append(len(b.queries))

            # Computation ledger only compares evidence search when paid evidence
            # is actually required. No-query cases do not need subset search.
            if not r.no_query_solvable:
                exhaustive_subset_solves.append(ediag.subset_solves)
                guided_subset_solves.append(gdiag.subset_solves)
                exhaustive_memo.append(ediag.total_memo_nodes)
                guided_memo.append(gdiag.total_memo_nodes)
                guided_preprocessing.append(gdiag.preprocessing_solves)

            by_outcome[r.outcome_class]['count']+=1
            by_outcome[r.outcome_class]['best_single_success']+=int(one)
            by_outcome[r.outcome_class]['fixed_pair_success']+=int(pair)
            by_outcome[r.outcome_class]['guided_success']+=int(guided.exact_solvable and guided.mode!='INFORMATION_INFEASIBLE')
        else:
            by_outcome[r.outcome_class]['count']+=1

    def mean(xs):
        return sum(xs)/len(xs) if xs else None

    info={
        'total_bundles':len(rows),
        'exact_solvable':len(exact_solvable),
        'no_query_solvable':sum(r.no_query_solvable for r in rows),
        'paid_evidence_positive':len(query_positive),
        'paid_evidence_positive_rate_among_exact_solvable':(
            len(query_positive)/len(exact_solvable) if exact_solvable else None
        ),
        'information_infeasible':sum(not r.exact_solvable for r in rows),
    }

    algorithm={
        'exact_solvable_denominator':len(exact_solvable),
        'best_single_query_success':best_single,
        'best_single_query_success_rate':best_single/len(exact_solvable) if exact_solvable else None,
        'fixed_primary_plus_receipt_success':fixed_pair,
        'fixed_primary_plus_receipt_success_rate':fixed_pair/len(exact_solvable) if exact_solvable else None,
        'conflict_guided_success':conflict_guided,
        'conflict_guided_success_rate':conflict_guided/len(exact_solvable) if exact_solvable else None,
        'mean_conflict_guided_query_count':mean(guided_queries),
        'mean_fixed_pair_query_count':mean(fixed_pair_queries),
        'mean_always_query_all_count':mean(always_all_queries),
    }

    computation={
        'query_required_cases':len(exhaustive_subset_solves),
        'mean_exhaustive_subset_solves':mean(exhaustive_subset_solves),
        'mean_guided_subset_solves':mean(guided_subset_solves),
        'mean_guided_preprocessing_solves':mean(guided_preprocessing),
        'mean_exhaustive_total_memo_nodes':mean(exhaustive_memo),
        'mean_guided_total_memo_nodes':mean(guided_memo),
        'guided_over_exhaustive_memo_ratio':(
            mean(guided_memo)/mean(exhaustive_memo)
            if exhaustive_memo and mean(exhaustive_memo) else None
        ),
    }

    return {
        'generator':'v0.4-multi-conflict-process-pilot',
        'information_gap':info,
        'algorithm_gap':algorithm,
        'computation_gap':computation,
        'by_outcome':{k:dict(v) for k,v in sorted(by_outcome.items())},
        'claim_boundary':[
            'Success is all-obligations feasibility; query count and memo nodes are primitive metrics, not weighted reward.',
            'Fixed-pair and always-query baselines are cost references; asynchronous query issuance is non-blocking.',
            'Information-infeasible bundles are not counted as algorithm failures.',
            'Conflict-guided search is compared against exhaustive exact evidence-subset selection on the same bundle.',
        ],
    }


if __name__=='__main__':
    print(json.dumps(build_ledger(),indent=2,sort_keys=True))
