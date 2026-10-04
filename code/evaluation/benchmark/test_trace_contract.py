#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from trace_contract import validate_trace_registry  # noqa: E402

REGISTRY = (
    ROOT
    / "local_research/current/benchmark/task-design/operational-needs"
    / "TRACE-PROFILE-REGISTRY.v0.1.json"
)


def main() -> int:
    profiles = json.loads(REGISTRY.read_text())["profiles"]
    validate_trace_registry(profiles, root=ROOT)
    p = profiles[0]
    assert p["provenance_class"] == "MODEL_DERIVED_TRACE"
    assert p["variables"]["elevation_mask_deg"]["provenance_class"] == "CONTROLLED_STRESS"
    assert p["variables"]["visibility_windows"]["provenance_class"] == "MODEL_DERIVED_TRACE"
    assert "measured contact" in p["scope"]["not"]
    print("PASS trace profiles: pinned inputs/hash, model-derived geometry, and stress masks stay distinct")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
