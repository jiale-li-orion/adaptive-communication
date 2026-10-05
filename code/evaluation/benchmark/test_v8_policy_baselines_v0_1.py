#!/usr/bin/env python3
from __future__ import annotations

from audit_v8_baselines_v0_1 import _representatives
from causal_evidence_process_v0_1 import attach_causal_evidence
from exact_reference_oracle_v0_1 import hindsight_bundle_reference, solve_observation_matched
from v8_policy_baselines_v0_1 import (
    solve_always_query_then_plan,
    solve_depth_k,
    solve_latest_feasible_send,
    solve_least_slack,
    solve_myopic_flow_voi,
    solve_receding_horizon,
    solve_shallow_rule,
)


def main() -> int:
    easy = None; paid = None
    for _cell, (_rank, b) in sorted(_representatives().items()):
        if easy is None and b["public_environment"]["terrestrial_process_class"] == "FINITE_CROSSING_WINDOWS":
            easy = b
        if paid is None:
            physical = hindsight_bundle_reference(b)
            if physical["all_worlds_solvable"]:
                p = attach_causal_evidence(b)
                ex = solve_observation_matched(b, p, max_memo_nodes=200_000)
                nq = solve_observation_matched(b, p, disable_paid_query=True, max_memo_nodes=200_000)
                if ex["status"] == nq["status"] == "EXACT" and ex["solvable"] and not nq["solvable"]:
                    paid = b
        if easy is not None and paid is not None:
            break
    assert easy is not None and paid is not None
    for solver in (
        solve_shallow_rule,
        lambda b: solve_depth_k(b, depth=1),
        lambda b: solve_depth_k(b, depth=2),
        lambda b: solve_receding_horizon(b, horizon_decisions=3),
        solve_always_query_then_plan,
        solve_latest_feasible_send,
        solve_least_slack,
        solve_myopic_flow_voi,
    ):
        r = solver(paid)
        assert isinstance(r["solvable"], bool)
        assert r["decisions"] >= 1
    print("PASS V8 policy baselines: shallow and true action-observation depth-k/receding policies run on paid-evidence compositional bundles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
