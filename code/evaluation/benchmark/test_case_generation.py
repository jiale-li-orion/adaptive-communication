#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from case_generation import compile_ready_registry  # noqa: E402
from case_contract import validate_case_semantics  # noqa: E402


REGISTRY = (
    ROOT
    / "local_research/current/benchmark/task-design/operational-needs"
    / "SOURCE-PROFILE-REGISTRY.v0.1.json"
)


def main() -> int:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    cases = compile_ready_registry(payload["profiles"])

    assert len(cases) == 20, len(cases)
    assert len({case["case_id"] for case in cases}) == 20
    assert all(case["release_status"] == "VALIDITY_PENDING" for case in cases)
    assert all(case["validity"]["filters"][0]["filter_id"] == "V0_SOURCE_COMPLETE" for case in cases)
    assert all(case["validity"]["filters"][0]["passed"] is True for case in cases)
    assert all(not case["validity"]["decision_benchmark_eligible"] for case in cases)
    assert all(case["observation"]["projection_provenance"] == "FULL_OBSERVATION" for case in cases)
    assert all(not case["observation"]["hidden_fields"] for case in cases)

    by_profile: dict[str, int] = {}
    for case in cases:
        validate_case_semantics(case)
        pid = case["source_profiles"][0]
        by_profile[pid] = by_profile.get(pid, 0) + 1

    assert by_profile == {
        "DB44T2457_2024_warning_reporting": 15,
        "JIAOZUO_2024_geohazard_monitoring_deployment": 1,
        "YINING_2025_pre_disaster_warning_delivery": 1,
        "BAOSHAN_1262_progressive_call_response": 3,
    }, by_profile

    db44 = [c for c in cases if c["source_profiles"] == ["DB44T2457_2024_warning_reporting"]]
    assert len(db44) == 15
    assert all(
        c["world"]["transport_classes"]
        == ["mobile", "LPWAN", "high_or_low_orbit_satellite"]
        for c in db44
    )

    t2 = [c for c in cases if c["family"] == "T2_WARNING_DELIVERY_RESPONSE_HANDOFF"]
    assert len(t2) == 4
    assert all(c["hardness"] == ["H6_AUTHORITY_GATED_DELIVERY"] for c in t2)

    print("PASS nominal case generation: 20 source-derived V0-complete cases, no invented hardness")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
