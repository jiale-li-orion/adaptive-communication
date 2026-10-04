#!/usr/bin/env python3
"""True receding-horizon baseline for the v0.5 dynamic process.

At every legal history the planner performs k-decision robust lookahead, executes
only the first action, consumes the real observation/event stream, then replans
with a fresh k-step horizon.  This is deliberately different from truncating the
whole episode after k actions.
"""
from __future__ import annotations
from math import inf
from typing import Any

from dynamic_scenario_tree_v0_5 import (
    Bundle,LocalState,_actions,_expired,_normalize,_step_action,_success,
)
from frontier_guided_planner_v0_5 import frontier_prefix_upper_bound


def _state_key(st:LocalState):
    return (st.final_delivered,st.violated_obligations,st.gateway_received,st.pending_queries,st.pending_deliveries,st.seen_passive,st.next_request_seq,st.sat_budget)


def _canon(states:dict[str,LocalState]):
    return tuple(sorted((wid,_state_key(st)) for wid,st in states.items()))


def _leaf_score(bundle:Bundle,t:int,states:dict[str,LocalState]) -> float:
    if any(_expired(bundle,st,t) for st in states.values()): return -inf
    if not frontier_prefix_upper_bound(bundle,t,states): return -inf
    vals=[]
    total=len(bundle.obligations)
    for st in states.values():
        delivered=len(st.final_delivered)
        ontime_pending=0
        for d in st.pending_deliveries:
            if not d.accepted or d.final_ack_at_s is None: continue
            deadline=next(o.deadline_s for o in bundle.obligations if o.oid==d.oid)
            if t<d.final_ack_at_s<=deadline: ontime_pending+=1
        query_penalty=len(st.pending_queries)
        # Generic terminal heuristic: reward secured completion and retained backup,
        # penalize unresolved work and outstanding diagnostic requests.
        vals.append(100.0*delivered + 40.0*ontime_pending + 2.0*st.sat_budget - 8.0*(total-delivered-ontime_pending) - 3.0*query_penalty)
    # Robust planning uses the worst compatible world, not an expected score.
    return min(vals) - 0.25*(len(states)-1)


def _lookahead_value(bundle:Bundle,t:int,states:dict[str,LocalState],depth:int,disabled_queries:frozenset[str],memo:dict[Any,float]) -> float:
    norm=_normalize(bundle,t,states)
    if len(norm)>1 or next(iter(norm))!='same':
        return min(_lookahead_value(bundle,t,ch,depth,disabled_queries,memo) for ch in norm.values())
    states=next(iter(norm.values()))
    if any(_expired(bundle,st,t) for st in states.values()): return -inf
    if all(_success(bundle,st) for st in states.values()): return 1e9
    if depth<=0:return _leaf_score(bundle,t,states)
    key=(t,depth,_canon(states),disabled_queries)
    if key in memo:return memo[key]
    best=-inf
    actions=[a for a in _actions(bundle,t,states) if not (a[0]=='ISSUE_QUERY' and a[1] in disabled_queries)]
    for action in actions:
        stepped=_step_action(bundle,t,states,action)
        if stepped is None:continue
        branches,next_t=stepped
        branch_values=[]
        for ch in branches.values():
            branch_values.append(_lookahead_value(bundle,next_t,ch,depth-1,disabled_queries,memo))
        if branch_values:
            best=max(best,min(branch_values))
    memo[key]=best
    return best


def _choose_action(bundle:Bundle,t:int,states:dict[str,LocalState],horizon_decisions:int,disabled_queries:frozenset[str]) -> tuple[str,str|None] | None:
    actions=[a for a in _actions(bundle,t,states) if not (a[0]=='ISSUE_QUERY' and a[1] in disabled_queries)]
    scored=[]
    for action in actions:
        stepped=_step_action(bundle,t,states,action)
        if stepped is None:continue
        branches,next_t=stepped
        memo={};vals=[]
        for ch in branches.values():
            vals.append(_lookahead_value(bundle,next_t,ch,horizon_decisions-1,disabled_queries,memo))
        if vals:
            # Stable tie break prefers task progress over extra diagnosis, then wait.
            pref={'SEND_TERR':0,'SEND_SAT':1,'ISSUE_QUERY':2,'WAIT':3}.get(action[0],4)
            scored.append((min(vals),-pref,action))
    if not scored:return None
    scored.sort(key=lambda x:(x[0],x[1],repr(x[2])),reverse=True)
    return scored[0][2]


def solve_receding_horizon(bundle:Bundle,*,horizon_decisions:int=2,disabled_queries:frozenset[str]=frozenset(),max_path_replans:int|None=None) -> dict[str,Any]:
    if horizon_decisions<1:raise ValueError('horizon_decisions must be >=1')
    start=min(bundle.fixed_event_times)
    initial={w.world_id:LocalState(sat_budget=bundle.satellite_budget) for w in bundle.worlds}
    cap=max_path_replans or max(24,6*len(bundle.obligations)+3*len(bundle.fixed_event_times))
    total_replans=0

    def rec(t:int,states:dict[str,LocalState],seen_path:frozenset[Any],path_replans:int):
        nonlocal total_replans
        norm=_normalize(bundle,t,states)
        if len(norm)>1 or next(iter(norm))!='same':
            children=[]
            for obs,ch in sorted(norm.items()):
                ok,sub=rec(t,ch,seen_path,path_replans)
                if not ok:return False,None
                children.append({'observation':obs,'worlds':sorted(ch),'subpolicy':sub})
            return True,{'time_s':t,'event':'OBSERVATION','children':children}
        states=next(iter(norm.values()))
        if any(_expired(bundle,st,t) for st in states.values()):return False,None
        if all(_success(bundle,st) for st in states.values()):return True,{'terminal':True}
        key=(t,_canon(states))
        if key in seen_path or path_replans>=cap:return False,None
        total_replans+=1
        action=_choose_action(bundle,t,states,horizon_decisions,disabled_queries)
        if action is None:return False,None
        stepped=_step_action(bundle,t,states,action)
        if stepped is None:return False,None
        branches,next_t=stepped
        children=[]
        next_seen=seen_path|{key}
        for obs,ch in sorted(branches.items()):
            ok,sub=rec(next_t,ch,next_seen,path_replans+1)
            if not ok:return False,None
            children.append({'observation':obs,'worlds':sorted(ch),'subpolicy':sub})
        return True,{'time_s':t,'action':action[0],'arg':action[1],'children':children}

    solvable,policy=rec(start,initial,frozenset(),0)
    return {'solvable':solvable,'policy':policy,'replans':total_replans,'horizon_decisions':horizon_decisions,'max_path_replans':cap}
