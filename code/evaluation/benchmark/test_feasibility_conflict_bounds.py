#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from feasibility_conflict_planner import (  # noqa: E402
    action_feasibility_bounds,
    build_decision_context,
    update_context_after_gateway_evidence,
)
from scenario_generator_v0_2 import generate  # noqa: E402


def main() -> int:
    rows = generate()
    required = [r for r in rows if r["kind"] == "QUERY_REQUIRED"]
    assert len(required) == 24

    resolved_branches = 0
    sound_bounds = 0
    for row in required:
        bundle = row["bundle"]
        bounds = action_feasibility_bounds(bundle)
        assert bounds
        assert all(b.lower <= b.upper for b in bounds)
        sound_bounds += 1

        ctx = build_decision_context(bundle)
        assert ctx.conflict is not None
        assert ctx.evidence_needs and ctx.evidence_needs[0].resolves_conflict

        values = sorted({w.query_value for w in bundle.worlds})
        assert len(values) == 2
        for value in values:
            updated = update_context_after_gateway_evidence(
                bundle,
                observed_value=value,
            )
            assert len(updated.remaining_world_ids) == 1
            # Once the owner evidence identifies the current mode, there must
            # be at least one observation-matched direct continuation.
            post_bounds = action_feasibility_bounds(
                __import__("feasibility_conflict_planner")._restricted_bundle(
                    bundle, updated.remaining_world_ids
                )
            )
            assert any(b.lower == 1 for b in post_bounds)
            resolved_branches += 1

    assert sound_bounds == 24
    assert resolved_branches == 48
    print(
        "PASS feasibility bounds + incremental context: 24 sound pre-query "
        "bound sets; 48 evidence branches regain a directly winning continuation"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
