"""Deterministic R0/R1/R2 replay over Agentic Communication runtime traces.

R0 validates protocol/information-boundary invariants without rerunning physics.
R1 exposes the exact frozen PromptAssembly objects used at the consumer boundary.
R2 rebuilds Context/PromptAssembly from frozen Task + EvidenceWorld coordinates and
requires exact assembly-hash equality.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Callable, Iterable

from .contracts import EvidenceWorldSnapshot, OperationalTask, RuntimeTraceEvent
from .context_runtime import CommunicationContextRuntime
from .runtime_contracts import ContextManifest, MaterializedFragment, PromptAssembly, TaskContract
from .planner import PlannerConsumer, PlannerInvocationResult, invoke_consumer


def load_trace(path: str | Path) -> list[RuntimeTraceEvent]:
    rows: list[RuntimeTraceEvent] = []
    with Path(path).open(encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                rows.append(RuntimeTraceEvent.model_validate_json(line))
            except Exception as exc:  # pragma: no cover - error path is surfaced to audit
                raise ValueError(f"invalid trace JSON at {path}:{lineno}: {exc}") from exc
    return rows


def _rebuilt_assembly(recorded: PromptAssembly) -> PromptAssembly:
    fragments = [MaterializedFragment.model_validate(f.model_dump(mode="json")) for f in recorded.fragments]
    return PromptAssembly.build(
        task_contract_id=recorded.task_contract_id,
        task_run_id=recorded.task_run_id,
        context_manifest_revision=recorded.context_manifest_revision,
        fragments=fragments,
        percept_refs=list(recorded.percept_refs),
    )


def audit_r0(events: Iterable[RuntimeTraceEvent]) -> dict:
    rows = list(events)
    failures: list[str] = []
    if not rows:
        return {"level": "R0", "passed": False, "failures": ["empty_trace"]}

    expected_seq = list(range(1, len(rows) + 1))
    seqs = [e.seq for e in rows]
    if seqs != expected_seq:
        failures.append("non_contiguous_sequence")
    times = [e.t_s for e in rows]
    if times != sorted(times):
        failures.append("non_monotone_sim_time")

    task_contracts: dict[str, TaskContract] = {}
    evidence_by_revision: dict[int, EvidenceWorldSnapshot] = {}
    requests: set[str] = set()
    results: set[str] = set()
    contexts: dict[tuple[str, int], ContextManifest] = {}
    prompt_count = 0
    completion_count = 0

    for event in rows:
        p = event.payload
        if event.event_type == "runtime_task_contract":
            task = TaskContract.model_validate(p)
            task_contracts[task.task_contract_id] = task
        elif event.event_type == "evidence_world_revision":
            snap = EvidenceWorldSnapshot.model_validate(p)
            prior = evidence_by_revision.get(snap.revision)
            if prior is not None and prior.digest != snap.digest:
                failures.append(f"revision_reused_with_different_digest:{snap.revision}")
            evidence_by_revision[snap.revision] = snap
        elif event.event_type == "capability_request":
            rid = str(p.get("request_id"))
            if rid in requests:
                failures.append(f"duplicate_capability_request:{rid}")
            requests.add(rid)
        elif event.event_type == "capability_result":
            rid = str(p.get("request_id"))
            if rid not in requests:
                failures.append(f"result_without_request:{rid}")
            results.add(rid)
        elif event.event_type == "percept":
            rid = str(p.get("request_id"))
            if rid not in requests:
                failures.append(f"percept_without_request:{rid}")
            if rid not in results:
                failures.append(f"percept_before_result:{rid}")
        elif event.event_type == "context_manifest":
            ctx = ContextManifest.model_validate(p)
            if ctx.task_contract_ref not in task_contracts:
                failures.append(f"context_unknown_task:{ctx.task_contract_ref}")
            snap = evidence_by_revision.get(ctx.world_revision)
            if snap is None:
                failures.append(f"context_unknown_world_revision:{ctx.world_revision}")
            else:
                legal = set(snap.by_id())
                bad = sorted(set(ctx.evidence_refs) - legal)
                if bad:
                    failures.append(f"context_unknown_evidence:{ctx.context_id}:{','.join(bad)}")
            contexts[(event.task_run_id or "", ctx.context_revision)] = ctx
        elif event.event_type == "prompt_assembly":
            prompt_count += 1
            assembly = PromptAssembly.model_validate(p)
            if (event.task_run_id or "", assembly.context_manifest_revision) not in contexts:
                failures.append(
                    f"assembly_without_context:{event.task_run_id}:{assembly.context_manifest_revision}"
                )
            rebuilt = _rebuilt_assembly(assembly)
            if rebuilt.assembly_hash != assembly.assembly_hash:
                failures.append(f"assembly_hash_mismatch:{assembly.assembly_id}")
            if rebuilt.assembly_id != assembly.assembly_id:
                failures.append(f"assembly_id_mismatch:{assembly.assembly_id}")
        elif event.event_type == "physical_effect":
            rid = str(p.get("request_id"))
            if rid not in requests:
                failures.append(f"physical_effect_without_request:{rid}")
            if rid not in results:
                failures.append(f"physical_effect_without_accept_result:{rid}")
        elif event.event_type == "task_completion":
            completion_count += 1

    if not task_contracts:
        failures.append("missing_runtime_task_contract")
    if not evidence_by_revision:
        failures.append("missing_evidence_world")
    if not contexts:
        failures.append("missing_context_manifest")
    if prompt_count == 0:
        failures.append("missing_prompt_assembly")
    if completion_count != 1:
        failures.append(f"task_completion_count:{completion_count}")

    return {
        "level": "R0",
        "passed": not failures,
        "events": len(rows),
        "task_contracts": len(task_contracts),
        "evidence_revisions": len(evidence_by_revision),
        "contexts": len(contexts),
        "prompt_assemblies": prompt_count,
        "capability_requests": len(requests),
        "capability_results": len(results),
        "failures": failures,
    }


@dataclass(frozen=True)
class FrozenPlannerInput:
    seq: int
    t_s: int
    task_run_id: str
    assembly: PromptAssembly


def frozen_r1_inputs(events: Iterable[RuntimeTraceEvent]) -> list[FrozenPlannerInput]:
    """Return exact consumer-boundary inputs, independent of the physical simulator.

    A later model runner can map any callable over these records.  No model-specific
    schema is baked into the trace format.
    """
    out: list[FrozenPlannerInput] = []
    for event in events:
        if event.event_type != "prompt_assembly":
            continue
        out.append(
            FrozenPlannerInput(
                seq=event.seq,
                t_s=event.t_s,
                task_run_id=event.task_run_id or "",
                assembly=PromptAssembly.model_validate(event.payload),
            )
        )
    return out


def replay_r1(
    events: Iterable[RuntimeTraceEvent],
    consumer: Callable[[FrozenPlannerInput], object],
) -> list[object]:
    return [consumer(record) for record in frozen_r1_inputs(events)]


def replay_r1_planner(
    events: Iterable[RuntimeTraceEvent],
    consumer: PlannerConsumer,
) -> list[PlannerInvocationResult]:
    """Run a typed planner/model consumer over exact frozen model inputs.

    This is the R1 measurement path for model substitution. It records request,
    attempt/usage and structured decision without rerunning physics.
    """
    out: list[PlannerInvocationResult] = []
    for idx, record in enumerate(frozen_r1_inputs(events), 1):
        out.append(
            invoke_consumer(
                assembly=record.assembly,
                consumer=consumer,
                request_id=f"r1:{record.task_run_id}:{record.seq}:{idx}",
            )
        )
    return out


def audit_r2(events: Iterable[RuntimeTraceEvent], *, context_mode: str) -> dict:
    rows = list(events)
    failures: list[str] = []
    operational: OperationalTask | None = None
    task_by_run: dict[str, TaskContract] = {}
    evidence_by_revision: dict[int, EvidenceWorldSnapshot] = {}
    context_by_key: dict[tuple[str, int], tuple[int, ContextManifest]] = {}
    assembly_by_key: dict[tuple[str, int], PromptAssembly] = {}

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
            context_by_key[(event.task_run_id or "", ctx.context_revision)] = (event.t_s, ctx)
        elif event.event_type == "prompt_assembly":
            assembly = PromptAssembly.model_validate(event.payload)
            assembly_by_key[(event.task_run_id or "", assembly.context_manifest_revision)] = assembly

    if operational is None:
        return {"level": "R2", "passed": False, "failures": ["missing_operational_task"]}

    runtime = CommunicationContextRuntime()
    matched = 0
    for key, (t_s, ctx) in sorted(context_by_key.items(), key=lambda kv: (kv[1][0], kv[0][1])):
        run_id, revision = key
        recorded = assembly_by_key.get(key)
        task = task_by_run.get(run_id)
        snap = evidence_by_revision.get(ctx.world_revision)
        if recorded is None or task is None or snap is None:
            failures.append(f"missing_replay_coordinate:{run_id}:{revision}")
            continue
        cap_fragment = next((f for f in recorded.fragments if f.kind == "capability_catalog"), None)
        capability_specs = (
            cap_fragment.content
            if cap_fragment is not None and isinstance(cap_fragment.content, list)
            else None
        )
        inventory_fragment = next(
            (f for f in recorded.fragments if f.kind == "resource_inventory"), None
        )
        resource_ids = (
            list(inventory_fragment.content)
            if inventory_fragment is not None and isinstance(inventory_fragment.content, list)
            else None
        )
        outcomes_fragment = next(
            (f for f in recorded.fragments if f.kind == "recent_capability_outcomes"), None
        )
        recent_capability_outcomes = (
            list(outcomes_fragment.content)
            if outcomes_fragment is not None and isinstance(outcomes_fragment.content, list)
            else None
        )
        _state, _needs, rebuilt_ctx, rebuilt, _stats = runtime.build(
            operational_task=operational,
            task=task,
            task_run_id=run_id,
            evidence_world=snap,
            capability_ids=list(ctx.capability_refs),
            capability_specs=capability_specs,
            resource_ids=resource_ids,
            recent_capability_outcomes=recent_capability_outcomes,
            t_s=t_s,
            context_revision=revision,
            parent_context_id=ctx.parent_context_id,
            context_mode=context_mode,
        )
        if rebuilt_ctx.evidence_refs != ctx.evidence_refs:
            failures.append(f"context_evidence_refs_mismatch:{run_id}:{revision}")
        if rebuilt_ctx.context_id != ctx.context_id:
            failures.append(f"context_id_mismatch:{run_id}:{revision}")
        if rebuilt.assembly_hash != recorded.assembly_hash:
            failures.append(f"assembly_hash_mismatch:{run_id}:{revision}")
        else:
            matched += 1

    return {
        "level": "R2",
        "passed": not failures,
        "context_mode": context_mode,
        "contexts": len(context_by_key),
        "exact_assembly_matches": matched,
        "failures": failures,
    }


def audit_trace(path: str | Path, *, context_mode: str) -> dict:
    events = load_trace(path)
    r0 = audit_r0(events)
    r1 = {
        "level": "R1",
        "passed": True,
        "frozen_prompt_assemblies": len(frozen_r1_inputs(events)),
        "note": "consumer/model substitution API ready; no model result is asserted by this audit",
    }
    r2 = audit_r2(events, context_mode=context_mode)
    return {"trace": str(path), "passed": r0["passed"] and r2["passed"], "R0": r0, "R1": r1, "R2": r2}
