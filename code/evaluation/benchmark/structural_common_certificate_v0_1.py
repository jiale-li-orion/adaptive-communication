#!/usr/bin/env python3
"""Conservative common-opportunity completion certificate."""
from __future__ import annotations

from typing import Any, Mapping

from causal_evidence_process_v0_1 import attach_causal_evidence
from exact_reference_oracle_v0_1 import (
    FINAL_ACK_DELAY_S, SATELLITE_COMPLETION_DELAY_S, LocalState,
    _attempt_lattice, _expired, _next_time, _normalize, _success, _world_map,
)
from v8_policy_baselines_v0_1 import _legal_actions, _step


def _same(states: Mapping[str, LocalState], attr: str):
    vals = {getattr(st, attr) for st in states.values()}
    return next(iter(vals)) if len(vals) == 1 else None


def _resource_tokens(bundle, at_s: int, states: Mapping[str, LocalState]):
    wm = _world_map(bundle); ids = sorted(states); tokens = []
    rows = [{str(w["window_id"]): w for w in wm[wid]["terrestrial_windows"]} for wid in ids]
    common = set(rows[0]) if rows else set()
    for row in rows[1:]: common &= set(row)
    for window_id in sorted(common):
        ws = [row[window_id] for row in rows]
        starts = {int(w["start_s"]) for w in ws}; ends = {int(w["end_s"]) for w in ws}
        if len(starts) != 1 or len(ends) != 1: continue
        t = max(at_s, next(iter(starts))); end = next(iter(ends))
        if t >= end: continue
        cap = min(int(w["capacity_units"]) - dict(states[wid].terrestrial_used).get(window_id, 0)
                  for wid, w in zip(ids, ws))
        tokens.extend([(t, "SEND_TERR", FINAL_ACK_DELAY_S)] * max(0, cap))
    sat_used = _same(states, "satellite_used"); budgets = {st.satellite_budget for st in states.values()}
    if sat_used is not None and len(budgets) == 1:
        used = dict(sat_used); sat = []
        for w in bundle["public_environment"]["satellite_windows"]:
            t = max(at_s, int(w["start_s"])); end = int(w["end_s"])
            if t >= end: continue
            cap = max(0, int(w["capacity_units"]) - used.get(str(w["window_id"]), 0))
            sat.extend([(t, "SEND_SAT", SATELLITE_COMPLETION_DELAY_S)] * cap)
        tokens.extend(sorted(sat)[:next(iter(budgets))])
    return sorted(tokens)


def _match(bundle, at_s: int, states: Mapping[str, LocalState]):
    delivered = _same(states, "delivered")
    if delivered is None: return None
    obligations = [o for o in bundle["obligations"] if str(o["obligation_id"]) not in set(delivered)]
    if not obligations: return []
    tokens = _resource_tokens(bundle, at_s, states)
    cand = {}
    for o in obligations:
        oid = str(o["obligation_id"])
        cand[oid] = [i for i, (t, _kind, delay) in enumerate(tokens)
                     if int(o["release_s"]) <= t and t + delay <= int(o["deadline_s"])]
        if not cand[oid]: return None
    order = sorted(cand, key=lambda oid: (len(cand[oid]), oid)); used = set(); chosen = {}
    def dfs(k: int) -> bool:
        if k == len(order): return True
        oid = order[k]
        for idx in cand[oid]:
            if idx in used: continue
            used.add(idx); chosen[oid] = idx
            if dfs(k + 1): return True
            used.remove(idx); chosen.pop(oid, None)
        return False
    if not dfs(0): return None
    return sorted((tokens[idx][0], tokens[idx][1], oid) for oid, idx in chosen.items())


def common_opportunity_certificate(bundle: Mapping[str, Any], at_s: int,
                                   states: Mapping[str, LocalState]) -> dict[str, Any] | None:
    process = attach_causal_evidence(bundle)
    if process["passive_observation_rules"] or process["direct_observation"]:
        return None
    if any(st.pending_query is not None or st.pending_deliveries for st in states.values()):
        return None
    lattice = _attempt_lattice(bundle)

    def rec(t: int, support: Mapping[str, LocalState], plan):
        branches = _normalize(bundle, process, t, support)
        if len(branches) != 1 or next(iter(branches)) != "same": return None
        support = next(iter(branches.values()))
        if any(_expired(bundle, st, t) for st in support.values()): return None
        if all(_success(bundle, st) for st in support.values()): return {"terminal": True}
        if plan:
            send_t, kind, oid = plan[0]
            if send_t <= t:
                action = (kind, oid)
                if action not in _legal_actions(bundle, process, support, t): return None
                stepped = _step(bundle, process, support, t, action)
                if stepped is None: return None
                child, nt = stepped; sub = rec(nt, child, plan[1:])
                return None if sub is None else {"time_s": t, "action": kind, "arg": oid,
                                                 "worlds": sorted(support), "subpolicy": sub}
        nt = _next_time(lattice, t, support)
        if nt is None: return None
        sub = rec(nt, support, plan)
        return None if sub is None else {"time_s": t, "action": "WAIT", "arg": None,
                                         "worlds": sorted(support), "subpolicy": sub}

    plan = _match(bundle, at_s, states)
    return None if plan is None else rec(at_s, dict(states), plan)

