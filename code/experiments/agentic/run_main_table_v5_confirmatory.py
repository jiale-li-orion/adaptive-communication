#!/usr/bin/env python3
"""Protocol-v5 confirmatory table: reuse formal seed0, run only seeds 1..4."""
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
SEED0_ROOT = ROOT / "results" / "agentic" / "main-table-v5-corrected" / "deepseek-flash"
OUT = ROOT / "results" / "agentic" / "main-table-v5-confirmatory" / "deepseek-flash"
PROTOCOL = "communication-planner-json-v5-candidate-plan-selection"
MODEL = "deepseek-flash"
METHOD = "action_conditioned_compact"
SEEDS = (1, 2, 3, 4)
TASKS = (("localized-o2", ("--variant", "localized")), ("o5", ("--episode", "O5")), ("o6", ("--episode", "O6")))
ARMS = (METHOD, "task_conditioned", "full_dump", "generic_react")
CORE_SOURCES = (
    "code/agentic_communication/action_context.py",
    "code/agentic_communication/capabilities.py",
    "code/agentic_communication/context_runtime.py",
    "code/agentic_communication/model_protocol.py",
    "code/agentic_communication/planner.py",
    "code/agentic_communication/policy.py",
    "code/agentic_communication/run.py",
    "code/agentic_communication/runtime_contracts.py",
    "code/agentic_communication/episodes.py",
    "code/experiments/agentic/run_r3_model_eval.py",
)


def now() -> str:
    return datetime.now(UTC).isoformat()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def current_sources() -> dict[str, str]:
    return {rel: sha(ROOT / rel) for rel in CORE_SOURCES}


def validate_seed0() -> list[dict]:
    manifest = json.loads((SEED0_ROOT / "source-manifest.json").read_text(encoding="utf-8"))
    current = current_sources()
    for rel, digest in current.items():
        if manifest.get("files", {}).get(rel) != digest:
            raise RuntimeError(f"formal seed0 source mismatch: {rel}")
    summary = json.loads((SEED0_ROOT / "seed0-main-table-summary.json").read_text(encoding="utf-8"))
    if summary.get("completed_rows") != 12 or summary.get("protocol_revision") != PROTOCOL:
        raise RuntimeError("formal seed0 main table is incomplete or wrong protocol")
    return list(summary["rows"])


def freeze() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "source-manifest.json"
    snapshot = {**current_sources(), "code/experiments/agentic/run_main_table_v5_confirmatory.py": sha(Path(__file__))}
    if path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        if old.get("files") != snapshot:
            raise RuntimeError("confirmatory source changed after freeze")
        return
    path.write_text(json.dumps({"frozen_at": now(), "protocol_revision": PROTOCOL, "files": snapshot}, indent=2) + "\n", encoding="utf-8")


def valid(path: Path, task: str, seed: int, arm: str) -> bool:
    if not path.exists():
        return False
    try:
        d = json.loads(path.read_text(encoding="utf-8")); c = d.get("config", {})
    except Exception:
        return False
    expected_episode = {"localized-o2": None, "o5": "O5", "o6": "O6"}[task]
    expected_variant = "localized" if task == "localized-o2" else "global"
    return all((
        c.get("model") == MODEL,
        c.get("protocol_revision") == PROTOCOL,
        c.get("context_mode") == arm,
        int(c.get("seed", -1)) == seed,
        c.get("planner_replan_mode") == "decision_state",
        c.get("episode") == expected_episode,
        c.get("variant") == expected_variant,
        float(c.get("temperature", 1.0)) == 0.0,
        c.get("reasoning_effort") == "low",
        int(c.get("max_tokens") or 0) == 8192,
        bool(c.get("json_object")) is True,
        c.get("credential_profile") == "deepseek_official",
    ))


def usage(trace: Path) -> dict:
    out = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "latency_ms": 0.0}
    if not trace.exists(): return out
    for line in trace.read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        if e.get("event_type") != "model_usage": continue
        u = e.get("payload", {})
        for k in ("input_tokens", "output_tokens", "total_tokens"): out[k] += int(u.get(k) or 0)
        out["latency_ms"] += float(u.get("latency_ms") or 0)
    return out


def row_from_summary(task: str, seed: int, arm: str, path: Path) -> dict:
    d = json.loads(path.read_text(encoding="utf-8")); a = d.get("planner_behavior_audit", {}); m = d.get("agent_metrics", {})
    return {"task": task, "seed": seed, "context_mode": arm, "model_calls": d.get("model_calls_consumed"), "successful_model_attempts": a.get("successful_model_attempts"), "failed_model_attempts": a.get("failed_model_attempts"), "effect_scope_exact_turns": a.get("effect_scope_exact_turns"), "effect_scope_inexact_turns": a.get("effect_scope_inexact_turns"), "local_observation_invocations": a.get("local_observation_invocations"), "remote_observation_invocations": a.get("remote_observation_invocations"), "physical_equal_candidate_reference": d.get("physical_equal_candidate_reference"), "physical_equal_legacy": d.get("physical_equal_legacy"), "mean_materialized_bytes": m.get("mean_materialized_bytes"), "capability_requests": m.get("capability_requests"), "usage": usage(path.parent / "runtime_trace.jsonl"), "communication_metrics": d.get("communication_metrics", {}), "delta_vs_candidate_reference": d.get("delta_vs_candidate_reference"), "delta_vs_legacy": d.get("delta_vs_legacy"), "summary": str(path)}


def aggregate(seed0_rows: list[dict]) -> Path:
    rows = list(seed0_rows)
    for arm in ARMS:
        for task, _ in TASKS:
            for seed in SEEDS:
                p = OUT / task / f"seed-{seed:03d}" / arm / "summary.json"
                if valid(p, task, seed, arm): rows.append(row_from_summary(task, seed, arm, p))
    path = OUT / "aggregate.json"
    path.write_text(json.dumps({"experiment": "agentic-main-table-v5-confirmatory", "generated_at": now(), "protocol_revision": PROTOCOL, "expected_rows": 60, "completed_rows": len(rows), "reused_seed0_rows": 12, "new_expected_rows": 48, "rows": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def method_gate(path: Path) -> tuple[bool, dict]:
    d = json.loads(path.read_text(encoding="utf-8")); a = d["planner_behavior_audit"]
    g = {"inexact": int(a.get("effect_scope_inexact_turns") or 0), "obs": int(a.get("local_observation_invocations") or 0) + int(a.get("remote_observation_invocations") or 0), "candidate": d.get("physical_equal_candidate_reference"), "legacy": d.get("physical_equal_legacy")}
    return g == {"inexact": 0, "obs": 0, "candidate": True, "legacy": True}, g


def run_one(task: str, args: tuple[str, ...], seed: int, arm: str, seed0_rows: list[dict]) -> Path:
    root = OUT / task / f"seed-{seed:03d}" / arm; summary = root / "summary.json"
    if valid(summary, task, seed, arm): print(f"SKIP {arm}/{task}/seed-{seed}", flush=True); return summary
    root.mkdir(parents=True, exist_ok=True); log = root / "runner.log"
    cmd = [sys.executable, str(R3), "--model", MODEL, *args, "--seed", str(seed), "--context-mode", arm, "--planner-replan-mode", "decision_state", "--credential-profile", "deepseek_official", "--temperature", "0", "--reasoning-effort", "low", "--max-tokens", "8192", "--json-object", "--max-model-calls", "32", "--out", str(root)]
    print(f"START {arm}/{task}/seed-{seed}", flush=True)
    with log.open("w", encoding="utf-8") as f: rc = subprocess.run(cmd, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT, check=False).returncode
    aggregate(seed0_rows)
    if rc != 0 or not valid(summary, task, seed, arm): raise RuntimeError(f"failed {arm}/{task}/seed-{seed}: {log}")
    print(f"DONE {arm}/{task}/seed-{seed}", flush=True); return summary


def main() -> int:
    seed0_rows = validate_seed0(); freeze(); aggregate(seed0_rows)
    for task, args in TASKS:
        for seed in SEEDS:
            p = run_one(task, args, seed, METHOD, seed0_rows); ok, g = method_gate(p); print(f"METHOD_GATE {task}/seed-{seed} {g}", flush=True)
            if not ok: return 2
    for arm in ARMS[1:]:
        for task, args in TASKS:
            for seed in SEEDS: run_one(task, args, seed, arm, seed0_rows)
    print(f"COMPLETE {aggregate(seed0_rows)}", flush=True); return 0


if __name__ == "__main__": raise SystemExit(main())
