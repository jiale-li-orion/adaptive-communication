#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from multi_evidence_conflict_planner import (  # noqa: E402
    choose_evidence_plan,
    conflict_guided_query_search,
)
from test_multi_evidence_scenario_tree import (  # noqa: E402
    complementary_bundle,
    crossed_bundle,
)


def main() -> int:
    cases = [
        crossed_bundle(primary_distinguishes=True, receipt_distinguishes=False),
        crossed_bundle(primary_distinguishes=False, receipt_distinguishes=True),
        crossed_bundle(primary_distinguishes=True, receipt_distinguishes=True),
        complementary_bundle(),
    ]

    total_guided = 0
    total_full_subsets = 0
    for bundle in cases:
        reference = choose_evidence_plan(bundle)
        guided, diag = conflict_guided_query_search(bundle)
        assert guided.mode == reference.mode
        assert set(guided.selected_query_ids) == set(reference.selected_query_ids)

        # Full subset enumeration over three catalog queries would inspect all
        # seven non-empty subsets in the absence of structure.
        total_full_subsets += 2 ** len(bundle.queries) - 1
        total_guided += diag.subset_solves

        assert "node_report" in diag.constant_pruned
        assert "node_report" not in diag.candidate_query_ids

    assert total_guided < total_full_subsets
    # Current four mechanism cases: 28 raw subsets vs a small exact guided set.
    print(
        f"PASS conflict-guided query search: exact decisions preserved with "
        f"{total_guided} subset solves vs {total_full_subsets} unstructured subsets"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
