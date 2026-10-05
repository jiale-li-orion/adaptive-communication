#!/usr/bin/env python3
"""Exact resource-conditioned causal continuation reference for v0.5.

This object separates two stopping questions:
1. can we stop paid acquisition and still preserve task completion?
2. even if completion is already secured, can more evidence reduce rescue use?

It is intentionally an expensive reference used to define the target frontier
for a future incremental algorithm.
"""
from __future__ import annotations

from typing import Any

import dynamic_scenario_tree_v0_5 as tree
from receipt_cost_frontier_v0_5 import exact_cost_frontier


def _points(result:dict[str,Any]) -> list[tuple[int,int]]:
    return [(int(x['remote_queries']),int(x['satellite_sends'])) for x in result['points']]


def continuation_resource_frontier(bundle:tree.Bundle,at_s:int,
                                   states:dict[str,tree.LocalState],*,
                                   max_queries_per_world:int=2,
                                   include_actions:bool=False) -> dict[str,Any]:
    base=exact_cost_frontier(
        bundle,start_at_s=at_s,initial_states=states,
        max_queries_per_world=max_queries_per_world)
    pts=_points(base)
    stop_pts=[p for p in pts if p[0]==0]
    min_q=min((p[0] for p in pts),default=None)
    min_sat=min((p[1] for p in pts),default=None)
    min_sat_stop=min((p[1] for p in stop_pts),default=None)
    query_can_reduce_rescue=(
        min_sat is not None and min_sat_stop is not None and min_sat < min_sat_stop)

    actions=[]
    if include_actions:
        norm=tree._normalize(bundle,at_s,states)
        if len(norm)!=1 or next(iter(norm))!='same':
            raise ValueError('split received observations before action certification')
        normalized=next(iter(norm.values()))
        for action in tree._actions(bundle,at_s,normalized):
            r=exact_cost_frontier(
                bundle,start_at_s=at_s,initial_states=normalized,
                max_queries_per_world=max_queries_per_world,
                forced_first_action=action)
            actions.append({
                'action':action,
                'solvable':r['solvable'],
                'pareto':_points(r),
            })

    return {
        'at_s':at_s,
        'compatible_worlds':sorted(states),
        'pareto':pts,
        'minimum_aggregate_future_queries':min_q,
        'minimum_aggregate_future_satellite_sends':min_sat,
        'can_stop_acquiring':bool(stop_pts),
        'satellite_sends_if_stop_best':min_sat_stop,
        'query_can_reduce_rescue':query_can_reduce_rescue,
        'action_frontier':actions,
        'memo_states':base['memo_states'],
        'scope':'exact reached-history reference; aggregate costs over compatible worlds',
    }
