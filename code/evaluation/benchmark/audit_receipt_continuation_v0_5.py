#!/usr/bin/env python3
"""Bounded mechanism audit. stdout by default; no registered result overwrites."""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import dynamic_scenario_tree_v0_5 as tree
from frontier_guided_planner_v0_5 import solve_frontier_guided
from physical_admission_v0_5 import physical
from receipt_continuation_v0_5 import continuation_frontier
from receipt_reserve_baseline_v0_5 import PublicReceiptContract, solve_receipt_reserve
from scenario_generator_v0_5 import (build_receipt_race_bundle,
                                    build_overlapping_receipt_chain_bundle)


def public_contract(bundle):
    # These are fixture-declared schedules, not online reads of a realized world.
    # Validate that extracting their common template cannot reveal an outcome.
    times = {w.query_reachable_times for w in bundle.worlds}
    dispatch = {tuple((e.send_at_s, e.oid) for e in w.delivery_events)
                for w in bundle.worlds}
    assert len(times) == len(dispatch) == 1
    return PublicReceiptContract(bundle.obligations, next(iter(dispatch)),
                                 bundle.satellite_send_times, next(iter(times)),
                                 bundle.queries[0].query_id)


def oracle_summary(bundle, result):
    accounting = (tree.execution_accounting(bundle, result['policy'])
                  if result['solvable'] else None)
    if accounting:
        for row in accounting['per_world'].values():
            row['query_times_s'] = [event[1] for event in row.pop('trace')
                                    if event[0] == 'ACTION' and event[2] == 'ISSUE_QUERY']
    return {'solvable': result['solvable'], 'memo_nodes': result['memo_nodes'],
            'accounting': accounting}


def audit():
    race = build_receipt_race_bundle()
    chain = build_overlapping_receipt_chain_bundle()
    parent = build_overlapping_receipt_chain_bundle(include_all_failed=True)
    out = {'scope': 'mechanism fixture; not a method-performance claim',
           'support_contract': 'seven-world pilot assumes at least one terrestrial success',
           'cost_contract': 'query count and response latency only; no calibrated bytes/energy',
           'per_world_physical': {w.world_id: physical(chain, w) for w in chain.worlds},
           'parent_physical': {w.world_id: physical(parent, w) for w in parent.worlds},
           'parent_robust_solvable': solve_frontier_guided(parent)['solvable']}
    out['receipt_race_query_budget'] = {
        str(k): tree.solve(race, query_budget=k)['solvable'] for k in (0, 1)}
    out['chain_query_budget'] = {
        str(k): tree.solve(chain, query_budget=k)['solvable'] for k in (0, 1, 2)}
    out['plain_exact'] = oracle_summary(chain, tree.solve(chain))
    out['guided_exact'] = oracle_summary(chain, solve_frontier_guided(chain))
    contract = public_contract(chain)
    out['ordinary_baselines'] = {
        mode: solve_receipt_reserve(chain, contract, mode=mode)
        for mode in ('conditional', 'fixed-read', 'passive')}
    out['ordinary_baselines']['gateway_local'] = solve_receipt_reserve(
        chain, contract, gateway_local=True)

    t = chain.terrestrial_send_times[0]
    states = {w.world_id: tree.LocalState(sat_budget=chain.satellite_budget)
              for w in chain.worlds}
    children, t = tree._step_action(chain, t, states, ('SEND_TERR', 'A'))
    states = next(iter(tree._normalize(chain, t, children['same']).values()))
    children, _ = tree._step_action(chain, t, states, ('ISSUE_QUERY', 'receipt_summary'))
    t += chain.queries[0].response_delay_s
    branches = tree._normalize(chain, t, children['same'])
    out['after_first_receipt'] = {
        obs: continuation_frontier(chain, t, ch, max_queries=1, include_actions=True)
        for obs, ch in branches.items()}

    # Counterfactual environment, not an extra field or task: if the same final
    # ACK arrives before rescue, ordinary feedback removes the paid EvidenceNeed.
    ack_worlds = tuple(replace(w, delivery_events=tuple(
        replace(e, final_ack_at_s=e.gateway_receipt_at_s) if e.accepted else e
        for e in w.delivery_events)) for w in chain.worlds)
    out['early_final_ack_no_query'] = tree.solve(
        replace(chain, worlds=ack_worlds), query_budget=0)['solvable']
    # If the queried snapshot arrives after A's last rescue, perfect content
    # cannot restore a lost opportunity. All other fields remain fixed.
    late_query = replace(chain.queries[0], response_delay_s=3000)
    out['late_query_solvable'] = solve_frontier_guided(
        replace(chain, queries=(late_query,)))['solvable']
    here = Path(__file__).resolve().parent
    out['source_sha256'] = {
        name: hashlib.sha256((here/name).read_bytes()).hexdigest()
        for name in ('dynamic_scenario_tree_v0_5.py', 'scenario_generator_v0_5.py',
                     'receipt_continuation_v0_5.py', 'receipt_reserve_baseline_v0_5.py',
                     'frontier_guided_planner_v0_5.py', 'future_choice_frontier_v0_5.py',
                     'dynamic_feasibility_frontier_v0_5.py',
                     'audit_receipt_continuation_v0_5.py')}
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    payload = json.dumps(audit(), indent=2, sort_keys=True) + '\n'
    if args.output:
        args.output.write_text(payload)
        print(args.output)
    else:
        print(payload, end='')
