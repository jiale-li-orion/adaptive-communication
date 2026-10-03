#!/usr/bin/env python3
"""Formal five-seed MiMo audit for the frozen query-positive coordinate."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "results" / "agentic" / "query-positive-gateway-backup-v1"
MODEL_ROOT = BASE / "mimo-v2.6-flash"
SEED0_MANIFEST = BASE / "mimo-seed0-source-manifest.json"
CONFIRM_MANIFEST = BASE / "mimo-confirmatory-safe-source-manifest.json"
OUT = BASE / "mimo-confirmatory-audit.json"
SEEDS = tuple(range(5))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    failures: list[dict] = []
    seed0_manifest = json.loads(SEED0_MANIFEST.read_text(encoding="utf-8"))
    confirm_manifest = json.loads(CONFIRM_MANIFEST.read_text(encoding="utf-8"))

    # Freeze integrity: every shared base source must still match the seed0
    # manifest, and the confirmatory manifest must point back to it.
    for rel, expected in (seed0_manifest.get("base_files") or {}).items():
        path = ROOT / rel
        actual = _sha(path) if path.is_file() else None
        if actual != expected:
            failures.append({"type": "source_hash", "path": rel, "expected": expected, "actual": actual})
    if confirm_manifest.get("mimo_seed0_manifest_sha256") != _sha(SEED0_MANIFEST):
        failures.append({"type": "seed0_manifest_link"})

    rows = []
    for seed in SEEDS:
        path = MODEL_ROOT / f"seed-{seed:03d}" / "summary.json"
        if not path.is_file():
            failures.append({"type": "missing_summary", "seed": seed})
            continue
        row = json.loads(path.read_text(encoding="utf-8"))
        rows.append(row)
        cfg = row.get("config") or {}
        planner = row.get("planner_behavior_audit") or {}
        query = row.get("query_behavior_audit") or {}
        replay = row.get("replay_audit") or {}
        delta = row.get("delta_vs_no_acquisition") or {}
        if row.get("status") != "PASS":
            failures.append({"type": "status", "seed": seed, "value": row.get("status")})
        if cfg.get("model") != "mimo-v2.6-flash" or int(cfg.get("seed", -1)) != seed:
            failures.append({"type": "coordinate", "seed": seed, "config": cfg})
        if planner.get("failed_model_attempts") != 0:
            failures.append({"type": "model_failure", "seed": seed})
        if planner.get("effect_scope_inexact_turns") != 0:
            failures.append({"type": "effect_inexact", "seed": seed})
        if query.get("covered_all_open_query_capabilities") is not True:
            failures.append({"type": "query_coverage", "seed": seed})
        if query.get("backup_effect_count") != 1:
            failures.append({"type": "backup_effect_count", "seed": seed, "value": query.get("backup_effect_count")})
        if row.get("physical_equal_deterministic_query_positive_reference") is not True:
            failures.append({"type": "physical_reference", "seed": seed})
        if replay.get("passed") is not True:
            failures.append({"type": "replay", "seed": seed})
        if float(delta.get("timely_delivery_rate") or 0.0) <= 0:
            failures.append({"type": "tdr_gain", "seed": seed, "value": delta.get("timely_delivery_rate")})
        if float(delta.get("aoi_mean_s") or 0.0) >= 0:
            failures.append({"type": "aoi_gain", "seed": seed, "value": delta.get("aoi_mean_s")})

    total_turns = sum(int((row.get("planner_behavior_audit") or {}).get("planner_decision_turns") or 0) for row in rows)
    exact_turns = sum(int((row.get("planner_behavior_audit") or {}).get("effect_scope_exact_turns") or 0) for row in rows)
    failed_attempts = sum(int((row.get("planner_behavior_audit") or {}).get("failed_model_attempts") or 0) for row in rows)
    query_count = sum(int((row.get("planner_behavior_audit") or {}).get("remote_observation_invocations") or 0) for row in rows)
    backup_effects = sum(int((row.get("query_behavior_audit") or {}).get("backup_effect_count") or 0) for row in rows)
    tdr_deltas = [float((row.get("delta_vs_no_acquisition") or {}).get("timely_delivery_rate") or 0.0) for row in rows]
    aoi_deltas = [float((row.get("delta_vs_no_acquisition") or {}).get("aoi_mean_s") or 0.0) for row in rows]
    payload = {
        "experiment": "query-positive-gateway-backup-v1-mimo-confirmatory-audit",
        "status": "PASS" if not failures and len(rows) == 5 else "FAIL",
        "completed_rows": len(rows),
        "expected_rows": 5,
        "model": "mimo-v2.6-flash",
        "planner_turns": total_turns,
        "effect_scope_exact_turns": exact_turns,
        "failed_model_attempts": failed_attempts,
        "owner_query_invocations": query_count,
        "gateway_backup_applied_effects": backup_effects,
        "physical_reference_exact_episodes": sum(
            row.get("physical_equal_deterministic_query_positive_reference") is True for row in rows
        ),
        "positive_tdr_gain_episodes": sum(delta > 0 for delta in tdr_deltas),
        "negative_aoi_delta_episodes": sum(delta < 0 for delta in aoi_deltas),
        "mean_tdr_gain": sum(tdr_deltas) / len(tdr_deltas) if tdr_deltas else None,
        "mean_aoi_delta_s": sum(aoi_deltas) / len(aoi_deltas) if aoi_deltas else None,
        "failures": failures,
        "claim_boundary": (
            "Second-model confirmatory on the same frozen gateway-backup query-positive family. "
            "Supports model-transfer of the acquisition loop only; does not establish globally optimal acquisition."
        ),
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

