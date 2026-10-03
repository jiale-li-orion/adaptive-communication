#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(os.path.dirname(HERE))
if CODE not in sys.path:
    sys.path.insert(0, CODE)

from agentic_communication.episodes import o2_risk_escalation_task  # noqa: E402
from agentic_communication.run import run_reference_comply  # noqa: E402


def main() -> int:
    result, _, _ = run_reference_comply(
        seed=0,
        operational_task=o2_risk_escalation_task(),
        simulator_kwargs={"enable_backup": False, "outage_hours": 0.0},
    )
    m = result["agentic"]["communication_metrics"]
    delivered = m["routine_delivered"]
    fixed = m["delivery_oracle_fixed_send"]
    mid = m["delivery_oracle_free_send_require_sample"]
    free = m["delivery_oracle_link_opportunity_ceiling"]
    assert delivered <= fixed <= mid <= free, (delivered, fixed, mid, free)
    assert m["delivery_gap_to_fixed_oracle"] == fixed - delivered
    assert m["delivery_gap_to_free_sample_oracle"] == mid - delivered
    assert m["delivery_gap_to_link_opportunity_ceiling"] == free - delivered
    assert 0.0 <= m["delivery_oracle_link_opportunity_rate"] <= 1.0
    note = result["evaluator_oracles"]["semantics"]
    assert "not a full Feasible-Obligation denominator" in note

    multipath, _, _ = run_reference_comply(
        seed=0,
        operational_task=o2_risk_escalation_task(),
        simulator_kwargs={"enable_backup": True},
    )
    mm = multipath["agentic"]["communication_metrics"]
    assert mm["delivery_oracle_applicable"] is False
    assert mm["delivery_oracle_fixed_send"] is None
    assert "primary-path-only" in mm["delivery_oracle_na_reason"]
    print("PASS delivery oracle metrics: actual <= fixed <= free-with-sample <= link-opportunity ceiling")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
