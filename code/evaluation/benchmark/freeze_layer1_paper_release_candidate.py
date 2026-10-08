#!/usr/bin/env python3
"""Freeze the current paper-facing Layer-1 pre-release candidate manifest.

The manifest binds semantic coverage, the fresh execution split, the full-sim
execution evaluator audit and the internal source/task/evaluator audit.  It is
not BENCHMARK_ADMIT: the paper baseline/policy protocol is still open and the
150-coordinate test outcomes remain locked.

Future-Choice Stress is recorded separately and may remain empty without
invalidating the Operational-Conformance / Interactive-Decision benchmark
tracks.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "results/benchmark/layer1-paper-release-candidate.json"

FILES = {
    "semantic_inventory": ROOT / "results/benchmark/layer1-paper-track-inventory.json",
    "execution_split": ROOT / "results/benchmark/layer1-paper-split.json",
    "fullsim_evaluator_audit": ROOT / "results/benchmark/layer1-fullsim-evaluator-release-audit.json",
    "internal_source_audit": ROOT / "results/benchmark/layer1-internal-source-audit-2026-10-09.json",
    "task_registry": ROOT / "research/benchmark/TASK-SURFACE-REGISTRY.v0.1.json",
    "source_registry": ROOT / "research/benchmark/profiles/v0.1/SOURCE-PROFILE-REGISTRY.v0.1.json",
    "release_tracks": ROOT / "research/benchmark/LAYER1-RELEASE-TRACKS.json",
    "quality_gate": ROOT / "research/benchmark/BENCHMARK-QUALITY-GATE.v0.1.md",
    "system_model": ROOT / "research/substrate/SYSTEM-MODEL-v1.md",
    "paper_positioning": ROOT / "research/benchmark/BENCHMARK-PAPER-POSITIONING.md",
    "baseline_protocol": ROOT / "research/benchmark/PAPER-BASELINE-PROTOCOL.json",
}


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def main() -> int:
    inv = json.loads(FILES["semantic_inventory"].read_text(encoding="utf-8"))
    split = json.loads(FILES["execution_split"].read_text(encoding="utf-8"))
    evaluator = json.loads(FILES["fullsim_evaluator_audit"].read_text(encoding="utf-8"))
    internal = json.loads(FILES["internal_source_audit"].read_text(encoding="utf-8"))
    tracks = json.loads(FILES["release_tracks"].read_text(encoding="utf-8"))
    baseline_protocol = json.loads(FILES["baseline_protocol"].read_text(encoding="utf-8"))

    release_surfaces = sorted(
        row["surface_id"] for row in inv["surfaces"] if row["paper_release_candidate"]
    )
    evaluator_surfaces = sorted(evaluator["paper_surfaces_covered"])
    stress_surfaces = sorted(tracks["tracks"]["FUTURE_CHOICE_STRESS"]["surfaces"])

    checks = {
        "seven_release_candidate_surfaces": len(release_surfaces) == 7,
        "evaluator_covers_all_release_candidate_surfaces": release_surfaces == evaluator_surfaces,
        "fullsim_evaluator_audit_pass": all(evaluator["checks"].values()),
        "internal_source_audit_pass": internal["status"] == "INTERNAL_ASSISTANT_AUDIT_PASS",
        "independent_external_review_not_falsely_claimed": internal["independent_external_expert_review"] is False,
        "execution_split_200_200_150": split["counts"] == {"train": 200, "dev": 200, "test": 150},
        "fresh_test_identity_audit_pass": bool(split["contamination_audit"]["passed"]),
        "test_outcomes_locked": bool(split["access_policy"]["test_outcomes_locked"]),
        "future_choice_stress_separate_from_release": stress_surfaces == [],
        "baseline_protocol_frozen": baseline_protocol["status"] == "FROZEN_BEFORE_TEST_EXECUTION",
        "baseline_protocol_forbids_test_tuning": bool(baseline_protocol["test_tuning_forbidden"]),
    }
    assert all(checks.values()), checks

    payload = {
        "stage": "LAYER1_PAPER_PRE_RELEASE_CANDIDATE",
        "status": "PRE_RELEASE_TEST_EXECUTION_UNLOCKED_NOT_YET_RUN",
        "base_git_commit": _head(),
        "benchmark_scope": {
            "main_family": "T1_MONITORING_INFORMATION_CONTINUITY",
            "release_candidate_surfaces": release_surfaces,
            "release_candidate_surface_count": len(release_surfaces),
            "blocked_surface_count": int(inv["counts"]["blocked_surface_count"]),
            "tracks": {
                name: spec["surfaces"] for name, spec in tracks["tracks"].items()
            },
        },
        "execution_split": {
            "counts": split["counts"],
            "test_rule": split["split_rule"]["test"],
            "access_policy": split["access_policy"],
        },
        "audit_state": {
            "fullsim_evaluator": evaluator["checks"],
            "internal_source_audit": {
                "status": internal["status"],
                "sample_count": internal["sample_count"],
                "review_fields": internal["review_fields"],
                "independent_external_expert_review": internal["independent_external_expert_review"],
            },
        },
        "files": {
            name: {
                "path": str(path.relative_to(ROOT)),
                "bytes": path.stat().st_size,
                "sha256": _sha(path),
            }
            for name, path in sorted(FILES.items())
        },
        "checks": checks,
        "remaining_release_blockers": [
            "Execute the 150 locked test coordinates under the frozen protocol and produce statistical/failure reporting.",
            "Freeze the final release/result manifest after test execution."
        ],
        "method_stress_state": {
            "future_choice_stress_surface_count": len(stress_surfaces),
            "blocks_benchmark_release": False,
            "blocks_future_choice_method_claim": True,
        },
        "limitations": [
            "No independent external domain-expert review was performed; the completed source/task/evaluator review is assistant-led internal audit.",
            "The test cohort identities and baseline protocol are frozen; test outcomes remain unavailable until the frozen runner is executed.",
            "Future-Choice Stress is currently empty; Layer-2/3 method claims require a separate future hard subset and pristine method holdout."
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(OUT), "status": payload["status"], **checks}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
