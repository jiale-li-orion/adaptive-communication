#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from case_augmentation import augment_db44_universe  # noqa: E402
from case_generation import compile_ready_registry  # noqa: E402
from oracle_preflight import preflight_universe  # noqa: E402
from source_derivation import expand_source_ranges  # noqa: E402

BASE = ROOT / "local_research/current/benchmark/task-design/operational-needs"


def load(name: str):
    return json.loads((BASE / name).read_text())


def main() -> int:
    tasks = load("SOURCE-PROFILE-REGISTRY.v0.1.json")["profiles"]
    caps = load("CAPABILITY-PROFILE-REGISTRY.v0.1.json")["profiles"]
    traces = load("TRACE-PROFILE-REGISTRY.v0.1.json")["profiles"]
    mapping = load("T1-SIMULATOR-MAPPING.v0.1.json")
    source_cases = expand_source_ranges(compile_ready_registry(tasks))
    cap = next(
        p for p in caps
        if p["capability_profile_id"] == "PLAN_S_CONNECTA_IOT_MODULE_D2S"
    )
    trace = next(p for p in traces if p["trace_profile_id"] == "CONNECTA_20260922_SIHUI_GEOMETRY_48H")
    payload = json.loads((ROOT / trace["trace_ref"]).read_text())
    worlds = augment_db44_universe(
        source_cases,
        capability_profile=cap,
        trace_profile=trace,
        trace_payload=payload,
    )
    rows = preflight_universe(worlds, mapping=mapping, capability_profiles=caps)

    assert len(rows) == 135
    assert all(not row["oracle_ready"] for row in rows)
    assert all("selected_capability_profile" not in row["blocking_fields"] for row in rows)
    assert all("path_opportunity_trace" not in row["blocking_fields"] for row in rows)
    assert all(
        row["blocking_fields"]
        == [
            "report_payload_bytes_or_source_payload_class",
            "path_service_success_semantics",
        ]
        for row in rows
    )

    print(
        "PASS augmented preflight: 135 worlds clear capability/geometry blockers; "
        "only payload + service-success semantics remain"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
