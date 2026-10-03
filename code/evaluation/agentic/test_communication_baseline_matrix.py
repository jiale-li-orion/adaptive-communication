#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "code" / "evaluation" / "agentic" / "run_communication_baseline_matrix.py"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="comm-baseline-smoke-") as tmp:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--seeds", "0", "--out", tmp],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=240,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        audit = json.loads((Path(tmp) / "audit.json").read_text())
        agg = json.loads((Path(tmp) / "aggregate.json").read_text())
        assert audit["status"] == "PASS", audit
        assert set(agg["online"]) == {
            "local_edf",
            "local_maxcov",
            "aoi_edf",
            "energy_aware_edf",
            "mission_comply_edf",
        }
        assert agg["oracles"]["dynamic_energy"]["all_upper_bounds_valid"]
        assert agg["oracles"]["delivery_primary_only"]["all_upper_bound_orders_valid"]
    print("PASS communication baseline matrix: online controllers + evaluator-only oracles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
