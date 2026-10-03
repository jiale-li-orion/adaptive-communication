#!/usr/bin/env python3
"""Five-seed WOA-style confirmatory table, reusing the audited seed-0 rows."""
from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
ROOT = HERE.parents[2]
for path in (CODE, CODE / "substrate" / "monitoring", CODE / "substrate" / "runtime", HERE):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from agentic_communication.episodes import (  # noqa: E402
    benchmark_episode_catalog,
    o2_localized_risk_escalation_task,
)
from agentic_communication.metrics import (  # noqa: E402
    communication_metrics,
    metric_delta,
    physical_signature,
)
from agentic_communication.model_protocol import PROTOCOL_REVISION  # noqa: E402
from agentic_communication.planner import (  # noqa: E402
    ActionConditionedReferencePlannerConsumer,
    BackendPlannerConsumer,
    BudgetedPlannerConsumer,
)
from agentic_communication.replay import audit_trace  # noqa: E402
from agentic_communication.run import run_agentic_episode, run_reference_comply  # noqa: E402
from run_r3_model_eval import _load_shell_export, _planner_behavior_audit  # noqa: E402
from woa_style_adapter import WirelessOpsStyleAssuranceConsumer  # noqa: E402


MODEL = "deepseek-flash"
BASELINE_REVISION = "woa-style-adaptation-v1"
OUT_ROOT = ROOT / "results" / "agentic" / "woa-style-baseline-v1" / MODEL
SEEDS = tuple(range(5))
NEW_SEEDS = (1, 2, 3, 4)
TASKS = (
    ("localized-o2", o2_localized_risk_escalation_task(), {}),
    (
        "o5",
        benchmark_episode_catalog()["O5"].task,
        benchmark_episode_catalog()["O5"].simulator_overrides,
    ),
    (
        "o6",
        benchmark_episode_catalog()["O6"].task,
        benchmark_episode_catalog()["O6"].simulator_overrides,
    ),
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _seed0_manifest() -> dict:
    path = OUT_ROOT / "source-manifest.json"
    if not path.is_file():
        raise RuntimeError("seed0 source-manifest.json is missing")
    return json.loads(path.read_text(encoding="utf-8"))


def _freeze_confirmatory_sources() -> None:
    seed0 = _seed0_manifest()
    seed0_files = dict(seed0.get("files") or {})
    mismatches = []
    for rel, expected in seed0_files.items():
        path = ROOT / rel
        current = _sha(path) if path.is_file() else None
        if current != expected:
            mismatches.append({"path": rel, "seed0": expected, "current": current})
    if mismatches:
        raise RuntimeError(
            "WOA shared source differs from seed0; refuse mixed-revision confirmatory: "
            + json.dumps(mismatches, ensure_ascii=False)
        )

    manifest_path = OUT_ROOT / "confirmatory-source-manifest.json"
    current = {
        "seed0_shared_files": seed0_files,
        "confirmatory_runner": {
            str(Path(__file__).resolve().relative_to(ROOT)): _sha(Path(__file__).resolve())
        },
    }
    if manifest_path.exists():
        frozen = json.loads(manifest_path.read_text(encoding="utf-8"))
        if frozen.get("files") != current:
            raise RuntimeError("WOA confirmatory source manifest changed after freeze")
        return
    manifest_path.write_text(
        json.dumps(
            {
                "experiment": "woa-style-baseline-v1-confirmatory",
                "frozen_at": _now(),
                "model": MODEL,
                "baseline_revision": BASELINE_REVISION,
                "protocol_revision": PROTOCOL_REVISION,
                "seeds": list(SEEDS),
                "tasks": [row[0] for row in TASKS],
                "seed0_manifest_sha256": _sha(OUT_ROOT / "source-manifest.json"),
                "files": current,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _usage(policy) -> dict:
    total = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "latency_ms": 0.0}
    for event in policy.trace.events:
        if event.event_type != "model_usage":
            continue
        row = event.payload
        for key in ("input_tokens", "output_tokens", "total_tokens"):
            total[key] += int(row.get(key) or 0)
        total["latency_ms"] += float(row.get("latency_ms") or 0.0)
    return total


def _raw_proposal_diagnostics(records: list[dict]) -> dict:
    raw_plan_exact = 0
    raw_effect_exact = 0
    raw_stop_exact = 0
    raw_query_turns = 0
    repaired_turns = 0
    for record in records:
        ready = list(record.get("ready_supported_plan_ids") or [])
        raw = record.get("raw_proposal") or {}
        final = record.get("final_decision") or {}
        if len(ready) == 1 and raw.get("selected_plan_id") == ready[0]:
            raw_plan_exact += 1

        def effects(decision: dict) -> set[tuple[str, str, str]]:
            return {
                (
                    str(row.get("capability_id") or ""),
                    str(row.get("resource") or ""),
                    json.dumps(
                        dict(row.get("canonical_arguments") or {}),
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                )
                for row in (decision.get("invocations") or [])
                if str(row.get("capability_id") or "").startswith(
                    ("communication.config.", "communication.fallback.")
                )
            }

        if effects(raw) == effects(final):
            raw_effect_exact += 1
        if bool(raw.get("stop")) == bool(final.get("stop")):
            raw_stop_exact += 1
        if any(
            str(row.get("capability_id") or "").startswith(
                ("communication.center.", "communication.gateway.")
            )
            for row in (raw.get("invocations") or [])
        ):
            raw_query_turns += 1
        if record.get("repairs"):
            repaired_turns += 1
    return {
        "turns": len(records),
        "raw_selected_plan_exact_turns": raw_plan_exact,
        "raw_effect_scope_exact_turns": raw_effect_exact,
        "raw_stop_exact_turns": raw_stop_exact,
        "raw_query_turns": raw_query_turns,
        "repaired_turns": repaired_turns,
        "governor_counts": dict(sorted(Counter(row.get("governor") for row in records).items())),
        "repair_type_counts": dict(
            sorted(
                Counter(
                    repair.get("type")
                    for row in records
                    for repair in (row.get("repairs") or [])
                ).items()
            )
        ),
    }


def _summary_path(task_name: str, seed: int) -> Path:
    return OUT_ROOT / task_name / f"seed-{seed:03d}" / "summary.json"


def _summary_valid(path: Path, *, task_name: str, seed: int) -> bool:
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    cfg = data.get("config") or {}
    return (
        cfg.get("model") == MODEL
        and cfg.get("baseline_revision") == BASELINE_REVISION
        and cfg.get("context_mode") == "woa_style"
        and int(cfg.get("seed", -1)) == seed
        and cfg.get("task") == task_name
    )


def _run_one(*, task_name: str, task, simulator_kwargs: dict, seed: int, api_key: str) -> dict:
    summary_path = _summary_path(task_name, seed)
    if _summary_valid(summary_path, task_name=task_name, seed=seed):
        print(f"SKIP {task_name}/seed-{seed:03d}", flush=True)
        return json.loads(summary_path.read_text(encoding="utf-8"))

    from llm_planner import make_real_backend  # noqa: E402

    backend, reason = make_real_backend(
        model=MODEL,
        base_url="https://api.deepseek.com",
        api_key=api_key,
        timeout=60.0,
        temperature=0.0,
        max_tokens=8192,
        reasoning_effort="low",
        json_object=True,
    )
    if backend is None:
        raise RuntimeError(f"model backend unavailable: {reason}")
    raw_consumer = BackendPlannerConsumer(
        backend,
        consumer_id=f"woa-style-proposal:{MODEL}",
        provider=str(getattr(backend, "name", "openai-compatible")),
        model=MODEL,
    )
    assured = WirelessOpsStyleAssuranceConsumer(raw_consumer)
    consumer = BudgetedPlannerConsumer(assured, 32)

    legacy, _, _ = run_reference_comply(
        seed=seed,
        operational_task=task,
        simulator_kwargs=simulator_kwargs,
    )
    candidate, _, _, _ = run_agentic_episode(
        seed=seed,
        operational_task=task,
        context_mode="action_conditioned_compact",
        planner_consumer=ActionConditionedReferencePlannerConsumer(),
        planner_replan_mode="decision_state",
        simulator_kwargs=simulator_kwargs,
    )
    result, policy, _, _ = run_agentic_episode(
        seed=seed,
        operational_task=task,
        context_mode="woa_style",
        planner_consumer=consumer,
        planner_replan_mode="decision_state",
        simulator_kwargs=simulator_kwargs,
    )
    out = summary_path.parent
    out.mkdir(parents=True, exist_ok=True)
    trace = out / "runtime_trace.jsonl"
    policy.trace.write_jsonl(trace)
    replay = audit_trace(trace, context_mode="woa_style")
    behavior = _planner_behavior_audit(policy)
    records_path = out / "authorization_records.json"
    records_path.write_text(
        json.dumps(assured.records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    summary = {
        "generated_at": _now(),
        "config": {
            "model": MODEL,
            "baseline_revision": BASELINE_REVISION,
            "protocol_revision": PROTOCOL_REVISION,
            "task": task_name,
            "seed": seed,
            "context_mode": "woa_style",
            "planner_replan_mode": "decision_state",
            "temperature": 0.0,
            "reasoning_effort": "low",
            "max_tokens": 8192,
            "json_object": True,
            "max_model_calls": 32,
        },
        "communication_metrics": result["agentic"]["communication_metrics"],
        "agent_metrics": result["agentic"]["agent_metrics"],
        "physical_equal_legacy": physical_signature(result) == physical_signature(legacy),
        "physical_equal_candidate_reference": physical_signature(result) == physical_signature(candidate),
        "delta_vs_legacy": metric_delta(
            result["agentic"]["communication_metrics"], communication_metrics(legacy)
        ),
        "delta_vs_candidate_reference": metric_delta(
            result["agentic"]["communication_metrics"], communication_metrics(candidate)
        ),
        "model_calls_consumed": consumer.calls,
        "usage": _usage(policy),
        "planner_behavior_audit": behavior,
        "assurance_audit": _raw_proposal_diagnostics(assured.records),
        "replay_audit": replay,
        "trace": str(trace),
        "authorization_records": str(records_path),
        "adaptation_boundary": (
            "WirelessOpsAgent-style method adaptation over the repository's public Task/Evidence/"
            "candidate interface; not an official source-code reproduction."
        ),
    }
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"DONE {task_name}/seed-{seed:03d} calls={consumer.calls} "
        f"exact={behavior['effect_scope_exact_turns']}/{behavior['planner_decision_turns']} "
        f"physical={summary['physical_equal_legacy']}",
        flush=True,
    )
    return summary


def _aggregate() -> Path:
    rows = []
    for task_name, _, _ in TASKS:
        for seed in SEEDS:
            path = _summary_path(task_name, seed)
            if _summary_valid(path, task_name=task_name, seed=seed):
                rows.append(json.loads(path.read_text(encoding="utf-8")))
    aggregate = {
        "experiment": "woa-style-baseline-v1-confirmatory",
        "model": MODEL,
        "baseline_revision": BASELINE_REVISION,
        "seeds": list(SEEDS),
        "tasks": [row[0] for row in TASKS],
        "completed_rows": len(rows),
        "expected_rows": len(SEEDS) * len(TASKS),
        "rows": rows,
    }
    path = OUT_ROOT / "confirmatory-aggregate.json"
    path.write_text(json.dumps(aggregate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    _freeze_confirmatory_sources()
    # Seed0 must remain a complete valid checkpoint from task 012.
    for task_name, _, _ in TASKS:
        if not _summary_valid(_summary_path(task_name, 0), task_name=task_name, seed=0):
            raise RuntimeError(f"missing/invalid seed0 checkpoint for {task_name}")

    api_key = os.environ.get("DEEPSEEK_API_KEY") or _load_shell_export("DEEPSEEK_API_KEY")
    if not api_key:
        raise SystemExit("DEEPSEEK_API_KEY is not set")

    for task_name, task, simulator_kwargs in TASKS:
        for seed in NEW_SEEDS:
            _run_one(
                task_name=task_name,
                task=task,
                simulator_kwargs=simulator_kwargs,
                seed=seed,
                api_key=api_key,
            )
            _aggregate()
    aggregate = _aggregate()
    print(f"COMPLETE {aggregate}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

