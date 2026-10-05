#!/usr/bin/env python3
"""Exact query--satellite Pareto reference for the v0.5 receipt process.

Task success is a hard constraint.  Costs are not scalarized.  For a single
non-anticipative policy we aggregate the actually executed remote receipt reads
and satellite sends over every declared world, matching the mechanism audit's
finite-support accounting.  The result is a small-instance reference oracle,
not the fast method.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import dynamic_scenario_tree_v0_5 as tree
from frontier_guided_planner_v0_5 import frontier_prefix_upper_bound


@dataclass(frozen=True, order=True)
class CostPoint:
    remote_queries: int
    satellite_sends: int


@dataclass(frozen=True)
class ParetoWitness:
    cost: CostPoint
    policy: dict[str, Any]


def _state_key(st: tree.LocalState):
    return (
        st.final_delivered, st.violated_obligations, st.gateway_received,
        st.pending_queries, st.pending_deliveries, st.seen_passive,
        st.next_request_seq, st.sat_budget,
    )


def _canon(states: dict[str, tree.LocalState]):
    return tuple(sorted((wid, _state_key(st)) for wid, st in states.items()))


def _pareto(rows: list[ParetoWitness]) -> tuple[ParetoWitness, ...]:
    best: dict[CostPoint, ParetoWitness] = {}
    for row in rows:
        best.setdefault(row.cost, row)
    pts = sorted(best)
    keep = []
    for p in pts:
        if any(q.remote_queries <= p.remote_queries
               and q.satellite_sends <= p.satellite_sends
               and q != p for q in pts):
            continue
        keep.append(best[p])
    return tuple(keep)


def _sum_children(children: list[tuple[str, dict[str, tree.LocalState], tuple[ParetoWitness, ...]]],
                  *, event_time: int) -> tuple[ParetoWitness, ...]:
    acc = [ParetoWitness(CostPoint(0, 0), {'terminal': True})]
    for obs, states, frontier in children:
        nxt = []
        for left in acc:
            for right in frontier:
                nxt.append(ParetoWitness(
                    CostPoint(left.cost.remote_queries + right.cost.remote_queries,
                              left.cost.satellite_sends + right.cost.satellite_sends),
                    {'time_s': event_time, 'event': 'OBSERVATION_COMBINATION',
                     'left': left.policy,
                     'right': {'observation': obs, 'worlds': sorted(states),
                               'subpolicy': right.policy}},
                ))
        acc = list(_pareto(nxt))
    return tuple(acc)


def exact_cost_frontier(bundle: tree.Bundle, *,
                        max_queries_per_world: int | None = None,
                        use_safe_upper_bound: bool = True) -> dict[str, Any]:
    """Return every non-dominated successful aggregate cost point.

    max_queries_per_world is only a search guard.  For the current receipt
    fixtures it can be set to the number of useful read opportunities.  A None
    value leaves the search unbounded except by the finite event process.
    """
    start = min(bundle.fixed_event_times)
    initial = {w.world_id: tree.LocalState(sat_budget=bundle.satellite_budget)
               for w in bundle.worlds}
    memo: dict[Any, tuple[ParetoWitness, ...]] = {}
    calls = 0

    def rec(t: int, states: dict[str, tree.LocalState]) -> tuple[ParetoWitness, ...]:
        nonlocal calls
        calls += 1
        norm = tree._normalize(bundle, t, states)
        if len(norm) > 1 or next(iter(norm)) != 'same':
            children = []
            for obs, ch in sorted(norm.items()):
                fr = rec(t, ch)
                if not fr:
                    return ()
                children.append((obs, ch, fr))
            return _sum_children(children, event_time=t)
        states = next(iter(norm.values()))

        if any(tree._expired(bundle, st, t) for st in states.values()):
            return ()
        if all(tree._success(bundle, st) for st in states.values()):
            return (ParetoWitness(CostPoint(0, 0), {'terminal': True}),)
        if use_safe_upper_bound and not frontier_prefix_upper_bound(bundle, t, states):
            return ()

        key = (t, _canon(states))
        if key in memo:
            return memo[key]

        rows: list[ParetoWitness] = []
        actions = tree._actions(bundle, t, states)
        filtered = []
        for action in actions:
            if action[0] == 'ISSUE_QUERY':
                if not tree._query_partitions(bundle, t, states, str(action[1])):
                    continue
                if max_queries_per_world is not None:
                    if any(st.next_request_seq >= max_queries_per_world for st in states.values()):
                        continue
            filtered.append(action)

        for action in filtered:
            stepped = tree._step_action(bundle, t, states, action)
            if stepped is None:
                continue
            branches, nt = stepped
            branch_rows = []
            valid = True
            for obs, ch in sorted(branches.items()):
                fr = rec(nt, ch)
                if not fr:
                    valid = False
                    break
                branch_rows.append((obs, ch, fr))
            if not valid:
                continue
            children = _sum_children(branch_rows, event_time=nt)
            dq = len(states) if action[0] == 'ISSUE_QUERY' else 0
            ds = len(states) if action[0] == 'SEND_SAT' else 0
            for child in children:
                rows.append(ParetoWitness(
                    CostPoint(child.cost.remote_queries + dq,
                              child.cost.satellite_sends + ds),
                    {'time_s': t, 'action': action[0], 'arg': action[1],
                     'children': child.policy},
                ))
        ans = _pareto(rows)
        memo[key] = ans
        return ans

    frontier = rec(start, initial)
    return {
        'solvable': bool(frontier),
        'points': [
            {'remote_queries': row.cost.remote_queries,
             'satellite_sends': row.cost.satellite_sends}
            for row in frontier
        ],
        'witnesses': frontier,
        'memo_states': len(memo),
        'recursive_calls': calls,
        'accounting': 'sum over declared worlds; success required in every world',
    }
