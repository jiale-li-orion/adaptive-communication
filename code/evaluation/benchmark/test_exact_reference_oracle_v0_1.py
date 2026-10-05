#!/usr/bin/env python3
"""Exact reference regression for physical and observation-matched semantics."""
from __future__ import annotations

from itertools import islice

from causal_evidence_process_v0_1 import attach_causal_evidence
from dynamic_world_materializer_v0_1 import iter_world_bundles
from exact_reference_oracle_v0_1 import (
    hindsight_bundle_reference,
    reference_labels,
    solve_observation_matched,
)


def main() -> int:
    # Easy/full-observation controls must be exactly solvable when physical
    # matching says the single world is feasible.
    checked = 0
    for bundle in iter_world_bundles():
        if (
            bundle["pre_oracle_disposition"] == "EASY_CONFORMANCE"
            and bundle["observation_projection"]["evidence_regime"] == "FULL_OBSERVATION_CONTROL"
        ):
            physical = hindsight_bundle_reference(bundle)
            if not physical["all_worlds_solvable"]:
                continue
            process = attach_causal_evidence(bundle)
            exact = solve_observation_matched(bundle, process, max_memo_nodes=50_000)
            assert exact["status"] == "EXACT"
            assert exact["solvable"] is True
            checked += 1
            if checked >= 3:
                break
    assert checked == 3

    # The reference bundle must keep hindsight and full-current-state separate.
    sample = next(iter(iter_world_bundles()))
    labels = reference_labels(sample, max_memo_nodes=50_000)
    assert labels["hindsight_physical"]["mode"] == "HINDSIGHT_PHYSICAL_FEASIBILITY"
    assert labels["full_current_state"]["mode"] == "FULL_CURRENT_STATE"
    assert labels["full_current_state"]["status"] == "EXACT"
    assert labels["release_status"] == "NOT_BENCHMARK_ADMIT"
    assert labels["observation_matched_exact"]["scalarization_used"] is False
    assert labels["observation_matched_no_paid_query"]["scalarization_used"] is False

    # A dynamic bundle must retain multiple future realizations even under the
    # full-observation evidence regime.  FULL_CURRENT_STATE may separate worlds
    # only when their *current* state diverges; it is not allowed to collapse
    # the support merely because their future service schedules differ.
    dynamic = next(
        b
        for b in iter_world_bundles()
        if b["public_environment"]["terrestrial_process_class"] == "MULTI_WINDOW_DYNAMIC"
        and b["observation_projection"]["evidence_regime"] == "FULL_OBSERVATION_CONTROL"
        and len(b["worlds"]) >= 2
    )
    assert len(dynamic["worlds"]) == dynamic["provenance"]["workload_density"]["value"]
    dyn_labels = reference_labels(dynamic, max_memo_nodes=50_000)
    assert dyn_labels["full_current_state"]["mode"] == "FULL_CURRENT_STATE"
    assert dyn_labels["full_current_state"]["status"] in {"EXACT", "SEARCH_LIMIT"}
    assert dyn_labels["hindsight_physical"]["mode"] == "HINDSIGHT_PHYSICAL_FEASIBILITY"

    # Passive feedback is two-stage: gateway receipt is observable before the
    # final completion ACK and therefore must appear as a distinct policy event.
    passive = next(
        b
        for b in iter_world_bundles()
        if b["public_environment"]["terrestrial_process_class"] == "STEADY_AVAILABLE_CONTROL"
        and b["observation_projection"]["evidence_regime"] == "PASSIVE_ACK_ONLY"
    )
    passive_exact = solve_observation_matched(
        passive,
        attach_causal_evidence(passive),
        disable_paid_query=True,
        max_memo_nodes=50_000,
    )
    policy_text = str(passive_exact["policy"])
    assert "gateway_receipt:" in policy_text
    assert "final_ack:" in policy_text
    assert policy_text.index("gateway_receipt:") < policy_text.index("final_ack:")

    print(
        "PASS exact reference oracle v0.1: hindsight, full-current-state and "
        "observation-matched references preserve distinct future-information boundaries"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
