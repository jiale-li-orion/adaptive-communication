#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from capability_contract import (  # noqa: E402
    unresolved_answer_fields,
    validate_capability_registry,
)


REGISTRY = (
    ROOT
    / "local_research/current/benchmark/task-design/operational-needs"
    / "CAPABILITY-PROFILE-REGISTRY.v0.1.json"
)


def main() -> int:
    profiles = json.loads(REGISTRY.read_text())["profiles"]
    validate_capability_registry(profiles)
    by_id = {p["capability_profile_id"]: p for p in profiles}

    leo = by_id["DZT0450_2023_leo_narrowband_satellite"]
    assert leo["oracle_status"] == "READY_FOR_COMPATIBILITY"
    assert unresolved_answer_fields(leo) == []
    assert leo["capabilities"][0]["constraints"]["max_packet_bytes"] == 200
    assert leo["capabilities"][0]["constraints"]["send_period_s_min"] == 5

    short = by_id["DZT0450_2023_satellite_short_message"]
    assert short["oracle_status"] == "PARTIAL_SOURCE_GAP"
    assert unresolved_answer_fields(short) == ["max_packet_bytes", "send_period_s_min"]

    device = by_id["F9164_BD305_4G_Beidou_dual_mode"]
    assert device["oracle_status"] == "READY_FOR_COMPATIBILITY"
    assert device["capabilities"][0]["owner"] == "device_runtime"

    print("PASS capability profiles: normative parameters, gaps, and device-local fallback stay separated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
