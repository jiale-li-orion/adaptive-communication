#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(os.path.dirname(HERE))
if CODE not in sys.path:
    sys.path.insert(0, CODE)

from agentic_communication.robustness import (  # noqa: E402
    robustness_coordinates,
    robustness_summary,
    task_for_coordinate,
)


def main() -> int:
    rows = robustness_coordinates()
    summary = robustness_summary(rows)
    assert set(summary) == {
        "backhaul_outage",
        "deployment_scale",
        "evidence_owner",
        "target_scope",
        "weather_window",
    }
    assert all(x["n_coordinates"] == 2 for x in summary.values()), summary
    for row in rows:
        task = task_for_coordinate(row)
        assert task.task_horizon_s == row.task_hours * 3600
    print("PASS robustness manifest: five paired full-sim axes, two coordinates each")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
