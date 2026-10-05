#!/usr/bin/env python3
"""Conservative satellite-only causal completion certificate."""
from __future__ import annotations

from typing import Any, Mapping

from causal_evidence_process_v0_1 import attach_causal_evidence
from exact_reference_oracle_v0_1 import (
    SATELLITE_COMPLETION_DELAY_S,
    LocalState,
    _attempt_lattice,
    _expired,
    _next_time,
    _normalize,
    _success,
)
from v8_policy_baselines_v0_1 import _legal_actions, _step


def _common_tuple(states: Mapping[str, LocalState], attr: str):
    values = {getattr(st, attr) for st in states.values()}
    return next(iter(values)) if len(values) == 1 else None


def _schedule(bundle, at_s: int, states: Mapping[str, LocalState]):
    delivered = _common_tuple(states, "delivered")
    sat_used = _common_tuple(states, "satellite_used")
    budgets = {st.satellite_budget for st in states.values()}
    if delivered is None or sat_used is None or len(budgets) != 1:
        return None
    if any(st.pending_query is not None or st.pending_deliveries for st in states.values()):
        return None
    budget = next(iter(budgets))
    unresolved = [o for o in bundle["obligations"] if str(o["obligation_id"]) not in set(delivered)]
    if not unresolved:
        return []
    used = dict(sat_used)
    slots = []
    for w in bundle["public_environment"]["satellite_windows"]:
        residual = max(0, int(w["capacity_units"]) - used.get(str(w["window_id"]), 0))
        t = max(at_s, int(w["start_s"]))
        if t >= int(w["end_s"]):
            continue
        slots.extend([(t, str(w["window_id"]))] * residual)
    slots = sorted(slots)[:budget]
    remaining = {str(o["obligation_id"]): o for o in unresolved}
    assignment = []
    for t, wid in slots:
        available = [
            o for o in remaining.values()
            if int(o["release_s"]) <= t and t + SATELLITE_COMPLETION_DELAY_S <= int(o["deadline_s"])
        ]
        if not available:
            continue
        o = min(available, key=lambda x: (int(x["deadline_s"]), str(x["obligation_id"])))
        oid = str(o["obligation_id"])
        assignment.append((t, wid, oid))
        remaining.pop(oid)
        if not remaining:
            return assignment
    return None


def satellite_only_certificate(bundle: Mapping[str, Any], at_s: int,
                               states: Mapping[str, LocalState]) -> dict[str, Any] | None:
    process = attach_causal_evidence(bundle)
    lattice = _attempt_lattice(bundle)

    def rec(t: int, support: Mapping[str, LocalState]):
        branches = _normalize(bundle, process, t, support)
        if len(branches) != 1 or next(iter(branches)) != "same":
            children = []
            for obs, child in sorted(branches.items()):
                sub = rec(t, child)
                if sub is None:
                    return None
                children.append({"observation": obs, "worlds": sorted(child), "subpolicy": sub})
            return {"time_s": t, "event": "OBSERVATION", "children": children}
        support = next(iter(branches.values()))
        if any(_expired(bundle, st, t) for st in support.values()):
            return None
        if all(_success(bundle, st) for st in support.values()):
            return {"terminal": True}

        if any(st.pending_query is not None or st.pending_deliveries for st in support.values()):
            stepped = _step(bundle, process, support, t, ("WAIT", None))
            if stepped is None:
                return None
            child, nt = stepped
            sub = rec(nt, child)
            return None if sub is None else {
                "time_s": t, "action": "WAIT", "arg": None,
                "worlds": sorted(support), "subpolicy": sub,
            }

        schedule = _schedule(bundle, t, support)
        if schedule is None:
            return None
        if not schedule:
            return {"terminal": True} if all(_success(bundle, st) for st in support.values()) else None
        send_t, _window_id, oid = schedule[0]
        if send_t > t:
            nt = _next_time(lattice, t, support)
            if nt is None:
                return None
            sub = rec(nt, support)
            return None if sub is None else {
                "time_s": t, "action": "WAIT", "arg": None,
                "worlds": sorted(support), "subpolicy": sub,
            }
        action = ("SEND_SAT", oid)
        if action not in _legal_actions(bundle, process, support, t):
            return None
        stepped = _step(bundle, process, support, t, action)
        if stepped is None:
            return None
        child, nt = stepped
        sub = rec(nt, child)
        return None if sub is None else {
            "time_s": t, "action": action[0], "arg": action[1],
            "worlds": sorted(support), "subpolicy": sub,
        }

    return rec(at_s, dict(states))

