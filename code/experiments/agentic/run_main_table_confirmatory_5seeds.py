#!/usr/bin/env python3
"""Checkpointed 5-seed confirmatory main table for the frozen Method v1."""
from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
R3 = HERE / "run_r3_model_eval.py"
OUT_ROOT = ROOT / "results" / "agentic" / "main-table-v2-confirmatory" / "deepseek-flash"

MODEL = "deepseek-flash"
REPLAN_MODE = "decision_state"
SEEDS = tuple(range(5))
# Run the frozen Method first. If confirmatory robustness fails, stop before
# spending the remaining baseline budget and return to research judgment.
ARMS = (
    "action_conditioned_compact",
    "task_conditioned",
    "full_dump",
    "generic_react",
)
TASKS = (
    ("localized-o2", ("--variant", "localized")),
    ("o5", ("--episode", "O5")),
    ("o6", ("--episode", "O6")),
)
SOURCE_FILES = (
    "code/agentic_communication/action_context.py",
    "code/agentic_communication/context_runtime.py",
    "code/agentic_communication/model_protocol.py",
    "code/agentic_communication/planner.py",
    "code/agentic_communication/policy.py",
    "code/agentic_communication/run.py",
    "code/agentic_communication/episodes.py",
    "code/experiments/agentic/run_r3_model_eval.py",
    "code/experiments/agentic/run_main_table_confirmatory_5seeds.py",
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _source_snapshot() -> dict:
    return {
        rel: _sha256(ROOT / rel)
        for rel in SOURCE_FILES
    }


def _ensure_source_manifest() -> None:
    path = OUT_ROOT / "source-manifest.json"
    current = _source_snapshot()
    if path.exists():
        frozen = json.loads(path.read_text(encoding="utf-8"))
        if frozen.get("files") != current:
            changed = sorted(
                rel
                for rel in set(current) | set(frozen.get("files") or {})
                if current.get(rel) != (frozen.get("files") or {}).get(rel)
            )
            raise RuntimeError(
                "confirmatory source changed after freeze; refuse mixed-code resume: "
                + ", ".join(changed)
            )
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "experiment": "agentic-main-table-v2-confirmatory",
                "frozen_at": _now(),
                "model": MODEL,
                "seeds": list(SEEDS),
                "tasks": [name for name, _ in TASKS],
                "arms": list(ARMS),
                "planner_replan_mode": REPLAN_MODE,
                "files": current,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _valid_summary(path: Path, *, task_label: str, seed: int, arm: str) -> bool:
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
            int(config.get("seed", -1)) == seed,
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


def _command(*, task_args: tuple[str, ...], seed: int, arm: str, out: Path) -> list[str]:
    return [
        sys.executable,
        str(R3),
        "--model", MODEL,
        *task_args,
        "--seed", str(seed),
        "--context-mode", arm,
        "--planner-replan-mode", REPLAN_MODE,
        "--credential-profile", "deepseek_official",
        "--temperature", "0",
        "--reasoning-effort", "low",
        "--max-tokens", "8192",
        "--json-object",
        "--max-model-calls", "32",
        "--out", str(out),
    ]


def _usage(trace: Path) -> dict:
    totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "latency_ms": 0.0}
    if not trace.exists():
        return totals
    for line in trace.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if event.get("event_type") != "model_usage":
            continue
        row = event.get("payload") or {}
        for key in ("input_tokens", "output_tokens", "total_tokens"):
            totals[key] += int(row.get(key) or 0)
        totals["latency_ms"] += float(row.get("latency_ms") or 0.0)
    return totals


def _aggregate() -> Path:
    rows: list[dict] = []
    for arm in ARMS:
        for task_label, _ in TASKS:
            for seed in SEEDS:
                out = OUT_ROOT / task_label / f"seed-{seed:03d}" / arm
                summary = out / "summary.json"
                if not _valid_summary(summary, task_label=task_label, seed=seed, arm=arm):
                    continue
                payload = json.loads(summary.read_text(encoding="utf-8"))
                audit = payload.get("planner_behavior_audit") or {}
                agent = payload.get("agent_metrics") or {}
                rows.append(
                    {
                        "task": task_label,
                        "seed": seed,
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
                        "mean_materialized_bytes": agent.get("mean_materialized_bytes"),
                        "capability_requests": agent.get("capability_requests"),
                        "physical_action_confirmation_rate": agent.get(
                            "physical_action_confirmation_rate"
                        ),
                        "usage": _usage(out / "runtime_trace.jsonl"),
                        "communication_metrics": payload.get("communication_metrics") or {},
                        "delta_vs_candidate_reference": payload.get(
                            "delta_vs_candidate_reference"
                        ),
                        "summary": str(summary),
                    }
                )
    result = {
        "experiment": "agentic-main-table-v2-confirmatory",
        "generated_at": _now(),
        "model": MODEL,
        "seeds": list(SEEDS),
        "tasks": [name for name, _ in TASKS],
        "arms": list(ARMS),
        "planner_replan_mode": REPLAN_MODE,
        "expected_rows": len(SEEDS) * len(TASKS) * len(ARMS),
        "completed_rows": len(rows),
        "rows": rows,
    }
    path = OUT_ROOT / "aggregate.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    _ensure_source_manifest()
    progress = OUT_ROOT / "progress.jsonl"
    for arm in ARMS:
        for task_label, task_args in TASKS:
            for seed in SEEDS:
                out = OUT_ROOT / task_label / f"seed-{seed:03d}" / arm
                summary = out / "summary.json"
                if _valid_summary(summary, task_label=task_label, seed=seed, arm=arm):
                    print(f"SKIP {arm}/{task_label}/seed-{seed:03d}", flush=True)
                    continue
                out.mkdir(parents=True, exist_ok=True)
                log = out / "runner.log"
                progress.parent.mkdir(parents=True, exist_ok=True)
                with progress.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps({
                        "at": _now(), "event": "start", "arm": arm,
                        "task": task_label, "seed": seed, "out": str(out),
                    }, ensure_ascii=False) + "\n")
                print(f"START {arm}/{task_label}/seed-{seed:03d}", flush=True)
                with log.open("w", encoding="utf-8") as fh:
                    rc = subprocess.run(
                        _command(task_args=task_args, seed=seed, arm=arm, out=out),
                        cwd=ROOT,
                        stdout=fh,
                        stderr=subprocess.STDOUT,
                        check=False,
                    ).returncode
                ok = rc == 0 and _valid_summary(
                    summary, task_label=task_label, seed=seed, arm=arm
                )
                with progress.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps({
                        "at": _now(), "event": "done" if ok else "failed",
                        "arm": arm, "task": task_label, "seed": seed,
                        "returncode": rc, "log": str(log),
                    }, ensure_ascii=False) + "\n")
                _aggregate()
                if not ok:
                    print(
                        f"FAIL {arm}/{task_label}/seed-{seed:03d} rc={rc} log={log}",
                        file=sys.stderr,
                        flush=True,
                    )
                    return 1
                print(f"DONE {arm}/{task_label}/seed-{seed:03d}", flush=True)
    aggregate = _aggregate()
    print(f"COMPLETE {aggregate}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

