#!/usr/bin/env python3
"""Select method-independent hard-feasible UAV seeds by native constructive proof.

For the external paper's N=10 evaluation setting, a seed enters the cohort iff
at least one *official released heuristic* already completes all customers,
returns to depot, incurs zero tardiness and no infeasible action.  Such a route
is a constructive lower certificate that the hard mission is feasible.

The selector never invokes the future-choice method or exact continuation
oracle, so it cannot select seeds based on proposed-method success.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


ROOT=Path(__file__).resolve().parents[3]
TRANSFER=ROOT/"code/evaluation/transfer"
if str(TRANSFER) not in sys.path: sys.path.insert(0,str(TRANSFER))
from run_uav_attention_future_choice_lu import N_SETTINGS,_git_head,_install_gymnasium_shim  # noqa: E402

EXT=ROOT/"local_research/external/uav-attention-routing"


def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--customers",type=int,default=10,choices=sorted(N_SETTINGS)); ap.add_argument("--seeds",type=int,default=200); ap.add_argument("--out",type=Path,default=ROOT/"results/transfer/uav-attention-n10-constructive-cohort.json"); args=ap.parse_args()
    os.environ.setdefault("OPENBLAS_NUM_THREADS","1"); os.environ.setdefault("OMP_NUM_THREADS","1"); os.environ.setdefault("MKL_NUM_THREADS","1")
    _install_gymnasium_shim(); sys.path.insert(0,str(EXT))
    from src.env import SingleUAVConfig,SingleUAVEnv  # type: ignore
    from src.heuristic import NearestNeighbourHeuristic,NearestDeadlineFirstHeuristic,GreedyDeadlineBatteryHeuristic,BatteryAwareNearestNeighbour  # type: ignore
    mission_time,dmin,dmax=N_SETTINGS[args.customers]
    def cfg(): return SingleUAVConfig(num_customers=args.customers,num_chargers=1,mission_time=mission_time,deadline_min=dmin,deadline_max=dmax,reward_mode="completion_ratio")
    classes={"nearest_neighbour":NearestNeighbourHeuristic,"nearest_deadline":NearestDeadlineFirstHeuristic,"greedy_deadline_battery":GreedyDeadlineBatteryHeuristic,"battery_aware_nn":BatteryAwareNearestNeighbour}
    per={k:[] for k in classes}; cohort=[]; witnesses={}
    for seed in range(args.seeds):
        good=[]
        for name,cls in classes.items():
            env=SingleUAVEnv(cfg()); obs,info=env.reset(seed=seed); pol=cls(); actions=[]
            while True:
                action=int(pol.act(env,obs,info)); actions.append(action); obs,_r,term,trunc,info=env.step(action)
                if term or trunc: break
            ok=bool(info["completed"] and info["returned_to_depot"] and float(info["ep_tardiness"])<=1e-9 and int(info["ep_infeasible"])==0)
            if ok:
                per[name].append(seed); good.append(name); witnesses.setdefault(str(seed),{})[name]=actions
        if good: cohort.append(seed)
    payload={
        "stage":"UAV_ATTENTION_CONSTRUCTIVE_HARD_FEASIBLE_COHORT",
        "external_repo":"mdehghani86/uav-attention-routing",
        "external_commit":_git_head(EXT),
        "setting":{"num_customers":args.customers,"mission_time":mission_time,"deadline_min":dmin,"deadline_max":dmax,"seed_scan":[0,args.seeds-1]},
        "selection_rule":"include seed iff at least one official heuristic natively completes all customers, returns to depot, has zero tardiness and zero infeasible actions",
        "future_choice_method_used_for_selection":False,
        "exact_oracle_used_for_selection":False,
        "cohort":cohort,
        "cohort_count":len(cohort),
        "official_heuristic_success_seeds":per,
        "constructive_witness_actions":witnesses,
        "claim_boundary":["This cohort is a lower-bound subset of all hard-feasible seeds; seeds not selected may still admit a zero-tardiness route.","Selection favors seeds already solvable by at least one ordinary official heuristic and therefore is conservative for proposed-method evaluation."]
    }
    args.out.parent.mkdir(parents=True,exist_ok=True); args.out.write_text(json.dumps(payload,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"out":str(args.out),"cohort_count":len(cohort),"cohort":cohort,"by_heuristic":{k:len(v) for k,v in per.items()}},sort_keys=True)); return 0


if __name__=="__main__": raise SystemExit(main())
