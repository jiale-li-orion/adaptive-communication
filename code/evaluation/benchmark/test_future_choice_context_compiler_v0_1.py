#!/usr/bin/env python3
from audit_retry_action_mask_v0_1 import minimal_witness
from exact_reference_oracle_v0_1 import LocalState
from future_choice_context_compiler_v0_1 import FutureChoiceContextCompiler


def main() -> None:
    bundle = minimal_witness()
    states = {str(w["world_id"]): LocalState(satellite_budget=0) for w in bundle["worlds"]}
    compiler = FutureChoiceContextCompiler(bundle, choice_upper_depth=4, choice_lower_depth=6)
    first = compiler.context(at_s=0, states=states, query_budget=1)
    before = dict(first["memo_size"])
    second = compiler.context(at_s=0, states=states, query_budget=1)
    after = dict(second["memo_size"])
    assert first["labels"] == second["labels"]
    assert before == after
    assert second["new_nodes"]["upper"] == 0
    assert second["new_nodes"]["lower"] == 0
    print("PASS future-choice context compiler: persistent L/U proofs replay with zero new proof nodes")


if __name__ == "__main__":
    main()
