#!/usr/bin/env python3
"""Audit integrity/completeness of the five-seed WOA-style baseline."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WOA_ROOT = ROOT / "results" / "agentic" / "woa-style-baseline-v1"
MODEL_ROOT = WOA_ROOT / "deepseek-flash"
AGG = MODEL_ROOT / "confirmatory-aggregate.json"
SEED0_MANIFEST = MODEL_ROOT / "source-manifest.json"
CONFIRM_MANIFEST = MODEL_ROOT / "confirmatory-source-manifest.json"
FAIRNESS = WOA_ROOT / "fairness-audit.json"
OUT = MODEL_ROOT / "confirmatory-audit.json"
TASKS = ("localized-o2", "o5", "o6")
SEEDS = tuple(range(5))


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main() -> int:
    failures: list[dict] = []
    if not AGG.is_file():
        raise SystemExit("confirmatory aggregate missing")
    aggregate = json.loads(AGG.read_text(encoding="utf-8"))
    rows = list(aggregate.get("rows") or [])

    expected = {(task, seed) for task in TASKS for seed in SEEDS}
    seen = {
        (str((row.get("config") or {}).get("task")), int((row.get("config") or {}).get("seed", -1)))
        for row in rows
    }
    if seen != expected:
        failures.append(
            {
                "type": "coordinate_set_mismatch",
                "missing": sorted(expected - seen),
                "unexpected": sorted(seen - expected),
            }
        )
    if int(aggregate.get("completed_rows") or 0) != 15 or len(rows) != 15:
        failures.append(
            {
                "type": "incomplete_rows",
                "completed_rows": aggregate.get("completed_rows"),
                "row_count": len(rows),
            }
        )

    fairness = json.loads(FAIRNESS.read_text(encoding="utf-8"))
    if fairness.get("status") != "PASS" or fairness.get("failures"):
        failures.append({"type": "fairness_audit_failed", "detail": fairness})
    if int(fairness.get("episodes") or 0) != 15 or int(fairness.get("planner_requests") or 0) != 123:
        failures.append(
            {
                "type": "fairness_coordinate_count_mismatch",
                "episodes": fairness.get("episodes"),
                "planner_requests": fairness.get("planner_requests"),
            }
        )

    seed0_manifest = json.loads(SEED0_MANIFEST.read_text(encoding="utf-8"))
    confirm_manifest = json.loads(CONFIRM_MANIFEST.read_text(encoding="utf-8"))
    if confirm_manifest.get("seed0_manifest_sha256") != _sha(SEED0_MANIFEST):
        failures.append({"type": "seed0_manifest_hash_mismatch"})
    files = confirm_manifest.get("files") or {}
    for rel, expected_hash in (files.get("seed0_shared_files") or {}).items():
        path = ROOT / rel
        current = _sha(path) if path.is_file() else None
        if current != expected_hash:
            failures.append(
                {
                    "type": "source_hash_mismatch",
                    "path": rel,
                    "expected": expected_hash,
                    "current": current,
                }
            )
    for rel, expected_hash in (files.get("confirmatory_runner") or {}).items():
        path = ROOT / rel
        current = _sha(path) if path.is_file() else None
        if current != expected_hash:
            failures.append(
                {
                    "type": "confirmatory_runner_hash_mismatch",
                    "path": rel,
                    "expected": expected_hash,
                    "current": current,
                }
            )

    replay_pass = 0
    authorization_turns = 0
    model_turns = 0
    config_rows = 0
    for row in rows:
        cfg = row.get("config") or {}
        config_ok = (
            cfg.get("model") == "deepseek-flash"
            and cfg.get("baseline_revision") == "woa-style-adaptation-v1"
            and cfg.get("protocol_revision") == "communication-planner-json-v6-no-action-sufficiency"
            and cfg.get("context_mode") == "woa_style"
            and cfg.get("planner_replan_mode") == "decision_state"
            and float(cfg.get("temperature", 1.0)) == 0.0
            and cfg.get("reasoning_effort") == "low"
            and int(cfg.get("max_tokens") or 0) == 8192
            and bool(cfg.get("json_object")) is True
            and int(cfg.get("max_model_calls") or 0) == 32
        )
        if config_ok:
            config_rows += 1
        else:
            failures.append(
                {
                    "type": "config_mismatch",
                    "task": cfg.get("task"),
                    "seed": cfg.get("seed"),
                    "config": cfg,
                }
            )
        replay = row.get("replay_audit") or {}
        if replay.get("passed") is True and all(
            (replay.get(level) or {}).get("passed") is True for level in ("R0", "R1", "R2")
        ):
            replay_pass += 1
        else:
            failures.append(
                {
                    "type": "replay_failed",
                    "task": cfg.get("task"),
                    "seed": cfg.get("seed"),
                    "replay": replay,
                }
            )

        auth_path = Path(str(row.get("authorization_records") or ""))
        if not auth_path.is_absolute():
            auth_path = ROOT / auth_path
        if not auth_path.is_file():
            failures.append(
                {
                    "type": "authorization_records_missing",
                    "task": cfg.get("task"),
                    "seed": cfg.get("seed"),
                    "path": str(auth_path),
                }
            )
            continue
        records = json.loads(auth_path.read_text(encoding="utf-8"))
        turns = int((row.get("assurance_audit") or {}).get("turns") or 0)
        if len(records) != turns:
            failures.append(
                {
                    "type": "authorization_turn_count_mismatch",
                    "task": cfg.get("task"),
                    "seed": cfg.get("seed"),
                    "records": len(records),
                    "assurance_turns": turns,
                }
            )
        authorization_turns += len(records)
        model_turns += int((row.get("planner_behavior_audit") or {}).get("successful_model_attempts") or 0)

    payload = {
        "experiment": "woa-style-baseline-v1-confirmatory-audit",
        "status": "PASS" if not failures else "FAIL",
        "source": str(AGG.relative_to(ROOT)),
        "complete_coordinate_set": seen == expected,
        "no_posthoc_exclusion": len(rows) == 15 and seen == expected,
        "config_rows_exact": config_rows,
        "replay_pass_rows": replay_pass,
        "authorization_turns": authorization_turns,
        "successful_model_turns": model_turns,
        "fairness_status": fairness.get("status"),
        "fairness_episodes": fairness.get("episodes"),
        "fairness_planner_requests": fairness.get("planner_requests"),
        "seed0_source_manifest_sha256": _sha(SEED0_MANIFEST),
        "confirmatory_source_manifest_sha256": _sha(CONFIRM_MANIFEST),
        "failures": failures,
        "adaptation_boundary": (
            "This audit validates the repository's WirelessOpsAgent-style same-interface adaptation; "
            "it is not an audit of the authors' official implementation."
        ),
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

