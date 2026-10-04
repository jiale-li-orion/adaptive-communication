#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from multi_evidence_conflict_planner import choose_evidence_plan  # noqa: E402
from multi_evidence_scenario_tree import (  # noqa: E402
    Bundle,
    EvidenceQuery,
    Obligation,
    World,
    solve,
)


PRIMARY = EvidenceQuery(
    "primary_health",
    "communication.gateway.primary_health",
    "gateway",
    40,
)
RECEIPT = EvidenceQuery(
    "receipt_summary",
    "communication.gateway.receipt_summary",
    "gateway",
    20,
)
NODE = EvidenceQuery(
    "node_report",
    "communication.gateway.node_report",
    "gateway",
    60,
)


def crossed_bundle(*, primary_distinguishes: bool, receipt_distinguishes: bool) -> Bundle:
    # Same physical crossed structure as v0.2: one budget, two reports, early
    # vs late terrestrial rescue. Queries differ only in which current owner
    # fact they expose.
    vals_a = (
        ("primary_health", "recent" if primary_distinguishes else "same"),
        ("receipt_summary", "has-r0" if receipt_distinguishes else "same"),
        ("node_report", "same"),
    )
    vals_b = (
        ("primary_health", "stale" if primary_distinguishes else "same"),
        ("receipt_summary", "missing-r0" if receipt_distinguishes else "same"),
        ("node_report", "same"),
    )
    return Bundle(
        bundle_id=f"crossed-{int(primary_distinguishes)}-{int(receipt_distinguishes)}",
        fixed_event_times=(0, 100, 600, 1200, 2400, 3600, 4200, 4800, 7200),
        obligations=(
            Obligation("r0", 0, 3600),
            Obligation("r1", 3600, 7200),
        ),
        satellite_slots=(100, 4800),
        worlds=(
            World("wa", (600,), vals_a),
            World("wb", (4200,), vals_b),
        ),
        satellite_budget=1,
        queries=(PRIMARY, RECEIPT, NODE),
        initial_public_observation=(("gateway_health", "stale"),),
    )




def complementary_bundle() -> Bundle:
    queries = (
        EvidenceQuery("primary_health", PRIMARY.proposition, "gateway", 40),
        EvidenceQuery("receipt_summary", RECEIPT.proposition, "gateway", 20),
        EvidenceQuery("node_report", NODE.proposition, "gateway", 60),
    )
    return Bundle(
        bundle_id="complementary-primary-plus-receipt",
        fixed_event_times=(
            0, 20, 40, 60, 100, 200, 500,
            1000, 1100, 1200, 1500,
            2000, 2100, 2200, 2500,
        ),
        obligations=(
            Obligation("r0", 0, 500),
            Obligation("r1", 1000, 1500),
            Obligation("r2", 2000, 2500),
        ),
        satellite_slots=(100, 1100, 2100),
        worlds=(
            World(
                "w_r0_sat",
                (1200, 2200),
                (
                    ("primary_health", "early-path-unavailable"),
                    ("receipt_summary", "r2-not-indicated"),
                    ("node_report", "same"),
                ),
            ),
            World(
                "w_r1_sat",
                (200, 2200),
                (
                    ("primary_health", "early-path-available"),
                    ("receipt_summary", "r2-not-indicated"),
                    ("node_report", "same"),
                ),
            ),
            World(
                "w_r2_sat",
                (200, 1200),
                (
                    ("primary_health", "early-path-available"),
                    ("receipt_summary", "r2-needs-sat"),
                    ("node_report", "same"),
                ),
            ),
        ),
        satellite_budget=1,
        queries=queries,
        initial_public_observation=(
            ("gateway_health", "stale"),
            ("receipt_state", "stale"),
            ("sat_budget", "1"),
        ),
    )

def main() -> int:
    # Async regression: query issuance at t=0 must not consume a satellite slot
    # at t=100 while the response is still pending.
    async_bundle = Bundle(
        bundle_id="async-query-does-not-block-send",
        fixed_event_times=(0, 100, 500, 1000),
        obligations=(Obligation("r0", 0, 500),),
        satellite_slots=(100,),
        worlds=(
            World("w0", (), (("primary_health", "x"),)),
            World("w1", (), (("primary_health", "y"),)),
        ),
        satellite_budget=1,
        queries=(EvidenceQuery("primary_health", PRIMARY.proposition, "gateway", 400),),
    )
    result = solve(
        async_bundle,
        forced_first_action=("ISSUE_QUERY", "primary_health"),
    )
    assert result["solvable"], "asynchronous query must not block the t=100 send"

    primary_only = crossed_bundle(primary_distinguishes=True, receipt_distinguishes=False)
    plan = choose_evidence_plan(primary_only)
    assert plan.mode == "SINGLE_QUERY"
    assert plan.selected_query_ids == ("primary_health",)

    receipt_only = crossed_bundle(primary_distinguishes=False, receipt_distinguishes=True)
    plan = choose_evidence_plan(receipt_only)
    assert plan.mode == "SINGLE_QUERY"
    assert plan.selected_query_ids == ("receipt_summary",)

    both = crossed_bundle(primary_distinguishes=True, receipt_distinguishes=True)
    plan = choose_evidence_plan(both)
    assert plan.mode == "SINGLE_QUERY"
    # receipt_summary is the faster resolving query.
    assert plan.selected_query_ids == ("receipt_summary",)

    neither = crossed_bundle(primary_distinguishes=False, receipt_distinguishes=False)
    plan = choose_evidence_plan(neither)
    assert plan.mode == "INFORMATION_INFEASIBLE"

    complementary = complementary_bundle()
    plan = choose_evidence_plan(complementary)
    assert plan.mode == "MULTI_QUERY", plan
    assert set(plan.selected_query_ids) == {"primary_health", "receipt_summary"}
    assert "node_report" not in plan.selected_query_ids

    print(
        "PASS multi-evidence async oracle: query issuance does not block sends; "
        "planner selects the sufficient owner evidence and rejects irrelevant catalogs"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
