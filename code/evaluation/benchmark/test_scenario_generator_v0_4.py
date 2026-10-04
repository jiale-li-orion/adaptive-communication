#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0,str(HERE))

from experiment_ledger_v0_4 import build_ledger
from scenario_generator_v0_4 import generate,summarize


def main() -> int:
    rows=generate(phase_limit=1,catalog_size=5)
    summary=summarize(rows)
    assert summary['bundle_count']==16
    assert summary['outcome_counts']=={
        'INFORMATION_INFEASIBLE':7,
        'MULTI_QUERY':1,
        'NO_PAID_QUERY':4,
        'SINGLE_QUERY':4,
    }
    assert summary['exact_solvable_count']==9
    assert summary['no_query_solvable_count']==4

    ids=[r.bundle.bundle_id for r in rows]
    ids2=[r.bundle.bundle_id for r in generate(phase_limit=1,catalog_size=5)]
    assert ids==ids2
    assert len(ids)==len(set(ids))

    ledger=build_ledger(phase_limit=1,catalog_size=5)
    info=ledger['information_gap']
    alg=ledger['algorithm_gap']
    comp=ledger['computation_gap']

    assert info['paid_evidence_positive']==5
    assert alg['best_single_query_success']==8
    assert alg['conflict_guided_success']==9
    assert alg['fixed_primary_plus_receipt_success']==9
    assert alg['mean_conflict_guided_query_count'] < alg['mean_fixed_pair_query_count'] < alg['mean_always_query_all_count']
    assert comp['mean_guided_subset_solves'] < comp['mean_exhaustive_subset_solves']
    assert comp['guided_over_exhaustive_memo_ratio'] < 1.0

    print(
        'PASS Generator v0.4: multi-conflict process distribution exposes '
        'information, compositional-evidence, evidence-cost and computation gaps '
        'without claiming a success-rate win over the fixed two-query baseline'
    )
    return 0


if __name__=='__main__':
    raise SystemExit(main())
