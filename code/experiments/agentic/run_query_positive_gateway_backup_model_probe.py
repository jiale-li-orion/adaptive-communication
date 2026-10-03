#!/usr/bin/env python3
"""Seed-0 DeepSeek gate for real query -> evidence -> gateway-backup closure."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
ROOT = HERE.parents[2]
for path in (CODE, CODE / "monitoring", CODE / "runtime", CODE / "v3joint", CODE / "instance", HERE):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from agentic_communication.metrics import metric_delta, physical_signature  # noqa: E402
from agentic_communication.model_protocol import PROTOCOL_REVISION  # noqa: E402
from agentic_communication.planner import BackendPlannerConsumer, BudgetedPlannerConsumer  # noqa: E402
from agentic_communication.query_positive import (  # noqa: E402
    GATEWAY_BACKUP_PLAN_ID,
    QueryPositiveContextRuntime,
)
from agentic_communication.replay import audit_r0, frozen_r1_inputs, load_trace  # noqa: E402
from agentic_communication.runtime_contracts import (  # noqa: E402
    ContextManifest,
    PromptAssembly,
    TaskContract,
)
from agentic_communication.contracts import EvidenceWorldSnapshot, OperationalTask  # noqa: E402
from run_heldout_qili2024_seed0 import MODELS, _backend, _usage  # noqa: E402
from run_query_positive_gateway_backup_gate import (  # noqa: E402
    OUT as DETERMINISTIC_GATE,
    QueryPositiveReferenceConsumer,
    SIMULATOR,
    _run_policy,
    _trace_audit,
    query_positive_task,
)
from run_r3_model_eval import _planner_behavior_audit  # noqa: E402


EXPERIMENT = "query-positive-gateway-backup-v1-deepseek-seed0"
OUT_ROOT = ROOT / "results" / "agentic" / "query-positive-gateway-backup-v1" / "deepseek-flash" / "seed-000"
MANIFEST = ROOT / "results" / "agentic" / "query-positive-gateway-backup-v1" / "model-probe-source-manifest.json"
SUMMARY = OUT_ROOT / "summary.json"
TRACE = OUT_ROOT / "runtime_trace.jsonl"
SEED = 0
MAX_CALLS = 32
CONTEXT_MODE = "action_conditioned_compact_v7"
CONTEXT_VARIANT = "gateway-backup-query-positive-v1"
SELECTOR_REVISION = "action-conditioned-context-v8-gateway-backup-query-positive"
RUNTIME_REVISION = "communication-context-runtime-v8-gateway-backup-query-positive"
MODEL = MODELS[0]

SOURCE_FILES = (
    "code/agentic_communication/action_context.py",
    "code/agentic_communication/capabilities.py",
    "code/agentic_communication/context_runtime.py",
    "code/agentic_communication/evidence_world.py",
    "code/agentic_communication/model_protocol.py",
    "code/agentic_communication/planner.py",
    "code/agentic_communication/policy.py",
    "code/agentic_communication/query_positive.py",
    "code/agentic_communication/replay.py",
    "code/agentic_communication/runtime_contracts.py",
    "code/agentic_communication/task_compiler.py",
    "code/experiments/agentic/run_query_positive_gateway_backup_gate.py",
    "code/experiments/agentic/run_query_positive_gateway_backup_model_probe.py",
    "code/experiments/agentic/run_r3_model_eval.py",
    "code/experiments/agentic/run_heldout_qili2024_seed0.py",
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _freeze_sources() -> None:
    files = {rel: _sha(ROOT / rel) for rel in SOURCE_FILES}
    payload = {
        "experiment": EXPERIMENT,
        "frozen_at": _now(),
        "seed": SEED,
        "model": MODEL["id"],
        "provider": MODEL["provider"],
        "model_protocol_revision": PROTOCOL_REVISION,
        "context_mode": CONTEXT_MODE,
        "context_variant": CONTEXT_VARIANT,
        "selector_revision": SELECTOR_REVISION,
        "context_runtime_revision": RUNTIME_REVISION,
        "simulator": SIMULATOR,
        "files": files,
    }
    if MANIFEST.is_file():
        frozen = json.loads(MANIFEST.read_text(encoding="utf-8"))
        if frozen.get("files") != files:
            raise RuntimeError("query-positive model-probe source changed after freeze")
        return
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _deterministic_gate() -> dict:
    data = json.loads(DETERMINISTIC_GATE.read_text(encoding="utf-8"))
    if data.get("status") != "PASS":
        raise RuntimeError("query-positive deterministic gate is not PASS")
    row = next((row for row in data.get("rows") or [] if int(row.get("seed", -1)) == SEED), None)
    if row is None:
        raise RuntimeError("query-positive deterministic seed0 row missing")
    return row


def _audit_query_positive_r2(path: Path) -> dict:
    """Exact R2 reconstruction with the v8 selector's execution state."""
    rows = load_trace(path)
    failures: list[str] = []
    operational: OperationalTask | None = None
    task_by_run: dict[str, TaskContract] = {}
    evidence_by_revision: dict[int, EvidenceWorldSnapshot] = {}
    contexts: list[tuple[int, int, str, ContextManifest]] = []
    assemblies: dict[tuple[str, int], PromptAssembly] = {}
    backup_effect_seqs: list[int] = []

    for event in rows:
        if event.event_type == "operational_task":
            operational = OperationalTask.model_validate(event.payload)
        elif event.event_type == "runtime_task_contract":
            task_by_run[event.task_run_id or ""] = TaskContract.model_validate(event.payload)
        elif event.event_type == "evidence_world_revision":
            snap = EvidenceWorldSnapshot.model_validate(event.payload)
            evidence_by_revision[snap.revision] = snap
        elif event.event_type == "context_manifest":
            ctx = ContextManifest.model_validate(event.payload)
            contexts.append((event.seq, event.t_s, event.task_run_id or "", ctx))
        elif event.event_type == "prompt_assembly":
            assembly = PromptAssembly.model_validate(event.payload)
            assemblies[(event.task_run_id or "", assembly.context_manifest_revision)] = assembly
        elif (
            event.event_type == "physical_effect"
            and event.payload.get("capability_id") == "communication.fallback.gateway_backup"
            and event.payload.get("lifecycle_stage") == "applied"
        ):
            backup_effect_seqs.append(event.seq)

    if operational is None:
        return {"level": "R2-query-positive", "passed": False, "failures": ["missing_operational_task"]}

    runtime = QueryPositiveContextRuntime()
    matched = 0
    for seq, t_s, run_id, ctx in sorted(contexts):
        runtime.action_selector.backup_enabled_by_agent = any(effect_seq < seq for effect_seq in backup_effect_seqs)
        recorded = assemblies.get((run_id, ctx.context_revision))
        task = task_by_run.get(run_id)
        snap = evidence_by_revision.get(ctx.world_revision)
        if recorded is None or task is None or snap is None:
            failures.append(f"missing_replay_coordinate:{run_id}:{ctx.context_revision}")
            continue
        cap_fragment = next((f for f in recorded.fragments if f.kind == "capability_catalog"), None)
        capability_specs = (
            cap_fragment.content
            if cap_fragment is not None and isinstance(cap_fragment.content, list)
            else None
        )
        inventory_fragment = next((f for f in recorded.fragments if f.kind == "resource_inventory"), None)
        resource_ids = (
            list(inventory_fragment.content)
            if inventory_fragment is not None and isinstance(inventory_fragment.content, list)
            else None
        )
        outcomes_fragment = next(
            (f for f in recorded.fragments if f.kind == "recent_capability_outcomes"), None
        )
        recent_outcomes = (
            list(outcomes_fragment.content)
            if outcomes_fragment is not None and isinstance(outcomes_fragment.content, list)
            else None
        )
        _, _, rebuilt_ctx, rebuilt, _ = runtime.build(
            operational_task=operational,
            task=task,
            task_run_id=run_id,
            evidence_world=snap,
            capability_ids=list(ctx.capability_refs),
            capability_specs=capability_specs,
            resource_ids=resource_ids,
            recent_capability_outcomes=recent_outcomes,
            t_s=t_s,
            context_revision=ctx.context_revision,
            parent_context_id=ctx.parent_context_id,
            context_mode=CONTEXT_MODE,
        )
        if rebuilt_ctx.evidence_refs != ctx.evidence_refs:
            failures.append(f"context_evidence_refs_mismatch:{run_id}:{ctx.context_revision}")
        if rebuilt_ctx.context_id != ctx.context_id:
            failures.append(f"context_id_mismatch:{run_id}:{ctx.context_revision}")
        if rebuilt.assembly_hash != recorded.assembly_hash:
            failures.append(f"assembly_hash_mismatch:{run_id}:{ctx.context_revision}")
        else:
            matched += 1

    return {
        "level": "R2-query-positive",
        "passed": not failures,
        "context_mode": CONTEXT_MODE,
        "contexts": len(contexts),
        "exact_assembly_matches": matched,
        "backup_effect_count": len(backup_effect_seqs),
        "failures": failures,
    }


def _query_behavior(policy) -> dict:
    current_candidate: dict = {}
    current_needs: list[dict] = []
    turns = []
    queried_caps: set[str] = set()
    expected_open_caps: set[str] = set()
    backup_effects = 0
    for event in policy.trace.events:
        if event.event_type == "prompt_assembly":
            fragments = {
                str(row.get("kind", "")): row.get("content")
                for row in event.payload.get("fragments", [])
                if isinstance(row, dict)
            }
            current_candidate = dict(fragments.get("candidate_action_context") or {})
            current_needs = [
                row for row in (fragments.get("evidence_needs") or []) if isinstance(row, dict)
            ]
            continue
        if event.event_type == "physical_effect":
            if event.payload.get("capability_id") == "communication.fallback.gateway_backup":
                backup_effects += 1
            continue
        if event.event_type != "planner_decision":
            continue
        invocations = list(event.payload.get("invocations") or [])
        obs = {
            str(row.get("capability_id"))
            for row in invocations
            if str(row.get("capability_id", "")).startswith("communication.gateway.")
        }
        queried_caps |= obs
        qp = dict(current_candidate.get("query_positive_gateway_backup") or {})
        expected_obs = set()
        for need in current_needs:
            if GATEWAY_BACKUP_PLAN_ID not in set(need.get("blocking_plan_ids") or []):
                continue
            question = str(need.get("proposition_or_question") or "")
            for cap in ("communication.gateway.primary_health", "communication.gateway.receipt_summary"):
                if cap in question:
                    expected_obs.add(cap)
        expected_open_caps |= expected_obs
        turns.append(
            {
                "t_s": int(event.t_s),
                "guard_result": qp.get("guard_result"),
                "expected_open_query_capabilities": sorted(expected_obs),
                "actual_query_capabilities": sorted(obs),
                "selected_plan_id": event.payload.get("selected_plan_id"),
                "has_gateway_backup_effect": any(
                    row.get("capability_id") == "communication.fallback.gateway_backup"
                    for row in invocations
                ),
                "stop": bool(event.payload.get("stop")),
            }
        )
    return {
        "planner_turns": len(turns),
        "queried_capabilities": sorted(queried_caps),
        "expected_open_query_capabilities": sorted(expected_open_caps),
        "covered_all_open_query_capabilities": bool(expected_open_caps)
        and expected_open_caps <= queried_caps,
        "backup_effect_count": backup_effects,
        "needs_evidence_turns": sum(row["guard_result"] == "needs_evidence" for row in turns),
        "supported_turns": sum(row["guard_result"] == "supported" for row in turns),
        "rejected_turns": sum(row["guard_result"] == "rejected" for row in turns),
        "turns": turns,
    }


def _summary_valid() -> bool:
    if not SUMMARY.is_file():
        return False
    try:
        data = json.loads(SUMMARY.read_text(encoding="utf-8"))
    except Exception:
        return False
    cfg = data.get("config") or {}
    return (
        data.get("status") in {"PASS", "FAIL"}
        and cfg.get("model") == MODEL["id"]
        and cfg.get("provider") == MODEL["provider"]
        and int(cfg.get("seed", -1)) == SEED
        and cfg.get("context_variant") == CONTEXT_VARIANT
        and cfg.get("model_protocol_revision") == PROTOCOL_REVISION
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--freeze-only", action="store_true")
    args = ap.parse_args()
    deterministic = _deterministic_gate()
    _freeze_sources()
    if args.freeze_only:
        print(f"FROZEN {MANIFEST}")
        return 0
    if _summary_valid():
        data = json.loads(SUMMARY.read_text(encoding="utf-8"))
        print(f"SKIP existing status={data['status']} {SUMMARY}")
        return 0 if data["status"] == "PASS" else 2

    reference, reference_policy, _ = _run_policy(
        seed=SEED,
        consumer=QueryPositiveReferenceConsumer(),
    )

    backend = _backend(MODEL)
    base = BackendPlannerConsumer(
        backend,
        consumer_id=f"query-positive:{MODEL['provider']}:{MODEL['id']}",
        provider=MODEL["provider"],
        model=MODEL["id"],
    )
    consumer = BudgetedPlannerConsumer(base, MAX_CALLS)
    result, policy, inst = _run_policy(seed=SEED, consumer=consumer)

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    policy.trace.write_jsonl(TRACE)
    events = load_trace(TRACE)
    r0 = audit_r0(events)
    r1 = {
        "level": "R1",
        "passed": True,
        "frozen_prompt_assemblies": len(frozen_r1_inputs(events)),
    }
    r2 = _audit_query_positive_r2(TRACE)
    replay = {"passed": bool(r0["passed"] and r2["passed"]), "R0": r0, "R1": r1, "R2": r2}
    behavior = _planner_behavior_audit(policy)
    query_behavior = _query_behavior(policy)
    metrics = result["agentic"]["communication_metrics"]
    control_metrics = deterministic["no_acquisition_control"]
    physical_equal = physical_signature(result) == physical_signature(reference)
    reference_query = _trace_audit(reference_policy)
    success = bool(
        replay["passed"]
        and behavior["failed_model_attempts"] == 0
        and behavior["effect_scope_inexact_turns"] == 0
        and query_behavior["covered_all_open_query_capabilities"]
        and query_behavior["backup_effect_count"] == 1
        and bool(inst.plane.enable_backup)
        and physical_equal
        and metrics["timely_delivery_rate"] > control_metrics["timely_delivery_rate"]
        and metrics["aoi_mean_s"] < control_metrics["aoi_mean_s"]
    )
    summary = {
        "generated_at": _now(),
        "experiment": EXPERIMENT,
        "status": "PASS" if success else "FAIL",
        "config": {
            "model": MODEL["id"],
            "provider": MODEL["provider"],
            "seed": SEED,
            "generation": MODEL["generation"],
            "max_model_calls": MAX_CALLS,
            "model_protocol_revision": PROTOCOL_REVISION,
            "context_mode": CONTEXT_MODE,
            "context_variant": CONTEXT_VARIANT,
            "selector_revision": SELECTOR_REVISION,
            "context_runtime_revision": RUNTIME_REVISION,
            "planner_replan_mode": "decision_state",
            "simulator": SIMULATOR,
            "task_id": query_positive_task().task_id,
        },
        "claim_boundary": (
            "Single DeepSeek Flash seed-0 gate on gateway-placed O3 with backup initially disabled and "
            "3600s primary store-and-forward delay. Tests whether the model itself acquires existing "
            "gateway-owner evidence before enabling an already-authorized gateway backup."
        ),
        "communication_metrics": metrics,
        "no_acquisition_control_metrics": control_metrics,
        "delta_vs_no_acquisition": metric_delta(metrics, control_metrics),
        "physical_equal_deterministic_query_positive_reference": physical_equal,
        "deterministic_reference_query_audit": reference_query,
        "model_calls_consumed": consumer.calls,
        "usage": _usage(policy),
        "planner_behavior_audit": behavior,
        "query_behavior_audit": query_behavior,
        "replay_audit": replay,
        "trace": str(TRACE),
        "source_manifest": str(MANIFEST),
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": summary["status"],
                "calls": consumer.calls,
                "failed_model_attempts": behavior["failed_model_attempts"],
                "effect_exact": behavior["effect_scope_exact_turns"],
                "effect_inexact": behavior["effect_scope_inexact_turns"],
                "queried_capabilities": query_behavior["queried_capabilities"],
                "backup_effect_count": query_behavior["backup_effect_count"],
                "backup_final": bool(inst.plane.enable_backup),
                "physical_equal_reference": physical_equal,
                "tdr": metrics["timely_delivery_rate"],
                "tdr_control": control_metrics["timely_delivery_rate"],
                "aoi": metrics["aoi_mean_s"],
                "aoi_control": control_metrics["aoi_mean_s"],
                "replay": replay["passed"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )
    print(f"WROTE {SUMMARY}", flush=True)
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())

