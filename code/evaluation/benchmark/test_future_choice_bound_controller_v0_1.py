#!/usr/bin/env python3
from audit_retry_action_mask_v0_1 import minimal_witness
from exact_reference_oracle_v0_1 import LocalState
from future_choice_bound_controller_v0_1 import bound_future_choice_context


def main() -> None:
    bundle = minimal_witness()
    states = {str(w["world_id"]): LocalState(satellite_budget=0) for w in bundle["worlds"]}
    result = bound_future_choice_context(
        bundle,
        at_s=0,
        states=states,
        query_budget=1,
        upper_depth=0,
        choice_lower_depth=3,
    )
    assert "STOP_ACQUISITION_CERTIFIED" in result["labels"]
    assert "CAN_DEFER_QUERY" in result["labels"]
    print("PASS future-choice bound controller: safe stop/defer labels without exact fallback")


if __name__ == "__main__":
    main()
