#!/usr/bin/env python3
"""Seed-0 held-out model-transfer gate on Qili task + NASA POWER 2024/w1."""
from __future__ import annotations

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

from agentic_communication.benchmark_split import WINDOW_START_HOURS  # noqa: E402
from agentic_communication.metrics import communication_metrics, metric_delta, physical_signature  # noqa: E402
from agentic_communication.model_protocol import PROTOCOL_REVISION  # noqa: E402
from agentic_communication.planner import (  # noqa: E402
    ActionConditionedReferencePlannerConsumer,
    BackendPlannerConsumer,
    BudgetedPlannerConsumer,
)
from agentic_communication.replay import audit_trace  # noqa: E402
from agentic_communication.run import DEFAULT_FULLSIM, run_agentic_episode, run_reference_comply  # noqa: E402
from agentic_communication.task_transfer import qili_2016_rainfall_deformation_profile  # noqa: E402
from run_r3_model_eval import _load_shell_export, _planner_behavior_audit  # noqa: E402


EXPERIMENT = "heldout-qili-2024-w1-model-transfer-v1"
OUT_ROOT = ROOT / "results" / "agentic" / "heldout-qili-2024-w1" / "model-transfer-v1"
SEED = 0
MAX_CALLS = 32
MAX_TOKENS = 8192
MODELS = (
    {
        "id": "deepseek-flash",
        "provider": "deepseek_official",
        "api_key_env": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com",
        "generation": {
            "temperature": 0.0,
            "reasoning_effort": "low",
            "thinking": None,
            "json_object": True,
            "max_tokens": MAX_TOKENS,
        },
    },
    {
        "id": "mimo-v2.6-flash",
        "provider": "xiaomi_mimo_official",
        "api_key_env": "MIMO_API_KEY",
        "base_url_env": "MIMO_BASE_URL",
        "generation": {
            "temperature": 0.0,
            "reasoning_effort": None,
            "thinking": "disabled",
            "json_object": True,
            "max_tokens": MAX_TOKENS,
        },
    },
)

SOURCE_FILES = (
    "code/agentic_communication/action_context.py",
    "code/agentic_communication/context_runtime.py",
    "code/agentic_communication/model_protocol.py",
    "code/agentic_communication/planner.py",
    "code/agentic_communication/policy.py",
    "code/agentic_communication/replay.py",
    "code/agentic_communication/run.py",
    "code/agentic_communication/runtime_contracts.py",
    "code/agentic_communication/task_compiler.py",
    "code/agentic_communication/task_transfer.py",
    "code/agentic_communication/benchmark_split.py",
    "code/evaluation/agentic/run_r3_model_eval.py",
    "code/evaluation/agentic/run_heldout_qili2024_seed0.py",
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _heldout():
    profile = qili_2016_rainfall_deformation_profile()
    task = profile.to_operational_task(task_hours=12)
    simulator = dict(DEFAULT_FULLSIM)
    simulator.update(
        {
            "harvest_mode": "irradiance",
            "irradiance_year": 2024,
            "irradiance_start_hour": WINDOW_START_HOURS["w1"],
        }
    )
    return profile, task, simulator


def _freeze_sources() -> None:
    path = OUT_ROOT / "source-manifest.json"
    files = {rel: _sha(ROOT / rel) for rel in SOURCE_FILES}
    payload = {
        "experiment": EXPERIMENT,
        "frozen_at": _now(),
        "seed": SEED,
        "models": [row["id"] for row in MODELS],
        "protocol_revision": PROTOCOL_REVISION,
        "files": files,
    }
    if path.is_file():
        frozen = json.loads(path.read_text(encoding="utf-8"))
        if frozen.get("files") != files:
            raise RuntimeError("held-out seed0 source changed after freeze")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _deepseek_backend(config: dict):
    from llm_planner import make_real_backend

    key = os.environ.get(config["api_key_env"]) or _load_shell_export(config["api_key_env"])
    if not key:
        raise RuntimeError(f"{config['api_key_env']} missing")
    backend, reason = make_real_backend(
        model=config["id"],
        base_url=config["base_url"],
        api_key=key,
        timeout=60.0,
        temperature=0.0,
        max_tokens=MAX_TOKENS,
        reasoning_effort="low",
        json_object=True,
    )
    if backend is None:
        raise RuntimeError(f"DeepSeek backend unavailable: {reason}")
    return backend


def _mimo_backend(config: dict):
    try:
        from openai import OpenAI
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"openai client unavailable: {type(exc).__name__}") from exc

    key = os.environ.get(config["api_key_env"])
    base_url = os.environ.get(config["base_url_env"])
    if not key or not base_url:
        raise RuntimeError(f"MiMo env missing: {config['api_key_env']} / {config['base_url_env']}")
    client = OpenAI(base_url=base_url, api_key=key, timeout=60.0)
    # Reachability / credential check before the experiment starts charging model calls.
    client.models.list()

    class _MiMoBackend:
        name = "xiaomi-mimo-openai-compatible"
        model = config["id"]

        def __init__(self):
            self.usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            self.last_metadata = None

        def complete(self, messages):
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.0,
                max_tokens=MAX_TOKENS,
                response_format={"type": "json_object"},
                extra_body={"thinking": {"type": "disabled"}},
            )
            usage = getattr(response, "usage", None)
            choice = response.choices[0]
            prompt_tokens = getattr(usage, "prompt_tokens", None)
            completion_tokens = getattr(usage, "completion_tokens", None)
            total_tokens = getattr(usage, "total_tokens", None)
            if prompt_tokens is not None:
                self.usage["prompt_tokens"] += int(prompt_tokens)
            if completion_tokens is not None:
                self.usage["completion_tokens"] += int(completion_tokens)
            if total_tokens is not None:
                self.usage["total_tokens"] += int(total_tokens)
            self.last_metadata = {
                "requested_model": self.model,
                "actual_model": getattr(response, "model", None),
                "finish_reason": getattr(choice, "finish_reason", None),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "temperature": 0.0,
                "max_tokens": MAX_TOKENS,
                "thinking": "disabled",
                "response_format": "json_object",
            }
            return choice.message.content or "{}"

    return _MiMoBackend()


def _backend(config: dict):
    if config["provider"] == "deepseek_official":
        return _deepseek_backend(config)
    if config["provider"] == "xiaomi_mimo_official":
        return _mimo_backend(config)
    raise ValueError(config["provider"])


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


def _summary_valid(path: Path, config: dict) -> bool:
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    cfg = data.get("config") or {}
    return (
        cfg.get("model") == config["id"]
        and cfg.get("provider") == config["provider"]
        and int(cfg.get("seed", -1)) == SEED
        and cfg.get("context_mode") == "action_conditioned_compact"
        and cfg.get("heldout_coordinate") == "qili-2024-w1"
    )


def main() -> int:
    _freeze_sources()
    gate = json.loads(
        (ROOT / "results" / "agentic" / "heldout-qili-2024-w1" / "gate.json").read_text(
            encoding="utf-8"
        )
    )
    if gate.get("status") != "PASS":
        raise RuntimeError("held-out deterministic gate is not PASS")

    profile, task, simulator = _heldout()
    reference, _, _ = run_reference_comply(
        seed=SEED,
        operational_task=task,
        simulator_kwargs=simulator,
    )
    candidate, _, _, _ = run_agentic_episode(
        seed=SEED,
        operational_task=task,
        context_mode="action_conditioned_compact",
        planner_consumer=ActionConditionedReferencePlannerConsumer(),
        planner_replan_mode="decision_state",
        simulator_kwargs=simulator,
    )

    rows = []
    for model_config in MODELS:
        out = OUT_ROOT / model_config["id"] / "seed-000"
        summary_path = out / "summary.json"
        if _summary_valid(summary_path, model_config):
            rows.append(json.loads(summary_path.read_text(encoding="utf-8")))
            print(f"SKIP {model_config['id']}", flush=True)
            continue

        backend = _backend(model_config)
        base = BackendPlannerConsumer(
            backend,
            consumer_id=f"heldout:{model_config['provider']}:{model_config['id']}",
            provider=model_config["provider"],
            model=model_config["id"],
        )
        consumer = BudgetedPlannerConsumer(base, MAX_CALLS)
        result, policy, _, _ = run_agentic_episode(
            seed=SEED,
            operational_task=task,
            context_mode="action_conditioned_compact",
            planner_consumer=consumer,
            planner_replan_mode="decision_state",
            simulator_kwargs=simulator,
        )
        out.mkdir(parents=True, exist_ok=True)
        trace = out / "runtime_trace.jsonl"
        policy.trace.write_jsonl(trace)
        replay = audit_trace(trace, context_mode="action_conditioned_compact")
        behavior = _planner_behavior_audit(policy)
        summary = {
            "generated_at": _now(),
            "experiment": EXPERIMENT,
            "config": {
                "model": model_config["id"],
                "provider": model_config["provider"],
                "seed": SEED,
                "context_mode": "action_conditioned_compact",
                "planner_replan_mode": "decision_state",
                "heldout_coordinate": "qili-2024-w1",
                "source_split": "test",
                "irradiance_year": 2024,
                "window_id": "w1",
                "task_id": task.task_id,
                "task_source_refs": list(task.source_refs),
                "generation": model_config["generation"],
                "max_model_calls": MAX_CALLS,
            },
            "task_phases": [row.model_dump(mode="json") for row in task.phases],
            "claim_boundary": profile.claim_boundary,
            "communication_metrics": result["agentic"]["communication_metrics"],
            "agent_metrics": result["agentic"]["agent_metrics"],
            "physical_equal_legacy": physical_signature(result) == physical_signature(reference),
            "physical_equal_candidate_reference": physical_signature(result) == physical_signature(candidate),
            "delta_vs_legacy": metric_delta(
                result["agentic"]["communication_metrics"], communication_metrics(reference)
            ),
            "model_calls_consumed": consumer.calls,
            "usage": _usage(policy),
            "planner_behavior_audit": behavior,
            "replay_audit": replay,
            "trace": str(trace),
            "cross_provider_cost_boundary": (
                "Do not compare token counts between providers; tokenization/reasoning accounting differs."
            ),
        }
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        rows.append(summary)
        print(
            f"DONE {model_config['id']} calls={consumer.calls} "
            f"exact={behavior['effect_scope_exact_turns']}/{behavior['planner_decision_turns']} "
            f"physical={summary['physical_equal_legacy']}",
            flush=True,
        )

    aggregate = {
        "experiment": EXPERIMENT,
        "completed_rows": len(rows),
        "expected_rows": len(MODELS),
        "heldout_coordinate": gate["heldout_coordinate"],
        "rows": rows,
    }
    (OUT_ROOT / "seed0-aggregate.json").write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"COMPLETE {OUT_ROOT / 'seed0-aggregate.json'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

