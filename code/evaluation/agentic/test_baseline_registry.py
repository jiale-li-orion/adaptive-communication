#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(CODE)
if CODE not in sys.path:
    sys.path.insert(0, CODE)

from agentic_communication.baselines import (  # noqa: E402
    BaselineClass,
    baseline_registry,
    registry_for_task,
    validate_implementation_refs,
)
from agentic_communication.contracts import OperationalTaskFamily  # noqa: E402


def main() -> int:
    rows = baseline_registry()
    assert len(rows) >= 10
    assert not validate_implementation_refs(ROOT), validate_implementation_refs(ROOT)
    assert rows["oracle.dynamic_energy"].baseline_class == BaselineClass.EVALUATOR_ONLY_ORACLE
    assert rows["oracle.dynamic_energy"].online_legal is False
    o3 = registry_for_task(OperationalTaskFamily.BACKHAUL_OUTAGE_SUSTAINMENT)
    ids = {x.baseline_id for x in o3}
    assert {"comm.backup_edf", "comm.backup_maxcov", "agent.full_dump"} <= ids
    print(f"PASS baseline registry: {len(rows)} typed baselines/oracles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
