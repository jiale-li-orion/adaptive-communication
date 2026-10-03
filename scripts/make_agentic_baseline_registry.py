#!/usr/bin/env python3
"""Generate/check the public baseline/oracle registry from canonical Python specs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from agentic_communication.baselines import (  # noqa: E402
    BaselineClass,
    baseline_registry,
    validate_implementation_refs,
)

OUT = ROOT / "research" / "policy" / "BASELINE-REGISTRY.v1.json"


def build() -> dict:
    failures = validate_implementation_refs(ROOT)
    if failures:
        raise RuntimeError("invalid baseline implementation refs: " + ", ".join(failures))
    specs = baseline_registry()
    rows = [specs[k].model_dump(mode="json") for k in sorted(specs)]
    return {
        "schema_revision": "1",
        "canonical_owner": "code/agentic_communication/baselines.py",
        "rule": "online baselines and evaluator-only oracles must never share the same evaluation label",
        "counts": {
            "total": len(rows),
            "online_legal": sum(bool(x["online_legal"]) for x in rows),
            "evaluator_only_oracle": sum(
                x["baseline_class"] == BaselineClass.EVALUATOR_ONLY_ORACLE.value
                for x in rows
            ),
        },
        "baselines": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    expected = json.dumps(build(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    current = OUT.read_text(encoding="utf-8") if OUT.exists() else None
    if args.check:
        if current != expected:
            print("Agentic baseline registry is stale; run scripts/make_agentic_baseline_registry.py")
            return 1
        print("Agentic baseline registry matches canonical Python specs")
        return 0
    if current != expected:
        OUT.write_text(expected, encoding="utf-8")
        print(f"updated {OUT.relative_to(ROOT)}")
    else:
        print("Agentic baseline registry already current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
