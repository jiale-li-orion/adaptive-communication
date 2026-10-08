#!/usr/bin/env python3
"""Audit paper-construction track assignment against the task registry.

This audit deliberately does not infer hardness from method results.  It only
checks that every currently source-listed surface has exactly one paper role:
release-track candidate or explicit blocked disposition, and that blocked T2
surfaces remain simulator gaps in the canonical task registry.
"""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
TRACKS = ROOT / "research/benchmark/LAYER1-RELEASE-TRACKS.json"
REGISTRY = ROOT / "research/benchmark/TASK-SURFACE-REGISTRY.v0.1.json"


def main() -> int:
    tracks = json.loads(TRACKS.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

    canonical = {}
    for family in registry["families"].values():
        for row in family["task_surfaces"]:
            canonical[row["surface_id"]] = row

    assigned = {}
    duplicates = []
    for track_name, spec in tracks["tracks"].items():
        for sid in spec["surfaces"]:
            if sid in assigned:
                duplicates.append((sid, assigned[sid], track_name))
            assigned[sid] = track_name
    for sid in tracks["blocked"]:
        if sid in assigned:
            duplicates.append((sid, assigned[sid], "BLOCKED"))
        assigned[sid] = "BLOCKED"

    missing = sorted(set(canonical) - set(assigned))
    unknown = sorted(set(assigned) - set(canonical))

    t2_blocked_not_gap = {
        sid: canonical[sid]["standalone_disposition"]
        for sid in tracks["blocked"]
        if sid.startswith("T2.")
        and canonical.get(sid, {}).get("standalone_disposition") != "SIMULATOR_GAP"
    }

    stress = tracks["tracks"]["FUTURE_CHOICE_STRESS"]["surfaces"]
    checks = {
        "every_canonical_surface_has_one_role": not missing and not duplicates,
        "no_unknown_surface_ids": not unknown,
        "blocked_t2_remains_simulator_gap": not t2_blocked_not_gap,
        "future_choice_stress_is_explicit_not_inferred": isinstance(stress, list),
        "method_claim_does_not_block_benchmark_release": (
            "does not wait" in tracks["graduation_rule"]["benchmark_release"]
            or "does not wait" in tracks["graduation_rule"]["benchmark_release"].lower()
        )
    }
    payload = {
        "stage": "LAYER1_RELEASE_TRACK_AUDIT",
        "checks": checks,
        "assigned": assigned,
        "missing": missing,
        "duplicates": duplicates,
        "unknown": unknown,
        "blocked_t2_not_simulator_gap": t2_blocked_not_gap
    }
    assert all(checks.values()), payload
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
