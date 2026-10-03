#!/usr/bin/env python3
"""Generate/check the canonical Agent attribution layer protocol."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from agentic_communication.attribution import attribution_protocol  # noqa: E402

OUT = ROOT / "research" / "evaluation" / "AGENTIC-ATTRIBUTION-PROTOCOL.v1.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    expected = json.dumps(attribution_protocol(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    current = OUT.read_text(encoding="utf-8") if OUT.exists() else None
    if args.check:
        if current != expected:
            print("Agentic attribution protocol is stale; run scripts/make_agentic_attribution_protocol.py")
            return 1
        print("Agentic attribution protocol matches canonical layer ownership")
        return 0
    if current != expected:
        OUT.write_text(expected, encoding="utf-8")
        print(f"updated {OUT.relative_to(ROOT)}")
    else:
        print("Agentic attribution protocol already current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
