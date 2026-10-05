#!/usr/bin/env python3
"""Bounded semantic review, NOT a replacement exact-label generator.

Runs the production solver and two explicit action-mask interventions on frozen
inputs. No production module is mutated. A separate physical replay validates
every positive no-query witness, including capacity costs and duplicate count.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import inspect
import json
from pathlib import Path

import exact_reference_oracle_v0_1 as oracle
from causal_evidence_process_v0_1 import FINAL_ACK_DELAY_S, SATELLITE_COMPLETION_DELAY_S
from execution_trace_evaluator_v0_1 import evaluate_execution_trace

ROOT = Path(__file__).resolve().parents[3]


def retry_eligible(bundle, states, at_s):
    return [str(o['obligation_id']) for o in bundle['obligations']
            if int(o['release_s']) <= at_s <= int(o['deadline_s'])
            and not all(str(o['obligation_id']) in st.delivered for st in states.values())
            and not any(str(o['obligation_id']) in oracle._pending_oids(st) for st in states.values())]


def historical_eligible(bundle, states, at_s):
    """The pre-review mask, retained explicitly rather than as a moving baseline."""
    return [str(o['obligation_id']) for o in bundle['obligations']
            if int(o['release_s']) <= at_s <= int(o['deadline_s'])
            and not any(str(o['obligation_id']) in st.delivered or
                        str(o['obligation_id']) in oracle._pending_oids(st) for st in states.values())]


def diagnostic_solver(*, historical=False):
    """Isolated historical mask or alternate deduplicating-receiver contract.

    All other transition/search semantics remain the same. Production globals
    are never monkey-patched. Dedup is an ablation, not the production task.
    """
    source = inspect.getsource(oracle.solve_observation_matched)
    namespace = dict(vars(oracle))
    if source.count('_delivery_retry_allowed(') != 2:
        raise RuntimeError('Solver changed: independently review the diagnostic intervention')
    namespace['_active_common_obligations'] = historical_eligible if historical else retry_eligible
    namespace['_delivery_retry_allowed'] = lambda *args: True
    exec(compile(source, '<explicit-retry-mask-intervention>', 'exec'), namespace)
    return namespace['solve_observation_matched']


def minimal_witness():
    return {
        'stage': 'WORLD_BUNDLE_PRE_EVIDENCE_PRE_ORACLE',
        'bundle_id': 'retry-mask-witness', 'recipe_id': 'retry-mask-witness',
        'obligations': [{'obligation_id': 'o', 'release_s': 0, 'deadline_s': 200,
                         'protected_subject': 'report'}],
        'public_environment': {'horizon_s': 200, 'satellite_windows': [], 'satellite_budget_units': 0},
        'worlds': [
            {'world_id': 'A', 'terrestrial_windows': [{'window_id': 'A0', 'start_s': 0, 'end_s': 90, 'capacity_units': 2}]},
            {'world_id': 'B', 'terrestrial_windows': [{'window_id': 'B0', 'start_s': 100, 'end_s': 190, 'capacity_units': 2}]},
        ],
        'observation_projection': {'evidence_regime': 'GATEWAY_SUMMARY_QUERY',
                                   'evidence_surfaces': [{'kind': 'OWNER_QUERY'}]},
    }


def replay_open_loop(bundle, policy, *, allow_duplicates):
    """Independent replay of fixed, no-observation policies across all worlds.

    Unaccepted sends remain attempts; accepted transmissions consume a unit.
    Delivery counts once using earliest completion. This does not reuse solver
    transition/matching helpers. Diagnostic query-only regimes have no ACKs.
    """
    actions = []
    while policy and not policy.get('terminal'):
        if 'event' in policy or policy.get('action') == 'ISSUE_QUERY':
            raise AssertionError('Expected a common open-loop no-query witness')
        if policy['action'] != 'WAIT':
            actions.append((int(policy['time_s']), policy['action'], policy['arg']))
        policy = policy['subpolicy']
    obligations = {o['obligation_id']: o for o in bundle['obligations']}
    outcomes = []
    for world in bundle['worlds']:
        used = Counter(); sat_used = 0; completed = {}; trace = []; duplicates = 0
        for at, kind, oid in actions:
            o = obligations[oid]
            assert int(o['release_s']) <= at <= int(o['deadline_s'])
            windows = world['terrestrial_windows'] if kind == 'SEND_TERR' else bundle['public_environment']['satellite_windows']
            eligible = [w for w in windows if int(w['start_s']) <= at < int(w['end_s']) and used[(kind, w['window_id'])] < int(w['capacity_units'])]
            if not eligible:
                assert kind == 'SEND_TERR', 'Satellite must have legal public capacity'
                continue
            w = min(eligible, key=lambda w: (int(w['end_s']), str(w['window_id'])))
            used[(kind, w['window_id'])] += 1
            if kind == 'SEND_SAT':
                sat_used += 1
                assert sat_used <= int(bundle['public_environment']['satellite_budget_units'])
            completion = at + (FINAL_ACK_DELAY_S if kind == 'SEND_TERR' else SATELLITE_COMPLETION_DELAY_S)
            assert completion <= int(o['deadline_s'])
            duplicates += int(oid in completed)
            completed[oid] = min(completed.get(oid, completion), completion)
            trace.append({'action': kind, 'obligation_id': oid, 'actor': 'communication_subsystem',
                          'resource_id': w['window_id'], 'at_s': at, 'protected_subject': o['protected_subject']})
        assert set(completed) == set(obligations)
        if not allow_duplicates:
            assert duplicates == 0
            assert evaluate_execution_trace(bundle, world_id=world['world_id'], actions=trace)['success']
        outcomes.append({'world_id': world['world_id'], 'duplicate_completions': duplicates,
                         'accepted_transmissions': len(trace), 'satellite_used': sat_used,
                         'completed_at_s': completed})
    return {'common_actions': actions, 'world_outcomes': outcomes}


def run_case(bundle, solvers):
    rows = {}
    for name, solver in solvers.items():
        result = solver(bundle, disable_paid_query=True, max_memo_nodes=50000)
        rows[name] = {k: result[k] for k in ('status', 'solvable', 'memo_nodes')}
        if result['solvable']:
            rows[name]['replay'] = replay_open_loop(bundle, result['policy'], allow_duplicates=(name == 'deduplicating_receiver'))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--inputs', type=Path, default=ROOT/'results/benchmark/layer1-retry-review-inputs.json')
    ap.add_argument('--out', type=Path, default=Path('/tmp/layer1-retry-review.json'))
    args = ap.parse_args()
    solvers = {'historical_mask': diagnostic_solver(historical=True),
               'duplicate_free_repair': oracle.solve_observation_matched,
               'deduplicating_receiver': diagnostic_solver()}
    witness = minimal_witness()
    micro = run_case(witness, solvers)
    assert micro['historical_mask']['solvable'] is False
    assert micro['duplicate_free_repair']['solvable'] is True
    assert oracle.solve_observation_matched(witness)['solvable'] is True
    # The ordinary V8 ladder must see the same repaired action set. At t=60
    # retry would duplicate A; at t=100 A rejects it and B can receive it.
    from v8_policy_baselines_v0_1 import _legal_actions
    from causal_evidence_process_v0_1 import attach_causal_evidence
    states = {'A': oracle.LocalState(delivered=('o',), terrestrial_used=(('A0', 1),)),
              'B': oracle.LocalState()}
    process = attach_causal_evidence(witness)
    assert ('SEND_TERR', 'o') not in _legal_actions(witness, process, states, 60)
    assert ('SEND_TERR', 'o') in _legal_actions(witness, process, states, 100)
    assert not oracle._delivery_retry_allowed(witness, states, 100, 'SEND_SAT', 'o')
    inputs = json.loads(args.inputs.read_text())
    rows = []
    for index, row in enumerate(inputs['rows']):
        result = run_case(row['bundle'], solvers)
        assert result['historical_mask']['status'] == 'EXACT' and result['historical_mask']['solvable'] is False
        rows.append({'signature': row['signature'], 'recipe_id': row['bundle']['recipe_id'],
                     'process': row['bundle']['public_environment']['terrestrial_process_class'], 'results': result})
        print(index + 1, {name: (r['status'], r['solvable']) for name, r in result.items()}, flush=True)
    output = {'status': 'DIAGNOSTIC_NOT_UNIVERSE_RELABEL',
              'inputs_sha256': sha256(args.inputs.read_bytes()).hexdigest(),
              'solver_sha256': sha256(Path(oracle.__file__).read_bytes()).hexdigest(),
              'selection': inputs['selection'], 'source_profile_sha256': inputs['source_profile_sha256'],
              'minimal_witness': micro, 'rows': rows,
              'solvable_counts': {name: sum(r['results'][name]['solvable'] is True for r in rows) for name in solvers}}
    args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(output['solvable_counts']), 'written', args.out)


if __name__ == '__main__':
    main()
