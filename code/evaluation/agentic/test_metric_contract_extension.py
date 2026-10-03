#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(os.path.dirname(HERE))
if CODE not in sys.path:
    sys.path.insert(0, CODE)

from agentic_communication.episodes import o2_risk_escalation_task  # noqa: E402
from agentic_communication.metrics import communication_metrics  # noqa: E402
from agentic_communication.run import run_reference_comply  # noqa: E402


def main() -> int:
    result, _, _ = run_reference_comply(seed=0, operational_task=o2_risk_escalation_task())
    m = communication_metrics(result)
    for key in (
        "delivery_latency_p50_s",
        "delivery_latency_p90_s",
        "delivery_latency_p95_s",
        "aoi_p50_s",
        "aoi_p90_s",
        "aoi_p95_s",
        "node_survival_rate",
        "command_delivery_rate",
        "recovery_delivery_rate",
        "recovery_backlog_recovered",
        "access_assist_bypassed",
        "backup_boost_bytes",
    ):
        assert key in m, key
    assert m["delivery_latency_p50_s"] <= m["delivery_latency_p90_s"] <= m["delivery_latency_p95_s"]
    assert m["aoi_p50_s"] <= m["aoi_p90_s"] <= m["aoi_p95_s"]
    assert 0.0 <= m["node_survival_rate"] <= 1.0
    if m["command_delivery_rate"] is not None:
        assert 0.0 <= m["command_delivery_rate"] <= 1.0
    print("PASS metric contract extension: latency/AoI quantiles, recovery/resource/lifecycle scalars")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
