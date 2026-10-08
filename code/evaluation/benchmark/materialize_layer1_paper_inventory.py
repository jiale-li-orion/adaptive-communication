#!/usr/bin/env python3
"""Materialize the paper-facing Layer-1 task/source inventory.

This artifact is intentionally upstream of case generation and method results.
It projects three current authorities:

* TASK-SURFACE-REGISTRY: canonical operational surfaces;
* SOURCE-PROFILE-REGISTRY: provenance / held-out grouping / unresolved fields;
* LAYER1-RELEASE-TRACKS: paper role (conformance / interactive / stress / blocked).

The output is not a benchmark release and contains no selected hard cases.  It
defines the semantic mother set from which a fresh paper-facing split can be
constructed without consulting Layer-2/3 performance.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
TASKS = ROOT / "research/benchmark/TASK-SURFACE-REGISTRY.v0.1.json"
SOURCES = ROOT / "research/benchmark/profiles/v0.1/SOURCE-PROFILE-REGISTRY.v0.1.json"
TRACKS = ROOT / "research/benchmark/LAYER1-RELEASE-TRACKS.json"
DEFAULT_OUT = ROOT / "results/benchmark/layer1-paper-track-inventory.json"


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _unresolved(profile: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for name, spec in (profile.get("variables") or {}).items():
        if spec.get("provenance_class") == "UNRESOLVED":
            rows.append({
                "field": name,
                "answer_relevant": bool(spec.get("answer_relevant")),
                "reason": spec.get("unresolved_reason"),
            })
    return rows


def build() -> dict[str, Any]:
    tasks = json.loads(TASKS.read_text(encoding="utf-8"))
    sources_doc = json.loads(SOURCES.read_text(encoding="utf-8"))
    tracks = json.loads(TRACKS.read_text(encoding="utf-8"))
    sources = {p["profile_id"]: p for p in sources_doc["profiles"]}

    role_by_surface: dict[str, str] = {}
    for track, spec in tracks["tracks"].items():
        for sid in spec["surfaces"]:
            role_by_surface[sid] = track
    for sid in tracks["blocked"]:
        role_by_surface[sid] = "BLOCKED"

    rows = []
    source_ids_used = set()
    for family_id, family in tasks["families"].items():
        for surface in family["task_surfaces"]:
            sid = surface["surface_id"]
            profile_rows = []
            source_families = set()
            jurisdictions = set()
            for pid in surface["source_profiles"]:
                if pid not in sources:
                    raise KeyError(f"{sid} references missing source profile {pid}")
                source_ids_used.add(pid)
                profile = sources[pid]
                heldout = profile.get("heldout_groups") or {}
                if heldout.get("SOURCE_FAMILY"):
                    source_families.add(str(heldout["SOURCE_FAMILY"]))
                if heldout.get("JURISDICTION"):
                    jurisdictions.add(str(heldout["JURISDICTION"]))
                refs = profile.get("source_refs") or []
                profile_rows.append({
                    "profile_id": pid,
                    "generator_status": profile.get("generator_status"),
                    "heldout_groups": heldout,
                    "direct_task_authority": any(
                        ref.get("directness") == "DIRECT_TASK_AUTHORITY" for ref in refs
                    ),
                    "source_classes": sorted({
                        str(ref.get("source_class")) for ref in refs if ref.get("source_class")
                    }),
                    "source_ids": sorted({
                        str(ref.get("source_id")) for ref in refs if ref.get("source_id")
                    }),
                    "unresolved_variables": _unresolved(profile),
                    "obligation_template_count": len(profile.get("obligation_templates") or []),
                    "capability_count": len(profile.get("capabilities") or []),
                })

            blocked_reason = tracks["blocked"].get(sid)
            role = role_by_surface[sid]
            rows.append({
                "family_id": family_id,
                "family_release_role": family["release_role"],
                "surface_id": sid,
                "semantics": surface["semantics"],
                "paper_track": role,
                "paper_release_candidate": role != "BLOCKED",
                "blocked_reason": blocked_reason,
                "standalone_disposition": surface["standalone_disposition"],
                "generator_role": surface["generator_role"],
                "historical_templates": surface["historical_templates"],
                "closure": surface["closure"],
                "source_profiles": profile_rows,
                "heldout_source_families": sorted(source_families),
                "heldout_jurisdictions": sorted(jurisdictions),
            })

    by_track: dict[str, int] = {}
    for row in rows:
        by_track[row["paper_track"]] = by_track.get(row["paper_track"], 0) + 1

    all_referenced_profiles_resolve = all(
        pid in sources
        for family in tasks["families"].values()
        for surface in family["task_surfaces"]
        for pid in surface["source_profiles"]
    )
    candidate_rows = [r for r in rows if r["paper_release_candidate"]]
    payload = {
        "stage": "LAYER1_PAPER_TRACK_SEMANTIC_INVENTORY",
        "status": "PAPER_CONSTRUCTION_INPUT_NOT_BENCHMARK_RELEASE",
        "inputs": {
            str(TASKS.relative_to(ROOT)): _digest(TASKS),
            str(SOURCES.relative_to(ROOT)): _digest(SOURCES),
            str(TRACKS.relative_to(ROOT)): _digest(TRACKS),
        },
        "counts": {
            "canonical_surface_count": len(rows),
            "paper_release_candidate_surface_count": len(candidate_rows),
            "blocked_surface_count": len(rows) - len(candidate_rows),
            "referenced_source_profile_count": len(source_ids_used),
            "by_track": dict(sorted(by_track.items())),
        },
        "fresh_split_coordinates": {
            "source_families": sorted({
                x for row in candidate_rows for x in row["heldout_source_families"]
            }),
            "jurisdictions": sorted({
                x for row in candidate_rows for x in row["heldout_jurisdictions"]
            }),
            "note": (
                "These are only semantic held-out coordinates present in the source profiles. "
                "A fresh case-level split must be frozen later from method-independent site/regime/trace instances."
            ),
        },
        "checks": {
            "all_referenced_source_profiles_resolve": all_referenced_profiles_resolve,
            "every_surface_has_paper_role": len(role_by_surface) == len(rows),
            "future_choice_stress_not_required_for_inventory": True,
            "inventory_does_not_read_layer2_or_layer3_results": True,
        },
        "surfaces": rows,
        "claim_boundary": [
            "This inventory freezes semantic paper coverage, not benchmark case identities or train/dev/test membership.",
            "Ordinary-solved surfaces may remain paper release candidates in Operational-Conformance or Interactive-Decision tracks.",
            "No Layer-2/3 score, hard-survivor label, LLM output or learned-policy result is an input dependency.",
            "Blocked surfaces remain visible for coverage/accountability and are not silently removed from the taxonomy."
        ],
    }
    if not all(payload["checks"].values()):
        raise AssertionError(payload["checks"])
    return payload


def main() -> int:
    payload = build()
    DEFAULT_OUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"out": str(DEFAULT_OUT), **payload["counts"], **payload["checks"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
