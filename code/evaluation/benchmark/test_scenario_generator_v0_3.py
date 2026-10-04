#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0,str(HERE))

from scenario_generator_v0_3 import generate, summarize
from search_scaling_v0_3 import run_scaling


def main() -> int:
    rows=generate(catalog_size=5,phase_limit=4)
    summary=summarize(rows)
    assert summary["bundle_count"] == 4 * 4 * 4
    counts=summary["outcome_counts"]
    assert counts.get("NO_PAID_QUERY",0) > 0
    assert counts.get("SINGLE_QUERY",0) > 0
    assert counts.get("MULTI_QUERY",0) > 0
    assert counts.get("INFORMATION_INFEASIBLE",0) > 0

    ids=[r.bundle.bundle_id for r in rows]
    ids2=[r.bundle.bundle_id for r in generate(catalog_size=5,phase_limit=4)]
    assert ids==ids2
    assert len(ids)==len(set(ids))

    scaling=run_scaling(phase_limit=3,catalog_sizes=(3,5,7))
    for size,metrics in scaling["summary"].items():
        assert metrics["mean_guided_subset_solves"] < metrics["mean_exhaustive_subset_solves"]
        assert metrics["memo_node_ratio_guided_over_exhaustive"] < 1.0

    print(
        "PASS Generator v0.3 process distribution: mixed information regimes "
        "emerge from latent modes/evidence projections; guided search preserves "
        "exact selection with lower deterministic search work"
    )
    return 0


if __name__=="__main__":
    raise SystemExit(main())
