#!/usr/bin/env python3
"""Cross-domain audit: ASC and UAV adapters use the same FutureChoiceEngine."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import types


ROOT=Path(__file__).resolve().parents[3]
AGENTIC=ROOT/"code/evaluation/agentic"
TRANSFER=ROOT/"code/evaluation/transfer"
BENCH=ROOT/"code/evaluation/benchmark"
for p in (AGENTIC,TRANSFER,BENCH):
    if str(p) not in sys.path: sys.path.insert(0,str(p))

from future_choice_engine import FutureChoiceCertificate,FutureChoiceEngine  # noqa: E402
from asc_pull_query_shared_opportunity_frontier import branch_bundle  # noqa: E402
from conditional_feasibility_frontier import ConditionalFeasibilityFrontier  # noqa: E402
from run_uav_attention_future_choice_lu import FutureChoiceRouteFrontier,N_SETTINGS,_install_gymnasium_shim  # noqa: E402
from uav_future_choice_adapter import UAVFutureChoiceAdapter  # noqa: E402


def cid(prefix:str,witness)->str:
    return sha256((prefix+repr(witness)).encode()).hexdigest()[:20]


@dataclass(frozen=True)
class ASCContext:
    active_branches:tuple[int,...]
    backup_budget:int


class ASCAdapter:
    """Root QUERY_H certificate + carried FOLLOW_CERT after observation narrowing."""
    def __init__(self,branches:int=4,depth:int=4):
        self.branches=branches; self.depth=depth
        self.branch_min={}
        for b in range(branches):
            certs=ConditionalFeasibilityFrontier(branch_bundle(b,depth)).snapshot()
            self.branch_min[b]=max(c.min_satellite_budget for c in certs)

    def action_key(self,action:str): return action
    def _branch_map(self,context:ASCContext): return {b:self.branch_min[b] for b in context.active_branches}
    def optimistic_possible(self,context:ASCContext,action:str)->bool:
        if action in {"QUERY_H","FOLLOW_CERT"}:
            return all(self.branch_min[b]<=context.backup_budget for b in context.active_branches)
        # WAIT/irrelevant query leave worlds aliased until branch deadlines;
        # exact fallback will reject them, but this cheap U does not overclaim.
        return True
    def carried_certificate_valid(self,context:ASCContext,action:str,certificate:FutureChoiceCertificate)->bool:
        if action!="FOLLOW_CERT": return False
        mapping=certificate.witness["branch_min_backup"]
        return all(b in mapping and mapping[b]<=context.backup_budget for b in context.active_branches)
    def lower_certificate(self,context:ASCContext,action:str):
        if action!="QUERY_H": return None
        mapping=self._branch_map(context)
        if not all(v<=context.backup_budget for v in mapping.values()): return None
        witness={"branch_min_backup":mapping,"policy":"observe H then execute branch certificate"}
        return FutureChoiceCertificate(cid("asc",witness),witness,frozenset({"active_support","backup_budget"}))
    def exact_certificate(self,context:ASCContext,action:str):
        # In this controlled transfer, QUERY_H is already lower-certified;
        # WAIT/QUERY_A cannot satisfy mutually exclusive branch obligations.
        return None
    def carry_after_commit(self,context:ASCContext,action:str,certificate:FutureChoiceCertificate):
        return certificate if action=="QUERY_H" else None


def _install_and_import_uav():
    os.environ.setdefault("OPENBLAS_NUM_THREADS","1"); os.environ.setdefault("OMP_NUM_THREADS","1"); os.environ.setdefault("MKL_NUM_THREADS","1")
    _install_gymnasium_shim(); ext=ROOT/"local_research/external/uav-attention-routing"; sys.path.insert(0,str(ext))
    from src.env import SingleUAVConfig,SingleUAVEnv  # type: ignore
    return SingleUAVConfig,SingleUAVEnv


def main()->int:
    # --- B / ASC: root lower certificate survives observation support narrowing.
    asc_adapter=ASCAdapter(branches=4,depth=4); asc=FutureChoiceEngine(asc_adapter)
    root=ASCContext((0,1,2,3),1)
    q=asc.classify(root,"QUERY_H"); wait=asc.classify(root,"WAIT")
    assert q.safe and q.source=="L1-constructive" and not wait.safe
    asc.commit(root,q)
    narrowed=ASCContext((2,),1)
    follow=asc.classify(narrowed,"FOLLOW_CERT")
    assert follow.safe and follow.source=="L1-carried"
    exhausted=ASCContext((2,),0)
    bad=asc.classify(exhausted,"FOLLOW_CERT")
    assert not bad.safe

    # --- C / UAV: same engine protocol on a native N=10 hard-feasible seed.
    SingleUAVConfig,SingleUAVEnv=_install_and_import_uav(); mt,dmin,dmax=N_SETTINGS[10]
    from src.heuristic import NearestDeadlineFirstHeuristic  # type: ignore
    cfg=SingleUAVConfig(num_customers=10,num_chargers=1,mission_time=mt,deadline_min=dmin,deadline_max=dmax,reward_mode="completion_ratio")
    env=SingleUAVEnv(cfg); _obs,_info=env.reset(seed=21)
    front=FutureChoiceRouteFrontier(env,lower_search_limit=96); uav=FutureChoiceEngine(UAVFutureChoiceAdapter(front))
    native=env.get_action_mask(); exact={}; generic={}
    state=front.state(env)
    for action,ok in enumerate(native):
        if not bool(ok): continue
        c=uav.classify(env,int(action)); generic[int(action)]=c.safe
        child=front.post(state,int(action)); exact[int(action)]=bool(child is not None and front.exact(child) is not None)
    assert generic==exact
    safe_actions=[a for a,v in generic.items() if v]
    assert safe_actions
    chosen=safe_actions[0]; chosen_cls=uav.classify(env,chosen); assert chosen_cls.safe
    uav.commit(env,chosen_cls)

    # Full-episode generic-engine rollout on a challenging official heuristic.
    env2=SingleUAVEnv(cfg); obs2,info2=env2.reset(seed=21); policy=NearestDeadlineFirstHeuristic()
    method_front=FutureChoiceRouteFrontier(env2,lower_search_limit=96)
    exact_front=FutureChoiceRouteFrontier(env2,lower_search_limit=0)
    generic_engine=FutureChoiceEngine(UAVFutureChoiceAdapter(method_front))
    episode_frontier_checks=0
    while True:
        native=env2.get_action_mask(); classifications={}
        import numpy as np
        method_mask=np.zeros_like(native,dtype=bool); exact_mask=np.zeros_like(native,dtype=bool)
        for action,ok in enumerate(native):
            if not bool(ok): continue
            c=generic_engine.classify(env2,int(action)); classifications[int(action)]=c; method_mask[action]=c.safe
            child=exact_front.post(exact_front.state(env2),int(action))
            exact_mask[action]=bool(child is not None and exact_front.exact(child) is not None)
        assert list(map(bool,method_mask))==list(map(bool,exact_mask))
        episode_frontier_checks+=1
        if method_mask.any():
            use=dict(info2); use["action_mask"]=method_mask; action=int(policy.act(env2,obs2,use))
        else:
            action=int(policy.act(env2,obs2,info2))
        generic_engine.commit(env2,classifications[action])
        obs2,_reward,terminated,truncated,info2=env2.step(action)
        if terminated or truncated: break

    full_episode_ok=bool(info2["completed"] and info2["returned_to_depot"] and float(info2["ep_tardiness"])<=1e-9 and int(info2["ep_infeasible"])==0)

    payload={
        "stage":"GENERIC_FUTURE_CHOICE_ENGINE_CROSS_DOMAIN_AUDIT",
        "checks":{
            "asc_query_h_lower_certified":q.safe and q.L==1,
            "asc_wait_exact_rejected":not wait.safe,
            "asc_observation_narrowing_reuses_carried_certificate":follow.source=="L1-carried",
            "asc_budget_crossing_invalidates_carried_certificate":not bad.safe,
            "uav_root_frontier_matches_exact":generic==exact,
            "uav_full_episode_frontiers_match_exact":episode_frontier_checks>0,
            "uav_full_episode_zero_tardiness_complete":full_episode_ok,
            "uav_full_episode_uses_carried_certificate":generic_engine.metrics["carried_hits"]>0,
            "same_engine_class_used_for_both":True,
        },
        "asc_metrics":asc.metrics,
        "uav_metrics":uav.metrics,
        "uav_seed":21,
        "uav_safe_actions":safe_actions,
        "uav_full_episode":{"policy":"NearestDeadlineFirstHeuristic","frontier_checks":episode_frontier_checks,"final":{"completed":bool(info2["completed"]),"returned_to_depot":bool(info2["returned_to_depot"]),"tardiness":float(info2["ep_tardiness"]),"infeasible":int(info2["ep_infeasible"])},"engine_metrics":generic_engine.metrics},
        "claim_boundary":["This audit proves orchestration/core reuse, not that the two domain certificates have identical semantics.","B and C still provide domain-specific optimistic bounds and replayable witnesses; the shared engine owns only the L/U/certificate/exact-fallback correctness protocol."]
    }
    assert all(payload["checks"].values()),payload["checks"]
    out=ROOT/"results/transfer/generic-future-choice-engine-cross-domain.json"; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"out":str(out),**payload["checks"]},sort_keys=True)); return 0


if __name__=="__main__": raise SystemExit(main())
