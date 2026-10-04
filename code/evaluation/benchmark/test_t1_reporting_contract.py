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
from source_derivation import expand_source_ranges  # noqa: E402
from t1_reporting_contract import (  # noqa: E402
    compile_periodic_reporting_obligations,
    evaluate_report_deliveries,
)


REGISTRY = (
    ROOT
    / "local_research/current/benchmark/task-design/operational-needs"
    / "SOURCE-PROFILE-REGISTRY.v0.1.json"
)


def main() -> int:
    profiles = json.loads(REGISTRY.read_text())["profiles"]
    cases = expand_source_ranges(compile_ready_registry(profiles))
    red = next(
        c
        for c in cases
        if c["source_profiles"] == ["DB44T2457_2024_warning_reporting"]
        and c["world"]["monitoring_grade"] == 1
        and c["world"]["warning_state"] == "red"
    )
    assert red["world"]["report_interval_s"] == 300

    obligations = compile_periodic_reporting_obligations(red, cycles=3)
    assert [(o.release_at_s, o.deadline_s) for o in obligations] == [
        (0, 300),
        (300, 600),
        (600, 900),
    ]

    delivered = {
        obligations[0].obligation_id: 301,
        obligations[1].obligation_id: 590,
        obligations[2].obligation_id: None,
    }
    result = evaluate_report_deliveries(obligations, delivered)
    assert result["completed_on_time"] == 1
    assert result["late"] == 1
    assert result["missing"] == 1
    assert result["rows"][0]["deadline_s"] == 300

    print(
        "PASS T1 source-aware reporting: source interval is the deadline; "
        "no historical grace"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
