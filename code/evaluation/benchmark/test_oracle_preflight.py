#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from case_generation import compile_ready_registry  # noqa: E402
from oracle_preflight import preflight_universe  # noqa: E402
from source_derivation import expand_source_ranges  # noqa: E402

BASE = ROOT / "local_research/current/benchmark/task-design/operational-needs"


def load(name: str):
    return json.loads((BASE / name).read_text())


def main() -> int:
    profiles = load("SOURCE-PROFILE-REGISTRY.v0.1.json")["profiles"]
    caps = load("CAPABILITY-PROFILE-REGISTRY.v0.1.json")["profiles"]
    mapping = load("T1-SIMULATOR-MAPPING.v0.1.json")
    cases = expand_source_ranges(compile_ready_registry(profiles))
    rows = preflight_universe(cases, mapping=mapping, capability_profiles=caps)

    assert len(rows) == 32
    db44 = [r for r in rows if r["source_profile"] == "DB44T2457_2024_warning_reporting"]
    assert len(db44) == 27
    assert all(r["mapping_disposition"] == "ADAPTER_REQUIRED" for r in db44)
    assert all(not r["oracle_ready"] for r in db44)
    assert all(
        "DZT0450_2023_leo_narrowband_satellite"
        in r["compatible_capability_profiles"]
        for r in db44
    )
    assert all(
        "report_payload_bytes_or_source_payload_class" in r["blocking_fields"]
        for r in db44
    )

    jiaozuo = [r for r in rows if r["source_profile"] == "JIAOZUO_2024_geohazard_monitoring_deployment"]
    assert len(jiaozuo) == 1
    assert jiaozuo[0]["mapping_disposition"] == "SUPPORT_ONLY"

    t2 = [r for r in rows if r["family"] == "T2_WARNING_DELIVERY_RESPONSE_HANDOFF"]
    assert len(t2) == 4
    assert all(r["mapping_disposition"] == "SIMULATOR_GAP" for r in t2)

    assert not any(r["oracle_ready"] for r in rows)

    print("PASS oracle preflight: 32 cases mapped; blockers explicit; zero silent defaults")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
