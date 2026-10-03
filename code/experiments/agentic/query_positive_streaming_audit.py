"""Low-memory R0/R2 audit for query-positive Agentic Communication traces."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from agentic_communication.contracts import (  # noqa: E402
    EvidenceWorldSnapshot,
    OperationalTask,
    RuntimeTraceEvent,
)
from agentic_communication.query_positive import QueryPositiveContextRuntime  # noqa: E402
from agentic_communication.replay import _rebuilt_assembly  # noqa: E402
from agentic_communication.runtime_contracts import (  # noqa: E402
    ContextManifest,
    PromptAssembly,
    TaskContract,
)


def audit_query_positive_trace_streaming(
    trace_path: str | Path,
    *,
    context_mode: str = "action_conditioned_compact_v7",
) -> dict:
    trace = Path(trace_path)
    runtime = QueryPositiveContextRuntime()
    operational: OperationalTask | None = None
    task_by_run: dict[str, TaskContract] = {}
    latest_snapshot: EvidenceWorldSnapshot | None = None
    latest_context: tuple[int, int, str, ContextManifest] | None = None

    failures: list[str] = []
    event_counts = Counter()
    evidence_digests: dict[int, str] = {}
    requests: set[str] = set()
    results: set[str] = set()
    expected_seq = 1
    last_t = -1
    prompt_count = 0
    context_count = 0
    r2_exact = 0
    completion = None
    backup_effect_count = 0

    with trace.open(encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            if not line.strip():
                continue
            event = RuntimeTraceEvent.model_validate_json(line)
            event_counts[event.event_type] += 1
            if event.seq != expected_seq:
                failures.append(
                    f"non_contiguous_sequence:{lineno}:expected={expected_seq}:actual={event.seq}"
                )
                expected_seq = event.seq
            expected_seq += 1
            if event.t_s < last_t:
                failures.append(f"non_monotone_sim_time:{lineno}:{event.t_s}<{last_t}")
            last_t = event.t_s
            payload = event.payload

            if event.event_type == "operational_task":
                operational = OperationalTask.model_validate(payload)
            elif event.event_type == "runtime_task_contract":
                task_by_run[event.task_run_id or ""] = TaskContract.model_validate(payload)
            elif event.event_type == "evidence_world_revision":
                snap = EvidenceWorldSnapshot.model_validate(payload)
                prior = evidence_digests.get(snap.revision)
                if prior is not None and prior != snap.digest:
                    failures.append(f"revision_reused_with_different_digest:{snap.revision}")
                evidence_digests[snap.revision] = snap.digest
                latest_snapshot = snap
            elif event.event_type == "capability_request":
                request_id = str(payload.get("request_id"))
                if request_id in requests:
                    failures.append(f"duplicate_capability_request:{request_id}")
                requests.add(request_id)
            elif event.event_type == "capability_result":
                request_id = str(payload.get("request_id"))
                if request_id not in requests:
                    failures.append(f"result_without_request:{request_id}")
                results.add(request_id)
            elif event.event_type == "percept":
                request_id = str(payload.get("request_id"))
                if request_id not in requests:
                    failures.append(f"percept_without_request:{request_id}")
                if request_id not in results:
                    failures.append(f"percept_before_result:{request_id}")
            elif event.event_type == "context_manifest":
                context_count += 1
                ctx = ContextManifest.model_validate(payload)
                run_id = event.task_run_id or ""
                task = task_by_run.get(run_id)
                if task is None or ctx.task_contract_ref != task.task_contract_id:
                    failures.append(f"context_unknown_task:{ctx.task_contract_ref}")
                if latest_snapshot is None or latest_snapshot.revision != ctx.world_revision:
                    failures.append(
                        f"context_not_on_latest_world:{ctx.context_revision}:"
                        f"ctx={ctx.world_revision}:latest="
                        f"{None if latest_snapshot is None else latest_snapshot.revision}"
                    )
                elif set(ctx.evidence_refs) - set(latest_snapshot.by_id()):
                    failures.append(f"context_unknown_evidence:{ctx.context_revision}")
                latest_context = (event.seq, event.t_s, run_id, ctx)
            elif event.event_type == "prompt_assembly":
                prompt_count += 1
                assembly = PromptAssembly.model_validate(payload)
                rebuilt_static = _rebuilt_assembly(assembly)
                if rebuilt_static.assembly_hash != assembly.assembly_hash:
                    failures.append(f"assembly_hash_mismatch:{assembly.assembly_id}")
                if rebuilt_static.assembly_id != assembly.assembly_id:
                    failures.append(f"assembly_id_mismatch:{assembly.assembly_id}")

                if operational is None or latest_snapshot is None or latest_context is None:
                    failures.append(f"r2_missing_state:{assembly.context_manifest_revision}")
                    continue
                _, context_t_s, run_id, ctx = latest_context
                if assembly.context_manifest_revision != ctx.context_revision:
                    failures.append(
                        f"assembly_context_mismatch:{assembly.context_manifest_revision}!={ctx.context_revision}"
                    )
                    continue
                task = task_by_run.get(run_id)
                if task is None:
                    failures.append(f"r2_missing_task:{run_id}")
                    continue

                cap_fragment = next(
                    (fragment for fragment in assembly.fragments if fragment.kind == "capability_catalog"),
                    None,
                )
                capability_specs = (
                    cap_fragment.content
                    if cap_fragment is not None and isinstance(cap_fragment.content, list)
                    else None
                )
                inventory_fragment = next(
                    (fragment for fragment in assembly.fragments if fragment.kind == "resource_inventory"),
                    None,
                )
                resource_ids = (
                    list(inventory_fragment.content)
                    if inventory_fragment is not None and isinstance(inventory_fragment.content, list)
                    else None
                )
                outcomes_fragment = next(
                    (
                        fragment
                        for fragment in assembly.fragments
                        if fragment.kind == "recent_capability_outcomes"
                    ),
                    None,
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
                    evidence_world=latest_snapshot,
                    capability_ids=list(ctx.capability_refs),
                    capability_specs=capability_specs,
                    resource_ids=resource_ids,
                    recent_capability_outcomes=recent_outcomes,
                    t_s=context_t_s,
                    context_revision=ctx.context_revision,
                    parent_context_id=ctx.parent_context_id,
                    context_mode=context_mode,
                )
                if rebuilt_ctx.evidence_refs != ctx.evidence_refs:
                    failures.append(f"r2_context_evidence_refs:{ctx.context_revision}")
                if rebuilt_ctx.context_id != ctx.context_id:
                    failures.append(f"r2_context_id:{ctx.context_revision}")
                if rebuilt.assembly_hash != assembly.assembly_hash:
                    failures.append(f"r2_assembly_hash:{ctx.context_revision}")
                else:
                    r2_exact += 1
            elif event.event_type == "physical_effect":
                request_id = str(payload.get("request_id"))
                if request_id not in requests:
                    failures.append(f"physical_effect_without_request:{request_id}")
                if request_id not in results:
                    failures.append(f"physical_effect_without_accept_result:{request_id}")
                if (
                    payload.get("capability_id") == "communication.fallback.gateway_backup"
                    and payload.get("lifecycle_stage") == "applied"
                ):
                    backup_effect_count += 1
                    runtime.action_selector.backup_enabled_by_agent = True
            elif event.event_type == "task_completion":
                completion = dict(payload)

    if operational is None:
        failures.append("missing_operational_task")
    if not task_by_run:
        failures.append("missing_runtime_task_contract")
    if not evidence_digests:
        failures.append("missing_evidence_world")
    if context_count == 0:
        failures.append("missing_context_manifest")
    if prompt_count == 0:
        failures.append("missing_prompt_assembly")
    if event_counts["task_completion"] != 1:
        failures.append(f"task_completion_count:{event_counts['task_completion']}")
    if r2_exact != prompt_count:
        failures.append(f"r2_exact_count:{r2_exact}/{prompt_count}")

    r0_failures = [failure for failure in failures if not failure.startswith("r2_")]
    r2_failures = [failure for failure in failures if failure.startswith("r2_")]
    return {
        "passed": not failures,
        "R0": {
            "passed": not r0_failures,
            "events": sum(event_counts.values()),
            "event_counts": dict(sorted(event_counts.items())),
            "evidence_revisions": len(evidence_digests),
            "contexts": context_count,
            "prompt_assemblies": prompt_count,
            "capability_requests": len(requests),
            "capability_results": len(results),
            "failures": r0_failures,
        },
        "R1": {
            "passed": True,
            "frozen_prompt_assemblies": prompt_count,
        },
        "R2": {
            "passed": not r2_failures and r2_exact == prompt_count,
            "contexts": prompt_count,
            "exact_assembly_matches": r2_exact,
            "backup_effect_count": backup_effect_count,
            "failures": r2_failures,
        },
        "task_completion": completion,
        "failures": failures,
    }

