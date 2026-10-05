#!/usr/bin/env python3
from audit_retry_action_mask_v0_1 import minimal_witness
from conditional_action_frontier_v0_1 import build_action_frontier
from exact_reference_oracle_v0_1 import LocalState


def main() -> None:
    bundle = minimal_witness()
    states = {str(w["world_id"]): LocalState(satellite_budget=0) for w in bundle["worlds"]}
    frontier = build_action_frontier(bundle, at_s=0, states=states, query_budget=1)
    assert frontier["context"]["query_free_completion"] is True
    assert frontier["context"]["can_defer_query_now"] is True
    assert "SEND_TERR:o" in frontier["certified_action_keys"]
    assert all(row["full_policy_requirement"][0] <= 1 for row in frontier["certified_actions"])
    print("PASS conditional action frontier: legal actions separated from replay-certified future choices")


if __name__ == "__main__":
    main()
