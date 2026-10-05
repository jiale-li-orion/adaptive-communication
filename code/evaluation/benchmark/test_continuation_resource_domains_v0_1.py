#!/usr/bin/env python3
"""One focused integration test for causal resource-domain transfer."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import json

from audit_retry_action_mask_v0_1 import minimal_witness
from exact_reference_oracle_v0_1 import LocalState, PendingQuery


def main():
    path = Path(__file__).with_name('continuation_resource_domains_v0_1.py')
    assert path.exists(), 'resource-domain planner has not been implemented'
    from continuation_resource_domains_v0_1 import ContinuationPlanner, verify_witness

    bundle = minimal_witness()
    planner = ContinuationPlanner(bundle, mode='witness_domain')
    states = {w['world_id']: LocalState(satellite_budget=2) for w in bundle['worlds']}
    rich = planner.solve(0, states, query_budget=2)
    assert rich['status'] == 'EXACT' and rich['solvable']
    # The planner returns the first causal witness under the shared exact/V8
    # action ordering.  Its requirement is a sound inner certificate, not a
    # Pareto-minimum resource point.  This fixture's first witness spends two
    # queries but no satellite resource.
    assert rich['requirement'] == [2, 0]
    poor_states = {w: replace(s, satellite_budget=0) for w, s in states.items()}
    poor = planner.solve(0, poor_states, query_budget=2)
    assert poor['status'] == 'EXACT' and poor['solvable']
    assert poor['metrics']['domain_hits'] == 1 and poor['metrics']['expanded'] == 0
    assert verify_witness(bundle, 0, poor_states, poor['policy'], query_budget=2) == [2, 0]

    # Another boundary is not interchangeable merely because budget is equal.
    changed = {w: replace(s, pending_query=PendingQuery(150, 'diagnostic')) for w, s in poor_states.items()}
    changed_result = planner.solve(0, changed, query_budget=2, max_expansions=0)
    assert changed_result['status'] == 'SEARCH_LIMIT' and changed_result['solvable'] is None
    assert changed_result['metrics']['domain_hits'] == 0

    # No terrestrial service, one satellite slot: exact resource threshold is 1.
    sat = deepcopy(bundle)
    for w in sat['worlds']: w['terrestrial_windows'] = []
    sat['public_environment']['satellite_windows'] = [dict(window_id='s', start_s=0, end_s=100, capacity_units=1)]
    sat['public_environment']['satellite_budget_units'] = 2
    sat_planner = ContinuationPlanner(sat, mode='witness_domain')
    got = sat_planner.solve(0, states, query_budget=0)
    assert got['requirement'] == [0, 1]
    enough = {w: replace(s, satellite_budget=1) for w, s in states.items()}
    assert sat_planner.solve(0, enough, query_budget=0)['metrics']['domain_hits'] == 1
    bad = sat_planner.solve(0, poor_states, query_budget=0)
    assert bad['status'] == 'EXACT' and bad['solvable'] is False
    assert verify_witness(sat, 0, enough, got['policy'], query_budget=0) == [0, 1]

    direct = deepcopy(bundle); direct['observation_projection']['evidence_regime'] = 'FULL_OBSERVATION_CONTROL'
    try: ContinuationPlanner(direct)
    except ValueError: pass
    else: raise AssertionError('budget-observing direct mode must not enter transfer theorem')
    print('PASS continuation resource domains: transfer, exhaustion, invalidation, bounded search and replay')


if __name__ == '__main__': main()
