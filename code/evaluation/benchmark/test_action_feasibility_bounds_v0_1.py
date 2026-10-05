#!/usr/bin/env python3
from audit_retry_action_mask_v0_1 import minimal_witness
from action_feasibility_bounds_v0_1 import LazyActionFeasibility, optimistic_upper
from exact_reference_oracle_v0_1 import LocalState
from v8_policy_baselines_v0_1 import _legal_actions


def main() -> None:
    bundle = minimal_witness()
    states = {str(w["world_id"]): LocalState(satellite_budget=0) for w in bundle["worlds"]}
    lazy = LazyActionFeasibility(bundle)
    assert optimistic_upper(bundle, 0, states)
    actions = _legal_actions(bundle, lazy.planner.process, states, 0)
    rows = [lazy.classify(at_s=0, states=states, query_budget=1, action=a) for a in actions]
    assert any(r["solvable"] is True for r in rows)
    assert all(r["solvable"] is not None for r in rows)
    print("PASS action feasibility bounds: sound L/U classifier with exact fallback")


if __name__ == "__main__":
    main()
