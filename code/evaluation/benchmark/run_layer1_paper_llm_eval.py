#!/usr/bin/env python3
"""Run the frozen 30-coordinate Layer-1 paper LLM subset.

The frozen paper protocol selects exactly:

    {O1,O2,O3,O4,O6} × {w0,w2,w3} × {seed100,seed105}
    × {generic_react,task_conditioned}

under the 2024 test weather coordinates.  This runner does not reuse the old
``run_r3_model_eval.py`` episode defaults: each run reconstructs the simulator
from the frozen paper split (DEFAULT_FULLSIM + episode overrides + coordinate
overrides), exactly like the deterministic paper runner.

Scientific safeguards:

* a dev smoke is available before test execution;
* frozen-test execution requires a clean git worktree;
* protocol/split/pre-release digests are checked before any model call;
* source hashes are frozen in the output directory and checked on resume;
* results are append-only / row-id resumable;
* provider/model/context modes and all generation parameters come only from the
  frozen protocol -- there is no CLI override;
* model/runtime failures are recorded as rows and are not silently retried with
  another model or context mode.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import UTC, datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

# Keep numerical libraries from fanning out across the whole WSL VM.  The
# Layer-1 LLM paper run is latency/API bound; parallel BLAS gives no scientific
# benefit here and previously made long headless runs unnecessarily hostile to
# the workstation.
for _name in (
    "OPENBLAS_NUM_THREADS",
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ.setdefault(_name, "1")


ROOT = Path(__file__).resolve().parents[3]
CODE = ROOT / "code"
AGENTIC_EVAL = CODE / "evaluation" / "agentic"
for _p in (
    CODE,
    AGENTIC_EVAL,
    CODE / "substrate" / "monitoring",
    CODE / "substrate" / "runtime",
    CODE / "substrate" / "joint",
    CODE / "substrate" / "instance",
    CODE / "substrate" / "physics",
):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from agentic_communication.episodes import benchmark_episode_catalog  # noqa: E402
from agentic_communication.run import DEFAULT_FULLSIM, run_agentic_episode  # noqa: E402
from agentic_communication.planner import BackendPlannerConsumer, BudgetedPlannerConsumer  # noqa: E402
from agentic_communication.replay import audit_trace  # noqa: E402
from llm_planner import make_real_backend  # noqa: E402
from run_r3_model_eval import _load_shell_export, _planner_behavior_audit  # noqa: E402


PROTOCOL = ROOT / "research/benchmark/PAPER-BASELINE-PROTOCOL.json"
SPLIT = ROOT / "results/benchmark/layer1-paper-split.json"
PRE_RELEASE = ROOT / "results/benchmark/layer1-paper-release-candidate.json"

SOURCE_FILES = (
    "code/evaluation/benchmark/run_layer1_paper_llm_eval.py",
    "code/agentic_communication/action_context.py",
    "code/agentic_communication/capabilities.py",
    "code/agentic_communication/context_runtime.py",
    "code/agentic_communication/model_protocol.py",
    "code/agentic_communication/planner.py",
    "code/agentic_communication/policy.py",
    "code/agentic_communication/run.py",
    "code/agentic_communication/runtime_contracts.py",
    "code/agentic_communication/episodes.py",
    "code/substrate/joint/joint_run.py",
    "code/substrate/joint/joint_plane.py",
    "code/substrate/joint/mission_policy.py",
    "code/substrate/instance/center.py",
    "code/substrate/instance/network.py",
    "code/substrate/instance/scoring.py",
    "code/substrate/monitoring/llm_planner.py",
    "research/benchmark/PAPER-BASELINE-PROTOCOL.json",
    "results/benchmark/layer1-paper-split.json",
    "results/benchmark/layer1-paper-release-candidate.json",
)


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _dirty() -> list[str]:
    raw = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=ROOT, text=True
    )
    return [line for line in raw.splitlines() if line.strip()]


def _dirty_outside_output(out: Path) -> list[str]:
    """Return dirty entries other than this run's own output directory.

    A resumable paper run necessarily makes ``results/...`` dirty after the
    first checkpoint.  Treating its own append-only output as source drift makes
    safe chunking impossible.  Source/protocol integrity is still protected by
    the frozen source-manifest and input digests; *all other* worktree changes
    remain fatal.
    """

    out_rel = out.resolve().relative_to(ROOT.resolve()).as_posix().rstrip("/")
    blocked = []
    for line in _dirty():
        # porcelain v1: XY<space>path. For renames, conservatively reject the
        # entry unless every visible path is inside the output directory.
        payload = line[3:].strip() if len(line) >= 4 else line.strip()
        paths = [part.strip() for part in payload.split(" -> ")]
        if paths and all(p == out_rel or p.startswith(out_rel + "/") for p in paths):
            continue
        blocked.append(line)
    return blocked


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_inputs(protocol: dict, split: dict, pre: dict) -> None:
    files = pre["files"]
    if _sha(PROTOCOL) != files["baseline_protocol"]["sha256"]:
        raise RuntimeError("paper baseline protocol drifted after pre-release freeze")
    if _sha(SPLIT) != files["execution_split"]["sha256"]:
        raise RuntimeError("paper execution split drifted after pre-release freeze")
    if protocol["status"] != "FROZEN_BEFORE_TEST_EXECUTION":
        raise RuntimeError("paper LLM protocol is not frozen")


def _source_manifest() -> dict[str, str]:
    return {rel: _sha(ROOT / rel) for rel in SOURCE_FILES}


def _freeze_or_check_sources(out: Path) -> None:
    path = out / "source-manifest.json"
    current = {"git_commit_at_start": _head(), "files": _source_manifest()}
    if path.exists():
        old = _load(path)
        if old.get("files") != current["files"]:
            changed = sorted(
                rel
                for rel in set(current["files"]) | set(old.get("files") or {})
                if current["files"].get(rel) != (old.get("files") or {}).get(rel)
            )
            raise RuntimeError("paper LLM source drift on resume: " + ", ".join(changed))
        return
    out.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(current, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _simulator(template, coordinate: dict) -> dict:
    sim = dict(DEFAULT_FULLSIM)
    sim.update(template.simulator_overrides)
    sim.update(coordinate["simulator_overrides"])
    return sim


def _selected_test(protocol: dict, split: dict) -> list[dict]:
    llm = protocol["llm_subset"]
    rows = [
        row
        for row in split["coordinates"]["test"]
        if row["task_template"] in llm["task_templates"]
        and row["window_id"] in llm["windows"]
        and int(row["seed"]) in llm["seeds"]
    ]
    rows.sort(key=lambda r: r["coordinate_id"])
    if len(rows) != int(llm["coordinate_count"]) != 30:
        raise AssertionError(f"unexpected LLM coordinate count {len(rows)}")
    if len(rows) != 30:
        raise AssertionError(f"unexpected LLM coordinate count {len(rows)}")
    return rows


def _dev_smoke(split: dict) -> list[dict]:
    rows = [
        row for row in split["coordinates"]["dev"]
        if row["task_template"] == "O1"
        and row["window_id"] == "w0"
        and int(row["seed"]) == 0
    ]
    if len(rows) != 1:
        raise AssertionError(f"expected one fixed dev smoke coordinate, got {len(rows)}")
    return rows


def _usage(trace: Path) -> dict[str, float | int]:
    out: dict[str, float | int] = {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "latency_ms": 0.0,
    }
    if not trace.exists():
        return out
    for line in trace.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if event.get("event_type") != "model_usage":
            continue
        payload = event.get("payload") or {}
        for key in ("input_tokens", "output_tokens", "total_tokens"):
            out[key] = int(out[key]) + int(payload.get(key) or 0)
        out["latency_ms"] = float(out["latency_ms"]) + float(payload.get("latency_ms") or 0.0)
    return out


def _read_existing(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    rows = {}
    with path.open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"invalid JSONL {path}:{lineno}") from exc
            rows[str(row["row_id"])] = row
    return rows


def _append(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        fh.flush()


def _make_backend(model_cfg: dict):
    provider = str(model_cfg["provider"])
    if provider != "deepseek_official":
        raise RuntimeError(f"unsupported frozen provider {provider}")
    key = os.environ.get("DEEPSEEK_API_KEY") or _load_shell_export("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY is missing; no fallback provider is allowed")
    backend, reason = make_real_backend(
        model=str(model_cfg["model"]),
        base_url="https://api.deepseek.com",
        api_key=key,
        timeout=60.0,
        temperature=float(model_cfg["temperature"]),
        max_tokens=int(model_cfg["max_tokens"]),
        reasoning_effort=str(model_cfg["reasoning_effort"]),
        json_object=bool(model_cfg["json_object"]),
    )
    if backend is None:
        raise RuntimeError(f"DeepSeek backend unavailable: {reason}")
    return backend


def _run_one(
    *,
    backend,
    coordinate: dict,
    context_mode: str,
    model_cfg: dict,
    out: Path,
) -> dict:
    catalog = benchmark_episode_catalog()
    template = catalog[coordinate["task_template"]]
    sim = _simulator(template, coordinate)
    consumer = BudgetedPlannerConsumer(
        BackendPlannerConsumer(
            backend,
            consumer_id=f"paper:{model_cfg['provider']}:{model_cfg['model']}",
            provider=str(model_cfg["provider"]),
            model=str(model_cfg["model"]),
        ),
        int(model_cfg["max_model_calls"]),
    )
    trace_dir = out / "traces" / coordinate["coordinate_id"].replace(":", "__") / context_mode
    trace_dir.mkdir(parents=True, exist_ok=True)
    trace_path = trace_dir / "runtime_trace.jsonl"

    try:
        result, policy, _inst, _obligations = run_agentic_episode(
            seed=int(coordinate["seed"]),
            operational_task=template.task,
            context_mode=context_mode,
            planner_consumer=consumer,
            planner_replan_mode=str(model_cfg["planner_replan_mode"]),
            simulator_kwargs=sim,
        )
        policy.trace.write_jsonl(trace_path)
        replay = audit_trace(trace_path, context_mode=context_mode)
        row = {
            "status": "OK",
            "communication_metrics": result["agentic"]["communication_metrics"],
            "agent_metrics": result["agentic"]["agent_metrics"],
            "planner_behavior_audit": _planner_behavior_audit(policy),
            "replay_audit": replay,
            "model_calls_consumed": int(consumer.calls),
            "model_usage": _usage(trace_path),
            "trace": str(trace_path.relative_to(ROOT)),
        }
    except Exception as exc:  # runtime/provider failure is part of the frozen evaluation outcome
        row = {
            "status": "RUNTIME_FAILURE",
            "error_type": type(exc).__name__,
            "error_message": str(exc)[:1000],
            "model_calls_consumed": int(getattr(consumer, "calls", 0)),
            "model_usage": _usage(trace_path),
            "trace": str(trace_path.relative_to(ROOT)) if trace_path.exists() else None,
        }

    return {
        "row_id": f"{coordinate['coordinate_id']}::{context_mode}",
        "coordinate_id": coordinate["coordinate_id"],
        "coordinate_sha256": coordinate["coordinate_sha256"],
        "split": coordinate["split"],
        "task_template": coordinate["task_template"],
        "seed": int(coordinate["seed"]),
        "window_id": coordinate["window_id"],
        "irradiance_year": int(sim["irradiance_year"]),
        "irradiance_start_hour": int(sim["irradiance_start_hour"]),
        "context_mode": context_mode,
        "model": dict(model_cfg),
        **row,
    }


def _aggregate(rows: list[dict], *, expected: int) -> dict:
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        groups[(str(row["task_template"]), str(row["context_mode"]))].append(row)
    grouped = {}
    for (task, mode), items in sorted(groups.items()):
        ok = [row for row in items if row["status"] == "OK"]
        tdr = [float(row["communication_metrics"]["timely_delivery_rate"]) for row in ok]
        grouped[f"{task}/{mode}"] = {
            "rows": len(items),
            "ok": len(ok),
            "runtime_failure": len(items) - len(ok),
            "mean_tdr": (sum(tdr) / len(tdr)) if tdr else None,
            "model_calls": sum(int(row.get("model_calls_consumed") or 0) for row in items),
            "input_tokens": sum(int((row.get("model_usage") or {}).get("input_tokens") or 0) for row in items),
            "output_tokens": sum(int((row.get("model_usage") or {}).get("output_tokens") or 0) for row in items),
        }
    return {
        "stage": "LAYER1_PAPER_LLM_EVALUATION",
        "expected_rows": expected,
        "actual_rows": len(rows),
        "complete": len(rows) == expected,
        "status_counts": {
            "OK": sum(row["status"] == "OK" for row in rows),
            "RUNTIME_FAILURE": sum(row["status"] == "RUNTIME_FAILURE" for row in rows),
        },
        "groups": grouped,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smoke-dev", action="store_true")
    mode.add_argument("--execute-frozen-test", action="store_true")
    ap.add_argument("--out", type=Path)
    ap.add_argument(
        "--max-new-rows",
        type=int,
        default=None,
        help=(
            "Execution-only chunk limit. Run at most this many previously missing row_ids, "
            "write checkpoints, then exit with code 2 until the full frozen cohort is complete. "
            "Does not alter the paper protocol or selected coordinates."
        ),
    )
    ap.add_argument(
        "--inter-row-sleep-s",
        type=float,
        default=0.0,
        help="Execution-only cooldown between newly completed rows; scientific outputs are unchanged.",
    )
    args = ap.parse_args()

    if args.max_new_rows is not None and args.max_new_rows <= 0:
        raise SystemExit("--max-new-rows must be positive")
    if args.inter_row_sleep_s < 0:
        raise SystemExit("--inter-row-sleep-s must be non-negative")

    protocol = _load(PROTOCOL)
    split = _load(SPLIT)
    pre = _load(PRE_RELEASE)
    _assert_inputs(protocol, split, pre)
    llm = protocol["llm_subset"]
    model_cfg = dict(llm["model"])
    context_modes = list(llm["context_modes"])

    if args.execute_frozen_test:
        out = (args.out or ROOT / "results/benchmark/layer1-paper-llm-test").resolve()
        dirty = _dirty_outside_output(out)
        if dirty:
            raise SystemExit(
                "refusing frozen LLM test on source/protocol worktree drift: "
                + " | ".join(dirty[:10])
            )
        coordinates = _selected_test(protocol, split)
        expected = 30 * len(context_modes)
    else:
        coordinates = _dev_smoke(split)
        expected = len(coordinates) * len(context_modes)
        out = (args.out or ROOT / "local_research/current/benchmark/layer1-paper-llm-dev-smoke").resolve()

    _freeze_or_check_sources(out)
    rows_path = out / "rows.jsonl"
    existing = _read_existing(rows_path)
    backend = _make_backend(model_cfg)

    new_rows = 0
    stop_after_chunk = False
    for coordinate in coordinates:
        for context_mode in context_modes:
            row_id = f"{coordinate['coordinate_id']}::{context_mode}"
            if row_id in existing:
                continue
            row = _run_one(
                backend=backend,
                coordinate=coordinate,
                context_mode=context_mode,
                model_cfg=model_cfg,
                out=out,
            )
            _append(rows_path, row)
            existing[row_id] = row
            new_rows += 1
            print(
                json.dumps(
                    {
                        "row_id": row_id,
                        "status": row["status"],
                        "model_calls": row.get("model_calls_consumed"),
                        "tdr": (row.get("communication_metrics") or {}).get("timely_delivery_rate"),
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                flush=True,
            )
            if args.inter_row_sleep_s:
                import time
                time.sleep(args.inter_row_sleep_s)
            if args.max_new_rows is not None and new_rows >= args.max_new_rows:
                stop_after_chunk = True
                break
        if stop_after_chunk:
            break

    rows = [existing[k] for k in sorted(existing)]
    aggregate = _aggregate(rows, expected=expected)
    (out / "aggregate.json").write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "git_commit": _head(),
        "runner": str(Path(__file__).relative_to(ROOT)),
        "protocol_sha256": _sha(PROTOCOL),
        "split_sha256": _sha(SPLIT),
        "pre_release_sha256": _sha(PRE_RELEASE),
        "rows_sha256": _sha(rows_path),
        "source_manifest_sha256": _sha(out / "source-manifest.json"),
        "complete": aggregate["complete"],
    }
    (out / "run-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"out": str(out), **aggregate}, ensure_ascii=False, sort_keys=True))
    return 0 if aggregate["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
