#!/usr/bin/env python3
"""Checkpointed DeepSeek Flash seed-0 main table for Agentic Communication.

This driver is intentionally boring: experiment design is frozen in code and a
process supervisor only needs to run/monitor it.  Completed arms with a valid
matching ``summary.json`` are skipped, so restarting the driver does not burn
the same API calls twice.
"""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
R3 = HERE / "run_r3_model_eval.py"
OUT_ROOT = ROOT / "results" / "agentic" / "main-table-v1" / "deepseek-flash"

MODEL = "deepseek-flash"
SEED = 0
REPLAN_MODE = "decision_state"
ARMS = (
    "generic_react",
    "full_dump",
    "task_conditioned",
    "action_conditioned_compact",
)
TASKS = (
    ("localized-o2", ("--variant", "localized")),
    ("o5", ("--episode", "O5")),
    ("o6", ("--episode", "O6")),
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _valid_completed_summary(path: Path, *, arm: str, task_label: str) -> bool:
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    config = payload.get("config") or {}
    expected_episode = {"localized-o2": None, "o5": "O5", "o6": "O6"}[task_label]
    expected_variant = "localized" if task_label == "localized-o2" else "global"
    return all(
        (
            config.get("model") == MODEL,
            int(config.get("seed", -1)) == SEED,
            config.get("context_mode") == arm,
            config.get("planner_replan_mode") == REPLAN_MODE,
            config.get("episode") == expected_episode,
            config.get("variant") == expected_variant,
            float(config.get("temperature", 1.0)) == 0.0,
            config.get("reasoning_effort") == "low",
            int(config.get("max_tokens") or 0) == 8192,
            bool(config.get("json_object")) is True,
            config.get("credential_profile") == "deepseek_official",
        )
    )


def _command(*, task_args: tuple[str, ...], arm: str, out: Path) -> list[str]:
    return [
        sys.executable,
        str(R3),
        "--model",
        MODEL,
        *task_args,
        "--seed",
        str(SEED),
        "--context-mode",
        arm,
        "--planner-replan-mode",
        REPLAN_MODE,
        "--credential-profile",
        "deepseek_official",
        "--temperature",
        "0",
        "--reasoning-effort",
        "low",
        "--max-tokens",
        "8192",
        "--json-object",
        "--max-model-calls",
        "32",
        "--out",
        str(out),
    ]


def _usage_from_trace(path: Path) -> dict:
    input_tokens = 0
    output_tokens = 0
    total_tokens = 0
    latency_ms = 0.0
    if not path.exists():
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "latency_ms": 0.0,
        }
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if event.get("event_type") != "model_usage":
            continue
        usage = event.get("payload") or {}
        input_tokens += int(usage.get("input_tokens") or 0)
        output_tokens += int(usage.get("output_tokens") or 0)
        total_tokens += int(usage.get("total_tokens") or 0)
        latency_ms += float(usage.get("latency_ms") or 0.0)
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "latency_ms": latency_ms,
    }


def _aggregate() -> Path:
    rows: list[dict] = []
    for task_label, _ in TASKS:
        for arm in ARMS:
            out = OUT_ROOT / task_label / f"seed-{SEED:03d}" / arm
            summary_path = out / "summary.json"
            if not _valid_completed_summary(summary_path, arm=arm, task_label=task_label):
                continue
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
            audit = payload.get("planner_behavior_audit") or {}
            usage = _usage_from_trace(out / "runtime_trace.jsonl")
            rows.append(
                {
                    "task": task_label,
                    "seed": SEED,
                    "context_mode": arm,
                    "model_calls": payload.get("model_calls_consumed"),
                    "successful_model_attempts": audit.get("successful_model_attempts"),
                    "failed_model_attempts": audit.get("failed_model_attempts"),
                    "effect_scope_exact_turns": audit.get("effect_scope_exact_turns"),
                    "effect_scope_inexact_turns": audit.get("effect_scope_inexact_turns"),
                    "local_observation_invocations": audit.get("local_observation_invocations"),
                    "remote_observation_invocations": audit.get("remote_observation_invocations"),
                    "physical_equal_candidate_reference": payload.get(
                        "physical_equal_candidate_reference"
                    ),
                    "physical_equal_legacy": payload.get("physical_equal_legacy"),
                    "usage": usage,
                    "communication_metrics": payload.get("communication_metrics") or {},
                    "delta_vs_candidate_reference": payload.get(
                        "delta_vs_candidate_reference"
                    ),
                    "summary": str(summary_path),
                }
            )
    result = {
        "experiment": "agentic-main-table-v1-seed0",
        "generated_at": _now(),
        "model": MODEL,
        "seed": SEED,
        "planner_replan_mode": REPLAN_MODE,
        "expected_rows": len(TASKS) * len(ARMS),
        "completed_rows": len(rows),
        "rows": rows,
    }
    path = OUT_ROOT / "seed0-main-table-summary.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--aggregate-only", action="store_true")
    args = ap.parse_args()

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    progress = OUT_ROOT / "seed0-progress.jsonl"

    if args.aggregate_only:
        print(_aggregate())
        return 0

    for task_label, task_args in TASKS:
        for arm in ARMS:
            out = OUT_ROOT / task_label / f"seed-{SEED:03d}" / arm
            summary_path = out / "summary.json"
            cmd = _command(task_args=task_args, arm=arm, out=out)
            if _valid_completed_summary(summary_path, arm=arm, task_label=task_label):
                print(f"SKIP complete {task_label}/{arm}: {summary_path}", flush=True)
                continue
            if args.dry_run:
                print(" ".join(cmd))
                continue

            out.mkdir(parents=True, exist_ok=True)
            log_path = out / "runner.log"
            with progress.open("a", encoding="utf-8") as fp:
                fp.write(
                    json.dumps(
                        {
                            "at": _now(),
                            "event": "start",
                            "task": task_label,
                            "arm": arm,
                            "out": str(out),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
            print(f"START {task_label}/{arm} -> {out}", flush=True)
            with log_path.open("w", encoding="utf-8") as log:
                proc = subprocess.run(
                    cmd,
                    cwd=ROOT,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    text=True,
                    check=False,
                )
            ok = proc.returncode == 0 and _valid_completed_summary(
                summary_path, arm=arm, task_label=task_label
            )
            with progress.open("a", encoding="utf-8") as fp:
                fp.write(
                    json.dumps(
                        {
                            "at": _now(),
                            "event": "done" if ok else "failed",
                            "task": task_label,
                            "arm": arm,
                            "returncode": proc.returncode,
                            "summary_exists": summary_path.exists(),
                            "log": str(log_path),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
            if not ok:
                print(
                    f"FAIL {task_label}/{arm} rc={proc.returncode}; inspect {log_path}",
                    file=sys.stderr,
                    flush=True,
                )
                _aggregate()
                return 1
            print(f"DONE {task_label}/{arm}", flush=True)
            _aggregate()

    summary = _aggregate()
    print(f"COMPLETE {summary}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
