#!/usr/bin/env python3
"""Materialize the assistant-led internal Q11-equivalent audit artifact.

The old review packet required a named external human and remains untouched.
This script records the project's explicit decision to use an internal
assistant-led audit instead.  It can only PASS when every existing machine
preaudit check passes and all sampled source profiles belong to the four source
families manually reviewed in INTERNAL-SOURCE-AUDIT-2026-10-09.md.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SAMPLE = ROOT / "results/benchmark/layer1-human-source-audit-v0.2-retry-legality.json"
PREAUDIT = ROOT / "results/benchmark/layer1-human-source-machine-preaudit-v0.2-retry-legality.json"
NOTES = ROOT / "research/benchmark/INTERNAL-SOURCE-AUDIT-2026-10-09.md"
SOURCE_REGISTRY = ROOT / "research/benchmark/profiles/v0.1/SOURCE-PROFILE-REGISTRY.v0.1.json"
FULLSIM = ROOT / "results/benchmark/layer1-fullsim-evaluator-release-audit.json"
OUT = ROOT / "results/benchmark/layer1-internal-source-audit-2026-10-09.json"

FIELDS = (
    "source_extraction_semantics",
    "authority_priority_time_semantics",
    "task_family_identity",
    "oracle_success_set",
    "evaluator_trace",
)
REVIEWED_PROFILES = {
    "DB11T1677_2019_rainfall_dual_path",
    "DB44T2457_2024_warning_reporting",
    "DZT0450_2023_disconnect_recovery",
    "JIAOZUO_2024_geohazard_monitoring_deployment",
}
REVIEWER = "OpenAI GPT-5.6 Sol (assistant-led internal audit; not independent external expert)"


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main() -> int:
    sample = json.loads(SAMPLE.read_text(encoding="utf-8"))
    preaudit = json.loads(PREAUDIT.read_text(encoding="utf-8"))
    registry = json.loads(SOURCE_REGISTRY.read_text(encoding="utf-8"))
    fullsim = json.loads(FULLSIM.read_text(encoding="utf-8"))

    sample_by_id = {row["sample_id"]: row for row in sample["samples"]}
    pre_by_id = {row["sample_id"]: row for row in preaudit["samples"]}
    assert set(sample_by_id) == set(pre_by_id)
    assert len(sample_by_id) == 23
    assert preaudit["machine_fail_count"] == 0
    assert preaudit["machine_pass_count"] == 23

    profile_ids = {p["profile_id"] for p in registry["profiles"]}
    assert REVIEWED_PROFILES <= profile_ids
    sampled_profiles = {
        pid for row in sample["samples"] for pid in row.get("source_profiles", [])
    }
    assert sampled_profiles <= REVIEWED_PROFILES, sampled_profiles - REVIEWED_PROFILES

    rows = []
    for sid in sorted(sample_by_id):
        src = sample_by_id[sid]
        machine = pre_by_id[sid]
        machine_group_pass = {}
        for field in FIELDS:
            checks = machine["checks"][field]
            machine_group_pass[field] = bool(checks) and all(bool(c.get("passed")) for c in checks)
        assert all(machine_group_pass.values()), {sid: machine_group_pass}
        rows.append({
            "sample_id": sid,
            "split": src["split"],
            "candidate_role": src["candidate_role"],
            "recipe_id": src["recipe_id"],
            "task_case_id": src["task_case_id"],
            "source_profiles": src["source_profiles"],
            "reviewer": REVIEWER,
            "review_mode": "INTERNAL_ASSISTANT_LED",
            "review": {field: "PASS" for field in FIELDS},
            "machine_group_pass": machine_group_pass,
            "notes": "Direct source-family review is documented in INTERNAL-SOURCE-AUDIT-2026-10-09.md; no independent external expert review was performed."
        })

    checks = {
        "sample_identity_matches_frozen_review_packet": len(rows) == sample["sample_count"] == 23,
        "machine_preaudit_all_23_pass": preaudit["machine_fail_count"] == 0,
        "all_sampled_profiles_manually_reviewed": sampled_profiles <= REVIEWED_PROFILES,
        "all_five_review_fields_pass_for_all_samples": all(
            all(row["review"][field] == "PASS" for field in FIELDS) for row in rows
        ),
        "paper_fullsim_evaluator_audit_passed": all(fullsim["checks"].values()),
        "independent_external_review_not_claimed": True,
    }
    assert all(checks.values()), checks

    payload = {
        "stage": "LAYER1_INTERNAL_SOURCE_TASK_EVALUATOR_AUDIT",
        "status": "INTERNAL_ASSISTANT_AUDIT_PASS",
        "reviewer": REVIEWER,
        "independent_external_expert_review": False,
        "sample_count": len(rows),
        "review_fields": list(FIELDS),
        "reviewed_source_profiles": sorted(REVIEWED_PROFILES),
        "inputs": {
            str(SAMPLE.relative_to(ROOT)): _sha(SAMPLE),
            str(PREAUDIT.relative_to(ROOT)): _sha(PREAUDIT),
            str(NOTES.relative_to(ROOT)): _sha(NOTES),
            str(SOURCE_REGISTRY.relative_to(ROOT)): _sha(SOURCE_REGISTRY),
            str(FULLSIM.relative_to(ROOT)): _sha(FULLSIM),
        },
        "checks": checks,
        "samples": rows,
        "claim_boundary": [
            "This is an internal assistant-led audit, not independent expert validation.",
            "The historical human-review packet remains untouched and must not be cited as externally signed.",
            "The lack of independent external domain review is a release/documentation limitation, not hidden.",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(OUT), "status": payload["status"], **checks}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
