#!/usr/bin/env python3
"""Formal audit for the held-out Qili/NASA-POWER v7 two-model table."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RESULT_ROOT = ROOT / "results" / "agentic" / "heldout-qili-2024-w1" / "model-transfer-v7"
AGG = RESULT_ROOT / "confirmatory-aggregate.json"
MANIFEST = RESULT_ROOT / "confirmatory-source-manifest.json"
OUT = RESULT_ROOT / "confirmatory-audit.json"
MODELS = ("deepseek-flash", "mimo-v2.6-flash")
SEEDS = tuple(range(5))


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main() -> int:
    failures: list[dict] = []
    aggregate = json.loads(AGG.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    if int(aggregate.get("completed_rows") or 0) != 10:
        failures.append({"type": "incomplete_rows", "value": aggregate.get("completed_rows")})
    if int(aggregate.get("expected_rows") or 0) != 10:
        failures.append({"type": "unexpected_expected_rows", "value": aggregate.get("expected_rows")})

    expected_coords = {(model, seed) for model in MODELS for seed in SEEDS}
    seen = []
    for row in aggregate.get("rows") or []:
        cfg = row.get("config") or {}
        coord = (str(cfg.get("model")), int(cfg.get("seed", -1)))
        seen.append(coord)
        if cfg.get("context_mode") != "action_conditioned_compact_v7":
            failures.append({"type": "context_mode", "coord": coord, "value": cfg.get("context_mode")})
        if cfg.get("protocol_revision") != "communication-planner-json-v7-retired-plan-projection":
            failures.append({"type": "protocol_revision", "coord": coord, "value": cfg.get("protocol_revision")})
        if cfg.get("heldout_coordinate") != "qili-2024-w1":
            failures.append({"type": "heldout_coordinate", "coord": coord})
        if cfg.get("source_split") != "test" or int(cfg.get("irradiance_year", -1)) != 2024:
            failures.append({"type": "source_split", "coord": coord})
        if row.get("physical_equal_legacy") is not True:
            failures.append({"type": "physical_legacy_divergence", "coord": coord})
        if row.get("physical_equal_candidate_reference") is not True:
            failures.append({"type": "physical_candidate_divergence", "coord": coord})
        replay = row.get("replay_audit") or {}
        if replay.get("passed") is not True:
            failures.append({"type": "replay_audit", "coord": coord, "value": replay})
        else:
            for level in ("R0", "R1", "R2"):
                if (replay.get(level) or {}).get("passed") is not True:
                    failures.append(
                        {
                            "type": "replay_level",
                            "coord": coord,
                            "level": level,
                            "value": replay.get(level),
                        }
                    )
        trace = ROOT / str(row.get("trace"))
        if not trace.is_file():
            failures.append({"type": "missing_trace", "coord": coord, "path": str(trace)})

    if len(seen) != len(set(seen)):
        failures.append({"type": "duplicate_coordinate", "seen": seen})
    if set(seen) != expected_coords:
        failures.append(
            {
                "type": "coordinate_set",
                "missing": sorted(expected_coords - set(seen)),
                "extra": sorted(set(seen) - expected_coords),
            }
        )

    files = manifest.get("files") or {}
    seed0_files = files.get("seed0_shared_files") or {}
    for rel, expected in seed0_files.items():
        path = ROOT / rel
        actual = _sha(path) if path.is_file() else None
        if actual != expected:
            failures.append(
                {"type": "source_hash", "path": rel, "expected": expected, "actual": actual}
            )
    for rel, expected in (files.get("confirmatory_runner") or {}).items():
        path = ROOT / rel
        actual = _sha(path) if path.is_file() else None
        if actual != expected:
            failures.append(
                {"type": "runner_hash", "path": rel, "expected": expected, "actual": actual}
            )

    by_model = {}
    for model in MODELS:
        rows = [row for row in aggregate.get("rows") or [] if (row.get("config") or {}).get("model") == model]
        by_model[model] = {
            "episodes": len(rows),
            "planner_turns": sum(int((row.get("planner_behavior_audit") or {}).get("planner_decision_turns") or 0) for row in rows),
            "effect_exact_turns": sum(int((row.get("planner_behavior_audit") or {}).get("effect_scope_exact_turns") or 0) for row in rows),
            "effect_inexact_turns": sum(int((row.get("planner_behavior_audit") or {}).get("effect_scope_inexact_turns") or 0) for row in rows),
            "observations": sum(
                int((row.get("planner_behavior_audit") or {}).get("local_observation_invocations") or 0)
                + int((row.get("planner_behavior_audit") or {}).get("remote_observation_invocations") or 0)
                for row in rows
            ),
            "failed_model_attempts": sum(int((row.get("planner_behavior_audit") or {}).get("failed_model_attempts") or 0) for row in rows),
            "physical_legacy_exact_episodes": sum(row.get("physical_equal_legacy") is True for row in rows),
        }

    payload = {
        "experiment": "heldout-qili-2024-w1-model-transfer-v7-confirmatory-audit",
        "status": "PASS" if not failures else "FAIL",
        "source": str(AGG.relative_to(ROOT)),
        "source_manifest": str(MANIFEST.relative_to(ROOT)),
        "complete_coordinate_set": set(seen) == expected_coords and len(seen) == 10,
        "no_posthoc_exclusion": set(seen) == expected_coords and len(seen) == 10,
        "by_model": by_model,
        "failures": failures,
        "claim_boundary": (
            "Held-out Qili source-derived Operational Task + NASA POWER 2024 test/w1, five seeds, "
            "DeepSeek Flash and MiMo v2.6 Flash. This supports task/source/model transfer of action "
            "and physical fidelity only. Do not compare token counts across providers and do not infer "
            "autonomous evidence acquisition; all measured coordinates remain query-negative."
        ),
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

