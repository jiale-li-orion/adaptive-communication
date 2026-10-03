#!/usr/bin/env python3
"""Seed-0 full-episode gate for v7 retired-plan projection on DeepSeek + MiMo."""
from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
ROOT = HERE.parents[2]
for path in (CODE, CODE / "substrate" / "monitoring", CODE / "substrate" / "runtime", HERE):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from agentic_communication.metrics import communication_metrics, metric_delta, physical_signature  # noqa: E402
from agentic_communication.model_protocol import PROTOCOL_REVISION_V7  # noqa: E402
from agentic_communication.planner import (  # noqa: E402
    ActionConditionedReferencePlannerConsumer,
    BackendPlannerConsumer,
    BudgetedPlannerConsumer,
)
from agentic_communication.replay import audit_trace  # noqa: E402
from agentic_communication.run import run_agentic_episode, run_reference_comply  # noqa: E402
from run_heldout_qili2024_seed0 import MODELS, _backend, _heldout, _usage  # noqa: E402
from run_r3_model_eval import _planner_behavior_audit  # noqa: E402


EXPERIMENT = "heldout-qili-2024-w1-model-transfer-v7-seed0"
OUT_ROOT = ROOT / "results" / "agentic" / "heldout-qili-2024-w1" / "model-transfer-v7"
SEED = 0
MAX_CALLS = 32
CONTEXT_MODE = "action_conditioned_compact_v7"
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
    "code/evaluation/agentic/run_heldout_qili2024_v7_seed0.py",
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _freeze_sources() -> None:
    path = OUT_ROOT / "source-manifest.json"
    files = {rel: _sha(ROOT / rel) for rel in SOURCE_FILES}
    payload = {
        "experiment": EXPERIMENT,
        "frozen_at": _now(),
        "seed": SEED,
        "models": [row["id"] for row in MODELS],
        "protocol_revision": PROTOCOL_REVISION_V7,
        "context_mode": CONTEXT_MODE,
        "projection_change": (
            "omit unresolved_conditions from rejected/dominated model-facing candidate plans; "
            "full candidate audit, supported/conditional plan semantics, EvidenceNeed and top-level "
            "unresolved dependency audit remain unchanged"
        ),
        "files": files,
    }
    if path.is_file():
        frozen = json.loads(path.read_text(encoding="utf-8"))
        if frozen.get("files") != files:
            raise RuntimeError("v7 held-out seed0 source changed after freeze")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _summary_valid(path: Path, model_config: dict) -> bool:
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    cfg = data.get("config") or {}
    return (
        cfg.get("model") == model_config["id"]
        and cfg.get("provider") == model_config["provider"]
        and int(cfg.get("seed", -1)) == SEED
        and cfg.get("context_mode") == CONTEXT_MODE
        and cfg.get("protocol_revision") == PROTOCOL_REVISION_V7
        and cfg.get("heldout_coordinate") == "qili-2024-w1"
    )


def main() -> int:
    _freeze_sources()
    gate_path = ROOT / "results" / "agentic" / "heldout-qili-2024-w1" / "gate.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
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
        context_mode=CONTEXT_MODE,
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
            consumer_id=f"heldout-v7:{model_config['provider']}:{model_config['id']}",
            provider=model_config["provider"],
            model=model_config["id"],
        )
        consumer = BudgetedPlannerConsumer(base, MAX_CALLS)
        result, policy, _, _ = run_agentic_episode(
            seed=SEED,
            operational_task=task,
            context_mode=CONTEXT_MODE,
            planner_consumer=consumer,
            planner_replan_mode="decision_state",
            simulator_kwargs=simulator,
        )
        out.mkdir(parents=True, exist_ok=True)
        trace = out / "runtime_trace.jsonl"
        policy.trace.write_jsonl(trace)
        replay = audit_trace(trace, context_mode=CONTEXT_MODE)
        behavior = _planner_behavior_audit(policy)
        summary = {
            "generated_at": _now(),
            "experiment": EXPERIMENT,
            "config": {
                "model": model_config["id"],
                "provider": model_config["provider"],
                "seed": SEED,
                "context_mode": CONTEXT_MODE,
                "protocol_revision": PROTOCOL_REVISION_V7,
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
            f"obs={behavior['local_observation_invocations'] + behavior['remote_observation_invocations']} "
            f"physical={summary['physical_equal_legacy']}",
            flush=True,
        )

    old_root = ROOT / "results" / "agentic" / "heldout-qili-2024-w1" / "model-transfer-v1"
    comparison = {}
    for model_config in MODELS:
        old = json.loads(
            (old_root / model_config["id"] / "seed-000" / "summary.json").read_text(
                encoding="utf-8"
            )
        )
        new = next(row for row in rows if row["config"]["model"] == model_config["id"])
        oa = old["planner_behavior_audit"]
        na = new["planner_behavior_audit"]
        comparison[model_config["id"]] = {
            "v6": {
                "calls": old["model_calls_consumed"],
                "effect_inexact": oa["effect_scope_inexact_turns"],
                "observations": oa["local_observation_invocations"]
                + oa["remote_observation_invocations"],
                "physical_equal_legacy": old["physical_equal_legacy"],
            },
            "v7": {
                "calls": new["model_calls_consumed"],
                "effect_inexact": na["effect_scope_inexact_turns"],
                "observations": na["local_observation_invocations"]
                + na["remote_observation_invocations"],
                "physical_equal_legacy": new["physical_equal_legacy"],
            },
        }

    aggregate = {
        "experiment": EXPERIMENT,
        "completed_rows": len(rows),
        "expected_rows": len(MODELS),
        "heldout_coordinate": gate["heldout_coordinate"],
        "v6_vs_v7": comparison,
        "rows": rows,
    }
    (OUT_ROOT / "seed0-aggregate.json").write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(comparison, ensure_ascii=False, indent=2), flush=True)
    print(f"COMPLETE {OUT_ROOT / 'seed0-aggregate.json'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

