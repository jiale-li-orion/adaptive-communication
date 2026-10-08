#!/usr/bin/env python3
"""Exact references for the Layer-1 compositional world/evidence IR.

Two references are implemented without collapsing their information boundary:

1. per-world hindsight physical feasibility via an exact capacitated matching;
2. observation-matched non-anticipative policy search over the whole alias set,
   with an optional no-paid-query restriction.

``FULL_CURRENT_STATE`` is implemented as a causal AND/OR reference over the
declared physical future support: it receives the complete *current* state for
free, but future service transitions remain branched and therefore unknown.
This is deliberately different from solving one realized world, which remains
the hindsight physical upper bound.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from causal_evidence_process_v0_1 import (
    ACK_TIMEOUT_S,
    FINAL_ACK_DELAY_S,
    GATEWAY_RECEIPT_DELAY_S,
    QUERY_RESPONSE_DELAY_S,
    SATELLITE_COMPLETION_DELAY_S,
    attach_causal_evidence,
    gateway_snapshot,
)


class ExactOracleError(ValueError):
    pass


class SearchLimitExceeded(RuntimeError):
    pass


def _earliest_send(
    *,
    release_s: int,
    deadline_s: int,
    start_s: int,
    end_s: int,
    completion_delay_s: int,
) -> int | None:
    t = max(release_s, start_s)
    if t >= end_s or t + completion_delay_s > deadline_s:
        return None
    return t


def _add_edge(graph: dict[str, dict[str, int]], u: str, v: str, cap: int) -> None:
    graph.setdefault(u, {})[v] = graph.setdefault(u, {}).get(v, 0) + cap
    graph.setdefault(v, {}).setdefault(u, 0)


def _maxflow(graph: dict[str, dict[str, int]], source: str, sink: str) -> int:
    total = 0
    while True:
        parent: dict[str, str | None] = {source: None}
        q = [source]
        for u in q:
            for v, cap in graph[u].items():
                if cap > 0 and v not in parent:
                    parent[v] = u
                    q.append(v)
                    if v == sink:
                        break
            if sink in parent:
                break
        if sink not in parent:
            return total
        v = sink
        aug = 10**9
        while parent[v] is not None:
            u = str(parent[v])
            aug = min(aug, graph[u][v])
            v = u
        v = sink
        while parent[v] is not None:
            u = str(parent[v])
            graph[u][v] -= aug
            graph[v][u] += aug
            v = u
        total += aug


def hindsight_physical_reference(
    world_bundle: Mapping[str, Any],
    *,
    world_id: str,
) -> dict[str, Any]:
    """Exact unit-report feasibility for one frozen realized world."""
    world = next((w for w in world_bundle["worlds"] if str(w["world_id"]) == world_id), None)
    if world is None:
        raise ExactOracleError(f"unknown world {world_id}")
    obligations = list(world_bundle["obligations"])
    sat_windows = list(world_bundle["public_environment"]["satellite_windows"])
    sat_budget = int(world_bundle["public_environment"]["satellite_budget_units"])

    source = "SRC"
    sink = "SNK"
    sat_pool = "SAT_POOL"
    graph: dict[str, dict[str, int]] = {}
    edge_meta: dict[tuple[str, str], dict[str, Any]] = {}
    original_caps: dict[tuple[str, str], int] = {}

    def add(u: str, v: str, cap: int, meta: dict[str, Any] | None = None) -> None:
        _add_edge(graph, u, v, cap)
        original_caps[(u, v)] = original_caps.get((u, v), 0) + cap
        if meta is not None:
            edge_meta[(u, v)] = meta

    for o in obligations:
        on = f"O::{o['obligation_id']}"
        add(source, on, 1)
        for w in world["terrestrial_windows"]:
            t = _earliest_send(
                release_s=int(o["release_s"]),
                deadline_s=int(o["deadline_s"]),
                start_s=int(w["start_s"]),
                end_s=int(w["end_s"]),
                completion_delay_s=FINAL_ACK_DELAY_S,
            )
            if t is None:
                continue
            rn = f"T::{w['window_id']}"
            add(
                on,
                rn,
                1,
                {
                    "path": "TERRESTRIAL",
                    "resource_id": str(w["window_id"]),
                    "send_at_s": t,
                    "complete_at_s": t + FINAL_ACK_DELAY_S,
                },
            )
        for w in sat_windows:
            t = _earliest_send(
                release_s=int(o["release_s"]),
                deadline_s=int(o["deadline_s"]),
                start_s=int(w["start_s"]),
                end_s=int(w["end_s"]),
                completion_delay_s=SATELLITE_COMPLETION_DELAY_S,
            )
            if t is None:
                continue
            rn = f"S::{w['window_id']}"
            add(
                on,
                rn,
                1,
                {
                    "path": "SATELLITE",
                    "resource_id": str(w["window_id"]),
                    "send_at_s": t,
                    "complete_at_s": t + SATELLITE_COMPLETION_DELAY_S,
                },
            )

    for w in world["terrestrial_windows"]:
        add(f"T::{w['window_id']}", sink, int(w["capacity_units"]))
    for w in sat_windows:
        add(f"S::{w['window_id']}", sat_pool, int(w["capacity_units"]))
    add(sat_pool, sink, sat_budget)

    flow = _maxflow(graph, source, sink)
    witness: list[dict[str, Any]] = []
    if flow == len(obligations):
        for o in obligations:
            on = f"O::{o['obligation_id']}"
            for (u, v), meta in edge_meta.items():
                if u != on:
                    continue
                # An original unit edge is used when its forward residual is 0.
                if original_caps.get((u, v)) == 1 and graph[u][v] == 0:
                    witness.append({"obligation_id": str(o["obligation_id"]), **meta})
                    break
    return {
        "mode": "HINDSIGHT_PHYSICAL_FEASIBILITY",
        "world_id": world_id,
        "solvable": flow == len(obligations),
        "max_completed_obligations": flow,
        "obligation_count": len(obligations),
        "witness": witness,
        "scalarization_used": False,
    }


def hindsight_bundle_reference(world_bundle: Mapping[str, Any]) -> dict[str, Any]:
    rows = [
        hindsight_physical_reference(world_bundle, world_id=str(w["world_id"]))
        for w in world_bundle["worlds"]
    ]
    return {
        "mode": "HINDSIGHT_PHYSICAL_FEASIBILITY",
        "all_worlds_solvable": all(r["solvable"] for r in rows),
        "any_world_solvable": any(r["solvable"] for r in rows),
        "worlds": rows,
    }


@dataclass(frozen=True)
class PendingQuery:
    arrive_at_s: int
    observation_key: str


@dataclass(frozen=True)
class PendingDelivery:
    obligation_id: str
    accepted: bool
    gateway_receipt_at_s: int | None
    final_ack_at_s: int | None
    negative_observation_at_s: int | None
    gateway_receipt_seen: bool = False


@dataclass(frozen=True)
class LocalState:
    delivered: tuple[str, ...] = ()
    terrestrial_used: tuple[tuple[str, int], ...] = ()
    satellite_used: tuple[tuple[str, int], ...] = ()
    satellite_budget: int = 0
    pending_query: PendingQuery | None = None
    last_query_signature: str | None = None
    last_direct_signature: str | None = None
    pending_deliveries: tuple[PendingDelivery, ...] = ()


def _used_map(state: LocalState) -> dict[str, int]:
    return dict(state.terrestrial_used)


def _with_used(state: LocalState, window_id: str) -> tuple[tuple[str, int], ...]:
    d = _used_map(state)
    d[window_id] = d.get(window_id, 0) + 1
    return tuple(sorted(d.items()))


def _sat_used_map(state: LocalState) -> dict[str, int]:
    return dict(state.satellite_used)


def _with_sat_used(state: LocalState, window_id: str) -> tuple[tuple[str, int], ...]:
    d = _sat_used_map(state)
    d[window_id] = d.get(window_id, 0) + 1
    return tuple(sorted(d.items()))


def _world_map(bundle: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {str(w["world_id"]): w for w in bundle["worlds"]}


def _process_map(process: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {str(w["world_id"]): w for w in process["world_owner_processes"]}


def _query_rule(process: Mapping[str, Any]) -> Mapping[str, Any] | None:
    rows = list(process.get("query_capabilities", []))
    return rows[0] if rows else None


def _passive_rule(process: Mapping[str, Any]) -> Mapping[str, Any] | None:
    rows = list(process.get("passive_observation_rules", []))
    return rows[0] if rows else None


def _receipt_summary(state: LocalState) -> dict[str, Any]:
    """Owner-side receipt facts that have actually occurred by the prefix.

    Delivered obligations imply an earlier accepted gateway receipt. Pending
    deliveries contribute only after their gateway receipt has been observed by
    the execution kernel. No future service state or opportunity is exposed.
    """

    received = set(state.delivered)
    for d in state.pending_deliveries:
        if d.gateway_receipt_seen:
            received.add(d.obligation_id)
    return {"gateway_received": sorted(received)}


def _query_payload(
    process: Mapping[str, Any],
    proc_world: Mapping[str, Any],
    state: LocalState,
    at_s: int,
) -> dict[str, Any]:
    q = _query_rule(process)
    kind = str((q or {}).get("payload_kind", "GATEWAY_STATE_SUMMARY"))
    if kind == "RECEIPT_SUMMARY":
        return _receipt_summary(state)
    return gateway_snapshot(proc_world, at_s)


def _query_response_delay(process: Mapping[str, Any]) -> int:
    q = _query_rule(process)
    return int((q or {}).get("response_delay_s", QUERY_RESPONSE_DELAY_S))


def _query_timeout_delay(process: Mapping[str, Any]) -> int:
    q = _query_rule(process)
    return int((q or {}).get("timeout_s", _query_response_delay(process)))


def _gateway_receipt_delay(process: Mapping[str, Any]) -> int:
    rule = _passive_rule(process)
    return int((rule or {}).get("gateway_receipt_delay_s", GATEWAY_RECEIPT_DELAY_S))


def _final_ack_delay(process: Mapping[str, Any]) -> int:
    rule = _passive_rule(process)
    return int((rule or {}).get("final_ack_delay_s", FINAL_ACK_DELAY_S))


def _negative_observation_delay(process: Mapping[str, Any]) -> int:
    rule = _passive_rule(process)
    return int((rule or {}).get("negative_observation_after_s", ACK_TIMEOUT_S))


def _satellite_completion_delay(process: Mapping[str, Any]) -> int:
    resource = dict(process.get("resource_contract", {}))
    return int(resource.get("satellite_completion_delay_s", SATELLITE_COMPLETION_DELAY_S))


def _primary_generates_gateway_receipt(process: Mapping[str, Any]) -> bool:
    """Whether a terrestrial action has a later gateway-receipt stage.

    Historical Layer-1 processes model an end-to-end report attempt whose
    intermediate gateway receipt occurs after SEND_TERR.  A corrected
    gateway-backhaul process starts with the report already in the gateway
    queue, so its primary forwarding action must not manufacture another
    gateway receipt.  Defaulting to True preserves every historical process.
    """

    resource = dict(process.get("resource_contract", {}))
    return bool(resource.get("primary_generates_gateway_receipt", True))


def _matching_terrestrial_window(
    world: Mapping[str, Any],
    state: LocalState,
    at_s: int,
) -> Mapping[str, Any] | None:
    used = _used_map(state)
    candidates = []
    for w in world["terrestrial_windows"]:
        if int(w["start_s"]) <= at_s < int(w["end_s"]):
            if used.get(str(w["window_id"]), 0) < int(w["capacity_units"]):
                candidates.append(w)
    if not candidates:
        return None
    return min(candidates, key=lambda w: (int(w["end_s"]), str(w["window_id"])))


def _matching_satellite_window(
    bundle: Mapping[str, Any],
    state: LocalState,
    at_s: int,
) -> Mapping[str, Any] | None:
    used = _sat_used_map(state)
    candidates = []
    for w in bundle["public_environment"]["satellite_windows"]:
        if int(w["start_s"]) <= at_s < int(w["end_s"]):
            if used.get(str(w["window_id"]), 0) < int(w["capacity_units"]):
                candidates.append(w)
    if not candidates:
        return None
    return min(candidates, key=lambda w: (int(w["end_s"]), str(w["window_id"])))


def _attempt_lattice(bundle: Mapping[str, Any]) -> tuple[int, ...]:
    """Exact-safe shared event lattice for piecewise-constant service.

    Between two consecutive boundaries there is no release/deadline/service
    transition.  SEND earlier weakly dominates SEND later for feasibility, and
    gateway snapshots keep the same world partition inside the interval (age
    fields advance by the same delta).  Midpoints/end-1 samples therefore add
    search states without adding a distinct causal decision.

    The lattice is the union over declared future support, so every policy sees
    the same wake-up schedule; realized-world-specific event timing is never
    leaked through the action mask.
    """
    times = {0}
    for o in bundle["obligations"]:
        release = int(o["release_s"])
        deadline = int(o["deadline_s"])
        times.update({release, deadline, deadline + 1})
    for w in bundle["public_environment"]["satellite_windows"]:
        a, b = int(w["start_s"]), int(w["end_s"])
        times.update({a, b})
    for world in bundle["worlds"]:
        for w in world["terrestrial_windows"]:
            a, b = int(w["start_s"]), int(w["end_s"])
            times.update({a, b})
    horizon = int(bundle["public_environment"]["horizon_s"])
    return tuple(sorted(t for t in times if 0 <= t <= horizon + 1))


def _pending_oids(state: LocalState) -> set[str]:
    return {x.obligation_id for x in state.pending_deliveries}


def _active_common_obligations(
    bundle: Mapping[str, Any],
    states: Mapping[str, LocalState],
    at_s: int,
) -> list[str]:
    out = []
    for o in bundle["obligations"]:
        oid = str(o["obligation_id"])
        if not (int(o["release_s"]) <= at_s <= int(o["deadline_s"])):
            continue
        # A common retry can still be useful when only some compatible worlds
        # have completed the report. Whether it risks duplicate completion is
        # path-specific, checked by _delivery_retry_allowed below.
        if all(oid in st.delivered for st in states.values()):
            continue
        if any(oid in _pending_oids(st) for st in states.values()):
            continue
        out.append(oid)
    return out


def _delivery_retry_allowed(
    bundle: Mapping[str, Any],
    states: Mapping[str, LocalState],
    at_s: int,
    kind: str,
    oid: str,
) -> bool:
    """Preserve no-duplicate completion without forbidding harmless attempts.

    Uses the whole compatible support, never the realized hidden world. A
    terrestrial retry is safe if every already-completed world would reject
    that attempt (no remaining service). SAT accepts in every compatible world
    once its public resource preconditions hold, so its rule remains stricter.
    This does not relax the separate one-in-flight restriction.
    """
    if kind == "SEND_SAT":
        return not any(oid in st.delivered for st in states.values())
    if kind != "SEND_TERR":
        raise ValueError(f"Not a delivery action: {kind}")
    wm = _world_map(bundle)
    return not any(
        oid in st.delivered
        and _matching_terrestrial_window(wm[wid], st, at_s) is not None
        for wid, st in states.items()
    )


def _normalize(
    bundle: Mapping[str, Any],
    process: Mapping[str, Any],
    at_s: int,
    states: Mapping[str, LocalState],
    *,
    force_full_current_state: bool = False,
) -> dict[str, dict[str, LocalState]]:
    passive_enabled = bool(process["passive_observation_rules"])
    branches: dict[str, dict[str, LocalState]] = {}
    for wid, st in states.items():
        observations: list[str] = []
        delivered = set(st.delivered)
        pending: list[PendingDelivery] = []
        for d in st.pending_deliveries:
            receipt_seen = d.gateway_receipt_seen
            if d.accepted and d.gateway_receipt_at_s is not None and d.gateway_receipt_at_s <= at_s and not receipt_seen:
                if passive_enabled:
                    observations.append(f"gateway_receipt:{d.obligation_id}:ok")
                receipt_seen = True

            terminal = False
            if d.accepted and d.final_ack_at_s is not None and d.final_ack_at_s <= at_s:
                deadline = next(
                    int(o["deadline_s"])
                    for o in bundle["obligations"]
                    if str(o["obligation_id"]) == d.obligation_id
                )
                if d.final_ack_at_s <= deadline:
                    delivered.add(d.obligation_id)
                if passive_enabled:
                    observations.append(f"final_ack:{d.obligation_id}:ok")
                terminal = True
            elif not d.accepted and d.negative_observation_at_s is not None and d.negative_observation_at_s <= at_s:
                if passive_enabled:
                    observations.append(f"final_ack:{d.obligation_id}:timeout")
                terminal = True

            if not terminal:
                pending.append(
                    PendingDelivery(
                        obligation_id=d.obligation_id,
                        accepted=d.accepted,
                        gateway_receipt_at_s=d.gateway_receipt_at_s,
                        final_ack_at_s=d.final_ack_at_s,
                        negative_observation_at_s=d.negative_observation_at_s,
                        gateway_receipt_seen=receipt_seen,
                    )
                )

        pending_query = st.pending_query
        if pending_query is not None and pending_query.arrive_at_s <= at_s:
            observations.append(pending_query.observation_key)
            pending_query = None

        last_direct_signature = st.last_direct_signature
        if bool(process.get("direct_observation")) or force_full_current_state:
            current_signature = _full_current_state_signature(
                bundle,
                process,
                wid=wid,
                state=st,
                at_s=at_s,
            )
            if current_signature != last_direct_signature:
                observations.append("direct_current_state=" + current_signature)
                last_direct_signature = current_signature

        key = "|".join(sorted(observations)) or "same"
        ns = LocalState(
            delivered=tuple(sorted(delivered)),
            terrestrial_used=st.terrestrial_used,
            satellite_used=st.satellite_used,
            satellite_budget=st.satellite_budget,
            pending_query=pending_query,
            last_query_signature=st.last_query_signature,
            last_direct_signature=last_direct_signature,
            pending_deliveries=tuple(pending),
        )
        branches.setdefault(key, {})[wid] = ns
    return branches


def _expired(bundle: Mapping[str, Any], state: LocalState, at_s: int) -> bool:
    done = set(state.delivered)
    return any(
        str(o["obligation_id"]) not in done and int(o["deadline_s"]) < at_s
        for o in bundle["obligations"]
    )


def _success(bundle: Mapping[str, Any], state: LocalState) -> bool:
    return len(state.delivered) == len(bundle["obligations"])


def _next_time(
    lattice: tuple[int, ...],
    at_s: int,
    states: Mapping[str, LocalState],
) -> int | None:
    candidates = [t for t in lattice if t > at_s]
    for st in states.values():
        if st.pending_query is not None and st.pending_query.arrive_at_s > at_s:
            candidates.append(st.pending_query.arrive_at_s)
        for d in st.pending_deliveries:
            for t in (d.gateway_receipt_at_s, d.final_ack_at_s, d.negative_observation_at_s):
                if t is not None and t > at_s:
                    candidates.append(t)
    return min(candidates) if candidates else None


def solve_observation_matched(
    world_bundle: Mapping[str, Any],
    process: Mapping[str, Any] | None = None,
    *,
    disable_paid_query: bool = False,
    force_full_current_state: bool = False,
    max_memo_nodes: int = 200_000,
) -> dict[str, Any]:
    """Exact AND/OR feasibility on the frozen alias support and causal history."""
    process = attach_causal_evidence(world_bundle) if process is None else process
    wm = _world_map(world_bundle)
    pm = _process_map(process)
    lattice = _attempt_lattice(world_bundle)
    start = min(lattice)
    initial = {
        wid: LocalState(satellite_budget=int(world_bundle["public_environment"]["satellite_budget_units"]))
        for wid in wm
    }
    memo: dict[Any, tuple[bool, dict[str, Any] | None]] = {}

    def canon(states: Mapping[str, LocalState]) -> tuple[tuple[str, LocalState], ...]:
        return tuple(sorted(states.items()))

    def query_signature(wid: str, st: LocalState, at_s: int) -> str:
        world = wm[wid]
        proc_world = pm[wid]
        reachable = _matching_terrestrial_window(world, st, at_s) is not None
        q = _query_rule(process)
        qid = str((q or {}).get("query_id", "gateway_state_summary"))
        if not reachable:
            return f"query:{qid}=__TIMEOUT__"
        return f"query:{qid}=" + jsonable(_query_payload(process, proc_world, st, at_s))

    def query_can_change_history(states: Mapping[str, LocalState], at_s: int) -> bool:
        # Reissuing the same owner read while every compatible world's sampled
        # outcome is unchanged is dominated in this feasibility model: it adds
        # no partition/freshness semantics and can only consume capacity/time.
        return any(
            query_signature(wid, st, at_s) != st.last_query_signature
            for wid, st in states.items()
        )

    def terr_can_have_effect(states: Mapping[str, LocalState], at_s: int) -> bool:
        # If every compatible world lacks remaining terrestrial capacity now,
        # SEND_TERR deterministically fails and produces no information beyond
        # what WAIT can preserve.  Removing it is an exact dominance prune.
        return any(
            _matching_terrestrial_window(wm[wid], st, at_s) is not None
            for wid, st in states.items()
        )

    def rec(at_s: int, states: dict[str, LocalState]) -> tuple[bool, dict[str, Any] | None]:
        normalized = _normalize(
            world_bundle,
            process,
            at_s,
            states,
            force_full_current_state=force_full_current_state,
        )
        if len(normalized) > 1 or next(iter(normalized)) != "same":
            children = []
            for obs, child in sorted(normalized.items()):
                ok, sub = rec(at_s, child)
                if not ok:
                    return False, None
                children.append({"observation": obs, "worlds": sorted(child), "subpolicy": sub})
            return True, {"time_s": at_s, "event": "OBSERVATION", "children": children}
        states = next(iter(normalized.values()))

        key = (at_s, disable_paid_query, force_full_current_state, canon(states))
        if key in memo:
            return memo[key]
        if len(memo) >= max_memo_nodes:
            raise SearchLimitExceeded(f"observation-matched oracle exceeded {max_memo_nodes} memo nodes")
        if any(_expired(world_bundle, st, at_s) for st in states.values()):
            memo[key] = (False, None)
            return memo[key]
        if all(_success(world_bundle, st) for st in states.values()):
            memo[key] = (True, {"terminal": True})
            return memo[key]

        active = _active_common_obligations(world_bundle, states, at_s)
        actions: list[tuple[str, str | None]] = []
        # Ordinary execution first; exactness is preserved because all legal
        # branches are still explored if earlier actions fail.
        if terr_can_have_effect(states, at_s):
            actions.extend(("SEND_TERR", oid) for oid in active
                           if _delivery_retry_allowed(world_bundle, states, at_s, "SEND_TERR", oid))
        if all(
            st.satellite_budget > 0
            and _matching_satellite_window(world_bundle, st, at_s) is not None
            for st in states.values()
        ):
            actions.extend(("SEND_SAT", oid) for oid in active
                           if _delivery_retry_allowed(world_bundle, states, at_s, "SEND_SAT", oid))
        if (
            not disable_paid_query
            and process["query_capabilities"]
            and all(st.pending_query is None for st in states.values())
            and query_can_change_history(states, at_s)
        ):
            q = _query_rule(process)
            actions.append(("ISSUE_QUERY", str((q or {}).get("query_id", "gateway_state_summary"))))
        actions.append(("WAIT", None))

        for action, arg in actions:
            child_states: dict[str, LocalState] = {}
            next_t = at_s
            if action == "WAIT":
                nt = _next_time(lattice, at_s, states)
                if nt is None:
                    continue
                child_states = dict(states)
                next_t = nt

            elif action == "ISSUE_QUERY":
                for wid, st in states.items():
                    world = wm[wid]
                    proc_world = pm[wid]
                    window = _matching_terrestrial_window(world, st, at_s)
                    reachable = window is not None
                    used = st.terrestrial_used
                    if window is not None:
                        used = _with_used(st, str(window["window_id"]))
                    payload = _query_payload(process, proc_world, st, at_s) if reachable else None
                    q = _query_rule(process)
                    qid = str((q or {}).get("query_id", "gateway_state_summary"))
                    signature = (
                        f"query:{qid}="
                        + (jsonable(payload) if reachable else "__TIMEOUT__")
                    )
                    obs = signature + f":sampled@{at_s}"
                    arrive_delay = _query_response_delay(process) if reachable else _query_timeout_delay(process)
                    child_states[wid] = LocalState(
                        delivered=st.delivered,
                        terrestrial_used=used,
                        satellite_used=st.satellite_used,
                        satellite_budget=st.satellite_budget,
                        pending_query=PendingQuery(at_s + arrive_delay, obs),
                        last_query_signature=signature,
                        last_direct_signature=st.last_direct_signature,
                        pending_deliveries=st.pending_deliveries,
                    )
                next_t = at_s

            elif action == "SEND_TERR":
                oid = str(arg)
                for wid, st in states.items():
                    world = wm[wid]
                    window = _matching_terrestrial_window(world, st, at_s)
                    accepted = window is not None
                    used = st.terrestrial_used
                    if window is not None:
                        used = _with_used(st, str(window["window_id"]))
                    pd = PendingDelivery(
                        obligation_id=oid,
                        accepted=accepted,
                        gateway_receipt_at_s=(
                            at_s + _gateway_receipt_delay(process)
                            if accepted and _primary_generates_gateway_receipt(process)
                            else None
                        ),
                        final_ack_at_s=(at_s + _final_ack_delay(process) if accepted else None),
                        negative_observation_at_s=(None if accepted else at_s + _negative_observation_delay(process)),
                    )
                    child_states[wid] = LocalState(
                        delivered=st.delivered,
                        terrestrial_used=used,
                        satellite_used=st.satellite_used,
                        satellite_budget=st.satellite_budget,
                        pending_query=st.pending_query,
                        last_query_signature=st.last_query_signature,
                        last_direct_signature=st.last_direct_signature,
                        pending_deliveries=st.pending_deliveries + (pd,),
                    )
                next_t = at_s

            elif action == "SEND_SAT":
                oid = str(arg)
                for wid, st in states.items():
                    window = _matching_satellite_window(world_bundle, st, at_s)
                    if window is None:
                        raise ExactOracleError("SEND_SAT action lost its public window capacity")
                    pd = PendingDelivery(
                        obligation_id=oid,
                        accepted=True,
                        gateway_receipt_at_s=None,
                        final_ack_at_s=at_s + _satellite_completion_delay(process),
                        negative_observation_at_s=None,
                    )
                    child_states[wid] = LocalState(
                        delivered=st.delivered,
                        terrestrial_used=st.terrestrial_used,
                        satellite_used=_with_sat_used(st, str(window["window_id"])),
                        satellite_budget=st.satellite_budget - 1,
                        pending_query=st.pending_query,
                        last_query_signature=st.last_query_signature,
                        last_direct_signature=st.last_direct_signature,
                        pending_deliveries=st.pending_deliveries + (pd,),
                    )
                next_t = at_s
            else:
                continue

            ok, sub = rec(next_t, child_states)
            if ok:
                ans = (
                    True,
                    {
                        "time_s": at_s,
                        "action": action,
                        "arg": arg,
                        "worlds": sorted(states),
                        "subpolicy": sub,
                    },
                )
                memo[key] = ans
                return ans

        memo[key] = (False, None)
        return memo[key]

    try:
        solvable, policy = rec(start, initial)
        return {
            "mode": (
                "FULL_CURRENT_STATE"
                if force_full_current_state
                else "OBSERVATION_MATCHED_NO_PAID_QUERY"
                if disable_paid_query
                else "OBSERVATION_MATCHED_EXACT"
            ),
            "status": "EXACT",
            "solvable": solvable,
            "policy": policy,
            "memo_nodes": len(memo),
            "attempt_lattice_size": len(lattice),
            "scalarization_used": False,
        }
    except SearchLimitExceeded as exc:
        return {
            "mode": (
                "FULL_CURRENT_STATE"
                if force_full_current_state
                else "OBSERVATION_MATCHED_NO_PAID_QUERY"
                if disable_paid_query
                else "OBSERVATION_MATCHED_EXACT"
            ),
            "status": "SEARCH_LIMIT",
            "solvable": None,
            "policy": None,
            "memo_nodes": len(memo),
            "attempt_lattice_size": len(lattice),
            "scalarization_used": False,
            "reason": str(exc),
        }


def jsonable(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _full_current_state_signature(
    bundle: Mapping[str, Any],
    process: Mapping[str, Any],
    *,
    wid: str,
    state: LocalState,
    at_s: int,
) -> str:
    """Complete current state, excluding every not-yet-realized future transition."""

    proc_world = _process_map(process)[wid]
    return jsonable(
        {
            "gateway": gateway_snapshot(proc_world, at_s),
            "delivered": list(state.delivered),
            "pending_deliveries": [
                {
                    "obligation_id": d.obligation_id,
                    "accepted": d.accepted,
                    "gateway_receipt_at_s": d.gateway_receipt_at_s,
                    "final_ack_at_s": d.final_ack_at_s,
                    "negative_observation_at_s": d.negative_observation_at_s,
                    "gateway_receipt_seen": d.gateway_receipt_seen,
                }
                for d in state.pending_deliveries
            ],
            "pending_query": (
                None
                if state.pending_query is None
                else {"arrive_at_s": state.pending_query.arrive_at_s}
            ),
            "satellite_budget": state.satellite_budget,
            "terrestrial_used": list(state.terrestrial_used),
            "satellite_used": list(state.satellite_used),
        }
    )


def reference_labels(
    world_bundle: Mapping[str, Any],
    process: Mapping[str, Any] | None = None,
    *,
    max_memo_nodes: int = 200_000,
) -> dict[str, Any]:
    process = attach_causal_evidence(world_bundle) if process is None else process
    physical = hindsight_bundle_reference(world_bundle)
    full_current = solve_observation_matched(
        world_bundle,
        process,
        disable_paid_query=True,
        force_full_current_state=True,
        max_memo_nodes=max_memo_nodes,
    )
    exact = solve_observation_matched(
        world_bundle,
        process,
        disable_paid_query=False,
        max_memo_nodes=max_memo_nodes,
    )
    no_query = solve_observation_matched(
        world_bundle,
        process,
        disable_paid_query=True,
        max_memo_nodes=max_memo_nodes,
    )
    return {
        "schema_version": "0.1",
        "bundle_id": str(world_bundle["bundle_id"]),
        "hindsight_physical": physical,
        "full_current_state": full_current,
        "observation_matched_exact": exact,
        "observation_matched_no_paid_query": no_query,
        "release_status": "NOT_BENCHMARK_ADMIT",
    }
