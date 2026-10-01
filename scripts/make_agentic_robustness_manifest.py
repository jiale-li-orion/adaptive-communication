#!/usr/bin/env python3
"""Generate/check the paired Agentic robustness-coordinate manifest."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from agentic_communication.robustness import robustness_coordinates, robustness_summary  # noqa: E402

OUT = ROOT / "research" / "AGENTIC-ROBUSTNESS-MATRIX.v1.json"


def build() -> dict:
    rows = robustness_coordinates()
    return {
        "schema_revision": "1",
        "rule": (
            "axis-wise paired coordinates validate that robustness axes reach the real full simulator; "
            "this manifest is not a Cartesian sweep and carries no method-gain claim"
        ),
        "summary": robustness_summary(rows),
        "coordinates": [row.model_dump(mode="json") for row in rows],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    expected = json.dumps(build(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    current = OUT.read_text(encoding="utf-8") if OUT.exists() else None
    if args.check:
        if current != expected:
            print("Agentic robustness manifest is stale; run scripts/make_agentic_robustness_manifest.py")
            return 1
        print("Agentic robustness manifest matches canonical coordinates")
        return 0
    if current != expected:
        OUT.write_text(expected, encoding="utf-8")
        print(f"updated {OUT.relative_to(ROOT)}")
    else:
        print("Agentic robustness manifest already current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
