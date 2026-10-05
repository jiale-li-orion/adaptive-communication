#!/usr/bin/env python3
"""Small-instance reference for preserving causal future choices.

This is deliberately an expensive exact reference, not a new fast planner.
It distinguishes per-world possible rescue from a common contingent policy.
"""
from __future__ import annotations

from dynamic_scenario_tree_v0_5 import Bundle, LocalState, _actions, _normalize
from frontier_guided_planner_v0_5 import solve_frontier_guided


def continuation_frontier(bundle: Bundle, at_s: int,
                          states: dict[str, LocalState], *, max_queries: int = 2,
                          include_actions: bool = False) -> dict:
    """Minimum worst-branch acquisition count, up to an explicit search limit.

    None means no winning policy within max_queries, not unbounded
    impossibility. Certificate validity is this complete history/state only;
    there is no unsupported cross-event cache reuse.
    """
    norm = _normalize(bundle, at_s, states)
    if len(norm) != 1:
        raise ValueError('split by received observations before certifying a history')
    states = next(iter(norm.values()))
    memo_nodes = 0
    solves = 0

    def minimum(action=None):
        nonlocal memo_nodes, solves
        for budget in range(max_queries + 1):
            r = solve_frontier_guided(bundle, start_at_s=at_s,
                                     initial_states=states, query_budget=budget,
                                     forced_first_action=action)
            memo_nodes += r['memo_nodes']
            solves += 1
            if r['solvable']:
                return budget
        return None

    required = minimum()
    actions = []
    if include_actions:
        for action in _actions(bundle, at_s, states):
            needed = minimum(action)
            actions.append({'action': action, 'minimum_future_queries': needed,
                            'winning_within_budget': needed is not None})
    return {'at_s': at_s, 'compatible_worlds': sorted(states),
            'query_search_limit': max_queries,
            'minimum_future_queries': required,
            'can_stop_acquiring': required == 0,
            'action_frontier': actions,
            'exact_solves': solves, 'memo_nodes': memo_nodes,
            'scope': 'exact reached history; full rebuild after every event'}
