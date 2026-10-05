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
from source_derivation import (  # noqa: E402
    db44_reporting_range_s,
    expand_source_ranges,
    parse_interval_range_s,
)


REGISTRY = (
    ROOT
    / "local_research/current/benchmark/task-design/operational-needs"
    / "SOURCE-PROFILE-REGISTRY.v0.1.json"
)


def main() -> int:
    assert parse_interval_range_s("5min") == (300, 300)
    assert parse_interval_range_s("30-60min") == (1800, 3600)
    assert parse_interval_range_s("3-5d") == (259200, 432000)

    profiles = json.loads(REGISTRY.read_text())["profiles"]
    nominal = compile_ready_registry(profiles)
    db44 = [c for c in nominal if c["source_profiles"] == ["DB44T2457_2024_warning_reporting"]]
    assert len(db44) == 15

    grade1_red = next(
        c for c in db44
        if c["world"]["monitoring_grade"] == 1 and c["world"]["warning_state"] == "red"
    )
    assert db44_reporting_range_s(grade1_red) == (300, 300)

    grade1_normal = next(
        c for c in db44
        if c["world"]["monitoring_grade"] == 1 and c["world"]["warning_state"] == "none_stable"
    )
    assert db44_reporting_range_s(grade1_normal) == (86400, 259200)

    derived = expand_source_ranges(nominal)
    # 12 ranged DB44 cells -> 24 boundary cases; 3 exact red cells -> 3;
    # plus Jiaozuo 1 and T2 4 unchanged.
    assert len(derived) == 32, len(derived)
    db44_derived = [
        c for c in derived
        if c["source_profiles"] == ["DB44T2457_2024_warning_reporting"]
    ]
    assert len(db44_derived) == 27
    assert all("report_interval_s" in c["world"] for c in db44_derived)
    assert all(
        c["variable_provenance"]["report_interval_s"]["class"] == "SOURCE_RANGE"
        for c in db44_derived
    )

    print("PASS source derivation: DB44 cadence table -> 27 explicit boundary cases; total 32")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
