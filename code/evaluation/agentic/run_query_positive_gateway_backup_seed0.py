#!/usr/bin/env python3
"""Seed-0 real-model gate for decision-conditioned gateway-backup acquisition."""
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
for path in (
    CODE,
    CODE / "substrate" / "joint",
    CODE / "substrate" / "instance",
    CODE / "substrate" / "monitoring",
    CODE / "substrate" / "runtime",
    HERE,
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from joint_run import run_joint  # noqa: E402

from agentic_communication.metrics import (  # noqa: E402
    agent_metrics,
    communication_metrics,
    configuration_execution_metrics,
    metric_delta,
    physical_signature,
)
from agentic_communication.model_protocol import PROTOCOL_REVISION_V7  # noqa: E402
from agentic_communication.planner import (  # noqa: E402
    BackendPlannerConsumer,
    BudgetedPlannerConsumer,
    CompiledChecklistPlannerConsumer,
)
from agentic_communication.query_positive import QueryPositiveAgenticCommunicationPolicy  # noqa: E402
from agentic_communication.replay import audit_trace  # noqa: E402
from agentic_communication.run import DEFAULT_FULLSIM, _delivery_oracles  # noqa: E402
from run_query_positive_gateway_backup_gate import (  # noqa: E402
    QueryPositiveReferenceConsumer,
    SIMULATOR,
    _trace_audit,
    query_positive_task,
)
from run_r3_model_eval import _load_shell_export, _planner_behavior_audit  # noqa: E402


EXPERIMENT = "query-positive-gateway-backup-v1-seed0"
MODEL = "deepseek-flash"
SEED = 0
MAX_CALLS = 32
CONTEXT_MODE = "action_conditioned_compact_v7"
OUT_ROOT = ROOT / "results" / "agentic" / "query-positive-gateway-backup-v1" / MODEL
SOURCE_FILES = (
    "code/agentic_communication/action_context.py",
    "code/agentic_communication/capabilities.py",
    "code/agentic_communication/context_runtime.py",
    "code/agentic_communication/episodes.py",
    "code/agentic_communication/evidence_world.py",
    "code/agentic_communication/metrics.py",
    "code/agentic_communication/model_protocol.py",
    "code/agentic_communication/planner.py",
    "code/agentic_communication/policy.py",
    "code/agentic_communication/replay.py",
    "code/agentic_communication/run.py",
    "code/agentic_communication/runtime_contracts.py",
    "code/agentic_communication/task_compiler.py",
    "code/agentic_communication/query_positive.py",
    "code/evaluation/agentic/run_query_positive_gateway_backup_gate.py",
    "code/evaluation/agentic/run_query_positive_gateway_backup_seed0.py",
    "code/evaluation/agentic/run_r3_model_eval.py",
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _freeze_sources() -> None:
    gate = ROOT / "results" / "agentic" / "query-positive-gateway-backup-v1" / "deterministic-gate.json"
    gate_data = json.loads(gate.read_text(encoding="utf-8"))
    if gate_data.get("status") != "PASS":
        raise RuntimeError("query-positive deterministic gate is not PASS")
    files = {rel: _sha(ROOT / rel) for rel in SOURCE_FILES}
    path = OUT_ROOT / "source-manifest.json"
    payload = {
        "experiment": EXPERIMENT,
        "frozen_at": _now(),
        "model": MODEL,
        "seed": SEED,
        "protocol_revision": PROTOCOL_REVISION_V7,
        "context_mode": CONTEXT_MODE,
        "query_positive_compiler_revision": (
            "action-conditioned-context-v8-gateway-backup-query-positive"
        ),
        "deterministic_gate_sha256": _sha(gate),
        "files": files,
    }
    if path.is_file():
        frozen = json.loads(path.read_text(encoding="utf-8"))
        if frozen.get("files") != files:
            raise RuntimeError("query-positive seed0 source changed after freeze")
        if frozen.get("deterministic_gate_sha256") != payload["deterministic_gate_sha256"]:
            raise RuntimeError("query-positive deterministic gate changed after seed0 freeze")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _usage(policy) -> dict:
    total = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "latency_ms": 0.0}
    failed_attempts = 0
    successful_attempts = 0
    for event in policy.trace.events:
        if event.event_type == "model_usage":
            row = event.payload
            for key in ("input_tokens", "output_tokens", "total_tokens"):
                total[key] += int(row.get(key) or 0)
            total["latency_ms"] += float(row.get("latency_ms") or 0.0)
        elif event.event_type == "model_attempt":
            if event.payload.get("status") == "succeeded":
                successful_attempts += 1
            elif event.payload.get("status") == "failed":
                failed_attempts += 1
    return {
        **total,
        "successful_attempts": successful_attempts,
        "failed_attempts": failed_attempts,
    }


def _run_reference(*, consumer):
    task = query_positive_task()
    policy = QueryPositiveAgenticCommunicationPolicy(
        task,
        seed=SEED,
        context_mode=CONTEXT_MODE,
        planner_consumer=consumer,
        planner_replan_mode="decision_state",
    )
    kw = dict(DEFAULT_FULLSIM)
    kw.update(SIMULATOR)
    kw["trace"] = True
    result, inst, obligations = run_joint(
        seed=SEED,
        arm="local",
        mission_schedule=task.mission_schedule(),
        mission_scope=(task.target_node_ids or None),
        mission_policy_obj=policy,
        **kw,
    )
    end_s = int((kw["task_hours"] + kw["tail_hours"]) * 3600)
    policy.finalize(t_s=end_s, physical_result=result)
    result["evaluator_oracles"] = _delivery_oracles(
        inst, obligations, int(kw["task_hours"] + kw["tail_hours"])
    )
    result["configuration_execution"] = configuration_execution_metrics(inst, task)
    result["agentic"] = {
        "operational_task": task.model_dump(mode="json"),
        "context_mode": CONTEXT_MODE,
        "method_variant": "gateway-backup-query-positive-v1",
        "planner_replan_mode": "decision_state",
        "communication_metrics": communication_metrics(result),
        "agent_metrics": agent_metrics(policy),
    }
    return result, policy, inst


def _backend():
    api_key = os.environ.get("DEEPSEEK_API_KEY") or _load_shell_export("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not set")
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
    return backend


def main() -> int:
    _freeze_sources()
    deterministic_gate = json.loads(
        (
            ROOT
            / "results"
            / "agentic"
            / "query-positive-gateway-backup-v1"
            / "deterministic-gate.json"
        ).read_text(encoding="utf-8")
    )
    if deterministic_gate.get("status") != "PASS":
        raise RuntimeError("deterministic query-positive gate is not PASS")

    deterministic, deterministic_policy, deterministic_inst = _run_reference(
        consumer=QueryPositiveReferenceConsumer()
    )
    control, control_policy, control_inst = _run_reference(
        consumer=CompiledChecklistPlannerConsumer()
    )

    backend = _backend()
    base = BackendPlannerConsumer(
        backend,
        consumer_id=f"query-positive:{MODEL}",
        provider=str(getattr(backend, "name", "deepseek_official")),
        model=MODEL,
    )
    consumer = BudgetedPlannerConsumer(base, MAX_CALLS)
    result, policy, inst = _run_reference(consumer=consumer)

    out = OUT_ROOT / "seed-000"
    out.mkdir(parents=True, exist_ok=True)
    trace = out / "runtime_trace.jsonl"
    policy.trace.write_jsonl(trace)
    replay = audit_trace(trace, context_mode=CONTEXT_MODE)
    behavior = _planner_behavior_audit(policy)
    query_audit = _trace_audit(policy)
    deterministic_query_audit = _trace_audit(deterministic_policy)
    metrics = result["agentic"]["communication_metrics"]
    deterministic_metrics = deterministic["agentic"]["communication_metrics"]
    control_metrics = control["agentic"]["communication_metrics"]

    query_chain_pass = bool(
        query_audit["query_request_count"] >= 1
        and query_audit["backup_effect_count"] == 1
        and query_audit["guard_counts"].get("supported", 0) >= 1
        and bool(inst.plane.enable_backup)
    )
    physical_reference_exact = physical_signature(result) == physical_signature(deterministic)
    physical_control_different = physical_signature(result) != physical_signature(control)
    summary = {
        "generated_at": _now(),
        "experiment": EXPERIMENT,
        "config": {
            "model": MODEL,
            "seed": SEED,
            "context_mode": CONTEXT_MODE,
            "protocol_revision": PROTOCOL_REVISION_V7,
            "query_positive_compiler_revision": (
                "action-conditioned-context-v8-gateway-backup-query-positive"
            ),
            "planner_replan_mode": "decision_state",
            "simulator": SIMULATOR,
            "task_id": query_positive_task().task_id,
            "generation": {
                "temperature": 0.0,
                "max_tokens": 8192,
                "reasoning_effort": "low",
                "json_object": True,
            },
            "max_model_calls": MAX_CALLS,
        },
        "communication_metrics": metrics,
        "deterministic_reference_metrics": deterministic_metrics,
        "no_acquisition_control_metrics": control_metrics,
        "delta_vs_deterministic_reference": metric_delta(metrics, deterministic_metrics),
        "delta_vs_no_acquisition_control": metric_delta(metrics, control_metrics),
        "physical_equal_query_positive_reference": physical_reference_exact,
        "physical_equal_no_acquisition_control": physical_signature(result) == physical_signature(control),
        "physical_control_different": physical_control_different,
        "query_chain_pass": query_chain_pass,
        "query_audit": query_audit,
        "deterministic_query_audit": deterministic_query_audit,
        "model_calls_consumed": consumer.calls,
        "usage": _usage(policy),
        "planner_behavior_audit": behavior,
        "replay_audit": replay,
        "trace": str(trace),
        "final_gateway_backup": bool(inst.plane.enable_backup),
        "control_gateway_backup": bool(control_inst.plane.enable_backup),
        "deterministic_gateway_backup": bool(deterministic_inst.plane.enable_backup),
        "seed0_gate_pass": bool(
            query_chain_pass
            and physical_reference_exact
            and physical_control_different
            and metrics["timely_delivery_rate"] > control_metrics["timely_delivery_rate"]
            and metrics["aoi_mean_s"] < control_metrics["aoi_mean_s"]
            and replay.get("passed") is True
        ),
        "claim_boundary": (
            "Seed-0 gate only. A positive result shows one real model can resolve a public blocking "
            "EvidenceNeed, trigger the existing gateway-backup effect, and reproduce the deterministic "
            "query-positive physical trajectory. It is not a five-seed or cross-model claim."
        ),
    }
    (out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "seed0_gate_pass": summary["seed0_gate_pass"],
                "model_calls": consumer.calls,
                "queries": query_audit["query_request_count"],
                "guard_counts": query_audit["guard_counts"],
                "backup_effects": query_audit["backup_effect_count"],
                "final_gateway_backup": summary["final_gateway_backup"],
                "physical_reference_exact": physical_reference_exact,
                "physical_control_different": physical_control_different,
                "tdr": metrics["timely_delivery_rate"],
                "control_tdr": control_metrics["timely_delivery_rate"],
                "aoi_mean_s": metrics["aoi_mean_s"],
                "control_aoi_mean_s": control_metrics["aoi_mean_s"],
                "effect_exact": behavior["effect_scope_exact_turns"],
                "effect_inexact": behavior["effect_scope_inexact_turns"],
                "observations": behavior["local_observation_invocations"]
                + behavior["remote_observation_invocations"],
                "failed_attempts": summary["usage"]["failed_attempts"],
                "total_tokens": summary["usage"]["total_tokens"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )
    print(f"WROTE {out / 'summary.json'}", flush=True)
    return 0 if summary["seed0_gate_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

