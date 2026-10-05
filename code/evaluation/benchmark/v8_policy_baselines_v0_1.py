#!/usr/bin/env python3
"""Placement-preserving V8 policy baselines for compositional Layer-1 bundles.

These policies operate on the same observation history and action set as the
evaluated policy.  They deliberately do not read gateway-local hidden/current
state for free; gateway-local autonomy remains a separate deployment baseline.
"""
from __future__ import annotations

from math import inf
from typing import Any, Callable, Mapping

from causal_evidence_process_v0_1 import (
    ACK_TIMEOUT_S,
    FINAL_ACK_DELAY_S,
    GATEWAY_RECEIPT_DELAY_S,
    QUERY_RESPONSE_DELAY_S,
    SATELLITE_COMPLETION_DELAY_S,
    attach_causal_evidence,
    gateway_snapshot,
)
from exact_reference_oracle_v0_1 import (
    LocalState,
    PendingDelivery,
    PendingQuery,
    _active_common_obligations,
    _attempt_lattice,
    _expired,
    _matching_satellite_window,
    _matching_terrestrial_window,
    _maxflow,
    _next_time,
    _normalize,
    _process_map,
    _success,
    _with_sat_used,
    _with_used,
    _world_map,
    jsonable,
)


Action = tuple[str, str | None]


def _canon(states: Mapping[str, LocalState]) -> tuple[tuple[str, LocalState], ...]:
    return tuple(sorted(states.items()))


def _query_signature(process_world: Mapping[str, Any], reachable: bool, at_s: int) -> str:
    if not reachable:
        return "query:gateway_state_summary=__TIMEOUT__"
    return "query:gateway_state_summary=" + jsonable(gateway_snapshot(process_world, at_s))


def _query_can_change_history(bundle, process, states, at_s: int) -> bool:
    wm = _world_map(bundle); pm = _process_map(process)
    return any(
        _query_signature(pm[wid], _matching_terrestrial_window(wm[wid], st, at_s) is not None, at_s)
        != st.last_query_signature
        for wid, st in states.items()
    )


def _legal_actions(bundle, process, states, at_s: int) -> list[Action]:
    wm = _world_map(bundle)
    active = _active_common_obligations(bundle, states, at_s)
    actions: list[Action] = []
    if any(_matching_terrestrial_window(wm[wid], st, at_s) is not None for wid, st in states.items()):
        actions.extend(("SEND_TERR", oid) for oid in active)
    if all(
        st.satellite_budget > 0 and _matching_satellite_window(bundle, st, at_s) is not None
        for st in states.values()
    ):
        actions.extend(("SEND_SAT", oid) for oid in active)
    if (
        process["query_capabilities"]
        and all(st.pending_query is None for st in states.values())
        and _query_can_change_history(bundle, process, states, at_s)
    ):
        actions.append(("ISSUE_QUERY", "gateway_state_summary"))
    actions.append(("WAIT", None))
    return actions


def _step(bundle, process, states: Mapping[str, LocalState], at_s: int, action: Action):
    wm = _world_map(bundle); pm = _process_map(process); lattice = _attempt_lattice(bundle)
    kind, arg = action
    child: dict[str, LocalState] = {}
    next_t = at_s
    if kind == "WAIT":
        nt = _next_time(lattice, at_s, states)
        return None if nt is None else (dict(states), nt)
    if kind == "ISSUE_QUERY":
        for wid, st in states.items():
            window = _matching_terrestrial_window(wm[wid], st, at_s)
            reachable = window is not None
            used = _with_used(st, str(window["window_id"])) if window is not None else st.terrestrial_used
            sig = _query_signature(pm[wid], reachable, at_s)
            child[wid] = LocalState(
                delivered=st.delivered,
                terrestrial_used=used,
                satellite_used=st.satellite_used,
                satellite_budget=st.satellite_budget,
                pending_query=PendingQuery(at_s + QUERY_RESPONSE_DELAY_S, sig + f":sampled@{at_s}"),
                last_query_signature=sig,
                last_direct_signature=st.last_direct_signature,
                pending_deliveries=st.pending_deliveries,
            )
        return child, at_s
    if kind == "SEND_TERR":
        oid = str(arg)
        for wid, st in states.items():
            window = _matching_terrestrial_window(wm[wid], st, at_s)
            accepted = window is not None
            used = _with_used(st, str(window["window_id"])) if window is not None else st.terrestrial_used
            pd = PendingDelivery(
                obligation_id=oid,
                accepted=accepted,
                gateway_receipt_at_s=at_s + GATEWAY_RECEIPT_DELAY_S if accepted else None,
                final_ack_at_s=at_s + FINAL_ACK_DELAY_S if accepted else None,
                negative_observation_at_s=None if accepted else at_s + ACK_TIMEOUT_S,
            )
            child[wid] = LocalState(
                delivered=st.delivered, terrestrial_used=used,
                satellite_used=st.satellite_used, satellite_budget=st.satellite_budget,
                pending_query=st.pending_query, last_query_signature=st.last_query_signature,
                last_direct_signature=st.last_direct_signature,
                pending_deliveries=st.pending_deliveries + (pd,),
            )
        return child, at_s
    if kind == "SEND_SAT":
        oid = str(arg)
        for wid, st in states.items():
            window = _matching_satellite_window(bundle, st, at_s)
            if window is None:
                return None
            pd = PendingDelivery(
                obligation_id=oid, accepted=True, gateway_receipt_at_s=None,
                final_ack_at_s=at_s + SATELLITE_COMPLETION_DELAY_S,
                negative_observation_at_s=None,
            )
            child[wid] = LocalState(
                delivered=st.delivered, terrestrial_used=st.terrestrial_used,
                satellite_used=_with_sat_used(st, str(window["window_id"])),
                satellite_budget=st.satellite_budget - 1,
                pending_query=st.pending_query, last_query_signature=st.last_query_signature,
                last_direct_signature=st.last_direct_signature,
                pending_deliveries=st.pending_deliveries + (pd,),
            )
        return child, at_s
    return None


def _normalize_one(bundle, process, at_s: int, states: Mapping[str, LocalState]):
    branches = _normalize(bundle, process, at_s, states)
    return branches


def _public_deadline_score(bundle, at_s: int, states: Mapping[str, LocalState]) -> float:
    if any(_expired(bundle, st, at_s) for st in states.values()):
        return -inf
    vals = []
    total = len(bundle["obligations"])
    for st in states.values():
        delivered = len(st.delivered)
        pending = len(st.pending_deliveries)
        unresolved = total - delivered - pending
        nearest_slack = min(
            [int(o["deadline_s"]) - at_s for o in bundle["obligations"] if str(o["obligation_id"]) not in st.delivered]
            or [10**9]
        )
        vals.append(1000 * delivered + 120 * pending + 8 * st.satellite_budget - 40 * unresolved + min(nearest_slack, 10_000) / 1000)
    return min(vals)


def _residual_flow_score(bundle, at_s: int, states: Mapping[str, LocalState]) -> float:
    """Generic robust terminal relaxation using per-world residual max-flow.

    This is intentionally a strong ordinary planning heuristic: it may inspect
    every compatible world's declared future support, but only through a
    worst-case feasibility relaxation; it never learns which world is real.
    """
    wm = _world_map(bundle)
    sat_windows = list(bundle["public_environment"]["satellite_windows"])
    world_scores = []
    for wid, st in states.items():
        if _expired(bundle, st, at_s):
            return -inf
        secured = set(st.delivered)
        for d in st.pending_deliveries:
            if not d.accepted or d.final_ack_at_s is None:
                continue
            deadline = next(
                int(o["deadline_s"])
                for o in bundle["obligations"]
                if str(o["obligation_id"]) == d.obligation_id
            )
            if d.final_ack_at_s <= deadline:
                secured.add(d.obligation_id)
        obligations = [o for o in bundle["obligations"] if str(o["obligation_id"]) not in secured]
        source="SRC"; sink="SNK"; sat_pool="SAT_POOL"; graph={}
        def add(u,v,cap):
            if cap>0:
                graph.setdefault(u,{})[v]=graph.setdefault(u,{}).get(v,0)+cap
                graph.setdefault(v,{}).setdefault(u,0)
        terr_used=dict(st.terrestrial_used); sat_used=dict(st.satellite_used)
        for o in obligations:
            oid=str(o["obligation_id"]); on=f"O::{oid}"; add(source,on,1)
            for w in wm[wid]["terrestrial_windows"]:
                cap=max(0,int(w["capacity_units"])-terr_used.get(str(w["window_id"]),0))
                if cap<=0: continue
                t=max(at_s,int(o["release_s"]),int(w["start_s"]))
                if t<int(w["end_s"]) and t+FINAL_ACK_DELAY_S<=int(o["deadline_s"]):
                    add(on,f"T::{w['window_id']}",1)
            for w in sat_windows:
                cap=max(0,int(w["capacity_units"])-sat_used.get(str(w["window_id"]),0))
                if cap<=0: continue
                t=max(at_s,int(o["release_s"]),int(w["start_s"]))
                if t<int(w["end_s"]) and t+SATELLITE_COMPLETION_DELAY_S<=int(o["deadline_s"]):
                    add(on,f"S::{w['window_id']}",1)
        for w in wm[wid]["terrestrial_windows"]:
            add(f"T::{w['window_id']}",sink,max(0,int(w["capacity_units"])-terr_used.get(str(w["window_id"]),0)))
        for w in sat_windows:
            add(f"S::{w['window_id']}",sat_pool,max(0,int(w["capacity_units"])-sat_used.get(str(w["window_id"]),0)))
        add(sat_pool,sink,max(0,st.satellite_budget))
        flow=_maxflow(graph,source,sink) if obligations else 0
        completable=len(secured)+flow
        world_scores.append(10_000*completable + 10*st.satellite_budget - len(obligations))
    return min(world_scores) if world_scores else -inf


def _lookahead(bundle, process, at_s: int, states: Mapping[str, LocalState], depth: int, memo, leaf="public") -> float:
    branches = _normalize_one(bundle, process, at_s, states)
    if len(branches) > 1 or next(iter(branches)) != "same":
        return min(_lookahead(bundle, process, at_s, ch, depth, memo, leaf) for ch in branches.values())
    states = next(iter(branches.values()))
    if any(_expired(bundle, st, at_s) for st in states.values()):
        return -inf
    if all(_success(bundle, st) for st in states.values()):
        return 1e12
    if depth <= 0:
        return _residual_flow_score(bundle, at_s, states) if leaf=="flow" else _public_deadline_score(bundle, at_s, states)
    key = (at_s, depth, leaf, _canon(states))
    if key in memo:
        return memo[key]
    best = -inf
    for action in _legal_actions(bundle, process, states, at_s):
        stepped = _step(bundle, process, states, at_s, action)
        if stepped is None:
            continue
        child, next_t = stepped
        next_branches = _normalize_one(bundle, process, next_t, child)
        val = min(_lookahead(bundle, process, next_t, ch, depth - 1, memo, leaf) for ch in next_branches.values())
        best = max(best, val)
    memo[key] = best
    return best


def _choose_depth_k(bundle, process, at_s: int, states: Mapping[str, LocalState], depth: int, *, leaf="public") -> Action | None:
    ranked = []
    pref = {"SEND_TERR": 0, "SEND_SAT": 1, "ISSUE_QUERY": 2, "WAIT": 3}
    for action in _legal_actions(bundle, process, states, at_s):
        stepped = _step(bundle, process, states, at_s, action)
        if stepped is None:
            continue
        child, next_t = stepped
        branches = _normalize_one(bundle, process, next_t, child)
        memo = {}
        val = min(_lookahead(bundle, process, next_t, ch, depth - 1, memo, leaf) for ch in branches.values())
        ranked.append((val, -pref.get(action[0], 9), repr(action), action))
    return max(ranked)[3] if ranked else None


def _choose_shallow(bundle, process, at_s: int, states: Mapping[str, LocalState]) -> Action | None:
    actions = _legal_actions(bundle, process, states, at_s)
    active = _active_common_obligations(bundle, states, at_s)
    if not actions:
        return None
    # Two-level legal-feature rule: query only when a paid query is available,
    # there is active work, and a public satellite opportunity arrives before
    # the earliest active deadline; otherwise try normal send, then reserve SAT.
    deadlines = {
        str(o["obligation_id"]): int(o["deadline_s"])
        for o in bundle["obligations"]
    }
    sat_now = any(a[0] == "SEND_SAT" for a in actions)
    terr = [a for a in actions if a[0] == "SEND_TERR"]
    query = next((a for a in actions if a[0] == "ISSUE_QUERY"), None)
    if query is not None and active:
        next_sat = min(
            [int(w["start_s"]) for w in bundle["public_environment"]["satellite_windows"] if int(w["start_s"]) >= at_s]
            or [10**18]
        )
        if next_sat <= min(deadlines[o] for o in active):
            return query
    if terr:
        return min(terr, key=lambda a: deadlines[str(a[1])])
    if sat_now:
        sats = [a for a in actions if a[0] == "SEND_SAT"]
        return min(sats, key=lambda a: deadlines[str(a[1])])
    return ("WAIT", None)


def _execute_policy(bundle, chooser: Callable, *, max_steps: int = 128) -> dict[str, Any]:
    process = attach_causal_evidence(bundle)
    start = min(_attempt_lattice(bundle))
    initial = {
        str(w["world_id"]): LocalState(
            satellite_budget=int(bundle["public_environment"]["satellite_budget_units"])
        )
        for w in bundle["worlds"]
    }
    decisions = 0

    def rec(at_s: int, states: Mapping[str, LocalState], seen: frozenset[Any], depth_count: int):
        nonlocal decisions
        branches = _normalize_one(bundle, process, at_s, states)
        if len(branches) > 1 or next(iter(branches)) != "same":
            children = []
            for obs, ch in sorted(branches.items()):
                ok, sub = rec(at_s, ch, seen, depth_count)
                if not ok:
                    return False, None
                children.append({"observation": obs, "worlds": sorted(ch), "subpolicy": sub})
            return True, {"time_s": at_s, "event": "OBSERVATION", "children": children}
        states = next(iter(branches.values()))
        if any(_expired(bundle, st, at_s) for st in states.values()):
            return False, None
        if all(_success(bundle, st) for st in states.values()):
            return True, {"terminal": True}
        key = (at_s, _canon(states))
        if key in seen or depth_count >= max_steps:
            return False, None
        action = chooser(bundle, process, at_s, states)
        if action is None:
            return False, None
        stepped = _step(bundle, process, states, at_s, action)
        if stepped is None:
            return False, None
        decisions += 1
        child, next_t = stepped
        ok, sub = rec(next_t, child, seen | {key}, depth_count + 1)
        return ok, {"time_s": at_s, "action": action[0], "arg": action[1], "subpolicy": sub}

    solvable, policy = rec(start, initial, frozenset(), 0)
    return {"solvable": solvable, "policy": policy, "decisions": decisions}


def solve_shallow_rule(bundle) -> dict[str, Any]:
    out = _execute_policy(bundle, _choose_shallow)
    return {"baseline": "shallow_rule_combiner", **out}


def solve_depth_k(bundle, *, depth: int) -> dict[str, Any]:
    if depth < 1:
        raise ValueError("depth must be >=1")
    out = _execute_policy(bundle, lambda b, p, t, s: _choose_depth_k(b, p, t, s, depth))
    return {"baseline": f"true_depth_{depth}_belief", "depth": depth, **out}


def solve_depth_k_flow_terminal(bundle, *, depth: int) -> dict[str, Any]:
    if depth < 1:
        raise ValueError("depth must be >=1")
    out = _execute_policy(bundle, lambda b, p, t, s: _choose_depth_k(b, p, t, s, depth, leaf="flow"))
    return {"baseline": f"depth_{depth}_flow_terminal", "depth": depth, **out}


def solve_receding_horizon(bundle, *, horizon_decisions: int) -> dict[str, Any]:
    out = solve_depth_k(bundle, depth=horizon_decisions)
    out["baseline"] = f"receding_horizon_{horizon_decisions}"
    out["horizon_decisions"] = horizon_decisions
    return out


def _choose_always_query_then_plan(bundle, process, at_s: int, states: Mapping[str, LocalState]) -> Action | None:
    actions = _legal_actions(bundle, process, states, at_s)
    q = next((a for a in actions if a[0] == "ISSUE_QUERY"), None)
    if q is not None:
        return q
    return _choose_depth_k(bundle, process, at_s, states, 1)


def solve_always_query_then_plan(bundle) -> dict[str, Any]:
    out = _execute_policy(bundle, _choose_always_query_then_plan)
    return {"baseline": "always_query_then_plan", **out}


def _choose_latest_feasible(bundle, process, at_s: int, states: Mapping[str, LocalState]) -> Action | None:
    actions = _legal_actions(bundle, process, states, at_s)
    active = _active_common_obligations(bundle, states, at_s)
    if not active:
        return ("WAIT", None) if ("WAIT", None) in actions else None
    deadlines = {str(o["obligation_id"]): int(o["deadline_s"]) for o in bundle["obligations"]}
    oid = min(active, key=lambda x: deadlines[x])
    deadline = deadlines[oid]
    # Preserve resources while there remains a later public decision boundary
    # before the earliest deadline; commit only at the latest visible boundary.
    lattice = _attempt_lattice(bundle)
    later = [t for t in lattice if at_s < t <= deadline]
    if later and min(later) < deadline:
        return ("WAIT", None)
    for kind in ("SEND_TERR", "SEND_SAT"):
        a = (kind, oid)
        if a in actions:
            return a
    q = next((a for a in actions if a[0] == "ISSUE_QUERY"), None)
    return q if q is not None else (("WAIT", None) if ("WAIT", None) in actions else None)


def solve_latest_feasible_send(bundle) -> dict[str, Any]:
    out = _execute_policy(bundle, _choose_latest_feasible)
    return {"baseline": "latest_feasible_send", **out}


def _choose_least_slack(bundle, process, at_s: int, states: Mapping[str, LocalState]) -> Action | None:
    actions = _legal_actions(bundle, process, states, at_s)
    deadlines = {str(o["obligation_id"]): int(o["deadline_s"]) for o in bundle["obligations"]}
    sends = [a for a in actions if a[0] in {"SEND_TERR", "SEND_SAT"}]
    if sends:
        return min(
            sends,
            key=lambda a: (
                deadlines[str(a[1])] - at_s,
                0 if a[0] == "SEND_TERR" else 1,
                str(a[1]),
            ),
        )
    q = next((a for a in actions if a[0] == "ISSUE_QUERY"), None)
    return q if q is not None else (("WAIT", None) if ("WAIT", None) in actions else None)


def solve_least_slack(bundle) -> dict[str, Any]:
    out = _execute_policy(bundle, _choose_least_slack)
    return {"baseline": "least_slack", **out}


def solve_myopic_flow_voi(bundle) -> dict[str, Any]:
    """One-decision robust lookahead with residual-flow terminal value."""
    out = solve_depth_k_flow_terminal(bundle, depth=1)
    out["baseline"] = "myopic_flow_voi"
    return out


def _fixed_query_times(bundle, mode: str) -> set[int]:
    releases=sorted({int(o['release_s']) for o in bundle['obligations']})
    sat=sorted({int(w['start_s']) for w in bundle['public_environment']['satellite_windows']})
    lattice=list(_attempt_lattice(bundle))
    if mode=='FIRST_RELEASE':
        return {releases[0]} if releases else set()
    if mode=='EVERY_RELEASE':
        return set(releases)
    if mode=='SATELLITE_START':
        return set(sat)
    if mode=='EVERY_SECOND_EVENT':
        return set(lattice[::2])
    raise ValueError(mode)


def solve_fixed_query_schedule(bundle, *, mode: str) -> dict[str, Any]:
    schedule=_fixed_query_times(bundle,mode)
    def choose(b,p,t,s):
        actions=_legal_actions(b,p,s,t)
        if t in schedule:
            q=next((a for a in actions if a[0]=='ISSUE_QUERY'),None)
            if q is not None:
                return q
        return _choose_least_slack(b,p,t,s)
    out=_execute_policy(bundle,choose)
    return {'baseline':f'fixed_query_{mode.lower()}','schedule_mode':mode,**out}
