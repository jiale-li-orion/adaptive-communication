#!/usr/bin/env python3
"""Freeze final Layer-1 paper release after deterministic + LLM tests close."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "results/benchmark/layer1-paper-final-release.json"
FILES = {
    "pre_release": ROOT / "results/benchmark/layer1-paper-release-candidate.json",
    "split": ROOT / "results/benchmark/layer1-paper-split.json",
    "baseline_protocol": ROOT / "research/benchmark/PAPER-BASELINE-PROTOCOL.json",
    "deterministic_statistics": ROOT / "results/benchmark/layer1-paper-deterministic-test/statistical-analysis.json",
    "deterministic_manifest": ROOT / "results/benchmark/layer1-paper-deterministic-test/run-manifest.json",
    "llm_aggregate": ROOT / "results/benchmark/layer1-paper-llm-test/aggregate.json",
    "llm_statistics": ROOT / "results/benchmark/layer1-paper-llm-test/statistical-analysis.json",
    "llm_manifest": ROOT / "results/benchmark/layer1-paper-llm-test/run-manifest.json",
    "fullsim_evaluator": ROOT / "results/benchmark/layer1-fullsim-evaluator-release-audit.json",
    "internal_source_audit": ROOT / "results/benchmark/layer1-internal-source-audit-2026-10-09.json",
    "track_inventory": ROOT / "results/benchmark/layer1-paper-track-inventory.json",
    "release_tracks": ROOT / "research/benchmark/LAYER1-RELEASE-TRACKS.json",
}


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def main() -> int:
    for name, path in FILES.items():
        if not path.exists():
            raise FileNotFoundError(f"missing final-release input {name}: {path}")
    pre = _load(FILES["pre_release"])
    split = _load(FILES["split"])
    det = _load(FILES["deterministic_statistics"])
    det_manifest = _load(FILES["deterministic_manifest"])
    llm = _load(FILES["llm_statistics"])
    llm_agg = _load(FILES["llm_aggregate"])
    llm_manifest = _load(FILES["llm_manifest"])
    evaluator = _load(FILES["fullsim_evaluator"])
    internal = _load(FILES["internal_source_audit"])
    inventory = _load(FILES["track_inventory"])
    tracks = _load(FILES["release_tracks"])
    stress = tracks["tracks"]["FUTURE_CHOICE_STRESS"]["surfaces"]
    checks = {
        "pre_release_bound": pre["status"] in {"PRE_RELEASE_BASELINE_PROTOCOL_PENDING_TEST_LOCKED", "PRE_RELEASE_TEST_EXECUTION_UNLOCKED_NOT_YET_RUN"},
        "deterministic_test_complete": bool(det_manifest.get("complete")) and all(det["checks"].values()),
        "llm_test_complete_60": bool(llm_manifest.get("complete")) and bool(llm_agg.get("complete")) and llm_agg.get("actual_rows") == 60,
        "llm_analysis_checks_pass": all(llm["checks"].values()),
        "fullsim_evaluator_pass": all(evaluator["checks"].values()),
        "internal_source_audit_pass": internal["status"] == "INTERNAL_ASSISTANT_AUDIT_PASS",
        "seven_release_candidate_surfaces": inventory["counts"]["paper_release_candidate_surface_count"] == 7,
        "paper_split_200_200_150": split["counts"] == {"train": 200, "dev": 200, "test": 150},
        "future_choice_stress_empty_and_separate": stress == [],
        "independent_external_expert_review_not_claimed": internal["independent_external_expert_review"] is False,
    }
    if not all(checks.values()):
        raise AssertionError(checks)
    payload = {
        "stage": "LAYER1_PAPER_FINAL_RELEASE",
        "release_status": "BENCHMARK_ADMIT",
        "status": "OPERATIONAL_CONFORMANCE_AND_INTERACTIVE_DECISION_RELEASED_FUTURE_CHOICE_STRESS_EMPTY",
        "git_commit_at_freeze": _head(),
        "tracks": {name: spec["surfaces"] for name, spec in tracks["tracks"].items()},
        "execution": {
            "split_counts": split["counts"],
            "deterministic_online_rows": 750,
            "deterministic_oracle_diagnostic_rows": 210,
            "llm_rows": 60,
            "llm_status_counts": llm["status_counts"],
        },
        "checks": checks,
        "files": {
            name: {"path": str(path.relative_to(ROOT)), "sha256": _sha(path), "bytes": path.stat().st_size}
            for name, path in sorted(FILES.items())
        },
        "limitations": [
            "Future-Choice-Stress is empty in Layer 1; F* method claims come from separate B/C evidence and do not retroactively redefine benchmark tasks.",
            "No independent external domain-expert audit was performed; source/task/evaluator review is internal assistant-led and disclosed.",
            "The 30-coordinate × 2-mode DeepSeek LLM subset is a model-spectrum diagnostic and is not extrapolated to all 150 deterministic coordinates.",
            "Historical v0.2/v0.6/v0.7 hard/evidence lineages remain regression/provenance and are not the paper-facing release identity."
        ],
        "immutability_rule": "Any source/task/evaluator/split/protocol change after this manifest requires a new paper benchmark release identity or a disclosed evaluator-flaw migration; method outcomes may not mutate the released task distribution."
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(OUT), "release_status": payload["release_status"], **checks}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
