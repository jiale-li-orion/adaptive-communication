#!/usr/bin/env python3
from __future__ import annotations

from dynamic_world_materializer_v0_1 import iter_world_bundles
from validity_filters_v0_1 import count_physical_success_plans, evaluate_v0_v7


def _by_id(result):
    return {x["filter_id"]: x for x in result["filters"]}


def main() -> int:
    easy = next(
        b for b in iter_world_bundles()
        if b["pre_oracle_disposition"] == "EASY_CONFORMANCE"
        and b["observation_projection"]["evidence_regime"] == "FULL_OBSERVATION_CONTROL"
    )
    r = evaluate_v0_v7(easy, max_memo_nodes=50_000)
    f = _by_id(r)
    assert f["V0_SOURCE_COMPLETE"]["passed"] is True
    assert f["V1_SOLVABLE"]["passed"] is True
    assert f["V7_OBJECTIVE_DEFINED"]["passed"] is True
    assert r["next_stage"] == "V8_STRONG_BASELINE_SHORTCUT_AUDIT"

    # Exact assignment count is stable and never reports a physical plan for an
    # infeasible world.
    world = easy["worlds"][0]
    count = count_physical_success_plans(easy, world)
    assert count >= 1
    assert count_physical_success_plans(easy, world, relax_deadline=True) >= count
    assert count_physical_success_plans(easy, world, relax_capacity=True) >= count
    assert count_physical_success_plans(easy, world, relax_satellite_budget=True) >= count

    # Find one pilot-positive paid-evidence case without hard-coding a recipe id.
    found = None
    checked = 0
    for b in iter_world_bundles():
        if b["public_environment"]["terrestrial_process_class"] != "MULTI_WINDOW_DYNAMIC":
            continue
        if b["observation_projection"]["evidence_regime"] != "GATEWAY_SUMMARY_QUERY":
            continue
        rr = evaluate_v0_v7(b, max_memo_nodes=50_000)
        checked += 1
        ff = _by_id(rr)
        if ff["V4_OBSERVATION_RELEVANCE"].get("paid_evidence_required"):
            found = rr
            break
        if checked >= 40:
            break
    assert found is not None, "expected at least one paid-evidence-positive dynamic candidate in deterministic prefix"
    ff = _by_id(found)
    assert ff["V1_SOLVABLE"]["passed"] is True
    assert ff["V4_OBSERVATION_RELEVANCE"]["passed"] is True
    assert ff["V4_OBSERVATION_RELEVANCE"]["reason_code"] == "PASS_PAID_EVIDENCE_REQUIRED"
    assert ff["V7_OBJECTIVE_DEFINED"]["passed"] is True

    print("PASS V0-V7 validity filters: source/solvability/plan multiplicity/evidence/binding/objective boundaries remain explicit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
