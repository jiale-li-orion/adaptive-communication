#!/usr/bin/env python3
"""Compact strong receding-horizon red-team versus the L/U future-choice shield."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


ROOT=Path(__file__).resolve().parents[3]
RECEDING=ROOT/"local_research/current/transfer/uav-attention-receding-baselines-n5-1000.json"
ROBUST=ROOT/"results/transfer/uav-attention-future-choice-robustness-summary.json"
OUT=ROOT/"results/transfer/uav-attention-receding-headroom-summary.json"


def sha(path:Path)->str: return sha256(path.read_bytes()).hexdigest()


def main()->int:
    rec=json.loads(RECEDING.read_text(encoding="utf-8")); rob=json.loads(ROBUST.read_text(encoding="utf-8"))
    depth4={k:v for k,v in rec["summary"].items() if k.endswith(":depth4")}
    lu=rob["lu_frontier_1000"]
    rows={}
    for key,d4 in depth4.items():
        policy=key.split(":",1)[0]; m=lu[policy]
        lu_proxy=m["exact_fallback_new_states"]+m["lower_search_expanded"]
        rows[policy]={
            "hard_feasible_seed_count":d4["hard_feasible_seed_count"],
            "depth4":{"zero_tardiness":d4["zero_tardiness"],"completed":d4["completed"],"infeasible":d4["infeasible"],"mean_tardiness":d4["mean_tardiness"],"partial_states_expanded":d4["partial_states_expanded"]},
            "future_choice_lu":{"zero_tardiness":m["zero_tardiness"],"completed":m["completed"],"infeasible":m["infeasible"],"exact_fallback_new_states":m["exact_fallback_new_states"],"lower_search_expanded":m["lower_search_expanded"],"total_search_proxy":lu_proxy},
            "depth4_closes_zero_tardiness_gap":d4["zero_tardiness"]==m["zero_tardiness"],
            "future_choice_has_strict_completion_or_infeasible_advantage":(m["completed"]>d4["completed"] or m["infeasible"]<d4["infeasible"]),
            "depth4_partial_search_proxy_over_lu_proxy":d4["partial_states_expanded"]/lu_proxy if lu_proxy else None,
        }
    payload={
        "stage":"UAV_ATTENTION_RECEDING_HEADROOM_REDTEAM",
        "setting":rec["setting"],
        "rows":rows,
        "checks":{
            "all_policies_use_107_hard_feasible_seeds":all(r["hard_feasible_seed_count"]==107 for r in rows.values()),
            "depth4_zero_tardiness_matches_lu_for_all":all(r["depth4_closes_zero_tardiness_gap"] for r in rows.values()),
            "lu_retains_some_strict_terminal_quality_gain":any(r["future_choice_has_strict_completion_or_infeasible_advantage"] for r in rows.values()),
            "depth4_search_proxy_is_lower_than_lu_proxy_for_all":all(r["depth4_partial_search_proxy_over_lu_proxy"]<1 for r in rows.values()),
        },
        "raw_receding_sha256":sha(RECEDING),
        "rerun_command":"OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 code/evaluation/transfer/run_uav_attention_receding_baselines.py --customers 5 --seeds 1000 --depths 1,2,3,4 --out <path>",
        "scientific_interpretation":{
            "positive":"Short-horizon depth1-3 leave a measurable continuation gap; L/U exact-fallback closes it with exact frontier correctness.",
            "negative":"At N=5, depth4 reaches 107/107 zero-tardiness for every official heuristic and uses fewer partial-search expansions than the current L/U search-work proxy. Thus N=5 does not establish algorithmic superiority over deep receding lookahead.",
            "next_gate":"Evaluate the paper's N=10+ settings, where depth4 is genuinely local relative to route length; keep exact/L-U resource guards bounded."
        },
        "claim_boundary":["Partial-state expansions and L/U search-work proxy are comparable only as coarse search-work counts, not CPU-equivalent operations.","Depth4's zero-tardiness equality does not imply identical completion/infeasible outcomes: Battery-Aware NN and Nearest-Neighbour retain one residual terminal failure each that L/U removes.","N=10+ scaling is required before any method-efficiency claim."]
    }
    assert all(payload["checks"].values()),payload["checks"]
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"out":str(OUT),**payload["checks"]},sort_keys=True)); return 0


if __name__=="__main__": raise SystemExit(main())
