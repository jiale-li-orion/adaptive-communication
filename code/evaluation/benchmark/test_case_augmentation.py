#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from case_augmentation import (  # noqa: E402
    CaseAugmentationError,
    augment_db44_universe,
    validate_capability_trace_compatibility,
    validate_task_trace_scope,
)
from case_generation import compile_ready_registry  # noqa: E402
from source_derivation import expand_source_ranges  # noqa: E402

BASE = ROOT / "local_research/current/benchmark/task-design/operational-needs"


def load(path: Path):
    return json.loads(path.read_text())


def main() -> int:
    tasks = load(BASE / "SOURCE-PROFILE-REGISTRY.v0.1.json")["profiles"]
    caps = load(BASE / "CAPABILITY-PROFILE-REGISTRY.v0.1.json")["profiles"]
    traces = load(BASE / "TRACE-PROFILE-REGISTRY.v0.1.json")["profiles"]
    cases = expand_source_ranges(compile_ready_registry(tasks))

    connecta = next(
        p for p in caps
        if p["capability_profile_id"] == "PLAN_S_CONNECTA_IOT_MODULE_D2S"
    )
    generic_leo = next(
        p for p in caps
        if p["capability_profile_id"] == "DZT0450_2023_leo_narrowband_satellite"
    )
    tibet_trace = next(
        p for p in traces
        if p["trace_profile_id"] == "CONNECTA_20260922_TIBET_GEOMETRY_48H"
    )
    trace = next(
        p for p in traces
        if p["trace_profile_id"] == "CONNECTA_20260922_SIHUI_GEOMETRY_48H"
    )
    trace_payload = load(ROOT / trace["trace_ref"])

    assert (
        validate_capability_trace_compatibility(connecta, trace)
        == "PLAN_S_CONNECTA_D2S"
    )
    assert (
        validate_task_trace_scope(cases[0], trace)
        == "GUANGDONG_SIHUI_HIGH_SCHOOL_LANDSLIDE"
    )
    try:
        validate_task_trace_scope(cases[0], tibet_trace)
    except CaseAugmentationError as exc:
        assert "jurisdiction mismatch" in str(exc)
    else:
        raise AssertionError("DB44 Guangdong task must reject Tibet trace")

    try:
        validate_capability_trace_compatibility(generic_leo, trace)
    except CaseAugmentationError as exc:
        assert "service_family" in str(exc)
    else:
        raise AssertionError("generic DZ/T LEO capability must not pair with Connecta trace")

    rows = augment_db44_universe(
        cases,
        capability_profile=connecta,
        trace_profile=trace,
        trace_payload=trace_payload,
    )
    assert len(rows) == 27 * 5
    assert len({r["case_id"] for r in rows}) == 135
    assert all(
        r["world"]["selected_capability_profile"] == "PLAN_S_CONNECTA_IOT_MODULE_D2S"
        for r in rows
    )
    assert all(
        r["world"]["selected_service_family"] == "PLAN_S_CONNECTA_D2S"
        for r in rows
    )
    assert all(
        r["world"]["selected_site_profile"]
        == "GUANGDONG_SIHUI_HIGH_SCHOOL_LANDSLIDE"
        for r in rows
    )
    assert all(r["generator"]["trace_refs"] == [trace["trace_profile_id"]] for r in rows)
    assert {r["world"]["path_geometry"]["elevation_mask_deg"] for r in rows} == {
        0, 5, 10, 20, 30
    }
    assert all(
        r["variable_provenance"]["path_geometry_trace"]["class"]
        == "MODEL_DERIVED_TRACE"
        for r in rows
    )
    assert all(
        r["variable_provenance"]["elevation_mask_deg"]["class"]
        == "CONTROLLED_STRESS"
        for r in rows
    )
    assert all(
        r["release_status"] == "VALIDITY_PENDING"
        and not r["validity"]["decision_benchmark_eligible"]
        for r in rows
    )

    print(
        "PASS case augmentation: Connecta capability × Connecta geometry gives "
        "135 provenance-preserving worlds; incompatible service/jurisdiction composition rejected"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
