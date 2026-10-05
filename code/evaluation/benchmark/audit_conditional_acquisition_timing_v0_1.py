#!/usr/bin/env python3
"""Acquisition-timing frontier along an exact minimal-resource policy prefix.

For each frozen retry-review bundle, follow the exact minimal-(Q,B) policy until
its first paid query.  At every pre-query decision time where a query is legal,
force that single query and ask whether exact continuation succeeds with zero
additional queries.  This measures when evidence can be acquired without
destroying future feasibility.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from causal_evidence_process_v0_1 import attach_causal_evidence
from continuation_resource_domains_v0_1 import ContinuationPlanner, verify_witness
from exact_reference_oracle_v0_1 import LocalState, _attempt_lattice
from v8_policy_baselines_v0_1 import _legal_actions, _normalize_one, _step


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUTS = ROOT / 'results/benchmark/layer1-retry-review-inputs.json'
DEFAULT_OUT = ROOT / 'results/benchmark/layer2-conditional-acquisition-timing-v0.1.json'
QUERY = ('ISSUE_QUERY', 'gateway_state_summary')


def _initial(bundle, b):
    return {str(w['world_id']): LocalState(satellite_budget=b) for w in bundle['worlds']}


def _minimal_policy(bundle, max_expansions):
    start = min(_attempt_lattice(bundle))
    planner = ContinuationPlanner(bundle, mode='witness_domain')
    for q in range(len(bundle['obligations']) + 1):
        for b in range(int(bundle['public_environment']['satellite_budget_units']) + 1):
            result = planner.solve(start, _initial(bundle, b), query_budget=q, max_expansions=max_expansions)
            if result['solvable'] is True:
                return q, b, result
    return None


def _is_disconnected(legal_times, sufficient_times):
    if len(sufficient_times) < 2:
        return False
    positions = [legal_times.index(t) for t in sufficient_times]
    return any(b - a > 1 for a, b in zip(positions, positions[1:]))


def _run_case(bundle, max_expansions):
    chosen = _minimal_policy(bundle, max_expansions)
    if chosen is None:
        return {'classification': 'UNSOLVABLE_IN_BOUNDED_RECTANGLE'}
    q, b, solved = chosen
    start = min(_attempt_lattice(bundle))
    if q == 0:
        return {
            'classification': 'STOP_FROM_INITIAL_BOUNDARY',
            'minimal_resource_point': [q, b],
            'exact_query_time_s': None,
            'legal_query_times_s': [],
            'sufficient_query_times_s': [],
            'no_query_feasible_before_first_query': True,
        }

    process = attach_causal_evidence(bundle)
    states = _initial(bundle, b)
    at_s = start
    node = solved['policy']
    no_query_planner = ContinuationPlanner(bundle, mode='witness_domain')
    legal_times = []
    sufficient = []
    forced_rows = []
    exact_query_time = None
    prequery_noquery_flags = []
    steps = 0

    while node and not node.get('terminal') and steps < 512:
        branches = _normalize_one(bundle, process, at_s, states)
        if len(branches) != 1 or next(iter(branches)) != 'same':
            break
        states = next(iter(branches.values()))

        no_query_now = no_query_planner.solve(
            at_s, dict(states), query_budget=0, max_expansions=max_expansions,
        )
        prequery_noquery_flags.append({
            'time_s': at_s,
            'solvable': no_query_now['solvable'],
            'status': no_query_now['status'],
        })

        actions = _legal_actions(bundle, process, states, at_s)
        if QUERY in actions:
            legal_times.append(at_s)
            stepped = _step(bundle, process, states, at_s, QUERY)
            assert stepped is not None
            child, next_t = stepped
            continuation = no_query_planner.solve(
                next_t, child, query_budget=0, max_expansions=max_expansions,
            )
            row = {
                'time_s': at_s,
                'status': continuation['status'],
                'solvable_after_forcing_one_query': continuation['solvable'],
                'requirement_after_query': continuation['requirement'],
                'metrics': continuation['metrics'],
            }
            if continuation['solvable'] is True:
                actual = verify_witness(
                    bundle, next_t, child, continuation['policy'], query_budget=0,
                )
                row['replay_requirement_after_query'] = actual
                sufficient.append(at_s)
            forced_rows.append(row)

        if node.get('action') == 'ISSUE_QUERY':
            exact_query_time = at_s
            break
        stepped = _step(bundle, process, states, at_s, (node['action'], node['arg']))
        if stepped is None:
            break
        states, at_s = stepped
        node = node['subpolicy']
        steps += 1

    noquery_before = all(x['solvable'] is False for x in prequery_noquery_flags)
    disconnected = _is_disconnected(legal_times, sufficient)
    if not sufficient:
        timing_class = 'NO_SUFFICIENT_FORCED_QUERY_TIME_FOUND'
    elif disconnected:
        timing_class = 'DISCONNECTED_SUFFICIENT_QUERY_TIMES'
    elif len(sufficient) == 1:
        timing_class = 'SINGLE_CRITICAL_QUERY_TIME'
    else:
        timing_class = 'CONTIGUOUS_QUERY_WINDOW'

    return {
        'classification': timing_class,
        'minimal_resource_point': [q, b],
        'exact_query_time_s': exact_query_time,
        'legal_query_times_s': legal_times,
        'sufficient_query_times_s': sufficient,
        'earliest_sufficient_query_time_s': min(sufficient) if sufficient else None,
        'latest_sufficient_query_time_s': max(sufficient) if sufficient else None,
        'exact_query_is_latest_sufficient': bool(sufficient and exact_query_time == max(sufficient)),
        'no_query_feasible_before_first_query': not noquery_before,
        'no_query_infeasible_at_every_prequery_prefix': noquery_before,
        'forced_query_checks': forced_rows,
        'prequery_noquery_checks': prequery_noquery_flags,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--inputs', type=Path, default=DEFAULT_INPUTS)
    ap.add_argument('--out', type=Path, default=DEFAULT_OUT)
    ap.add_argument('--max-expansions', type=int, default=200_000)
    args = ap.parse_args()
    frozen = json.loads(args.inputs.read_text(encoding='utf-8'))
    rows = []
    classes = Counter()
    all_exact_latest = True
    for index, source_row in enumerate(frozen['rows']):
        bundle = source_row['bundle']
        result = _run_case(bundle, args.max_expansions)
        classes[result['classification']] += 1
        if result.get('exact_query_time_s') is not None:
            all_exact_latest = all_exact_latest and result.get('exact_query_is_latest_sufficient', False)
        rows.append({
            'index': index,
            'signature': source_row['signature'],
            'recipe_id': bundle['recipe_id'],
            'process': bundle['public_environment']['terrestrial_process_class'],
            'result': result,
        })
        print(index + 1, source_row['signature'][:12], result['classification'],
              result.get('exact_query_time_s'), result.get('sufficient_query_times_s'), flush=True)

    artifact = {
        'schema_version': '0.1',
        'status': 'CONDITIONAL_ACQUISITION_TIMING_DIAGNOSTIC',
        'inputs_ref': str(args.inputs.relative_to(ROOT)),
        'inputs_sha256': sha256(args.inputs.read_bytes()).hexdigest(),
        'classification_count': dict(sorted(classes.items())),
        'all_evidence_required_cases_query_at_latest_sufficient_time': all_exact_latest,
        'rows': rows,
        'rules': [
            'Only decision times on the exact minimal-resource policy prefix before its first query are tested.',
            'A forced query is sufficient only if exact continuation with zero additional queries succeeds and the returned witness replays.',
            'Query legality and query sufficiency are different: a legal query can consume capacity and destroy future feasibility.',
            'Disconnected sufficient query times are allowed; no monotone-in-time acquisition assumption is imposed.',
        ],
        'claim_boundary': [
            'This diagnoses timing structure on twelve preselected bundles; it is not a frequency estimate for the regenerated universe.',
            'The result conditions on the current no-duplicate-completion receiver contract and repaired retry legality.',
            'The exact policy action ordering is ordinary-execution-first; latest-sufficient behavior is an observed property, not a theorem yet.',
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({
        'classification_count': artifact['classification_count'],
        'all_evidence_required_cases_query_at_latest_sufficient_time': all_exact_latest,
        'out': str(args.out),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
