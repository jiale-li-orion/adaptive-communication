#!/usr/bin/env python3
"""Compact N=10 future-choice vs finite-horizon headroom results."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


ROOT=Path(__file__).resolve().parents[3]
COHORT=ROOT/"results/transfer/uav-attention-n10-constructive-cohort.json"
LU=ROOT/"local_research/current/transfer/uav-lu-n10-21cert.json"
RH=ROOT/"local_research/current/transfer/uav-receding-n10-21cert.json"
OUT=ROOT/"results/transfer/uav-attention-n10-future-choice-summary.json"


def sha(path:Path)->str: return sha256(path.read_bytes()).hexdigest()


def main()->int:
    cohort=json.loads(COHORT.read_text(encoding="utf-8")); lu=json.loads(LU.read_text(encoding="utf-8")); rh=json.loads(RH.read_text(encoding="utf-8"))
    seeds=cohort["cohort"]
    assert lu["setting"]["seed_values"]==seeds
    assert rh["setting"]["seed_values"]==seeds
    depth4={key.split(":",1)[0]:row for key,row in rh["summary"].items() if key.endswith(":depth4")}
    rows={}
    for policy,lrow in lu["paired_hard_feasible"].items():
        d4=depth4[policy]; total=lrow["exact_fallback_new_states"]+lrow["lower_search_expanded"]
        rows[policy]={
            "cohort_count":len(seeds),
            "future_choice_lu":{
                "zero_tardiness":lrow["zero_tardiness"],
                "completed":lrow["completed"],
                "infeasible":lrow["infeasible"],
                "exact_mask_new_states":lrow["exact_mask_new_states"],
                "exact_fallback_calls":lrow["exact_fallback_calls"],
                "exact_fallback_new_states":lrow["exact_fallback_new_states"],
                "lower_search_expanded":lrow["lower_search_expanded"],
                "carried_certificate":lrow["carried_certificate"],
                "upper_impossible":lrow["upper_impossible"],
                "total_search_proxy":total,
                "fallback_state_ratio_over_exact":lrow["exact_fallback_new_states"]/lrow["exact_mask_new_states"],
                "total_search_proxy_ratio_over_exact":total/lrow["exact_mask_new_states"],
            },
            "depth4_receding":{
                "zero_tardiness":d4["zero_tardiness"],
                "completed":d4["completed"],
                "infeasible":d4["infeasible"],
                "mean_tardiness":d4["mean_tardiness"],
                "partial_states_expanded":d4["partial_states_expanded"],
            },
            "strict_zero_tardiness_gain_vs_depth4":lrow["zero_tardiness"]-d4["zero_tardiness"],
            "strict_completion_gain_vs_depth4":lrow["completed"]-d4["completed"],
            "infeasible_reduction_vs_depth4":d4["infeasible"]-lrow["infeasible"],
        }
    checks={
        "method_independent_constructive_cohort":not cohort["future_choice_method_used_for_selection"] and not cohort["exact_oracle_used_for_selection"],
        "cohort_count_21":len(seeds)==21,
        "lu_frontier_exact_match":lu["correctness"]["frontier_mismatch"]==0,
        "lu_frontier_checks_924":lu["correctness"]["reached_frontier_match_checks"]==924,
        "lu_all_policies_21_of_21_zero_tardiness":all(r["future_choice_lu"]["zero_tardiness"]==21 for r in rows.values()),
        "lu_all_policies_21_of_21_completed":all(r["future_choice_lu"]["completed"]==21 for r in rows.values()),
        "lu_all_policies_zero_infeasible":all(r["future_choice_lu"]["infeasible"]==0 for r in rows.values()),
        "depth4_leaves_quality_gap_for_at_least_three_policies":sum(r["strict_zero_tardiness_gain_vs_depth4"]>0 or r["strict_completion_gain_vs_depth4"]>0 or r["infeasible_reduction_vs_depth4"]>0 for r in rows.values())>=3,
        "lu_reduces_exact_fallback_states_for_all":all(r["future_choice_lu"]["exact_fallback_new_states"]<r["future_choice_lu"]["exact_mask_new_states"] for r in rows.values()),
    }
    assert all(checks.values()),checks
    payload={
        "stage":"UAV_ATTENTION_N10_FUTURE_CHOICE_HEADROOM",
        "cohort_ref":str(COHORT.relative_to(ROOT)),
        "cohort":seeds,
        "checks":checks,
        "rows":rows,
        "raw_hashes":{"lu_local":sha(LU),"receding_local":sha(RH)},
        "rerun_commands":{
            "lu":"OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 code/evaluation/transfer/run_uav_attention_future_choice_lu.py --customers 10 --seed-list <cohort_csv> --lower-search-limit 96 --out <path>",
            "receding":"OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 code/evaluation/transfer/run_uav_attention_receding_baselines.py --customers 10 --seed-list <cohort_csv> --depths 2,3,4 --out <path>",
        },
        "scientific_interpretation":{
            "positive":"On a method-independent cohort already solvable by at least one official heuristic, full future-choice feasibility closes residual deadline/completion failures that depth4 receding lookahead leaves on three of four policy families, while matching exact action frontiers at 924 reached boundaries.",
            "compute":"L/U reduces exact-fallback new-state search to roughly 42-55% of pure exact-mask search; including constructive lower search, the total search-work proxy is roughly 66-78% of pure exact. Depth4 is cheaper but not exact-correct and leaves task-quality gaps.",
            "boundary":"Greedy Deadline-Battery already solves 20/21 seeds with depth4, so future-choice is not universally necessary. This is a selective correctness layer, not a blanket claim that ordinary receding planning fails."
        },
        "claim_boundary":["The 21-seed cohort is a constructive lower-bound subset of hard-feasible N=10 seeds, selected without the proposed method or exact oracle.","Search-work counts are not CPU-equivalent operations; wall-time superiority is not claimed.","The L/U route adapter is domain-specific transfer code; generic Layer-2 integration remains separate."]
    }
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"out":str(OUT),**checks},sort_keys=True)); return 0


if __name__=="__main__": raise SystemExit(main())
