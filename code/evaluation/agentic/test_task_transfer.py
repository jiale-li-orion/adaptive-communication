#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(os.path.dirname(HERE))
if CODE not in sys.path:
    sys.path.insert(0, CODE)

from agentic_communication.task_compiler import CommunicationTaskCompiler  # noqa: E402
from agentic_communication.task_transfer import qili_2016_rainfall_deformation_profile  # noqa: E402


def main() -> int:
    profile = qili_2016_rainfall_deformation_profile()
    task = profile.to_operational_task(task_hours=12)
    assert task.source_refs == ["S14"]
    assert [x.start_s for x in task.phases] == [0, 4 * 3600, 8 * 3600]
    assert [x.required_period_s for x in task.phases] == [3600, 300, 3600]
    assert task.metadata["risk_authority"] == "external-source-derived"
    assert "not Qili field warning thresholds" in task.metadata["claim_boundary"]
    compiler = CommunicationTaskCompiler()
    for t_s in (0, 4 * 3600, 8 * 3600):
        contract = compiler.compile(task, t_s)
        assert contract.desired_state["required_period_s"] == task.phase_at(t_s).required_period_s
    print("PASS task transfer: source-derived phase order compiles without changing runtime semantics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
