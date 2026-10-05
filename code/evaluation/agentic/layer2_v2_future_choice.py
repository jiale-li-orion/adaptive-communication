#!/usr/bin/env python3
"""Layer-2 v2 future-choice controller for Layer-1 v0.2.

This is the corrected L/U design retained by ``cache06.md``:

* ``U=0`` comes from a cheap optimistic residual-feasibility relaxation.  A
  false upper bound is a sound impossibility proof; a true upper bound is only
  unresolved.
* ``L=1`` comes from a replayable structural causal continuation.  Failure to
  find such a continuation never proves impossibility.
* unresolved states fall back to the exact same-information continuation
  search, but the fallback uses the same U/L structure internally and returns
  one complete causal witness that is carried through later execution instead
  of recomputing a proof for every action at every boundary.

The module is evaluation/method code only.  It does not modify Layer-1 task,
transition, evidence or oracle semantics.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Mapping

from causal_evidence_process_v0_1 import attach_causal_evidence
from exact_reference_oracle_v0_1 import (
    FINAL_ACK_DELAY_S,
    SATELLITE_COMPLETION_DELAY_S,
    LocalState,
    _attempt_lattice,
    _expired,
    _next_time,
    _normalize,
    _success,
    _world_map,
)
from layer1_v02_exact_continuation import replay_continuation_policy
from v8_policy_baselines_v0_1 import _legal_actions, _step


Action = tuple[str, str | None]


def action_key(action: Action) -> str:
    return f"{action[0]}:{action[1] if action[1] is not None else '-'}"


def _secured_obligations(bundle: Mapping[str, Any], state: LocalState) -> set[str]:
    secured = set(state.delivered)
    for pending in state.pending_deliveries:
        if not pending.accepted or pending.final_ack_at_s is None:
            continue
        deadline = next(
            int(row["deadline_s"])
            for row in bundle["obligations"]
            if str(row["obligation_id"]) == pending.obligation_id
        )
        if pending.final_ack_at_s <= deadline:
            secured.add(pending.obligation_id)
    return secured


def _world_residual_feasible(
    bundle: Mapping[str, Any],
    *,
    at_s: int,
    world_id: str,
    state: LocalState,
    world_map: Mapping[str, Any] | None = None,
    compiled_windows: Mapping[str, Any] | None = None,
    eligibility: Mapping[Any, Any] | None = None,
) -> bool:
    """Optimistic per-world max-flow relaxation used only as an upper bound."""

    if _expired(bundle, state, at_s):
        return False
    secured = _secured_obligations(bundle, state)
    obligations = [
        row for row in bundle["obligations"]
        if str(row["obligation_id"]) not in secured
    ]
    if not obligations:
        return True

    world = (world_map if world_map is not None else _world_map(bundle))[world_id]
    terr_used = dict(state.terrestrial_used)
    sat_used = dict(state.satellite_used)
    # Cheap optimistic relaxation.  U only needs to be sound when it returns
    # False; it does not need to solve the per-world matching problem exactly.
    # We therefore keep only necessary conditions: every unresolved obligation
    # must have at least one remaining feasible communication token, the total
    # number of residual tokens must cover the unresolved count, and the usable
    # satellite-token count cannot exceed the remaining satellite budget.
    if eligibility is not None and (world_id, at_s) in eligibility:
        candidates: dict[str, list[tuple[str, str, int]]] = {}
        for obligation in obligations:
            oid = str(obligation["obligation_id"])
            rows = []
            for kind, window_id, slot_index in eligibility[(world_id, at_s)][oid]:
                if kind == "T":
                    if slot_index < terr_used.get(window_id, 0):
                        continue
                else:
                    if slot_index < sat_used.get(window_id, 0):
                        continue
                rows.append((kind, window_id, slot_index))
            if not rows:
                return False
            candidates[oid] = rows

        order = sorted(candidates, key=lambda oid: (len(candidates[oid]), oid))
        used_slots: set[tuple[str, str, int]] = set()

        def fast_dfs(position: int, satellite_used_count: int) -> bool:
            if position == len(order):
                return True
            oid = order[position]
            for token in candidates[oid]:
                if token in used_slots:
                    continue
                kind = token[0]
                if kind == "S" and satellite_used_count >= max(0, state.satellite_budget):
                    continue
                used_slots.add(token)
                if fast_dfs(position + 1, satellite_used_count + int(kind == "S")):
                    return True
                used_slots.remove(token)
            return False

        return fast_dfs(0, 0)

    tokens: list[tuple[str, str, int, int, int]] = []
    terr_windows = (
        compiled_windows["terr"][world_id]
        if compiled_windows is not None
        else tuple(
            (
                str(window["window_id"]),
                int(window["start_s"]),
                int(window["end_s"]),
                int(window["capacity_units"]),
            )
            for window in world["terrestrial_windows"]
        )
    )
    sat_windows = (
        compiled_windows["sat"]
        if compiled_windows is not None
        else tuple(
            (
                str(window["window_id"]),
                int(window["start_s"]),
                int(window["end_s"]),
                int(window["capacity_units"]),
            )
            for window in bundle["public_environment"]["satellite_windows"]
        )
    )
    for wid, start, end, capacity in terr_windows:
        residual = max(0, capacity - terr_used.get(wid, 0))
        tokens.extend(
            ("T", wid, start, end, FINAL_ACK_DELAY_S)
            for _ in range(residual)
        )
    for wid, start, end, capacity in sat_windows:
        residual = max(0, capacity - sat_used.get(wid, 0))
        tokens.extend(
            ("S", wid, start, end, SATELLITE_COMPLETION_DELAY_S)
            for _ in range(residual)
        )

    candidates: dict[str, list[int]] = {}
    for obligation in obligations:
        oid = str(obligation["obligation_id"])
        candidates[oid] = [
            index
            for index, (_kind, _wid, start, end, delay) in enumerate(tokens)
            if (
                max(at_s, int(obligation["release_s"]), start) < end
                and max(at_s, int(obligation["release_s"]), start) + delay
                <= int(obligation["deadline_s"])
            )
        ]
        if not candidates[oid]:
            return False

    order = sorted(candidates, key=lambda oid: (len(candidates[oid]), oid))
    used: set[int] = set()

    def dfs(position: int, satellite_used_count: int) -> bool:
        if position == len(order):
            return True
        oid = order[position]
        for token_index in candidates[oid]:
            if token_index in used:
                continue
            kind = tokens[token_index][0]
            if kind == "S" and satellite_used_count >= max(0, state.satellite_budget):
                continue
            used.add(token_index)
            if dfs(position + 1, satellite_used_count + int(kind == "S")):
                return True
            used.remove(token_index)
        return False

    return dfs(0, 0)


def optimistic_upper(
    bundle: Mapping[str, Any],
    *,
    at_s: int,
    states: Mapping[str, LocalState],
    world_map: Mapping[str, Any] | None = None,
    compiled_windows: Mapping[str, Any] | None = None,
    eligibility: Mapping[Any, Any] | None = None,
) -> bool:
    """Sound U relaxation: every compatible world must remain physically feasible."""

    return all(
        _world_residual_feasible(
            bundle,
            at_s=at_s,
            world_id=wid,
            state=state,
            world_map=world_map,
            compiled_windows=compiled_windows,
            eligibility=eligibility,
        )
        for wid, state in states.items()
    )


def _same(states: Mapping[str, LocalState], attr: str):
    values = {getattr(state, attr) for state in states.values()}
    return next(iter(values)) if len(values) == 1 else None


def _common_resource_schedule(
    bundle: Mapping[str, Any],
    *,
    at_s: int,
    states: Mapping[str, LocalState],
) -> list[tuple[int, str, str]] | None:
    """Cheap lower certificate over opportunities common to the current support.

    The schedule uses only opportunities that are simultaneously valid in every
    compatible world, plus public satellite opportunities.  Therefore a found
    schedule is a robust causal lower certificate; failure is only UNKNOWN.
    """

    if not states:
        return None
    delivered = _same(states, "delivered")
    sat_used = _same(states, "satellite_used")
    if delivered is None or sat_used is None:
        return None
    # Pending deliveries may resolve differently and are handled by WAIT before
    # attempting to construct a static common schedule.
    if any(state.pending_query is not None or state.pending_deliveries for state in states.values()):
        return None

    obligations = [
        row for row in bundle["obligations"]
        if str(row["obligation_id"]) not in set(delivered)
    ]
    if not obligations:
        return []

    world_map = _world_map(bundle)
    world_ids = sorted(states)
    window_maps = [
        {str(row["window_id"]): row for row in world_map[wid]["terrestrial_windows"]}
        for wid in world_ids
    ]
    common_ids = set(window_maps[0])
    for mapping in window_maps[1:]:
        common_ids &= set(mapping)

    tokens: list[tuple[int, str, int]] = []
    for window_id in sorted(common_ids):
        rows = [mapping[window_id] for mapping in window_maps]
        starts = {int(row["start_s"]) for row in rows}
        ends = {int(row["end_s"]) for row in rows}
        if len(starts) != 1 or len(ends) != 1:
            continue
        send_at = max(at_s, next(iter(starts)))
        end = next(iter(ends))
        if send_at >= end:
            continue
        residual = min(
            int(row["capacity_units"])
            - dict(states[wid].terrestrial_used).get(window_id, 0)
            for wid, row in zip(world_ids, rows)
        )
        tokens.extend((send_at, "SEND_TERR", FINAL_ACK_DELAY_S) for _ in range(max(0, residual)))

    budgets = {state.satellite_budget for state in states.values()}
    if len(budgets) == 1:
        used = dict(sat_used)
        sat_tokens: list[tuple[int, str, int]] = []
        for window in bundle["public_environment"]["satellite_windows"]:
            wid = str(window["window_id"])
            send_at = max(at_s, int(window["start_s"]))
            if send_at >= int(window["end_s"]):
                continue
            residual = max(0, int(window["capacity_units"]) - used.get(wid, 0))
            sat_tokens.extend(
                (send_at, "SEND_SAT", SATELLITE_COMPLETION_DELAY_S)
                for _ in range(residual)
            )
        tokens.extend(sorted(sat_tokens)[: next(iter(budgets))])

    tokens.sort()
    candidates: dict[str, list[int]] = {}
    for obligation in obligations:
        oid = str(obligation["obligation_id"])
        candidates[oid] = [
            index
            for index, (send_at, _kind, delay) in enumerate(tokens)
            if int(obligation["release_s"]) <= send_at
            and send_at + delay <= int(obligation["deadline_s"])
        ]
        if not candidates[oid]:
            return None

    order = sorted(candidates, key=lambda oid: (len(candidates[oid]), oid))
    used_indices: set[int] = set()
    chosen: dict[str, int] = {}

    def dfs(index: int) -> bool:
        if index == len(order):
            return True
        oid = order[index]
        for token_index in candidates[oid]:
            if token_index in used_indices:
                continue
            used_indices.add(token_index)
            chosen[oid] = token_index
            if dfs(index + 1):
                return True
            used_indices.remove(token_index)
            chosen.pop(oid, None)
        return False

    if not dfs(0):
        return None
    return sorted((tokens[token][0], tokens[token][1], oid) for oid, token in chosen.items())


def common_opportunity_certificate(
    bundle: Mapping[str, Any],
    *,
    at_s: int,
    states: Mapping[str, LocalState],
    process: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Replayable L certificate using only common communication opportunities."""

    process = attach_causal_evidence(bundle) if process is None else process

    def rec(t: int, support: Mapping[str, LocalState]) -> dict[str, Any] | None:
        branches = _normalize(bundle, process, t, support)
        if len(branches) != 1 or next(iter(branches)) != "same":
            children = []
            for observation, child in sorted(branches.items()):
                sub = rec(t, child)
                if sub is None:
                    return None
                children.append(
                    {"observation": observation, "worlds": sorted(child), "subpolicy": sub}
                )
            return {"time_s": t, "event": "OBSERVATION", "children": children}

        support = next(iter(branches.values()))
        if any(_expired(bundle, state, t) for state in support.values()):
            return None
        if all(_success(bundle, state) for state in support.values()):
            return {"terminal": True}

        # Let already-issued asynchronous operations resolve before rebuilding
        # the residual schedule.  This keeps the lower certificate causal.
        if any(state.pending_query is not None or state.pending_deliveries for state in support.values()):
            stepped = _step(bundle, process, support, t, ("WAIT", None))
            if stepped is None:
                return None
            child, next_t = stepped
            sub = rec(next_t, child)
            return None if sub is None else {
                "time_s": t,
                "action": "WAIT",
                "arg": None,
                "worlds": sorted(support),
                "subpolicy": sub,
            }

        schedule = _common_resource_schedule(bundle, at_s=t, states=support)
        if schedule is None:
            return None
        if not schedule:
            return {"terminal": True} if all(_success(bundle, state) for state in support.values()) else None

        send_at, kind, oid = schedule[0]
        if send_at > t:
            stepped = _step(bundle, process, support, t, ("WAIT", None))
            if stepped is None:
                return None
            child, next_t = stepped
            sub = rec(next_t, child)
            return None if sub is None else {
                "time_s": t,
                "action": "WAIT",
                "arg": None,
                "worlds": sorted(support),
                "subpolicy": sub,
            }

        action: Action = (kind, oid)
        if action not in _legal_actions(bundle, process, support, t):
            return None
        stepped = _step(bundle, process, support, t, action)
        if stepped is None:
            return None
        child, next_t = stepped
        sub = rec(next_t, child)
        return None if sub is None else {
            "time_s": t,
            "action": action[0],
            "arg": action[1],
            "worlds": sorted(support),
            "subpolicy": sub,
        }

    return rec(at_s, dict(states))


@dataclass
class V2Metrics:
    expanded: int = 0
    memo_hits: int = 0
    upper_checks: int = 0
    upper_prunes: int = 0
    upper_skips: int = 0
    lower_attempts: int = 0
    lower_hits: int = 0
    lower_skips: int = 0
    exact_fallback_calls: int = 0
    wall_s: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


class FutureChoiceExactFallback:
    """Exact AND/OR fallback with structural L/U integrated into one search.

    Unlike the discarded prototype, this does not launch an independent proof
    search for each action.  One fallback search owns one memo, applies U before
    recursion, accepts a replayable L tail when available, and returns a single
    causal policy witness that can be carried through subsequent execution.
    """

    def __init__(
        self,
        bundle: Mapping[str, Any],
        *,
        upper_mode: str = "all_recursive",
        use_lower: bool = True,
    ):
        if upper_mode not in {"root_query", "query_recursive", "all_recursive", "none"}:
            raise ValueError(f"unsupported upper_mode: {upper_mode}")
        self.bundle = deepcopy(bundle)
        self.upper_mode = upper_mode
        self.use_lower = bool(use_lower)
        self.process = attach_causal_evidence(self.bundle)
        self.world_map = _world_map(self.bundle)
        self.compiled_windows = {
            "terr": {
                world_id: tuple(
                    (
                        str(window["window_id"]),
                        int(window["start_s"]),
                        int(window["end_s"]),
                        int(window["capacity_units"]),
                    )
                    for window in world["terrestrial_windows"]
                )
                for world_id, world in self.world_map.items()
            },
            "sat": tuple(
                (
                    str(window["window_id"]),
                    int(window["start_s"]),
                    int(window["end_s"]),
                    int(window["capacity_units"]),
                )
                for window in self.bundle["public_environment"]["satellite_windows"]
            ),
        }
        self.eligibility: dict[tuple[str, int], dict[str, tuple[tuple[str, str, int], ...]]] = {}
        obligations = tuple(self.bundle["obligations"])
        lattice = _attempt_lattice(self.bundle)
        for world_id, terr_windows in self.compiled_windows["terr"].items():
            for at_s in lattice:
                by_obligation: dict[str, tuple[tuple[str, str, int], ...]] = {}
                for obligation in obligations:
                    oid = str(obligation["obligation_id"])
                    release = int(obligation["release_s"])
                    deadline = int(obligation["deadline_s"])
                    rows: list[tuple[str, str, int]] = []
                    for window_id, start, end, capacity in terr_windows:
                        send_at = max(at_s, release, start)
                        if send_at < end and send_at + FINAL_ACK_DELAY_S <= deadline:
                            rows.extend(("T", window_id, slot) for slot in range(capacity))
                    for window_id, start, end, capacity in self.compiled_windows["sat"]:
                        send_at = max(at_s, release, start)
                        if send_at < end and send_at + SATELLITE_COMPLETION_DELAY_S <= deadline:
                            rows.extend(("S", window_id, slot) for slot in range(capacity))
                    by_obligation[oid] = tuple(rows)
                self.eligibility[(world_id, at_s)] = by_obligation
        self.memo: dict[Any, dict[str, Any] | None] = {}
        self.upper_memo: dict[Any, bool] = {}
        self.lower_memo: dict[Any, dict[str, Any] | None] = {}
        self.metrics = V2Metrics()

    def _should_check_upper(self, action: Action, *, apply_current_bounds: bool) -> bool:
        if self.upper_mode == "none":
            return False
        if self.upper_mode == "root_query":
            return apply_current_bounds and action[0] == "ISSUE_QUERY"
        if self.upper_mode == "query_recursive":
            return action[0] == "ISSUE_QUERY"
        return True

    @staticmethod
    def _canon(states: Mapping[str, LocalState]):
        return tuple(sorted(states.items()))

    def _rank_actions(
        self,
        at_s: int,
        states: Mapping[str, LocalState],
        actions: list[Action],
    ) -> list[Action]:
        deadlines = {
            str(row["obligation_id"]): int(row["deadline_s"])
            for row in self.bundle["obligations"]
        }
        preference = {"SEND_TERR": 0, "SEND_SAT": 1, "WAIT": 2, "ISSUE_QUERY": 3}

        def key(action: Action):
            oid = str(action[1]) if action[1] is not None else ""
            slack = deadlines.get(oid, 10**18) - at_s
            return (preference.get(action[0], 9), slack, repr(action))

        return sorted(actions, key=key)

    def solve(
        self,
        at_s: int,
        states: Mapping[str, LocalState],
        *,
        query_budget: int,
        max_expansions: int = 200_000,
    ) -> dict[str, Any]:
        before = V2Metrics(**self.metrics.as_dict())
        started = perf_counter()
        self.metrics.exact_fallback_calls += 1

        def rec(
            t: int,
            support: Mapping[str, LocalState],
            qleft: int,
            *,
            apply_current_bounds: bool,
        ) -> dict[str, Any] | None:
            branches = _normalize(self.bundle, self.process, t, support)
            if len(branches) != 1 or next(iter(branches)) != "same":
                children = []
                for observation, child in sorted(branches.items()):
                    sub = rec(
                        t,
                        child,
                        qleft,
                        apply_current_bounds=apply_current_bounds,
                    )
                    if sub is None:
                        return None
                    children.append(
                        {"observation": observation, "worlds": sorted(child), "subpolicy": sub}
                    )
                return {"time_s": t, "event": "OBSERVATION", "children": children}

            support = next(iter(branches.values()))
            key = (t, qleft, self._canon(support))
            if key in self.memo:
                self.metrics.memo_hits += 1
                # Policy nodes are immutable after construction in this solver;
                # returning the memoized object avoids copying an entire causal
                # subtree on every transposition hit.
                return self.memo[key]
            if any(_expired(self.bundle, state, t) for state in support.values()):
                self.memo[key] = None
                return None
            if all(_success(self.bundle, state) for state in support.values()):
                policy = {"terminal": True}
                self.memo[key] = policy
                return deepcopy(policy)

            # A static common-opportunity certificate is only plausible once
            # asynchronous operations have resolved and delivery state is common.
            # Skipping impossible attempts is an implementation optimization, not
            # a change in the L semantics: missed lower proofs remain UNKNOWN.
            can_try_lower = (
                self.use_lower
                and
                max(
                    (
                        sum(
                            str(row["obligation_id"])
                            not in _secured_obligations(self.bundle, state)
                            for row in self.bundle["obligations"]
                        )
                        for state in support.values()
                    ),
                    default=0,
                )
                <= 2
                and
                all(
                    state.pending_query is None and not state.pending_deliveries
                    for state in support.values()
                )
                and _same(support, "delivered") is not None
                and _same(support, "satellite_used") is not None
            )
            lower = None
            if can_try_lower:
                self.metrics.lower_attempts += 1
                lower_key = (t, self._canon(support))
                if lower_key in self.lower_memo:
                    lower = self.lower_memo[lower_key]
                else:
                    lower = common_opportunity_certificate(
                        self.bundle,
                        at_s=t,
                        states=support,
                        process=self.process,
                    )
                    self.lower_memo[lower_key] = lower
            else:
                self.metrics.lower_skips += 1
            if lower is not None:
                self.metrics.lower_hits += 1
                self.memo[key] = lower
                return lower

            if self.metrics.expanded - before.expanded >= max_expansions:
                raise RuntimeError(f"v2 fallback expansion limit {max_expansions}")
            self.metrics.expanded += 1

            actions = self._rank_actions(
                t,
                support,
                _legal_actions(self.bundle, self.process, support, t),
            )
            for action in actions:
                dq = int(action[0] == "ISSUE_QUERY")
                if dq > qleft:
                    continue
                stepped = _step(self.bundle, self.process, support, t, action)
                if stepped is None:
                    continue
                child, next_t = stepped
                if self._should_check_upper(action, apply_current_bounds=apply_current_bounds):
                    self.metrics.upper_checks += 1
                    upper_key = (next_t, self._canon(child))
                    if upper_key in self.upper_memo:
                        upper_ok = self.upper_memo[upper_key]
                    else:
                        upper_ok = optimistic_upper(
                            self.bundle,
                            at_s=next_t,
                            states=child,
                            world_map=self.world_map,
                            compiled_windows=self.compiled_windows,
                            eligibility=self.eligibility,
                        )
                        self.upper_memo[upper_key] = upper_ok
                    if not upper_ok:
                        self.metrics.upper_prunes += 1
                        continue
                else:
                    self.metrics.upper_skips += 1
                sub = rec(
                    next_t,
                    child,
                    qleft - dq,
                    apply_current_bounds=False,
                )
                if sub is None:
                    continue
                policy = {
                    "time_s": t,
                    "action": action[0],
                    "arg": action[1],
                    "worlds": sorted(support),
                    "subpolicy": sub,
                }
                self.memo[key] = policy
                return policy

            self.memo[key] = None
            return None

        try:
            policy = rec(
                at_s,
                dict(states),
                query_budget,
                apply_current_bounds=True,
            )
            status = "EXACT"
        except RuntimeError as exc:
            if "expansion limit" not in str(exc):
                raise
            policy = None
            status = "SEARCH_LIMIT"
        elapsed = perf_counter() - started
        self.metrics.wall_s += elapsed
        delta = {
            key: self.metrics.as_dict()[key] - before.as_dict()[key]
            for key in self.metrics.as_dict()
        }
        return {
            "status": status,
            "solvable": policy is not None if status == "EXACT" else None,
            "policy": policy,
            "metrics": delta,
            "memo_entries": len(self.memo),
        }


def future_choice_context(
    bundle: Mapping[str, Any],
    *,
    at_s: int,
    states: Mapping[str, LocalState],
    query_budget: int,
    witness_policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Materialize the model-facing L/U context without exposing hidden states."""

    process = attach_causal_evidence(bundle)
    normalized = _normalize(bundle, process, at_s, states)
    if len(normalized) != 1 or next(iter(normalized)) != "same":
        raise ValueError("future_choice_context requires a decision boundary")
    support = next(iter(normalized.values()))
    legal = _legal_actions(bundle, process, support, at_s)
    carried_action = None
    if witness_policy and witness_policy.get("action"):
        candidate = (str(witness_policy["action"]), witness_policy.get("arg"))
        if candidate in legal:
            carried_action = candidate

    rows = []
    for action in legal:
        dq = int(action[0] == "ISSUE_QUERY")
        if dq > query_budget:
            upper = 0
        else:
            stepped = _step(bundle, process, support, at_s, action)
            upper = int(
                stepped is not None
                and optimistic_upper(bundle, at_s=stepped[1], states=stepped[0])
            )
        lower = int(carried_action == action)
        rows.append(
            {
                "action_key": action_key(action),
                "lower": lower,
                "upper": upper,
                "status": "CERTIFIED" if lower else "IMPOSSIBLE" if not upper else "UNKNOWN",
            }
        )

    query = next((row for row in rows if row["action_key"] == "ISSUE_QUERY:gateway_state_summary"), None)
    labels: list[str] = []
    if query is not None and query["upper"] == 0:
        labels.append("QUERY_HARMFUL_NOW")
    if any(row["lower"] == 1 and not row["action_key"].startswith("ISSUE_QUERY:") for row in rows):
        labels.append("CAN_DEFER_QUERY")
    if carried_action is not None and carried_action[0] != "ISSUE_QUERY":
        labels.append("STOP_ACQUISITION_FOR_NOW")
    if not labels:
        labels.append("UNRESOLVED")
    return {
        "schema_version": "layer2-v2-future-choice-0.1",
        "time_s": at_s,
        "query_budget": query_budget,
        "labels": labels,
        "actions": rows,
        "hidden_state_exposed": False,
        "semantics": "L=1 replayable causal continuation; U=0 optimistic residual infeasibility",
    }


def solve_minimal_resource_v2(
    bundle: Mapping[str, Any],
    *,
    max_expansions: int = 200_000,
    upper_mode: str = "all_recursive",
    use_lower: bool = True,
) -> dict[str, Any]:
    """Find the minimum (paid-query, satellite-budget) point with the v2 solver."""

    from exact_reference_oracle_v0_1 import _attempt_lattice

    start = min(_attempt_lattice(bundle))
    max_sat = int(bundle["public_environment"]["satellite_budget_units"])
    aggregate = V2Metrics()
    tried = []
    # One solver owns the whole resource sweep.  Exact memo keys already include
    # query budget and full LocalState (including satellite budget), so reuse is
    # sound and avoids reconstructing identical residual subproblems.
    solver = FutureChoiceExactFallback(
        bundle,
        upper_mode=upper_mode,
        use_lower=use_lower,
    )
    for query_budget in range(len(bundle["obligations"]) + 1):
        for sat_budget in range(max_sat + 1):
            initial = {
                str(world["world_id"]): LocalState(satellite_budget=sat_budget)
                for world in bundle["worlds"]
            }
            before = V2Metrics(**solver.metrics.as_dict())
            result = solver.solve(
                start,
                initial,
                query_budget=query_budget,
                max_expansions=max_expansions,
            )
            after = solver.metrics.as_dict()
            metrics = {key: after[key] - before.as_dict()[key] for key in after}
            tried.append(
                {
                    "query_budget": query_budget,
                    "satellite_budget": sat_budget,
                    "status": result["status"],
                    "solvable": result["solvable"],
                    "metrics": metrics,
                }
            )
            for key, value in metrics.items():
                setattr(aggregate, key, getattr(aggregate, key) + value)
            if result["solvable"] is True:
                replay_continuation_policy(
                    bundle,
                    at_s=start,
                    states=initial,
                    policy=result["policy"],
                    query_budget=query_budget,
                )
                return {
                    "status": "EXACT",
                    "solvable": True,
                    "minimal_resource_point": [query_budget, sat_budget],
                    "policy": result["policy"],
                    "winning_metrics": metrics,
                    "aggregate_metrics": aggregate.as_dict(),
                    "tried": tried,
                }
    return {
        "status": "EXACT",
        "solvable": False,
        "minimal_resource_point": None,
        "policy": None,
        "aggregate_metrics": aggregate.as_dict(),
        "tried": tried,
    }
