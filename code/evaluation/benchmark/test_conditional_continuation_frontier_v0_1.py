#!/usr/bin/env python3
from audit_retry_action_mask_v0_1 import minimal_witness
from conditional_continuation_frontier_v0_1 import build_conditional_frontier


def main():
    bundle = minimal_witness()
    frontier = build_conditional_frontier(bundle, max_query_budget=2, max_satellite_budget=0)
    # Retry-legality repair makes the minimal witness query-free.
    assert frontier['evidence_gain_type'] == 'NO_INFORMATION_GAIN_IN_Q_B_RECTANGLE'
    assert frontier['context']['can_stop_acquiring_for_feasibility'] is True
    assert frontier['context']['minimum_query_budget_for_any_success'] == 0
    assert frontier['frontier_points'][0]['query_budget'] == 0
    assert frontier['frontier_points'][0]['satellite_budget'] == 0
    print('PASS conditional continuation frontier: query-free stopping and bounded Pareto point')


if __name__ == '__main__':
    main()
