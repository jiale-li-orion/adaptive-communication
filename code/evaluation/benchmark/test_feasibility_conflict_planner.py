#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from feasibility_conflict_planner import (  # noqa: E402
    build_decision_context,
    compact_context_dict,
    detect_feasibility_conflict,
    derive_evidence_need,
)
from scenario_generator_v0_2 import generate  # noqa: E402


def main() -> int:
    rows = generate()
    required = [r for r in rows if r["kind"] == "QUERY_REQUIRED"]
    harmful = [r for r in rows if r["kind"] == "QUERY_HARMFUL"]
    passive = [r for r in rows if r["kind"] == "PASSIVE_BETTER"]
    assert len(required) == len(harmful) == len(passive) == 24

    for row in required:
        bundle = row["bundle"]
        conflict = detect_feasibility_conflict(bundle)
        assert conflict is not None
        assert conflict.common_winning_actions == ()
        need = derive_evidence_need(bundle, conflict)
        assert need is not None
        assert need.owner == "gateway"
        assert need.proposition == "communication.gateway.primary_health"
        assert need.resolves_conflict
        assert len(need.partitions) == 2

        ctx = build_decision_context(bundle)
        materialized = compact_context_dict(ctx)
        assert "hidden_mode" not in json.dumps(materialized)
        assert "world_id" not in json.dumps(materialized)
        assert materialized["evidence_needs"][0]["resolves_conflict"] is True

    # Query-harmful controls may contain aliases, but the paid query must not be
    # promoted to a resolving EvidenceNeed.
    for row in harmful:
        conflict = detect_feasibility_conflict(row["bundle"])
        if conflict is not None:
            need = derive_evidence_need(row["bundle"], conflict)
            assert need is None or not need.resolves_conflict

    # Passive-better controls are retained as evidence-timing controls; the
    # compact context must not reveal hidden-world labels.
    for row in passive[:4]:
        materialized = compact_context_dict(build_decision_context(row["bundle"]))
        raw = json.dumps(materialized, sort_keys=True)
        assert "EARLY_WINDOW" not in raw
        assert "LATE_WINDOW" not in raw

    print(
        "PASS feasibility-conflict planner: 24/24 H2 bundles expose a "
        "gateway-owned resolving EvidenceNeed without hidden-world leakage"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
