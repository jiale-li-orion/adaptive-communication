#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
ROOT = CODE.parent
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from agentic_communication.run import DEFAULT_FULLSIM  # noqa: E402


RESULT_CONTRACTS = (
    ROOT / "results" / "agentic" / "o2-risk-escalation-v1" / "experiment_contract.json",
    ROOT / "results" / "agentic" / "o2-localized-risk-escalation-v1" / "experiment_contract.json",
    ROOT / "results" / "agentic" / "o2-diagnosis-first-v1" / "experiment_contract.json",
    ROOT / "results" / "agentic" / "o2-baseline-matrix-v1" / "experiment_contract.json",
    ROOT / "results" / "agentic" / "task-transfer-qili-v1" / "experiment_contract.json",
)


def main() -> int:
    expected = dict(DEFAULT_FULLSIM)
    failures = []
    for path in RESULT_CONTRACTS:
        if not path.is_file():
            failures.append(f"missing:{path.relative_to(ROOT)}")
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        actual = payload.get("simulator")
        if actual != expected:
            failures.append(f"simulator-drift:{path.relative_to(ROOT)}")
        authority = payload.get("simulator_authority")
        if authority != "code/agentic_communication/run.py::DEFAULT_FULLSIM":
            failures.append(f"authority-drift:{path.relative_to(ROOT)}:{authority}")
    if failures:
        for row in failures:
            print(row)
        return 1
    print("PASS O2 simulator authority: all formal O2-derived result contracts use DEFAULT_FULLSIM")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
