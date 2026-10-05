#!/usr/bin/env python3
"""Exact bounded conditional continuation frontier over query/satellite budgets.

This is a Layer-2 context object.  It summarizes which resource conditions
still support a causal continuation and whether paid evidence changes
feasibility or only resource use.  It does not change Layer-1 labels.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

from continuation_resource_domains_v0_1 import ContinuationPlanner, verify_witness
from exact_reference_oracle_v0_1 import LocalState, _attempt_lattice


def _initial_states(bundle: Mapping[str, Any], satellite_budget: int) -> dict[str, LocalState]:
    return {
        str(world['world_id']): LocalState(satellite_budget=satellite_budget)
        for world in bundle['worlds']
    }


def _pareto_minimal(points: list[tuple[int, int]]) -> list[tuple[int, int]]:
    out = []
    for q, b in sorted(set(points)):
        if any(q2 <= q and b2 <= b and (q2 < q or b2 < b) for q2, b2 in points):
            continue
        out.append((q, b))
    return out


def build_conditional_frontier(
    bundle: Mapping[str, Any],
    *,
    max_query_budget: int | None = None,
    max_satellite_budget: int | None = None,
    max_expansions: int = 200_000,
) -> dict[str, Any]:
    qmax = len(bundle['obligations']) if max_query_budget is None else int(max_query_budget)
    bmax = (
        int(bundle['public_environment']['satellite_budget_units'])
        if max_satellite_budget is None else int(max_satellite_budget)
    )
    if qmax < 0 or bmax < 0:
        raise ValueError('negative frontier bound')

    planner = ContinuationPlanner(bundle, mode='witness_domain')
    start = min(_attempt_lattice(bundle))
    cells = []
    feasible_points = []
    witness_by_point = {}
    for q in range(qmax + 1):
        for b in range(bmax + 1):
            states = _initial_states(bundle, b)
            result = planner.solve(start, states, query_budget=q, max_expansions=max_expansions)
            row = {
                'query_budget': q,
                'satellite_budget': b,
                'status': result['status'],
                'solvable': result['solvable'],
                'witness_requirement': result['requirement'],
                'metrics': result['metrics'],
            }
            if result['solvable'] is True:
                actual = verify_witness(bundle, start, states, result['policy'], query_budget=q)
                row['replay_requirement'] = actual
                row['policy_sha256'] = sha256(
                    json.dumps(result['policy'], sort_keys=True).encode()
                ).hexdigest()
                feasible_points.append((q, b))
                witness_by_point[(q, b)] = {
                    'requirement': actual,
                    'policy_sha256': row['policy_sha256'],
                }
            cells.append(row)

    pareto = _pareto_minimal(feasible_points)
    no_query_sat = min((b for q, b in feasible_points if q == 0), default=None)
    any_sat = min((b for _q, b in feasible_points), default=None)
    min_query = min((q for q, _b in feasible_points), default=None)

    if not feasible_points:
        gain_type = 'UNSOLVABLE_IN_BOUNDED_RECTANGLE'
        can_stop = None
        sat_release = None
    elif no_query_sat is None:
        gain_type = 'INFORMATION_FEASIBILITY_GAIN'
        can_stop = False
        sat_release = None
    elif any_sat is not None and any_sat < no_query_sat:
        gain_type = 'INFORMATION_RESOURCE_GAIN'
        can_stop = True
        sat_release = no_query_sat - any_sat
    else:
        gain_type = 'NO_INFORMATION_GAIN_IN_Q_B_RECTANGLE'
        can_stop = True
        sat_release = 0

    frontier_rows = []
    for q, b in pareto:
        witness = witness_by_point[(q, b)]
        frontier_rows.append({
            'query_budget': q,
            'satellite_budget': b,
            'certified_witness_requirement': witness['requirement'],
            'policy_sha256': witness['policy_sha256'],
            'validity_domain': {
                'query_budget_at_least': witness['requirement'][0],
                'satellite_budget_at_least': witness['requirement'][1],
                'boundary_condition': 'same causal execution/evidence boundary; later reuse requires certificate validation',
            },
        })

    return {
        'schema_version': '0.1',
        'status': 'EXACT_BOUNDED_CONDITIONAL_FRONTIER',
        'bundle_id': bundle['bundle_id'],
        'recipe_id': bundle['recipe_id'],
        'resource_rectangle': {
            'query_budget': [0, qmax],
            'satellite_budget': [0, bmax],
        },
        'frontier_points': frontier_rows,
        'evidence_gain_type': gain_type,
        'context': {
            'can_stop_acquiring_for_feasibility': can_stop,
            'minimum_query_budget_for_any_success': min_query,
            'minimum_satellite_budget_without_paid_query': no_query_sat,
            'minimum_satellite_budget_with_query_allowed': any_sat,
            'satellite_budget_released_by_allowing_query': sat_release,
            'completeness': 'complete over the declared integer Q/B rectangle only',
        },
        'cells': cells,
        'rules': [
            'Q is an analysis/selection bound, not a source SLA.',
            'Every positive frontier witness is replayed in its target resource cell.',
            'Feasibility gain and resource gain are reported separately; no weighted scalar reward is introduced.',
            'A query-free feasible point means evidence acquisition can stop for feasibility, not that more evidence can never improve another unmodeled cost.',
        ],
    }
