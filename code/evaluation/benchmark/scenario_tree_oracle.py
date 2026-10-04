#!/usr/bin/env python3
"""Exact non-anticipative solver for small Layer-1 alias bundles."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Mapping


@dataclass(frozen=True)
class Obligation:
    oid: str
    release_s: int
    deadline_s: int


@dataclass(frozen=True)
class World:
    world_id: str
    mode: str
    terrestrial_slots: tuple[int, ...]
    query_value: str
    passive_evidence_at_s: int | None = None
    passive_value: str | None = None


@dataclass(frozen=True)
class LocalState:
    delivered: tuple[str, ...]
    sat_budget: int
    queried: bool


@dataclass(frozen=True)
class Bundle:
    bundle_id: str
    decision_times: tuple[int, ...]
    obligations: tuple[Obligation, ...]
    satellite_slots: tuple[int, ...]
    worlds: tuple[World, ...]
    satellite_budget: int
    query_legal: bool
    query_delay_s: int
    initial_public_observation: tuple[tuple[str, str], ...]


def _pending(bundle: Bundle, state: LocalState, t: int) -> list[Obligation]:
    done=set(state.delivered)
    return [o for o in bundle.obligations if o.oid not in done and o.release_s <= t]


def _expired(bundle: Bundle, state: LocalState, t: int) -> bool:
    done=set(state.delivered)
    return any(o.oid not in done and o.deadline_s < t for o in bundle.obligations)


def _success(bundle: Bundle, state: LocalState) -> bool:
    return len(state.delivered)==len(bundle.obligations)


def _next_time(bundle: Bundle, t: int) -> int | None:
    for x in bundle.decision_times:
        if x>t:
            return x
    return None


def _initial_states(bundle: Bundle) -> tuple[tuple[str, LocalState], ...]:
    s=LocalState(delivered=(), sat_budget=bundle.satellite_budget, queried=False)
    return tuple((w.world_id,s) for w in bundle.worlds)


def _world_map(bundle: Bundle) -> dict[str,World]:
    return {w.world_id:w for w in bundle.worlds}


def _canonical_node(states: Mapping[str,LocalState]) -> tuple[tuple[str,LocalState],...]:
    return tuple(sorted(states.items()))


def _available_actions(bundle: Bundle, t: int, states: Mapping[str,LocalState], allow_query: bool) -> list[tuple[str,str|None]]:
    actions:[tuple[str,str|None]]
    actions=[("WAIT",None)]
    vals=list(states.values())
    common_pending=None
    for st in vals:
        ids={o.oid for o in _pending(bundle,st,t)}
        common_pending=ids if common_pending is None else common_pending & ids
    common_pending=common_pending or set()
    if t in bundle.satellite_slots and vals and all(st.sat_budget>0 for st in vals):
        actions.extend(("SEND_SAT",oid) for oid in sorted(common_pending))
    actions.extend(("SEND_TERR",oid) for oid in sorted(common_pending))
    if allow_query and bundle.query_legal and vals and all(not st.queried for st in vals):
        actions.append(("QUERY",None))
    return actions


def solve(bundle: Bundle, *, allow_query: bool=True, forced_first_action: tuple[str,str|None] | None=None) -> dict[str,Any]:
    worlds=_world_map(bundle)
    start=bundle.decision_times[0]
    memo={}

    def rec(t:int, node:tuple[tuple[str,LocalState],...]) -> tuple[bool,dict[str,Any]|None]:
        key=(t,node,allow_query)
        if key in memo:
            return memo[key]
        states=dict(node)
        if any(_expired(bundle,st,t) for st in states.values()):
            memo[key]=(False,None); return memo[key]
        if all(_success(bundle,st) for st in states.values()):
            memo[key]=(True,{"terminal":True}); return memo[key]

        actions=_available_actions(bundle,t,states,allow_query)
        if forced_first_action is not None and t==start and node==_initial_states(bundle):
            actions=[x for x in actions if x==forced_first_action]
        for action,arg in actions:
            branches:dict[str,dict[str,LocalState]]={}
            next_t=t
            if action=="WAIT":
                nt=_next_time(bundle,t)
                if nt is None:
                    continue
                next_t=nt
                # Passive evidence, if any, partitions worlds at arrival time.
                for wid,st in states.items():
                    w=worlds[wid]
                    obs="same"
                    if w.passive_evidence_at_s is not None and t < w.passive_evidence_at_s <= nt:
                        obs=f"passive:{w.passive_value}"
                    branches.setdefault(obs,{})[wid]=st
            elif action=="QUERY":
                next_t=t+bundle.query_delay_s
                for wid,st in states.items():
                    w=worlds[wid]
                    ns=LocalState(st.delivered,st.sat_budget,True)
                    branches.setdefault(f"query:{w.query_value}",{})[wid]=ns
            elif action=="SEND_SAT":
                next_t=t
                for wid,st in states.items():
                    ns=LocalState(tuple(sorted(set(st.delivered)|{str(arg)})),st.sat_budget-1,st.queried)
                    branches.setdefault("ack:sat:ok",{})[wid]=ns
            elif action=="SEND_TERR":
                next_t=t
                for wid,st in states.items():
                    w=worlds[wid]
                    ok=t in w.terrestrial_slots
                    delivered=set(st.delivered)
                    if ok:
                        delivered.add(str(arg))
                    ns=LocalState(tuple(sorted(delivered)),st.sat_budget,st.queried)
                    branches.setdefault(f"ack:terr:{'ok' if ok else 'fail'}",{})[wid]=ns
            else:
                continue

            # Prevent zero-time loops after send/attempt by advancing to next decision time.
            if action in {"SEND_SAT","SEND_TERR"}:
                nt=_next_time(bundle,t)
                if nt is None and not all(_success(bundle,s) for b in branches.values() for s in b.values()):
                    continue
                next_t=nt if nt is not None else t

            children=[]
            ok=True
            for obs,child_states in sorted(branches.items()):
                child_node=_canonical_node(child_states)
                solved,sub=rec(next_t,child_node)
                if not solved:
                    ok=False; break
                children.append({"observation":obs,"worlds":sorted(child_states),"subpolicy":sub})
            if ok:
                policy={"time_s":t,"action":action,"arg":arg,"children":children}
                memo[key]=(True,policy); return memo[key]
        memo[key]=(False,None); return memo[key]

    solvable,policy=rec(start,_initial_states(bundle))
    return {"solvable":solvable,"policy":policy,"memo_nodes":len(memo)}


def hindsight(bundle: Bundle) -> dict[str,bool]:
    out={}
    for world in bundle.worlds:
        single=Bundle(
            bundle_id=bundle.bundle_id+"::"+world.world_id,
            decision_times=bundle.decision_times,
            obligations=bundle.obligations,
            satellite_slots=bundle.satellite_slots,
            worlds=(world,),
            satellite_budget=bundle.satellite_budget,
            query_legal=False,
            query_delay_s=bundle.query_delay_s,
            initial_public_observation=bundle.initial_public_observation,
        )
        out[world.world_id]=solve(single,allow_query=False)["solvable"]
    return out


def winning_first_actions_single_world(bundle: Bundle, world_id: str) -> set[str]:
    world=next(w for w in bundle.worlds if w.world_id==world_id)
    single=Bundle(
        bundle_id=bundle.bundle_id+"::"+world_id,
        decision_times=bundle.decision_times,
        obligations=bundle.obligations,
        satellite_slots=bundle.satellite_slots,
        worlds=(world,),
        satellite_budget=bundle.satellite_budget,
        query_legal=False,
        query_delay_s=bundle.query_delay_s,
        initial_public_observation=bundle.initial_public_observation,
    )
    t=single.decision_times[0]
    states=dict(_initial_states(single))
    wins=set()
    # Direct commitments only; query excluded by construction.
    for action,arg in _available_actions(single,t,states,False):
        if action=="QUERY":
            continue
        # Force first action by constructing a tiny wrapper through one-step simulation.
        # Reuse public solver logic with action-specific transformed bundle/state via local simulation.
        if action=="WAIT":
            nt=_next_time(single,t)
            if nt is not None:
                reduced=Bundle(single.bundle_id,single.decision_times[single.decision_times.index(nt):],single.obligations,single.satellite_slots,single.worlds,single.satellite_budget,False,single.query_delay_s,single.initial_public_observation)
                if solve(reduced,allow_query=False)["solvable"]:
                    wins.add("WAIT")
        elif action=="SEND_SAT" and arg:
            # Conservative first-action witness: success iff report can be sent now and remainder solvable.
            o=next(x for x in single.obligations if x.oid==arg)
            if t in single.satellite_slots and o.release_s<=t<=o.deadline_s and single.satellite_budget>0:
                remaining=tuple(x for x in single.obligations if x.oid!=arg)
                if not remaining:
                    wins.add(f"SEND_SAT:{arg}")
                else:
                    reduced=Bundle(single.bundle_id,single.decision_times[1:],remaining,single.satellite_slots,single.worlds,single.satellite_budget-1,False,single.query_delay_s,single.initial_public_observation)
                    if reduced.decision_times and solve(reduced,allow_query=False)["solvable"]:
                        wins.add(f"SEND_SAT:{arg}")
    return wins
