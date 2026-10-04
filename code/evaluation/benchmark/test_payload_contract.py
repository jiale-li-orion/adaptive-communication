#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from payload_contract import validate_payload_registry  # noqa: E402

REGISTRY = (
    ROOT
    / "local_research/current/benchmark/task-design/operational-needs"
    / "PAYLOAD-PROFILE-REGISTRY.v0.1.json"
)


def main() -> int:
    profiles = json.loads(REGISTRY.read_text())["profiles"]
    validate_payload_registry(profiles)
    p = profiles[0]
    assert p["encoded_bytes"] == 32
    assert p["derivation"]["header_bytes"] == 3
    assert p["derivation"]["example_ascii_bytes"] == 29
    print("PASS payload profiles: exact DZ/T 0450 Type-1 source example derives to 32 bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
