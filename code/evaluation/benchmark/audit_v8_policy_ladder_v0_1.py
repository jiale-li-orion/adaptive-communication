#!/usr/bin/env python3
"""Second V8 layer: placement-preserving shallow/depth-k/receding baselines."""
from __future__ import annotations

from collections import Counter
import argparse
import json

from audit_v8_baselines_v0_1 import _representatives
from ordinary_baselines_compositional_v0_1 import audit_bundle
from v8_policy_baselines_v0_1 import solve_depth_k, solve_receding_horizon, solve_shallow_rule


def _first_layer_survivors():
    out = []
    for cell, (_rank, bundle) in sorted(_representatives().items()):
        ordinary = audit_bundle(bundle)
        winners = [
            name for name, row in ordinary.items()
            if row.get("legal")
            and row.get("robust_success") is True
            and row.get("comparison_role") == "SAME_INFORMATION_SHORTCUT"
        ]
        if not winners:
            out.append((cell, bundle))
    return out


def audit(*, max_cells: int | None = None) -> dict:
    rows = []
    coverage = Counter()
    disposition = Counter()
    survivors = _first_layer_survivors()
    if max_cells is not None:
        survivors = survivors[:max_cells]
    for cell, bundle in survivors:
        results = {
            "shallow_rule_combiner": solve_shallow_rule(bundle),
            "true_depth_1_belief": solve_depth_k(bundle, depth=1),
            "true_depth_2_belief": solve_depth_k(bundle, depth=2),
            "receding_horizon_3": solve_receding_horizon(bundle, horizon_decisions=3),
        }
        winners = sorted(name for name, row in results.items() if row["solvable"])
        for name in winners:
            coverage[name] += 1
        cls = "SHORTCUT_SOLVED_POLICY_LADDER" if winners else "SURVIVES_POLICY_LADDER_V0_1"
        disposition[cls] += 1
        rows.append({
            "cell": list(cell),
            "recipe_id": bundle["recipe_id"],
            "disposition": cls,
            "winning_baselines": winners,
            "results": {
                name: {"solvable": row["solvable"], "decisions": row["decisions"]}
                for name, row in results.items()
            },
        })
    return {
        "schema_version": "0.1",
        "status": "V8_POLICY_LADDER_AUDIT",
        "input_survivor_count": len(survivors),
        "disposition": dict(sorted(disposition.items())),
        "baseline_coverage": dict(sorted(coverage.items())),
        "rows": rows,
        "limitations": [
            "This layer still does not close V8: ordinary dependency/cache optimization and fair generic incremental AND-OR remain.",
            "Gateway-local autonomy is excluded here because it is tracked separately as a deployment alternative."
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-cells", type=int)
    args = ap.parse_args()
    print(json.dumps(audit(max_cells=args.max_cells), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
