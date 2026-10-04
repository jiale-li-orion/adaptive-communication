#!/usr/bin/env python3
"""Exact non-anticipative scenario tree with asynchronous evidence queries."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Obligation:
    oid: str
    release_s: int
    deadline_s: int


@dataclass(frozen=True)
class EvidenceQuery:
    query_id: str
    proposition: str
    owner: str
    delay_s: int
    capability_id: str | None = None
    required_path: tuple[str, ...] = ()
    return_path: tuple[str, ...] = ()
    opportunity_dependency: tuple[str, ...] = ()


@dataclass(frozen=True)
class World:
    world_id: str
    terrestrial_slots: tuple[int, ...]
    evidence_values: tuple[tuple[str, str], ...]
    query_reachable: bool = True
    prehistory_events: tuple[tuple[int, str, str], ...] = ()
    passive_events: tuple[tuple[int, str, str], ...] = ()

    def value(self, query_id: str) -> str:
        return dict(self.evidence_values)[query_id]


@dataclass(frozen=True)
class LocalState:
    delivered: tuple[str, ...] = ()
    sat_budget: int = 0
    issued_queries: tuple[str, ...] = ()
    pending_queries: tuple[tuple[str, int], ...] = ()
    seen_passive_events: tuple[tuple[int, str], ...] = ()


@dataclass(frozen=True)
class Bundle:
    bundle_id: str
    fixed_event_times: tuple[int, ...]
    obligations: tuple[Obligation, ...]
    satellite_slots: tuple[int, ...]
    worlds: tuple[World, ...]
    satellite_budget: int
    queries: tuple[EvidenceQuery, ...]
    initial_public_observation: tuple[tuple[str, str], ...] = ()


Action = tuple[str, str | None]


def _world_map(bundle: Bundle) -> dict[str, World]:
    return {w.world_id: w for w in bundle.worlds}


def _query_map(bundle: Bundle) -> dict[str, EvidenceQuery]:
    return {q.query_id: q for q in bundle.queries}


def _pending_obligations(bundle: Bundle, state: LocalState, t: int) -> list[Obligation]:
    done = set(state.delivered)
    return [
        o for o in bundle.obligations
        if o.oid not in done and o.release_s <= t <= o.deadline_s
    ]


def _expired(bundle: Bundle, state: LocalState, t: int) -> bool:
    done = set(state.delivered)
    return any(o.oid not in done and o.deadline_s < t for o in bundle.obligations)


def _success(bundle: Bundle, state: LocalState) -> bool:
    return len(state.delivered) == len(bundle.obligations)


def _next_event_time(bundle: Bundle, t: int, states: dict[str, LocalState]) -> int | None:
    candidates = [x for x in bundle.fixed_event_times if x > t]
    worlds = _world_map(bundle)
    for wid, state in states.items():
        candidates.extend(arrival for _, arrival in state.pending_queries if arrival > t)
        seen = set(state.seen_passive_events)
        for event_t, key, _value in worlds[wid].passive_events:
            if event_t > t and (event_t, key) not in seen:
                candidates.append(event_t)
    return min(candidates) if candidates else None


def _normalize_due_queries(
    bundle: Bundle,
    t: int,
    states: dict[str, LocalState],
) -> dict[str, dict[str, LocalState]]:
    """Apply due query responses and passive telemetry as observation events."""
    worlds = _world_map(bundle)
    branches: dict[str, dict[str, LocalState]] = {}
    for wid, state in states.items():
        world = worlds[wid]
        due = sorted((qid, arrival) for qid, arrival in state.pending_queries if arrival <= t)
        remaining = tuple((qid, arrival) for qid, arrival in state.pending_queries if arrival > t)
        observations: list[tuple[str, str]] = []
        for qid, _ in due:
            if world.query_reachable:
                observations.append((qid, world.value(qid)))
            else:
                observations.append((qid, "__TIMEOUT__"))

        seen = set(state.seen_passive_events)
        new_seen = set(seen)
        for event_t, key, value in sorted(world.passive_events):
            marker = (int(event_t), str(key))
            if event_t <= t and marker not in seen:
                observations.append((f"passive:{key}", str(value)))
                new_seen.add(marker)

        obs_key = "|".join(f"{qid}={value}" for qid, value in sorted(observations)) or "same"
        branches.setdefault(obs_key, {})[wid] = LocalState(
            delivered=state.delivered,
            sat_budget=state.sat_budget,
            issued_queries=state.issued_queries,
            pending_queries=remaining,
            seen_passive_events=tuple(sorted(new_seen)),
        )
    return branches

def _available_actions(bundle: Bundle, t: int, states: dict[str, LocalState]) -> list[Action]:
    vals = list(states.values())
    common_pending: set[str] | None = None
    for st in vals:
        ids = {o.oid for o in _pending_obligations(bundle, st, t)}
        common_pending = ids if common_pending is None else common_pending & ids
    common_pending = common_pending or set()

    actions: list[Action] = [("WAIT", None)]
    if t in bundle.satellite_slots and vals and all(st.sat_budget > 0 for st in vals):
        actions.extend(("SEND_SAT", oid) for oid in sorted(common_pending))
    actions.extend(("SEND_TERR", oid) for oid in sorted(common_pending))

    for query in bundle.queries:
        if all(query.query_id not in st.issued_queries for st in vals):
            actions.append(("ISSUE_QUERY", query.query_id))
    return actions



def _validate_query_contracts(bundle: Bundle) -> None:
    for query in bundle.queries:
        # Legacy mechanism fixtures may omit binding metadata. Mainline bundles
        # that declare a capability must be self-consistent and path-scoped.
        if query.capability_id is None:
            continue
        if query.proposition != query.capability_id:
            raise ValueError(f"query proposition/capability mismatch: {query.query_id}")
        if not query.owner:
            raise ValueError(f"query owner missing: {query.query_id}")
        if not query.return_path or not query.opportunity_dependency:
            raise ValueError(f"query path/opportunity contract missing: {query.query_id}")

def solve(
    bundle: Bundle,
    *,
    forced_first_action: Action | None = None,
    disabled_queries: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    _validate_query_contracts(bundle)
    worlds = _world_map(bundle)
    queries = _query_map(bundle)
    start = bundle.fixed_event_times[0]
    initial = {
        w.world_id: LocalState(sat_budget=bundle.satellite_budget)
        for w in bundle.worlds
    }
    memo: dict[Any, tuple[bool, dict[str, Any] | None]] = {}

    def canon(states: dict[str, LocalState]) -> tuple[tuple[str, LocalState], ...]:
        return tuple(sorted(states.items()))

    def rec(t: int, states: dict[str, LocalState]) -> tuple[bool, dict[str, Any] | None]:
        # Evidence arrival is an exogenous observation event, not an action.
        normalized = _normalize_due_queries(bundle, t, states)
        if len(normalized) > 1 or next(iter(normalized)) != "same":
            children = []
            for obs, child in sorted(normalized.items()):
                ok, sub = rec(t, child)
                if not ok:
                    return False, None
                children.append({"observation": obs, "worlds": sorted(child), "subpolicy": sub})
            return True, {"time_s": t, "event": "EVIDENCE_ARRIVAL", "children": children}
        states = next(iter(normalized.values()))

        key = (t, canon(states), disabled_queries)
        if key in memo:
            return memo[key]
        if any(_expired(bundle, st, t) for st in states.values()):
            memo[key] = (False, None)
            return memo[key]
        if all(_success(bundle, st) for st in states.values()):
            memo[key] = (True, {"terminal": True})
            return memo[key]

        actions = [
            a for a in _available_actions(bundle, t, states)
            if not (a[0] == "ISSUE_QUERY" and a[1] in disabled_queries)
        ]
        if forced_first_action is not None and t == start and canon(states) == canon(initial):
            actions = [a for a in actions if a == forced_first_action]

        for action, arg in actions:
            branches: dict[str, dict[str, LocalState]] = {"same": {}}
            next_t = t

            if action == "ISSUE_QUERY":
                q = queries[str(arg)]
                for wid, st in states.items():
                    issued = tuple(sorted(set(st.issued_queries) | {q.query_id}))
                    pending = tuple(sorted(st.pending_queries + ((q.query_id, t + q.delay_s),)))
                    branches["same"][wid] = LocalState(
                        st.delivered, st.sat_budget, issued, pending, st.seen_passive_events
                    )
                # Asynchronous: issuing does not consume the current send opportunity.
                next_t = t

            elif action == "WAIT":
                nt = _next_event_time(bundle, t, states)
                if nt is None:
                    continue
                next_t = nt
                branches["same"] = dict(states)

            elif action == "SEND_SAT":
                for wid, st in states.items():
                    branches["same"][wid] = LocalState(
                        tuple(sorted(set(st.delivered) | {str(arg)})),
                        st.sat_budget - 1,
                        st.issued_queries,
                        st.pending_queries,
                        st.seen_passive_events,
                    )
                nt = _next_event_time(bundle, t, branches["same"])
                if nt is None:
                    if not all(_success(bundle, st) for st in branches["same"].values()):
                        continue
                    next_t = t
                else:
                    next_t = nt

            elif action == "SEND_TERR":
                split: dict[str, dict[str, LocalState]] = {}
                for wid, st in states.items():
                    ok = t in worlds[wid].terrestrial_slots
                    delivered = set(st.delivered)
                    if ok:
                        delivered.add(str(arg))
                    ns = LocalState(
                        tuple(sorted(delivered)),
                        st.sat_budget,
                        st.issued_queries,
                        st.pending_queries,
                        st.seen_passive_events,
                    )
                    split.setdefault(f"ack:terr:{'ok' if ok else 'fail'}", {})[wid] = ns
                branches = split
                nt = _next_event_time(bundle, t, states)
                if nt is None:
                    if not all(
                        _success(bundle, st)
                        for branch in branches.values()
                        for st in branch.values()
                    ):
                        continue
                    next_t = t
                else:
                    next_t = nt
            else:
                continue

            # Query issue can keep the same time because issued_queries changes;
            # all other zero-time actions move to the next event.
            children = []
            good = True
            for obs, child in sorted(branches.items()):
                ok, sub = rec(next_t, child)
                if not ok:
                    good = False
                    break
                children.append({"observation": obs, "worlds": sorted(child), "subpolicy": sub})
            if good:
                policy = {
                    "time_s": t,
                    "action": action,
                    "arg": arg,
                    "children": children,
                }
                memo[key] = (True, policy)
                return memo[key]

        memo[key] = (False, None)
        return memo[key]

    solvable, policy = rec(start, initial)
    return {"solvable": solvable, "policy": policy, "memo_nodes": len(memo)}
