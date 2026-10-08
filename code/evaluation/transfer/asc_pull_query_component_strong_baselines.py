#!/usr/bin/env python3
"""Strong-baseline ladder for ASC component-local future-choice reuse.

Uses the same post-query revealed-branch family as
``asc_pull_query_component_invalidation`` and evaluates the same causal event
sequence with four deterministic mechanisms:

1. fresh ordered exact: new exact planner at every boundary;
2. ordinary persistent exact: same action order + exact memo, no dependency
   projection and no conflict certificates;
3. dependency-cache exact: dead-history projection + replay-gated persistent
   exact, but no conditional conflict frontier;
4. incremental conflict frontier: event-local component invalidation.

Exact arms must agree on the complete action-feasibility frontier at every
boundary.  The conflict frontier is compared to its own fresh structural
rebuild because it is a sound L/U structural layer, not an exact action solver.

The sequence intentionally contains a gateway-receipt update that is observable
history but does not change future feasibility once an accepted send already has
a deadline-safe final ACK.  This tests whether reuse follows *future dependency*
rather than merely the existence of a new event.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
TRANSFER = ROOT / "code/evaluation/transfer"
BENCH = ROOT / "code/evaluation/benchmark"
AGENTIC = ROOT / "code/evaluation/agentic"
for _p in (TRANSFER, BENCH, AGENTIC):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from asc_pull_query_component_invalidation import branch_bundle  # noqa: E402
from exact_reference_oracle_v0_1 import LocalState, PendingDelivery  # noqa: E402
from layer2_v2_conflict_frontier import (  # noqa: E402
    IncrementalConflictFrontier,
    canonical_snapshot,
)
from layer2_v2_dependency_cache_baseline import PersistentDependencyExact  # noqa: E402
from layer2_v2_incremental_exact_baseline import PersistentOrderedExact  # noqa: E402


def event_sequence(components: int) -> list[tuple[str, int, LocalState]]:
    state = LocalState(satellite_budget=components)
    rows = [("initial", 90, state)]
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
    rows.append(("send_pending_c0", 100, state))
    state = replace(
        state,
        pending_deliveries=(replace(pending, gateway_receipt_seen=True),),
    )
    rows.append(("gateway_receipt_c0", 110, state))
    state = replace(state, delivered=("c0:g0",), pending_deliveries=())
    rows.append(("final_ack_c0", 130, state))
    rows.append(("time_cross_c0", 160, state))
    state = replace(state, satellite_budget=components - 1)
    rows.append(("global_backup_budget", 160, state))
    return rows


def _exact_row(planner, *, at_s: int, state: LocalState) -> dict[str, Any]:
    out = planner.build_frontier(
        at_s=at_s,
        states={"revealed-branch": state},
        query_budget=0,
    )
    return {
        "actions": out["actions"],
        "expanded": int(out["metrics"]["expanded"]),
        "recursive_calls": int(out["metrics"]["recursive_calls"]),
        "memo_hits": int(out["metrics"]["memo_hits"]),
        "separator_replay_success": int(out["metrics"].get("separator_replay_success", 0)),
        "wall_s": float(out["wall_s"]),
    }


def run_cell(components: int, obligations_per_component: int = 3) -> dict[str, Any]:
    bundle = branch_bundle(components, obligations_per_component)
    persistent = PersistentOrderedExact(bundle)
    dependency = PersistentDependencyExact(bundle)
    conflict = IncrementalConflictFrontier(bundle)
    rows = []

    for label, at_s, state in event_sequence(components):
        fresh = _exact_row(PersistentOrderedExact(bundle), at_s=at_s, state=state)
        ordinary = _exact_row(persistent, at_s=at_s, state=state)
        dep = _exact_row(dependency, at_s=at_s, state=state)
        if fresh["actions"] != ordinary["actions"] or fresh["actions"] != dep["actions"]:
            raise AssertionError(
                {
                    "components": components,
                    "event": label,
                    "fresh": fresh["actions"],
                    "ordinary": ordinary["actions"],
                    "dependency": dep["actions"],
                }
            )

        states = {"revealed-branch": state}
        snap, delta = conflict.update(at_s=at_s, states=states)
        rebuilt = conflict.full_rebuild(at_s=at_s, states=states)
        structural_match = canonical_snapshot(snap) == canonical_snapshot(rebuilt)
        if not structural_match:
            raise AssertionError((components, label, "conflict frontier mismatch"))

        rows.append(
            {
                "event": label,
                "at_s": at_s,
                "action_frontier": fresh["actions"],
                "exact_frontier_match": True,
                "fresh_exact": fresh,
                "ordinary_persistent_exact": ordinary,
                "dependency_cache_exact": dep,
                "incremental_conflict": {
                    "structural_match_fresh": structural_match,
                    "component_count": int(snap.component_count),
                    "reused_components": int(delta["component_reuses"]),
                    "recomputed_components": int(delta["component_recomputes"]),
                    "partition_fallbacks": int(delta["partition_fallbacks"]),
                },
            }
        )

    def total(path: str, field: str) -> int:
        return sum(int(row[path][field]) for row in rows)

    return {
        "components": components,
        "obligations_per_component": obligations_per_component,
        "events": rows,
        "totals": {
            "fresh_exact_expanded": total("fresh_exact", "expanded"),
            "ordinary_persistent_exact_expanded": total("ordinary_persistent_exact", "expanded"),
            "dependency_cache_exact_expanded": total("dependency_cache_exact", "expanded"),
            "dependency_separator_replay_success": total("dependency_cache_exact", "separator_replay_success"),
            "incremental_conflict_component_recomputes": total("incremental_conflict", "recomputed_components"),
            "incremental_conflict_component_reuses": total("incremental_conflict", "reused_components"),
        },
        "checks": {
            "all_exact_frontiers_match": all(row["exact_frontier_match"] for row in rows),
            "all_conflict_frontiers_match_fresh": all(
                row["incremental_conflict"]["structural_match_fresh"] for row in rows
            ),
            "persistent_exact_not_more_expansions_than_fresh": (
                total("ordinary_persistent_exact", "expanded")
                <= total("fresh_exact", "expanded")
            ),
            "dependency_exact_not_more_expansions_than_fresh": (
                total("dependency_cache_exact", "expanded")
                <= total("fresh_exact", "expanded")
            ),
            "local_receipt_requires_zero_conflict_recompute": (
                next(row for row in rows if row["event"] == "gateway_receipt_c0")
                ["incremental_conflict"]["recomputed_components"] == 0
            ),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "results/transfer/asc-pull-query-component-strong-baselines.json")
    args = ap.parse_args()
    cells = [run_cell(components) for components in (2, 4, 8, 16)]
    checks = {
        "all_cells_exact_frontier_match": all(c["checks"]["all_exact_frontiers_match"] for c in cells),
        "all_cells_conflict_structural_match": all(c["checks"]["all_conflict_frontiers_match_fresh"] for c in cells),
        "persistent_exact_never_worse_than_fresh": all(c["checks"]["persistent_exact_not_more_expansions_than_fresh"] for c in cells),
        "dependency_exact_never_worse_than_fresh": all(c["checks"]["dependency_exact_not_more_expansions_than_fresh"] for c in cells),
        "receipt_event_zero_component_recompute_all_cells": all(c["checks"]["local_receipt_requires_zero_conflict_recompute"] for c in cells),
    }
    if not all(checks.values()):
        raise AssertionError({"checks": checks, "cells": cells})
    payload = {
        "stage": "ASC_PULL_QUERY_COMPONENT_STRONG_BASELINE_LADDER",
        "cells": cells,
        "checks": checks,
        "summary": {
            "component_axis": [2, 4, 8, 16],
            "fresh_exact_expanded": {str(c["components"]): c["totals"]["fresh_exact_expanded"] for c in cells},
            "ordinary_persistent_exact_expanded": {str(c["components"]): c["totals"]["ordinary_persistent_exact_expanded"] for c in cells},
            "dependency_cache_exact_expanded": {str(c["components"]): c["totals"]["dependency_cache_exact_expanded"] for c in cells},
            "incremental_component_recomputes": {str(c["components"]): c["totals"]["incremental_conflict_component_recomputes"] for c in cells},
            "incremental_component_reuses": {str(c["components"]): c["totals"]["incremental_conflict_component_reuses"] for c in cells},
            "dependency_separator_replay_success": {str(c["components"]): c["totals"]["dependency_separator_replay_success"] for c in cells},
        },
        "claim_boundary": [
            "Fresh/persistent/dependency exact arms compare complete action-feasibility frontiers; the conflict frontier is a structural L/U layer and is checked against fresh structural rebuild instead.",
            "Expansion counts and conflict-component recomputes are different work units and must not be ratioed as CPU-equivalent operations.",
            "The synthetic revealed branch is controlled stress for method attribution, not the source Pull-Based empirical distribution.",
            "Wall-time superiority is not claimed from this audit."
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(args.out), **payload["summary"], **checks}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
