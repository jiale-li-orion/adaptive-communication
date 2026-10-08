#!/usr/bin/env python3
"""Compact attribution for the B->C deadline-set MST upper certificate.

Compares the previously frozen/basic C-domain U/L adapter against the stronger
set-valued optimistic certificate motivated by B's obligation-set conflict
frontier.  Task quality, cohort and exact correctness authority are unchanged;
only the U-bound changes.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OLD_N10 = ROOT / "results/transfer/uav-attention-n10-future-choice-summary.json"
NEW_N10 = ROOT / "local_research/current/transfer/uav-lu-n10-21cert-setmst.json"
N15_BASIC = ROOT / "local_research/current/transfer/uav-lu-n15-seed1.json"
N15_SET = ROOT / "local_research/current/transfer/uav-lu-n15-seed1-setmst.json"
N15_D4 = ROOT / "local_research/current/transfer/uav-receding-n15-seed1.json"
OUT = ROOT / "results/transfer/uav-attention-set-mst-attribution.json"


def sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main() -> int:
    old = json.loads(OLD_N10.read_text(encoding="utf-8"))
    new = json.loads(NEW_N10.read_text(encoding="utf-8"))
    n15_basic = json.loads(N15_BASIC.read_text(encoding="utf-8"))
    n15_set = json.loads(N15_SET.read_text(encoding="utf-8"))
    n15_d4 = json.loads(N15_D4.read_text(encoding="utf-8"))

    rows = {}
    for policy, nrow in new["paired_hard_feasible"].items():
        orow = old["rows"][policy]["future_choice_lu"]
        d4 = old["rows"][policy]["depth4_receding"]
        old_total = int(orow["total_search_proxy"])
        new_total = int(nrow["exact_fallback_new_states"] + nrow["lower_search_expanded"])
        rows[policy] = {
            "n10_quality": {
                "depth4_zero_tardiness": int(d4["zero_tardiness"]),
                "depth4_completed": int(d4["completed"]),
                "depth4_infeasible": int(d4["infeasible"]),
                "set_mst_lu_zero_tardiness": int(nrow["zero_tardiness"]),
                "set_mst_lu_completed": int(nrow["completed"]),
                "set_mst_lu_infeasible": int(nrow["infeasible"]),
            },
            "n10_compute": {
                "pure_exact_mask_new_states": int(nrow["exact_mask_new_states"]),
                "basic_u_exact_fallback_new_states": int(orow["exact_fallback_new_states"]),
                "set_mst_exact_fallback_new_states": int(nrow["exact_fallback_new_states"]),
                "basic_u_total_search_proxy": old_total,
                "set_mst_total_search_proxy": new_total,
                "basic_fallback_ratio_over_exact": float(orow["fallback_state_ratio_over_exact"]),
                "set_mst_fallback_ratio_over_exact": (
                    nrow["exact_fallback_new_states"] / nrow["exact_mask_new_states"]
                ),
                "basic_total_ratio_over_exact": float(orow["total_search_proxy_ratio_over_exact"]),
                "set_mst_total_ratio_over_exact": new_total / nrow["exact_mask_new_states"],
                "set_mst_total_reduction_vs_basic": 1.0 - new_total / old_total,
                "depth4_partial_states_expanded": int(d4["partial_states_expanded"]),
                "set_mst_proxy_over_depth4": new_total / int(d4["partial_states_expanded"]),
            },
        }

    n15 = {}
    for policy, set_row in n15_set["paired_hard_feasible"].items():
        basic_row = n15_basic["paired_hard_feasible"][policy]
        d4 = n15_d4["summary"][f"{policy}:depth4"]
        n15[policy] = {
            "quality": {
                "depth4_zero_tardiness": int(d4["zero_tardiness"]),
                "depth4_completed": int(d4["completed"]),
                "depth4_infeasible": int(d4["infeasible"]),
                "lu_zero_tardiness": int(set_row["zero_tardiness"]),
                "lu_completed": int(set_row["completed"]),
                "lu_infeasible": int(set_row["infeasible"]),
            },
            "compute": {
                "exact_mask_new_states": int(set_row["exact_mask_new_states"]),
                "basic_u_fallback_new_states": int(basic_row["exact_fallback_new_states"]),
                "set_mst_fallback_new_states": int(set_row["exact_fallback_new_states"]),
                "basic_u_lower_search_expanded": int(basic_row["lower_search_expanded"]),
                "set_mst_lower_search_expanded": int(set_row["lower_search_expanded"]),
                "set_mst_fallback_ratio_over_exact": (
                    set_row["exact_fallback_new_states"] / set_row["exact_mask_new_states"]
                ),
            },
        }

    checks = {
        "n10_set_mst_frontier_exact_match": new["correctness"]["frontier_mismatch"] == 0,
        "n10_set_mst_924_frontier_checks": new["correctness"]["reached_frontier_match_checks"] == 924,
        "n10_quality_unchanged_21_of_21": all(
            row["n10_quality"]["set_mst_lu_zero_tardiness"] == 21
            and row["n10_quality"]["set_mst_lu_completed"] == 21
            and row["n10_quality"]["set_mst_lu_infeasible"] == 0
            for row in rows.values()
        ),
        "n10_total_search_proxy_reduced_all_policies": all(
            row["n10_compute"]["set_mst_total_search_proxy"]
            < row["n10_compute"]["basic_u_total_search_proxy"]
            for row in rows.values()
        ),
        "n15_seed1_set_mst_frontier_exact_match": n15_set["correctness"]["frontier_mismatch"] == 0,
        "n15_seed1_set_mst_reduces_fallback_all_policies": all(
            row["compute"]["set_mst_fallback_new_states"]
            < row["compute"]["basic_u_fallback_new_states"]
            for row in n15.values()
        ),
    }
    assert all(checks.values()), checks

    payload = {
        "stage": "UAV_ATTENTION_SET_MST_CONFLICT_ATTRIBUTION",
        "method_change": (
            "Replace C's basic individual-deadline + global-MST optimistic U with a set-valued deadline-threshold MST U. "
            "For every deadline d, all still-unserved customers due by d must fit inside the optimistic MST travel lower bound before d."
        ),
        "soundness_note": (
            "Any real route prefix serving all customers due by d is a connected walk spanning current plus that due-set, "
            "whose distance is at least the Euclidean MST. Battery, depot return and charger detours are ignored, so False remains a sound U=0 proof."
        ),
        "n10": {
            "cohort": old["cohort"],
            "rows": rows,
        },
        "n15_seed1": n15,
        "checks": checks,
        "raw_hashes": {
            "old_n10_summary": sha(OLD_N10),
            "new_n10_set_mst_local": sha(NEW_N10),
            "n15_basic_local": sha(N15_BASIC),
            "n15_set_mst_local": sha(N15_SET),
            "n15_depth4_local": sha(N15_D4),
        },
        "claim_boundary": [
            "The N=10 quality comparison is on the same frozen 21-seed method-independent constructive cohort used before this bound was introduced.",
            "The N=15 result is a single bounded scaling probe and is not a distribution-level claim.",
            "Search-state counts are not CPU-equivalent to depth-k partial expansions; the method is not claimed faster than depth4 receding planning.",
            "The new bound is a C-domain instantiation of B's set-level future-obligation conflict idea, not evidence that the two physical domains share identical constraints."
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(OUT), **checks}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
