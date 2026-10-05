#!/usr/bin/env python3
from __future__ import annotations

from copy import deepcopy

from dynamic_world_materializer_v0_1 import iter_world_bundles
from exact_reference_oracle_v0_1 import hindsight_bundle_reference
from execution_trace_evaluator_v0_1 import evaluate_execution_trace, witness_to_execution_trace


def main() -> int:
    bundle = None
    reference = None
    for b in iter_world_bundles():
        r = hindsight_bundle_reference(b)
        if r["all_worlds_solvable"] and all(x["witness"] for x in r["worlds"]):
            bundle, reference = b, r
            break
    assert bundle is not None and reference is not None
    world_ref = reference["worlds"][0]
    wid = world_ref["world_id"]
    trace = witness_to_execution_trace(bundle, world_ref["witness"])
    assert evaluate_execution_trace(bundle, world_id=wid, actions=trace)["success"] is True

    # Authority mutation.
    bad = deepcopy(trace); bad[0]["actor"] = "monitoring_center"
    assert evaluate_execution_trace(bundle, world_id=wid, actions=bad)["reason_code"] == "AUTHORITY_VIOLATION"

    # Textually plausible but physically unexecuted action.
    bad = deepcopy(trace); bad[0]["resource_id"] = "imaginary-window"
    assert "PHYSICALLY_UNEXECUTED" in evaluate_execution_trace(bundle, world_id=wid, actions=bad)["reason_code"]

    # Protected-state corruption.
    bad = deepcopy(trace); bad[0]["protected_subject"] = "unrelated state"
    assert evaluate_execution_trace(bundle, world_id=wid, actions=bad)["reason_code"] == "PROTECTED_SUBJECT_MISMATCH"

    # Missing one real execution cannot be converted into success by text.
    assert evaluate_execution_trace(bundle, world_id=wid, actions=trace[:-1])["reason_code"] == "MISSING_EXECUTED_COMPLETION"

    # Force one action to complete after its source deadline.
    bad = deepcopy(trace)
    oid = bad[0]["obligation_id"]
    o = next(x for x in bundle["obligations"] if x["obligation_id"] == oid)
    bad[0]["at_s"] = int(o["deadline_s"])
    reason = evaluate_execution_trace(bundle, world_id=wid, actions=bad)["reason_code"]
    assert reason in {"OUTSIDE_TERR_SERVICE_WINDOW", "OUTSIDE_SAT_SERVICE_WINDOW", "MISSED_SOURCE_DEADLINE"}

    print("PASS V9 evaluator core: valid oracle witness passes; authority/physics/deadline/protected-state/missing-execution mutations fail")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
