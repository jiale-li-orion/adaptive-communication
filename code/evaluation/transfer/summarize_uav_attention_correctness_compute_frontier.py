#!/usr/bin/env python3
"""Build C-domain correctness/search Pareto summaries from frozen N=10 evidence.

Two frontiers are reported deliberately:

1. exact-correct methods only: basic-U L/U, set-MST-U L/U, pure exact mask;
   all have the same exact action-feasibility surface, so their internal search
   state counts are directly useful for attribution;
2. depth4 vs set-MST Future-Choice: a *quality/search-proxy* trade-off showing
   that the cheaper finite-horizon planner and the exact-correct safety layer
   occupy different non-dominated operating points.

Depth-k partial-state expansions and exact-search new states are not CPU-
equivalent operations.  The second frontier is therefore descriptive, not a
runtime-speed claim.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
COMMON = ROOT / "code/evaluation/common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from pareto import frontier  # noqa: E402


OLD = ROOT / "results/transfer/uav-attention-n10-future-choice-summary.json"
SET = ROOT / "results/transfer/uav-attention-set-mst-attribution.json"
OUT = ROOT / "results/transfer/uav-attention-correctness-compute-frontier.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    old = load(OLD)
    setm = load(SET)
    rows = {}
    for policy, oldrow in old["rows"].items():
        setrow = setm["n10"]["rows"][policy]
        d4 = oldrow["depth4_receding"]
        basic = oldrow["future_choice_lu"]
        sq = setrow["n10_quality"]
        sc = setrow["n10_compute"]

        quality = {
            "depth4": {
                "zero_tardiness": int(d4["zero_tardiness"]),
                "completed": int(d4["completed"]),
                "infeasible": int(d4["infeasible"]),
                "search_proxy": int(d4["partial_states_expanded"]),
                "search_unit": "depth4_partial_states_expanded",
            },
            "basic_u_future_choice": {
                "zero_tardiness": int(basic["zero_tardiness"]),
                "completed": int(basic["completed"]),
                "infeasible": int(basic["infeasible"]),
                "search_proxy": int(basic["total_search_proxy"]),
                "search_unit": "lower_plus_exact_new_states",
            },
            "set_mst_future_choice": {
                "zero_tardiness": int(sq["set_mst_lu_zero_tardiness"]),
                "completed": int(sq["set_mst_lu_completed"]),
                "infeasible": int(sq["set_mst_lu_infeasible"]),
                "search_proxy": int(sc["set_mst_total_search_proxy"]),
                "search_unit": "lower_plus_exact_new_states",
            },
            "pure_exact_mask": {
                # Reached action masks are identical to set-MST L/U on all
                # 924 audited frontiers, so the same heuristic ranking sees the
                # same safe action surface and therefore the same task quality.
                "zero_tardiness": int(sq["set_mst_lu_zero_tardiness"]),
                "completed": int(sq["set_mst_lu_completed"]),
                "infeasible": int(sq["set_mst_lu_infeasible"]),
                "search_proxy": int(sc["pure_exact_mask_new_states"]),
                "search_unit": "exact_mask_new_states",
            },
        }

        exact_points = {
            name: (
                float(row["zero_tardiness"]),
                float(row["completed"]),
                float(row["infeasible"]),
                float(row["search_proxy"]),
            )
            for name, row in quality.items()
            if name != "depth4"
        }
        exact_front = frontier(exact_points, directions=(+1, +1, -1, -1))

        quality_points = {
            name: (
                float(row["zero_tardiness"]),
                float(row["completed"]),
                float(row["infeasible"]),
                float(row["search_proxy"]),
            )
            for name, row in quality.items()
            if name in {"depth4", "set_mst_future_choice"}
        }
        quality_front = frontier(quality_points, directions=(+1, +1, -1, -1))

        rows[policy] = {
            "methods": quality,
            "exact_correct_frontier": list(exact_front),
            "depth4_vs_future_choice_frontier": list(quality_front),
            "checks": {
                "set_mst_is_exact_correct_frontier": "set_mst_future_choice" in exact_front,
                "basic_u_dominated_by_set_mst": "basic_u_future_choice" not in exact_front,
                "pure_exact_dominated_by_set_mst": "pure_exact_mask" not in exact_front,
                "depth4_and_future_choice_both_nondominated": set(quality_front) == {"depth4", "set_mst_future_choice"},
            },
        }

    checks = {
        "all_policies_set_mst_exact_frontier": all(r["checks"]["set_mst_is_exact_correct_frontier"] for r in rows.values()),
        "all_policies_basic_u_dominated": all(r["checks"]["basic_u_dominated_by_set_mst"] for r in rows.values()),
        "all_policies_pure_exact_dominated": all(r["checks"]["pure_exact_dominated_by_set_mst"] for r in rows.values()),
        "all_policies_depth4_and_set_mst_nondominated": all(r["checks"]["depth4_and_future_choice_both_nondominated"] for r in rows.values()),
        "set_mst_exact_reference_match": bool(setm["checks"]["n10_set_mst_frontier_exact_match"]),
    }
    if not all(checks.values()):
        raise AssertionError({"checks": checks, "rows": rows})

    payload = {
        "stage": "UAV_ATTENTION_CORRECTNESS_COMPUTE_PARETO",
        "cohort": old["cohort"],
        "rows": rows,
        "checks": checks,
        "interpretation": {
            "exact_correct": "Set-MST Future-Choice dominates the older basic-U and pure-exact-mask points on the frozen exact-correct N=10 cohort under the declared search-state proxy.",
            "quality_compute": "Depth4 and set-MST Future-Choice are both non-dominated: depth4 is cheaper but leaves residual hard-feasibility failures, while Future-Choice removes those failures at higher search cost.",
        },
        "claim_boundary": [
            "The Pareto relation uses algorithm-internal search-state proxies, not measured CPU time.",
            "Depth4 partial expansions and exact-search new states are different operation types; non-dominance is descriptive and must not be translated into a runtime-speed ratio.",
            "All task-quality counts are from the same frozen 21-seed method-independent N=10 cohort."
        ],
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(OUT), **checks}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
