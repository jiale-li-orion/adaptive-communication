#!/usr/bin/env python3
"""Five-seed, two-model held-out confirmatory for v7 compact projection."""
from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
ROOT = HERE.parents[2]
for path in (CODE, CODE / "monitoring", CODE / "runtime", HERE):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from agentic_communication.metrics import communication_metrics, metric_delta, physical_signature  # noqa: E402
from agentic_communication.planner import (  # noqa: E402
    ActionConditionedReferencePlannerConsumer,
    BackendPlannerConsumer,
    BudgetedPlannerConsumer,
)
from agentic_communication.replay import audit_trace  # noqa: E402
from agentic_communication.run import run_agentic_episode, run_reference_comply  # noqa: E402
from run_heldout_qili2024_seed0 import MODELS, _backend, _heldout, _usage  # noqa: E402
from run_heldout_qili2024_v7_seed0 import (  # noqa: E402
    CONTEXT_MODE,
    MAX_CALLS,
    OUT_ROOT,
    PROTOCOL_REVISION_V7,
)
from run_r3_model_eval import _planner_behavior_audit  # noqa: E402


EXPERIMENT = "heldout-qili-2024-w1-model-transfer-v7-confirmatory"
SEEDS = tuple(range(5))
NEW_SEEDS = (1, 2, 3, 4)
SEED0_MANIFEST = OUT_ROOT / "source-manifest.json"
CONFIRMATORY_MANIFEST = OUT_ROOT / "confirmatory-source-manifest.json"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _summary_path(model: str, seed: int) -> Path:
    return OUT_ROOT / model / f"seed-{seed:03d}" / "summary.json"


def _summary_valid(path: Path, model_config: dict, seed: int) -> bool:
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
        and int(cfg.get("seed", -1)) == seed
        and cfg.get("context_mode") == CONTEXT_MODE
        and cfg.get("protocol_revision") == PROTOCOL_REVISION_V7
        and cfg.get("heldout_coordinate") == "qili-2024-w1"
    )


def _freeze_sources() -> None:
    if not SEED0_MANIFEST.is_file():
        raise RuntimeError("v7 seed0 source manifest missing")
    seed0 = json.loads(SEED0_MANIFEST.read_text(encoding="utf-8"))
    shared = dict(seed0.get("files") or {})
    changed = []
    for rel, expected in shared.items():
        path = ROOT / rel
        actual = _sha(path) if path.is_file() else None
        if actual != expected:
            changed.append({"path": rel, "seed0": expected, "current": actual})
    if changed:
        raise RuntimeError(
            "v7 shared source differs from seed0; refuse mixed-revision confirmatory: "
            + json.dumps(changed, ensure_ascii=False)
        )

    current = {
        "seed0_shared_files": shared,
        "confirmatory_runner": {
            str(Path(__file__).resolve().relative_to(ROOT)): _sha(Path(__file__).resolve())
        },
    }
    payload = {
        "experiment": EXPERIMENT,
        "frozen_at": _now(),
        "models": [row["id"] for row in MODELS],
        "seeds": list(SEEDS),
        "protocol_revision": PROTOCOL_REVISION_V7,
        "context_mode": CONTEXT_MODE,
        "seed0_manifest_sha256": _sha(SEED0_MANIFEST),
        "files": current,
        "claim_boundary": (
            "Held-out task/source/model transfer of action fidelity only. Cross-provider token counts "
            "are not compared; the coordinate remains unique-ready-plan and query-negative."
        ),
    }
    if CONFIRMATORY_MANIFEST.is_file():
        frozen = json.loads(CONFIRMATORY_MANIFEST.read_text(encoding="utf-8"))
        if frozen.get("files") != current:
            raise RuntimeError("held-out v7 confirmatory manifest changed after freeze")
        return
    CONFIRMATORY_MANIFEST.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _run_one(*, model_config: dict, seed: int, task, simulator: dict) -> dict:
    path = _summary_path(model_config["id"], seed)
    if _summary_valid(path, model_config, seed):
        print(f"SKIP {model_config['id']}/seed-{seed:03d}", flush=True)
        return json.loads(path.read_text(encoding="utf-8"))

    backend = _backend(model_config)
    base = BackendPlannerConsumer(
        backend,
        consumer_id=f"heldout-v7:{model_config['provider']}:{model_config['id']}",
        provider=model_config["provider"],
        model=model_config["id"],
    )
    consumer = BudgetedPlannerConsumer(base, MAX_CALLS)
    reference, _, _ = run_reference_comply(
        seed=seed,
        operational_task=task,
        simulator_kwargs=simulator,
    )
    candidate, _, _, _ = run_agentic_episode(
        seed=seed,
        operational_task=task,
        context_mode=CONTEXT_MODE,
        planner_consumer=ActionConditionedReferencePlannerConsumer(),
        planner_replan_mode="decision_state",
        simulator_kwargs=simulator,
    )
    result, policy, _, _ = run_agentic_episode(
        seed=seed,
        operational_task=task,
        context_mode=CONTEXT_MODE,
        planner_consumer=consumer,
        planner_replan_mode="decision_state",
        simulator_kwargs=simulator,
    )
    out = path.parent
    out.mkdir(parents=True, exist_ok=True)
    trace = out / "runtime_trace.jsonl"
    policy.trace.write_jsonl(trace)
    replay = audit_trace(trace, context_mode=CONTEXT_MODE)
    behavior = _planner_behavior_audit(policy)
    profile, _, _ = _heldout()
    summary = {
        "generated_at": _now(),
        "experiment": EXPERIMENT,
        "config": {
            "model": model_config["id"],
            "provider": model_config["provider"],
            "seed": seed,
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
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"DONE {model_config['id']}/seed-{seed:03d} calls={consumer.calls} "
        f"exact={behavior['effect_scope_exact_turns']}/{behavior['planner_decision_turns']} "
        f"obs={behavior['local_observation_invocations'] + behavior['remote_observation_invocations']} "
        f"physical={summary['physical_equal_legacy']}",
        flush=True,
    )
    return summary


def _aggregate() -> Path:
    rows = []
    for model_config in MODELS:
        for seed in SEEDS:
            path = _summary_path(model_config["id"], seed)
            if _summary_valid(path, model_config, seed):
                rows.append(json.loads(path.read_text(encoding="utf-8")))
    payload = {
        "experiment": EXPERIMENT,
        "models": [row["id"] for row in MODELS],
        "seeds": list(SEEDS),
        "completed_rows": len(rows),
        "expected_rows": len(MODELS) * len(SEEDS),
        "rows": rows,
    }
    path = OUT_ROOT / "confirmatory-aggregate.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    _freeze_sources()
    for model_config in MODELS:
        if not _summary_valid(_summary_path(model_config["id"], 0), model_config, 0):
            raise RuntimeError(f"missing/invalid seed0 v7 checkpoint for {model_config['id']}")
    _, task, simulator = _heldout()

    # Interleave providers within each seed so a time-local provider issue cannot
    # masquerade as a seed effect.  Every coordinate is retained regardless of outcome.
    for seed in NEW_SEEDS:
        for model_config in MODELS:
            _run_one(model_config=model_config, seed=seed, task=task, simulator=simulator)
            _aggregate()
    final = _aggregate()
    print(f"COMPLETE {final}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

