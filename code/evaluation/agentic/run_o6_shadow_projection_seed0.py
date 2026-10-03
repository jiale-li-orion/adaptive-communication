#!/usr/bin/env python3
"""Checkpointed O6 seed-0 rerun after shadow-only candidate projection fix."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]
RUNNER = Path(__file__).resolve().parent / "run_r3_model_eval.py"
OUT = ROOT / "results" / "agentic" / "main-table-v1b-shadow-projection" / "deepseek-flash" / "o6" / "seed-000"
ARMS = (
    "generic_react",
    "full_dump",
    "task_conditioned",
    "action_conditioned_compact",
)


def valid_summary(path: Path, arm: str) -> bool:
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    config = payload.get("config") or {}
    return (
        config.get("model") == "deepseek-flash"
        and config.get("episode") == "O6"
        and int(config.get("seed", -1)) == 0
        and config.get("context_mode") == arm
        and config.get("planner_replan_mode") == "decision_state"
        and float(config.get("temperature", 1.0)) == 0.0
        and config.get("reasoning_effort") == "low"
        and int(config.get("max_tokens") or 0) == 8192
        and bool(config.get("json_object")) is True
    )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for arm in ARMS:
        arm_out = OUT / arm
        summary = arm_out / "summary.json"
        if not valid_summary(summary, arm):
            arm_out.mkdir(parents=True, exist_ok=True)
            log = arm_out / "runner.log"
            cmd = [
                sys.executable,
                str(RUNNER),
                "--model", "deepseek-flash",
                "--episode", "O6",
                "--seed", "0",
                "--context-mode", arm,
                "--planner-replan-mode", "decision_state",
                "--credential-profile", "deepseek_official",
                "--temperature", "0",
                "--reasoning-effort", "low",
                "--max-tokens", "8192",
                "--json-object",
                "--max-model-calls", "32",
                "--out", str(arm_out),
            ]
            print(f"START {arm}", flush=True)
            with log.open("w", encoding="utf-8") as fh:
                rc = subprocess.run(
                    cmd,
                    cwd=ROOT,
                    stdout=fh,
                    stderr=subprocess.STDOUT,
                    check=False,
                ).returncode
            if rc != 0 or not valid_summary(summary, arm):
                print(f"FAIL {arm} rc={rc} log={log}", file=sys.stderr, flush=True)
                return 1
            print(f"DONE {arm}", flush=True)
        else:
            print(f"SKIP {arm}", flush=True)
        payload = json.loads(summary.read_text(encoding="utf-8"))
        audit = payload.get("planner_behavior_audit") or {}
        rows.append(
            {
                "context_mode": arm,
                "model_calls": payload.get("model_calls_consumed"),
                "effect_scope_exact_turns": audit.get("effect_scope_exact_turns"),
                "effect_scope_inexact_turns": audit.get("effect_scope_inexact_turns"),
                "local_observation_invocations": audit.get("local_observation_invocations"),
                "remote_observation_invocations": audit.get("remote_observation_invocations"),
                "physical_equal_candidate_reference": payload.get("physical_equal_candidate_reference"),
                "summary": str(summary),
            }
        )
    aggregate = OUT.parent / "seed0-summary.json"
    aggregate.write_text(
        json.dumps(
            {
                "experiment": "o6-shadow-projection-seed0",
                "completed_rows": len(rows),
                "expected_rows": len(ARMS),
                "rows": rows,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(f"COMPLETE {aggregate}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

