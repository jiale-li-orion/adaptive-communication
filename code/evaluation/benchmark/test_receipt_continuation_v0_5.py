#!/usr/bin/env python3
"""Causal continuation witnesses, not assertions about winning method names."""
from dataclasses import replace

import dynamic_scenario_tree_v0_5 as tree
from scenario_generator_v0_5 import build_overlapping_receipt_chain_bundle


def first_receipt_prefix(bundle):
    t = bundle.terrestrial_send_times[0]
    states = {w.world_id: tree.LocalState(sat_budget=bundle.satellite_budget)
              for w in bundle.worlds}
    stepped, t = tree._step_action(bundle, t, states, ('SEND_TERR', 'A'))
    states = next(iter(tree._normalize(bundle, t, stepped['same']).values()))
    stepped, _ = tree._step_action(bundle, t, states, ('ISSUE_QUERY', 'receipt_summary'))
    t += bundle.queries[0].response_delay_s
    return t, tree._normalize(bundle, t, stepped['same'])


def main():
    import inspect
    assert 'query_budget' in inspect.signature(tree.solve).parameters, \
        'Missing causal continuation oracle with a per-branch acquisition budget'
    from receipt_continuation_v0_5 import continuation_frontier

    bundle = build_overlapping_receipt_chain_bundle()
    assert not tree.solve(bundle, query_budget=0)['solvable']
    assert not tree.solve(bundle, query_budget=1)['solvable']
    assert tree.solve(bundle, query_budget=2)['solvable']
    t, branches = first_receipt_prefix(bundle)
    assert len(branches) == 2
    for obs, states in branches.items():
        frontier = continuation_frontier(bundle, t, states, max_queries=1)
        # Exact same clock, capability, and unspent satellite budget: the
        # completed A send, rather than the stage number, changes evidence need.
        failed = 'gateway_received=none' in obs
        assert frontier['minimum_future_queries'] == int(failed)
        assert frontier['can_stop_acquiring'] == (not failed)
        assert len(states) > 1  # neither first response resolves the whole future
        if not failed:
            # Dominance pruning is not a legality restriction: spending one
            # request on an uninformative timeout still admits a continuation.
            assert tree.solve(bundle, start_at_s=t, initial_states=states,
                              query_budget=1,
                              forced_first_action=('ISSUE_QUERY', 'receipt_summary'))['solvable']
        if failed:
            # A rescue remains possible; waiting all the way through its last
            # satellite slot removes every winning continuation.
            last_a = max(x for x in bundle.satellite_send_times
                         if x <= bundle.obligations[0].deadline_s)
            expired = continuation_frontier(bundle, last_a + 1, states, max_queries=1)
            assert expired['minimum_future_queries'] is None

    # A frozen receipt query must not incorporate sends that occur after sampling.
    w = bundle.worlds[0]
    st = tree.LocalState(sat_budget=2)
    now = w.query_reachable_times[0]
    qs, _ = tree._step_action(bundle, now, {w.world_id: st}, ('ISSUE_QUERY', 'receipt_summary'))
    query = qs['same'][w.world_id].pending_queries[0]
    assert query.sampled_value == 'gateway_received=none'
    st_after = replace(qs['same'][w.world_id], gateway_received=('A',))
    arrivals = tree._normalize(bundle, query.arrive_at_s, {w.world_id: st_after})
    assert 'gateway_received=none' in next(iter(arrivals))
    print('PASS causal continuation: 0/1/2-query budgets, conditional stop, '
          'irreversible opportunity loss, and frozen receipt sampling')


if __name__ == '__main__':
    main()
