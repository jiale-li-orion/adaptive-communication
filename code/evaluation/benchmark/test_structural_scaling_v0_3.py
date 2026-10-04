#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0,str(HERE))

from structural_scaling_v0_3 import run_structural_scaling


def main() -> int:
    result=run_structural_scaling(ks=(2,3,4),phase_limit=3)
    s=result['summary']

    assert s['2']['selected_query_count']==1
    assert s['3']['selected_query_count']==2
    assert s['4']['selected_query_count']==2

    # Delivery-constraint preprocessing no longer requires exact policy solves.
    # Guided exact memo work is lower even on the 2-world case; lightweight
    # max-flow preprocessing is reported separately rather than hidden.
    assert s['2']['guided_over_exhaustive_memo_ratio'] < 1.0
    assert s['3']['guided_over_exhaustive_memo_ratio'] < 1.0
    assert s['4']['guided_over_exhaustive_memo_ratio'] < 1.0
    assert s['2']['mean_guided_structural_flow_solves'] > 0
    assert s['3']['mean_guided_structural_flow_solves'] > s['2']['mean_guided_structural_flow_solves']
    assert s['4']['mean_guided_structural_flow_solves'] > s['3']['mean_guided_structural_flow_solves']

    assert s['3']['mean_guided_subset_solves'] < s['3']['mean_exhaustive_subset_solves']
    assert s['4']['mean_guided_subset_solves'] < s['4']['mean_exhaustive_subset_solves']

    print(
        'PASS structural scaling v0.3: delivery-constraint preprocessing '
        'reduces exact search work while reporting max-flow cost separately'
    )
    return 0


if __name__=='__main__':
    raise SystemExit(main())
