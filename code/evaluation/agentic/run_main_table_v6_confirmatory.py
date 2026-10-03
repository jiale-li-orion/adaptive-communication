#!/usr/bin/env python3
"""Protocol-v6 5-seed confirmatory main table with Method-first hard gate."""
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
OUT_ROOT = ROOT / "results" / "agentic" / "main-table-v6-confirmatory" / "deepseek-flash"

MODEL = "deepseek-flash"
PROTOCOL = "communication-planner-json-v6-no-action-sufficiency"
REPLAN_MODE = "decision_state"
SEEDS = tuple(range(5))
METHOD = "action_conditioned_compact"
ARMS = (METHOD, "task_conditioned", "full_dump", "generic_react")
TASKS = (
    ("localized-o2", ("--variant", "localized")),
    ("o5", ("--episode", "O5")),
    ("o6", ("--episode", "O6")),
)
SOURCE_FILES = (
    "code/agentic_communication/action_context.py",
    "code/agentic_communication/capabilities.py",
    "code/agentic_communication/context_runtime.py",
    "code/agentic_communication/model_protocol.py",
    "code/agentic_communication/planner.py",
    "code/agentic_communication/policy.py",
    "code/agentic_communication/run.py",
    "code/agentic_communication/runtime_contracts.py",
    "code/agentic_communication/episodes.py",
    "code/evaluation/agentic/run_r3_model_eval.py",
    "code/evaluation/agentic/run_main_table_v6_confirmatory.py",
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _freeze_sources() -> None:
    path = OUT_ROOT / "source-manifest.json"
    current = {rel: _sha256(ROOT / rel) for rel in SOURCE_FILES}
    if path.exists():
        frozen = json.loads(path.read_text(encoding="utf-8"))
        if frozen.get("files") != current:
            changed = sorted(
                rel
                for rel in set(current) | set(frozen.get("files") or {})
                if current.get(rel) != (frozen.get("files") or {}).get(rel)
            )
            raise RuntimeError("v6 confirmatory source changed: " + ", ".join(changed))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "experiment": "agentic-main-table-v6-confirmatory",
                "frozen_at": _now(),
                "model": MODEL,
                "protocol_revision": PROTOCOL,
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


def _valid(path: Path, *, task: str, seed: int, arm: str) -> bool:
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    config = payload.get("config") or {}
    episode = {"localized-o2": None, "o5": "O5", "o6": "O6"}[task]
    variant = "localized" if task == "localized-o2" else "global"
    return all(
        (
            config.get("model") == MODEL,
            config.get("protocol_revision") == PROTOCOL,
            int(config.get("seed", -1)) == seed,
            config.get("context_mode") == arm,
            config.get("planner_replan_mode") == REPLAN_MODE,
            config.get("episode") == episode,
            config.get("variant") == variant,
            float(config.get("temperature", 1.0)) == 0.0,
            config.get("reasoning_effort") == "low",
            int(config.get("max_tokens") or 0) == 8192,
            bool(config.get("json_object")) is True,
            config.get("credential_profile") == "deepseek_official",
        )
    )


def _usage(trace: Path) -> dict:
    out = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "latency_ms": 0.0}
    if not trace.exists():
        return out
    for line in trace.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if event.get("event_type") != "model_usage":
            continue
        row = event.get("payload") or {}
        for key in ("input_tokens", "output_tokens", "total_tokens"):
            out[key] += int(row.get(key) or 0)
        out["latency_ms"] += float(row.get("latency_ms") or 0.0)
    return out


def _method_gate(summary: Path) -> tuple[bool, dict]:
    payload = json.loads(summary.read_text(encoding="utf-8"))
    audit = payload.get("planner_behavior_audit") or {}
    observations = int(audit.get("local_observation_invocations") or 0) + int(
        audit.get("remote_observation_invocations") or 0
    )
    gate = {
        "effect_scope_inexact_turns": int(audit.get("effect_scope_inexact_turns") or 0),
        "observations": observations,
        "physical_equal_candidate_reference": payload.get("physical_equal_candidate_reference"),
        "physical_equal_legacy": payload.get("physical_equal_legacy"),
    }
    ok = (
        gate["effect_scope_inexact_turns"] == 0
        and gate["observations"] == 0
        and gate["physical_equal_candidate_reference"] is True
        and gate["physical_equal_legacy"] is True
    )
    return ok, gate


def _aggregate() -> Path:
    rows = []
    for arm in ARMS:
        for task, _ in TASKS:
            for seed in SEEDS:
                root = OUT_ROOT / task / f"seed-{seed:03d}" / arm
                summary = root / "summary.json"
                if not _valid(summary, task=task, seed=seed, arm=arm):
                    continue
                payload = json.loads(summary.read_text(encoding="utf-8"))
                audit = payload.get("planner_behavior_audit") or {}
                agent = payload.get("agent_metrics") or {}
                rows.append(
                    {
                        "task": task,
                        "seed": seed,
                        "context_mode": arm,
                        "model_calls": payload.get("model_calls_consumed"),
                        "successful_model_attempts": audit.get("successful_model_attempts"),
                        "failed_model_attempts": audit.get("failed_model_attempts"),
                        "effect_scope_exact_turns": audit.get("effect_scope_exact_turns"),
                        "effect_scope_inexact_turns": audit.get("effect_scope_inexact_turns"),
                        "local_observation_invocations": audit.get("local_observation_invocations"),
                        "remote_observation_invocations": audit.get("remote_observation_invocations"),
                        "physical_equal_candidate_reference": payload.get("physical_equal_candidate_reference"),
                        "physical_equal_legacy": payload.get("physical_equal_legacy"),
                        "mean_materialized_bytes": agent.get("mean_materialized_bytes"),
                        "capability_requests": agent.get("capability_requests"),
                        "physical_action_confirmation_rate": agent.get("physical_action_confirmation_rate"),
                        "usage": _usage(root / "runtime_trace.jsonl"),
                        "communication_metrics": payload.get("communication_metrics") or {},
                        "delta_vs_candidate_reference": payload.get("delta_vs_candidate_reference"),
                        "delta_vs_legacy": payload.get("delta_vs_legacy"),
                        "summary": str(summary),
                    }
                )
    path = OUT_ROOT / "aggregate.json"
    path.write_text(
        json.dumps(
            {
                "experiment": "agentic-main-table-v6-confirmatory",
                "generated_at": _now(),
                "model": MODEL,
                "protocol_revision": PROTOCOL,
                "seeds": list(SEEDS),
                "tasks": [name for name, _ in TASKS],
                "arms": list(ARMS),
                "expected_rows": len(SEEDS) * len(TASKS) * len(ARMS),
                "completed_rows": len(rows),
                "rows": rows,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _run_one(*, task: str, task_args: tuple[str, ...], seed: int, arm: str) -> Path:
    root = OUT_ROOT / task / f"seed-{seed:03d}" / arm
    summary = root / "summary.json"
    if _valid(summary, task=task, seed=seed, arm=arm):
        print(f"SKIP {arm}/{task}/seed-{seed:03d}", flush=True)
        return summary
    root.mkdir(parents=True, exist_ok=True)
    log = root / "runner.log"
    cmd = [
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
        "--out", str(root),
    ]
    progress = OUT_ROOT / "progress.jsonl"
    with progress.open("a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {"at": _now(), "event": "start", "arm": arm, "task": task, "seed": seed}
            )
            + "\n"
        )
    print(f"START {arm}/{task}/seed-{seed:03d}", flush=True)
    with log.open("w", encoding="utf-8") as fh:
        rc = subprocess.run(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT, check=False).returncode
    ok = rc == 0 and _valid(summary, task=task, seed=seed, arm=arm)
    with progress.open("a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "at": _now(),
                    "event": "done" if ok else "failed",
                    "arm": arm,
                    "task": task,
                    "seed": seed,
                    "returncode": rc,
                    "log": str(log),
                }
            )
            + "\n"
        )
    _aggregate()
    if not ok:
        raise RuntimeError(f"run failed {arm}/{task}/seed-{seed:03d} rc={rc} log={log}")
    print(f"DONE {arm}/{task}/seed-{seed:03d}", flush=True)
    return summary


def main() -> int:
    _freeze_sources()

    # Stage 1: all 15 Method rows must pass before any baseline spend.
    for task, task_args in TASKS:
        for seed in SEEDS:
            summary = _run_one(task=task, task_args=task_args, seed=seed, arm=METHOD)
            ok, gate = _method_gate(summary)
            print(
                f"METHOD_GATE {task}/seed-{seed:03d} {json.dumps(gate, sort_keys=True)}",
                flush=True,
            )
            if not ok:
                print(f"METHOD_GATE_FAIL {task}/seed-{seed:03d}", file=sys.stderr, flush=True)
                return 2

    # Stage 2: only after Method passes 15/15, run the remaining 45 rows.
    for arm in ARMS:
        if arm == METHOD:
            continue
        for task, task_args in TASKS:
            for seed in SEEDS:
                _run_one(task=task, task_args=task_args, seed=seed, arm=arm)

    aggregate = _aggregate()
    print(f"COMPLETE {aggregate}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

