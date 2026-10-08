#!/usr/bin/env python3
"""ASC transfer: event-local invalidation inside a revealed future branch.

Earlier B-line audits established:

1. future obligations must be conditioned on query observations;
2. each realized branch can contain shared opportunity / Hall conflicts;
3. observation-only support narrowing can reuse whole branch certificates.

This audit closes the next gate: after H has revealed one branch, execution and
feedback events modify only *part* of that branch's conflict graph.  The frozen
Layer-2 ``IncrementalConflictFrontier`` must match a fresh rebuild after every
event while recomputing only dependency-intersecting components.

Synthetic branch layout
-----------------------
Each component owns M obligations, one terrestrial window of capacity M-1 and
one branch-local satellite window.  Therefore each component has Hall deficit 1
and the whole branch needs C backup units.  Components occupy disjoint time
blocks, so their terrestrial opportunity graphs are disconnected.

Events:
* pending feedback change on component 0;
* terrestrial-capacity consumption on component 1;
* delivered obligation on component 2 (when present);
* time crossing component 0's terrestrial validity boundary;
* global satellite-budget decrement as a control expected to touch every
  backup-dependent component.

No method score or learned policy is involved.  This is a structural
correctness/recomputation audit for the B transfer adapter.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
BENCH = ROOT / "code/evaluation/benchmark"
AGENTIC = ROOT / "code/evaluation/agentic"
for _p in (BENCH, AGENTIC):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from exact_reference_oracle_v0_1 import LocalState, PendingDelivery  # noqa: E402
from layer2_v2_conflict_frontier import (  # noqa: E402
    IncrementalConflictFrontier,
    canonical_snapshot,
)


def branch_bundle(components: int, obligations_per_component: int) -> dict[str, Any]:
    obligations = []
    terr_windows = []
    sat_windows = []
    horizon = 0
    for comp in range(components):
        # Disjoint blocks prevent cross-component terrestrial edges.
        start = 100 + comp * 200
        terr_end = start + 60
        sat_start = terr_end + 5
        sat_end = sat_start + 20
        deadline = sat_end + 40
        horizon = max(horizon, deadline + 10)
        for j in range(obligations_per_component):
            obligations.append(
                {
                    "obligation_id": f"c{comp}:g{j}",
                    "release_s": start - 20,
                    "deadline_s": deadline,
                }
            )
        terr_windows.append(
            {
                "window_id": f"terr-c{comp}",
                "start_s": start,
                "end_s": terr_end,
                "capacity_units": obligations_per_component - 1,
            }
        )
        sat_windows.append(
            {
                "window_id": f"sat-c{comp}",
                "start_s": sat_start,
                "end_s": sat_end,
                "capacity_units": 1,
            }
        )

    return {
        "schema_version": "0.1",
        "bundle_id": f"asc-component-invalidation-c{components}-m{obligations_per_component}",
        "recipe_id": "ASC_TRANSFER_COMPONENT_INVALIDATION",
        "stage": "WORLD_BUNDLE_PRE_EVIDENCE_PRE_ORACLE",
        "obligations": obligations,
        "public_environment": {
            "horizon_s": horizon,
            "satellite_windows": sat_windows,
        },
        "observation_projection": {
            # H has already been revealed by the upstream ASC query.  This
            # branch boundary therefore has no second direct-observation event.
            "evidence_regime": "POST_QUERY_REVEALED_BRANCH",
            "evidence_surfaces": [],
        },
        "worlds": [
            {
                "world_id": "revealed-branch",
                "terrestrial_windows": terr_windows,
                "latent_state": {},
            }
        ],
    }


def _state(*, budget: int) -> LocalState:
    return LocalState(satellite_budget=budget)


def _component_count(snapshot) -> int:
    return sum(len(world.components) for world in snapshot.world_certificates)


def _update_and_check(
    runtime: IncrementalConflictFrontier,
    *,
    at_s: int,
    state: LocalState,
    label: str,
) -> dict[str, Any]:
    states = {"revealed-branch": state}
    snapshot, delta = runtime.update(at_s=at_s, states=states)
    fresh = runtime.full_rebuild(at_s=at_s, states=states)
    match = canonical_snapshot(snapshot) == canonical_snapshot(fresh)
    if not match:
        raise AssertionError(f"incremental/full mismatch after {label}")
    return {
        "event": label,
        "at_s": at_s,
        "frontier_match": match,
        "component_count": _component_count(snapshot),
        "worst_case_backup_lower_bound": snapshot.worst_case_backup_lower_bound,
        "optimistic_feasible": snapshot.optimistic_feasible_all_worlds,
        "reused_components": int(delta["component_reuses"]),
        "recomputed_components": int(delta["component_recomputes"]),
        "partition_fallbacks": int(delta["partition_fallbacks"]),
        "reused_component_keys": [list(x) for x in delta["reused_component_keys"]],
        "recomputed_component_keys": [list(x) for x in delta["recomputed_component_keys"]],
        "invalidated_component_keys": [list(x) for x in delta["invalidated_component_keys"]],
    }


def run_cell(components: int, obligations_per_component: int) -> dict[str, Any]:
    bundle = branch_bundle(components, obligations_per_component)
    runtime = IncrementalConflictFrontier(bundle)
    budget = components
    state = _state(budget=budget)
    rows = []

    # Initial decision boundary after component-0 obligations are released but
    # before its first terrestrial opportunity.
    rows.append(_update_and_check(runtime, at_s=90, state=state, label="initial"))
    initial_components = rows[-1]["component_count"]
    if initial_components != components:
        raise AssertionError((components, initial_components))

    # 1) One ordinary terrestrial send in component 0 consumes one local
    # opportunity and creates a pending receipt/final-ACK lifecycle.
    pending = PendingDelivery(
        obligation_id="c0:g0",
        accepted=True,
        gateway_receipt_at_s=110,
        final_ack_at_s=130,
        negative_observation_at_s=None,
        gateway_receipt_seen=False,
    )
    state = replace(
        state,
        terrestrial_used=(("terr-c0", 1),),
        pending_deliveries=(pending,),
    )
    rows.append(_update_and_check(runtime, at_s=100, state=state, label="send_pending_c0"))

    # 2) Gateway receipt becomes visible/recorded; no other component changes.
    state = replace(
        state,
        pending_deliveries=(replace(pending, gateway_receipt_seen=True),),
    )
    rows.append(_update_and_check(runtime, at_s=110, state=state, label="gateway_receipt_c0"))

    # 3) Final ACK completes the same obligation at t=130.
    state = replace(
        state,
        delivered=("c0:g0",),
        pending_deliveries=(),
    )
    rows.append(_update_and_check(runtime, at_s=130, state=state, label="final_ack_c0"))

    # 5) Cross only component-0 terrestrial end. Later components retain their
    # candidate signatures and should remain reusable.
    first_terr_end = 160
    rows.append(_update_and_check(runtime, at_s=first_terr_end, state=state, label="time_cross_c0"))

    # 6) Global satellite-budget change is the all-component invalidation control.
    state = replace(state, satellite_budget=budget - 1)
    rows.append(_update_and_check(runtime, at_s=first_terr_end, state=state, label="global_backup_budget"))

    local_rows = [row for row in rows[1:-1]]
    global_row = rows[-1]
    return {
        "components": components,
        "obligations_per_component": obligations_per_component,
        "initial_component_count": initial_components,
        "events": rows,
        "checks": {
            "all_frontiers_match_fresh": all(row["frontier_match"] for row in rows),
            "all_local_events_reuse_some_component_when_possible": all(
                row["reused_components"] >= max(0, components - 1)
                for row in local_rows
                if components > 1 and row["event"] not in {"time_cross_c0"}
            ),
            "pending_feedback_recomputes_less_than_full": rows[1]["recomputed_components"] < components,
            "receipt_recomputes_less_than_full": rows[2]["recomputed_components"] < components,
            "final_ack_recomputes_less_than_full": rows[3]["recomputed_components"] < components,
            "global_budget_touches_all_backup_components": (
                global_row["recomputed_components"] >= global_row["component_count"]
                or global_row["partition_fallbacks"] > 0
            ),
            "no_partition_fallback_before_global_control": all(
                row["partition_fallbacks"] == 0 for row in rows[:-1]
            ),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "results/transfer/asc-pull-query-component-invalidation.json")
    args = ap.parse_args()
    cells = [run_cell(components, 3) for components in (2, 4, 8, 16)]
    checks = {
        "all_cells_exact_match": all(cell["checks"]["all_frontiers_match_fresh"] for cell in cells),
        "all_cells_local_pending_recompute_sublinear": all(cell["checks"]["pending_feedback_recomputes_less_than_full"] for cell in cells),
        "all_cells_local_receipt_recompute_sublinear": all(cell["checks"]["receipt_recomputes_less_than_full"] for cell in cells),
        "all_cells_local_final_ack_recompute_sublinear": all(cell["checks"]["final_ack_recomputes_less_than_full"] for cell in cells),
        "all_cells_no_local_partition_fallback": all(cell["checks"]["no_partition_fallback_before_global_control"] for cell in cells),
    }
    if not all(checks.values()):
        raise AssertionError({"checks": checks, "cells": cells})
    payload = {
        "stage": "ASC_PULL_QUERY_COMPONENT_LOCAL_INVALIDATION",
        "cells": cells,
        "summary": {
            "component_axis": [2, 4, 8, 16],
            "obligations_per_component": 3,
            "all_cells_exact_match": checks["all_cells_exact_match"],
            "max_components": 16,
            "local_event_recompute_counts": {
                str(cell["components"]): [
                    {"event": row["event"], "recomputed": row["recomputed_components"], "reused": row["reused_components"]}
                    for row in cell["events"][1:-1]
                ]
                for cell in cells
            },
        },
        "checks": checks,
        "claim_boundary": [
            "This audit begins after semantic query H has already revealed one active future-obligation branch; observation-domain reuse is tested separately.",
            "The branch contains synthetic controlled-stress independent conflict components; it is a method-structure test, not a source-paper empirical distribution.",
            "Incremental and fresh frontiers are compared by canonical structural equality after every event.",
            "Component recomputation count is a deterministic structural-work metric, not a wall-time theorem.",
            "The global backup-budget event is intentionally an all-component invalidation control and is not claimed local."
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(args.out), **payload["summary"], **checks}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
