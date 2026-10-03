#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(os.path.dirname(HERE))
if CODE not in sys.path:
    sys.path.insert(0, CODE)

from agentic_communication.attribution import (  # noqa: E402
    AttributionOwner,
    ReplacementExecutionMode,
    attribution_layers,
)
from agentic_communication.trajectory_eval import GoldReplacementLayer  # noqa: E402


def main() -> int:
    rows = attribution_layers()
    assert [x.order for x in rows] == list(range(1, 10))
    assert [x.layer for x in rows] == [
        GoldReplacementLayer.TASK,
        GoldReplacementLayer.EVIDENCE_NEED,
        GoldReplacementLayer.PERCEPT,
        GoldReplacementLayer.CONTEXT,
        GoldReplacementLayer.CAPABILITY_SELECTION,
        GoldReplacementLayer.CAPABILITY_ORDER,
        GoldReplacementLayer.CAPABILITY_ARGUMENTS,
        GoldReplacementLayer.POLICY,
        GoldReplacementLayer.PHYSICAL_ORACLE,
    ]
    upstream = rows[:4]
    planner = rows[4:8]
    assert all(x.owner == AttributionOwner.RUNTIME for x in upstream)
    assert all(x.execution_mode == ReplacementExecutionMode.MODEL_RERUN for x in upstream)
    assert all(x.owner == AttributionOwner.PLANNER_MODEL for x in planner)
    assert rows[-1].owner == AttributionOwner.EVALUATOR
    print("PASS attribution protocol: runtime/model/evaluator ownership and replacement modes are explicit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
