#!/usr/bin/env python3
"""Third V8 layer: deeper placement-preserving receding belief planning."""
from __future__ import annotations

from collections import Counter
import json

from audit_v8_baselines_v0_1 import _representatives
from v8_policy_baselines_v0_1 import solve_receding_horizon


PRIOR = "results/benchmark/layer1-v8-policy-ladder-v0.1.json"


def audit() -> dict:
    prior = json.load(open(PRIOR, encoding="utf-8"))
    survivor_ids = {
        str(r["recipe_id"])
        for r in prior["rows"]
        if r["disposition"] == "SURVIVES_POLICY_LADDER_V0_1"
    }
    reps = {
        str(bundle["recipe_id"]): (cell, bundle)
        for cell, (_rank, bundle) in _representatives().items()
        if str(bundle["recipe_id"]) in survivor_ids
    }
    rows = []
    coverage = Counter()
    disposition = Counter()
    for rid in sorted(survivor_ids):
        cell, bundle = reps[rid]
        results = {
            f"receding_horizon_{k}": solve_receding_horizon(bundle, horizon_decisions=k)
            for k in (4, 5, 6)
        }
        winners = sorted(name for name, row in results.items() if row["solvable"])
        for name in winners:
            coverage[name] += 1
        cls = "SHORTCUT_SOLVED_DEEP_HORIZON" if winners else "SURVIVES_DEEP_HORIZON_V0_1"
        disposition[cls] += 1
        rows.append({
            "recipe_id": rid,
            "cell": list(cell),
            "disposition": cls,
            "winning_baselines": winners,
            "results": {
                name: {"solvable": row["solvable"], "decisions": row["decisions"]}
                for name, row in results.items()
            },
        })
    return {
        "schema_version": "0.1",
        "status": "V8_DEEP_HORIZON_AUDIT",
        "input_survivor_count": len(survivor_ids),
        "disposition": dict(sorted(disposition.items())),
        "baseline_coverage": dict(sorted(coverage.items())),
        "rows": rows,
    }


if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False, indent=2, sort_keys=True))
