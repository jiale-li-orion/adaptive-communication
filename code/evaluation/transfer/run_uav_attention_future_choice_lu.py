#!/usr/bin/env python3
"""L/U + exact-fallback future-choice shield for the public UAV mission.

This is the first C-line step from an evaluator-only exact shield toward the
Layer-2 method contract.

For every native-feasible action, the post-action continuation is classified:

* U=0: a sound optimistic necessary condition already proves impossibility;
* L=1: a bounded constructive search finds a replayable zero-tardiness route;
* unresolved: exact continuation search is used as the correctness fallback.

Successful continuation routes are carried across execution.  If the external
heuristic follows the first action of a carried route, its suffix remains a
valid L=1 certificate and no new exact search is required for that action.

The resulting mask is required to match the evaluator-only exact continuation
mask at every reached decision boundary.  Search-work metrics are kept
separate from task-quality metrics; wall time on this tiny N=5 environment is
not a method claim.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import argparse
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import types
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
EXT = ROOT / "local_research/external/uav-attention-routing"
N_SETTINGS={
    5:(15,3,12),
    10:(30,5,25),
    15:(50,8,40),
    20:(65,10,55),
    25:(80,12,65),
}


def _install_gymnasium_shim() -> None:
    class Env: pass
    class _Space:
        def __init__(self, *args, **kwargs): self.args=args; self.kwargs=kwargs
    class Box(_Space): pass
    class Dict(_Space): pass
    class MultiBinary(_Space): pass
    class Discrete(_Space):
        def __init__(self,n,*args,**kwargs): super().__init__(n,*args,**kwargs); self.n=n
    spaces=types.SimpleNamespace(Box=Box,Dict=Dict,MultiBinary=MultiBinary,Discrete=Discrete)
    gym=types.ModuleType("gymnasium"); gym.Env=Env; gym.spaces=spaces
    sys.modules.setdefault("gymnasium",gym); sys.modules.setdefault("gymnasium.spaces",spaces)


def _git_head(path: Path) -> str | None:
    try:
        return subprocess.check_output(["git","-C",str(path),"rev-parse","HEAD"],text=True).strip()
    except Exception:
        return None


@dataclass(frozen=True)
class RouteState:
    current: int
    visited: int
    battery_q: float
    elapsed_q: float


class FutureChoiceRouteFrontier:
    def __init__(self, env, *, lower_search_limit: int = 24):
        self.cfg=env.config
        self.pos=env.node_positions.copy()
        self.deadlines={nid:float(node.deadline) for nid,node in env.service_nodes.items()}
        self.chargers=tuple(sorted(env.charger_nodes))
        self.n=int(self.cfg.num_customers)
        self.all_mask=(1<<self.n)-1
        self.lower_search_limit=int(lower_search_limit)
        self.metrics={
            "frontier_calls":0,
            "actions_checked":0,
            "upper_impossible":0,
            "lower_certificate":0,
            "carried_certificate":0,
            "exact_fallback_calls":0,
            "exact_fallback_new_states":0,
            "lower_search_expanded":0,
            "frontier_mismatch":0,
        }
        self.carried_route: tuple[int,...] | None=None
        self._certificates: dict[tuple[RouteState,int],tuple[int,...]]={}

    @staticmethod
    def q(x:float)->float: return round(float(x),7)

    def state(self,env)->RouteState:
        visited=0
        for i,v in enumerate(env.visited_mask):
            if int(v): visited|=1<<i
        return RouteState(int(env.current_node),visited,self.q(env.battery),self.q(env.elapsed_time))

    def dist(self,a:int,b:int)->float:
        import numpy as np
        return float(np.linalg.norm(self.pos[a]-self.pos[b]))

    def travel(self,a:int,b:int)->tuple[float,float]:
        d=self.dist(a,b)
        return d*self.cfg.battery_per_meter,d/self.cfg.drone_speed

    def post(self,state:RouteState,action:int)->RouteState|None:
        if action==state.current: return None
        e,t=self.travel(state.current,action)
        battery=float(state.battery_q); elapsed=float(state.elapsed_q)
        if e>battery+1e-9 or elapsed+t>self.cfg.mission_time+1e-9 or t<=0: return None
        nb=battery-e; nt=elapsed+t; nv=state.visited
        if 1<=action<=self.n:
            bit=1<<(action-1)
            if nv&bit: return None
            if nt>self.deadlines[action]+1e-9: return None
            nv|=bit
        elif action in self.chargers:
            nt+=self.cfg.charger_time_cost
            if nt>self.cfg.mission_time+1e-9: return None
            nb=min(self.cfg.battery_capacity,nb+self.cfg.recharge_rate)
        elif action==0:
            if nv!=self.all_mask: return None
        else: return None
        return RouteState(action,nv,self.q(nb),self.q(nt))

    def _mst_lower_bound_distance(self,state:RouteState)->float:
        """Euclidean MST over current + unvisited + depot: sound route lower bound."""
        nodes=[state.current,0]+[1+i for i in range(self.n) if not(state.visited&(1<<i))]
        # unique while retaining deterministic order
        nodes=list(dict.fromkeys(nodes))
        if len(nodes)<=1: return 0.0
        seen={nodes[0]}; total=0.0
        while len(seen)<len(nodes):
            best=None
            for a in seen:
                for b in nodes:
                    if b in seen: continue
                    d=self.dist(a,b)
                    if best is None or (d,b,a)<best: best=(d,b,a)
            assert best is not None
            total+=best[0]; seen.add(best[1])
        return total

    def upper_possible(self,state:RouteState)->bool:
        """Sound necessary conditions only; False is a valid impossibility proof."""
        elapsed=float(state.elapsed_q)
        # Every unvisited customer must at least be directly reachable by its
        # deadline; any route through other nodes is no shorter than direct.
        for i in range(self.n):
            if state.visited&(1<<i): continue
            nid=1+i
            _e,t=self.travel(state.current,nid)
            if elapsed+t>self.deadlines[nid]+1e-9:
                return False
        # Any complete route must contain a connected spanning structure over
        # current, all unvisited customers and depot. MST travel time is a lower
        # bound even if chargers are optionally visited.
        remaining=self.cfg.mission_time-elapsed
        if self._mst_lower_bound_distance(state)/self.cfg.drone_speed>remaining+1e-9:
            return False
        return True

    def _candidate_actions(self,state:RouteState)->list[int]:
        customers=[1+i for i in range(self.n) if not(state.visited&(1<<i))]
        customers.sort(key=lambda nid:(self.deadlines[nid],self.dist(state.current,nid),nid))
        chargers=[c for c in self.chargers if c!=state.current]
        if state.visited==self.all_mask: return [0]
        return customers+chargers

    def bounded_lower_certificate(self,state:RouteState)->tuple[int,...]|None:
        """Constructive L=1 search. Failure/limit is UNKNOWN, never U=0."""
        key=(state,self.lower_search_limit)
        if key in self._certificates: return self._certificates[key]
        expanded=0
        seen:set[RouteState]=set()
        def dfs(s:RouteState)->tuple[int,...]|None:
            nonlocal expanded
            if s.visited==self.all_mask:
                if s.current==0:
                    return ()
                end=self.post(s,0)
                return (0,) if end is not None else None
            if not self.upper_possible(s): return None
            if expanded>=self.lower_search_limit: return None
            if s in seen: return None
            seen.add(s); expanded+=1
            for action in self._candidate_actions(s):
                child=self.post(s,action)
                if child is None: continue
                sub=dfs(child)
                if sub is not None: return (action,*sub)
            return None
        route=dfs(state)
        self.metrics["lower_search_expanded"]+=expanded
        if route is not None:
            self._certificates[key]=route
        return route

    @lru_cache(maxsize=None)
    def exact(self,state:RouteState)->tuple[int,...]|None:
        if state.visited==self.all_mask:
            if state.current==0:
                return ()
            end=self.post(state,0)
            return (0,) if end is not None else None
        if not self.upper_possible(state): return None
        for action in self._candidate_actions(state):
            child=self.post(state,action)
            if child is None: continue
            sub=self.exact(child)
            if sub is not None: return (action,*sub)
        return None

    def exact_with_delta(self,state:RouteState)->tuple[tuple[int,...]|None,int]:
        before=self.exact.cache_info().currsize
        route=self.exact(state)
        after=self.exact.cache_info().currsize
        return route,after-before

    def classify_child(self,child:RouteState,action:int)->tuple[bool,str,tuple[int,...]|None]:
        self.metrics["actions_checked"]+=1
        if not self.upper_possible(child):
            self.metrics["upper_impossible"]+=1
            return False,"U0",None

        # Carried suffix is the cheapest replayable certificate.
        if self.carried_route and self.carried_route[0]==action:
            route=self.carried_route[1:]
            self.metrics["carried_certificate"]+=1
            return True,"L1-carried",route

        route=self.bounded_lower_certificate(child)
        if route is not None:
            self.metrics["lower_certificate"]+=1
            return True,"L1-constructive",route

        self.metrics["exact_fallback_calls"]+=1
        route,new=self.exact_with_delta(child)
        self.metrics["exact_fallback_new_states"]+=new
        return route is not None,"exact-fallback",route

    def mask(self,env,native_mask):
        import numpy as np
        self.metrics["frontier_calls"]+=1
        state=self.state(env)
        out=np.zeros_like(native_mask,dtype=bool)
        routes:dict[int,tuple[int,...]]={}
        sources:dict[int,str]={}
        for action,native_ok in enumerate(native_mask):
            if not bool(native_ok): continue
            child=self.post(state,int(action))
            if child is None: continue
            ok,source,route=self.classify_child(child,int(action))
            if ok:
                out[action]=True
                routes[int(action)]=(int(action),*(route or ()))
            sources[int(action)]=source
        return out,routes,sources

    def commit(self,action:int,routes:dict[int,tuple[int,...]])->None:
        route=routes.get(int(action))
        # ``routes[action]`` includes the action about to be executed.  After
        # env.step(action), the persistent certificate for the *next* boundary
        # is its suffix only.
        self.carried_route=None if route is None else tuple(route[1:])


def summary(rows:list[dict[str,Any]])->dict[str,Any]:
    def mean(k): return float(statistics.fmean(float(r[k]) for r in rows))
    return {
        "episodes":len(rows),
        "hard_feasible_start_rate":mean("hard_feasible_start"),
        "zero_tardiness_rate":mean("zero_tardiness"),
        "completed_rate":mean("completed"),
        "mean_tardiness":mean("tardiness"),
        "mean_infeasible":mean("infeasible"),
        "mean_energy":mean("energy"),
        "mean_interventions":mean("interventions"),
        "mean_upper_impossible":mean("upper_impossible"),
        "mean_lower_certificate":mean("lower_certificate"),
        "mean_carried_certificate":mean("carried_certificate"),
        "mean_exact_fallback_calls":mean("exact_fallback_calls"),
        "mean_exact_fallback_new_states":mean("exact_fallback_new_states"),
        "mean_lower_search_expanded":mean("lower_search_expanded"),
    }


def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--seeds",type=int,default=200); ap.add_argument("--seed-list",default=None); ap.add_argument("--customers",type=int,default=5,choices=sorted(N_SETTINGS)); ap.add_argument("--lower-search-limit",type=int,default=24)
    ap.add_argument("--out",type=Path,default=ROOT/"results/transfer/uav-attention-future-choice-lu-n5-200.json"); args=ap.parse_args()
    os.environ.setdefault("OPENBLAS_NUM_THREADS","1"); os.environ.setdefault("OMP_NUM_THREADS","1"); os.environ.setdefault("MKL_NUM_THREADS","1")
    _install_gymnasium_shim(); sys.path.insert(0,str(EXT))
    from src.env import SingleUAVConfig,SingleUAVEnv  # type: ignore
    from src.heuristic import BatteryAwareNearestNeighbour,GreedyDeadlineBatteryHeuristic,NearestDeadlineFirstHeuristic,NearestNeighbourHeuristic  # type: ignore

    heuristics={"nearest_neighbour":NearestNeighbourHeuristic,"nearest_deadline":NearestDeadlineFirstHeuristic,"greedy_deadline_battery":GreedyDeadlineBatteryHeuristic,"battery_aware_nn":BatteryAwareNearestNeighbour}
    mission_time,deadline_min,deadline_max=N_SETTINGS[args.customers]
    def cfg(): return SingleUAVConfig(num_customers=args.customers,num_chargers=1,mission_time=mission_time,deadline_min=deadline_min,deadline_max=deadline_max,reward_mode="completion_ratio")
    seed_values=[int(x) for x in args.seed_list.split(",") if x.strip()] if args.seed_list else list(range(args.seeds))
    rows=[]; frontier_match_checks=0
    for seed in seed_values:
        probe=SingleUAVEnv(cfg()); probe.reset(seed=seed); pfront=FutureChoiceRouteFrontier(probe,lower_search_limit=args.lower_search_limit)
        start=pfront.state(probe); start_route,_=pfront.exact_with_delta(start); hard=start_route is not None
        for pname,pcls in heuristics.items():
            env=SingleUAVEnv(cfg()); obs,info=env.reset(seed=seed); policy=pcls(); front=FutureChoiceRouteFrontier(env,lower_search_limit=args.lower_search_limit)
            audit=FutureChoiceRouteFrontier(env,lower_search_limit=args.lower_search_limit)
            interventions=0; total_return=0.0
            audit_exact_new_states=0
            while True:
                native=env.get_action_mask(); native_action=int(policy.act(env,obs,info))
                if hard:
                    lu_mask,routes,_sources=front.mask(env,native)
                    # Correctness audit against exact mask at every reached boundary.
                    state=audit.state(env); exact_mask=[]
                    for action,ok in enumerate(native):
                        if not bool(ok): exact_mask.append(False); continue
                        child=audit.post(state,int(action))
                        if child is None:
                            exact_mask.append(False)
                            continue
                        route,new=audit.exact_with_delta(child)
                        audit_exact_new_states+=new
                        exact_mask.append(route is not None)
                    frontier_match_checks+=1
                    if list(map(bool,lu_mask))!=exact_mask:
                        front.metrics["frontier_mismatch"]+=1
                        raise AssertionError({"seed":seed,"policy":pname,"lu":list(map(bool,lu_mask)),"exact":exact_mask})
                    if lu_mask.any():
                        use_info=dict(info); use_info["action_mask"]=lu_mask; action=int(policy.act(env,obs,use_info)); interventions+=int(action!=native_action); front.commit(action,routes)
                    else: action=native_action
                else: action=native_action
                obs,reward,terminated,truncated,info=env.step(action); total_return+=float(reward)
                if terminated or truncated: break
            rows.append({"seed":seed,"policy":pname,"hard_feasible_start":int(hard),"completed":int(bool(info["completed"])),"zero_tardiness":int(float(info["ep_tardiness"])<=1e-9),"tardiness":float(info["ep_tardiness"]),"infeasible":int(info["ep_infeasible"]),"energy":float(info["ep_energy"]),"native_return":total_return,"interventions":interventions,"exact_mask_new_states":audit_exact_new_states,**front.metrics})

    summaries={}; paired={}
    for pname in heuristics:
        subset=[r for r in rows if r["policy"]==pname]; summaries[pname]=summary(subset)
        hardrows=[r for r in subset if r["hard_feasible_start"]]
        paired[pname]={
            "hard_feasible_seed_count":len(hardrows),
            "zero_tardiness":sum(r["zero_tardiness"] for r in hardrows),
            "completed":sum(r["completed"] for r in hardrows),
            "infeasible":sum(r["infeasible"]>0 for r in hardrows),
            "exact_fallback_calls":sum(r["exact_fallback_calls"] for r in hardrows),
            "exact_fallback_new_states":sum(r["exact_fallback_new_states"] for r in hardrows),
            "exact_mask_new_states":sum(r["exact_mask_new_states"] for r in hardrows),
            "lower_certificate":sum(r["lower_certificate"] for r in hardrows),
            "carried_certificate":sum(r["carried_certificate"] for r in hardrows),
            "upper_impossible":sum(r["upper_impossible"] for r in hardrows),
            "lower_search_expanded":sum(r["lower_search_expanded"] for r in hardrows),
        }
    payload={"stage":"UAV_ATTENTION_FUTURE_CHOICE_LU","external_repo":"mdehghani86/uav-attention-routing","external_commit":_git_head(EXT),"setting":{"num_customers":args.customers,"mission_time":mission_time,"deadline_min":deadline_min,"deadline_max":deadline_max,"seed_values":seed_values,"lower_search_limit":args.lower_search_limit},"correctness":{"reached_frontier_match_checks":frontier_match_checks,"frontier_mismatch":sum(r["frontier_mismatch"] for r in rows)},"summaries":summaries,"paired_hard_feasible":paired,"rows":rows,"claim_boundary":["L=1 is always a replayable complete route; U=0 uses only sound optimistic necessary conditions; unresolved actions fall back to exact continuation.","The reached L/U action mask is checked against exact continuation at every hard-feasible decision boundary.","This transfer measures search-work decomposition; wall-time superiority is not inferred from state/expansion counts.","The route certificate object is domain-specific transfer code; integration with the frozen generic Layer-2 conditional frontier remains separate work."]}
    assert payload["correctness"]["frontier_mismatch"]==0
    args.out.parent.mkdir(parents=True,exist_ok=True); args.out.write_text(json.dumps(payload,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"out":str(args.out),"correctness":payload["correctness"],"paired_hard_feasible":paired},sort_keys=True)); return 0


if __name__=="__main__": raise SystemExit(main())
