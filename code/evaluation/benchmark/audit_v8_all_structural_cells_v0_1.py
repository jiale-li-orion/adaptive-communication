#!/usr/bin/env python3
"""Ordinary-baseline coverage over all 216 VALIDITY_PENDING structural cells."""
from __future__ import annotations

from collections import Counter
import json

from audit_v8_baselines_v0_1 import _representatives
from ordinary_baselines_compositional_v0_1 import audit_bundle


def audit() -> dict:
    disposition = Counter()
    same_information_coverage = Counter()
    deployment_coverage = Counter()
    by_structure = Counter()
    rows = []
    for cell, (_rank, bundle) in sorted(_representatives().items()):
        baselines = audit_bundle(bundle)
        same_information_winners = sorted(
            name
            for name, row in baselines.items()
            if row.get("legal")
            and row.get("robust_success") is True
            and row.get("comparison_role") == "SAME_INFORMATION_SHORTCUT"
        )
        deployment_winners = sorted(
            name
            for name, row in baselines.items()
            if row.get("legal")
            and row.get("robust_success") is True
            and row.get("comparison_role") == "DEPLOYMENT_ALTERNATIVE"
        )
        cls = (
            "SHORTCUT_SOLVED_SAME_INFORMATION"
            if same_information_winners
            else "SURVIVES_SAME_INFORMATION_ORDINARY_BASELINES"
        )
        disposition[cls] += 1
        for name in same_information_winners:
            same_information_coverage[name] += 1
        for name in deployment_winners:
            deployment_coverage[name] += 1
        by_structure[(cell[0], cell[1], cls)] += 1
        rows.append(
            {
                "cell": list(cell),
                "recipe_id": bundle["recipe_id"],
                "disposition": cls,
                "same_information_shortcut_baselines": same_information_winners,
                "deployment_alternatives": deployment_winners,
            }
        )
    return {
        "schema_version": "0.1",
        "status": "V8_ALL_STRUCTURAL_CELLS_ORDINARY_BASELINE_AUDIT",
        "cell_count": len(rows),
        "disposition": dict(sorted(disposition.items())),
        "same_information_shortcut_coverage": dict(sorted(same_information_coverage.items())),
        "deployment_alternative_coverage": dict(sorted(deployment_coverage.items())),
        "by_structure": {
            f"{a}|{b}|{c}": v
            for (a, b, c), v in sorted(by_structure.items())
        },
        "rows": rows,
    }


if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False, indent=2, sort_keys=True))
