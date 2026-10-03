"""Planner/model consumer boundary for frozen or live PromptAssembly inputs.

The runtime never requires a specific model SDK.  A consumer receives a typed
PromptAssembly and returns a typed PlannerDecision plus ModelAttempt/Usage ledger.
This keeps deterministic, callable-model and gold consumers on the same surface.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import time
from typing import Callable, Protocol

from .runtime_contracts import (
    ModelAttempt,
    ModelAttemptStatus,
    ModelRequest,
    ModelUsage,
    PlannerDecisionProposal,
    PlannerDecision,
    PromptAssembly,
    PlannedCapabilityInvocation,
)
from .gold_replacement import (
    apply_gold_replacement,
    decision_steps,
    outcome_to_decision,
)
from .trajectory_eval import GoldReplacementLayer
from .model_protocol import PROTOCOL_REVISION, render_planner_protocol


@dataclass(frozen=True)
class PlannerInvocationResult:
    request: ModelRequest
    attempt: ModelAttempt
    decision: PlannerDecision | None


class PlannerConsumer(Protocol):
    consumer_id: str
    provider: str
    model: str

    def decide(self, request: ModelRequest, assembly: PromptAssembly) -> tuple[PlannerDecision, ModelUsage]: ...


def _hash_json(value) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return sha256(raw).hexdigest()


def _expand_selected_candidate_plan(
    decision: PlannerDecision,
    assembly: PromptAssembly,
) -> PlannerDecision:
    """Deterministically expand a model-selected Runtime candidate plan.

    Candidate construction is Runtime-owned.  The model still chooses the plan;
    this helper only removes mechanical repetition of an already-declared typed
    invocation list.  Additional explicit invocations (typically observations)
    are preserved, allowing query+effect mixed decisions.
    """
    plan_id = decision.selected_plan_id
    if plan_id is None:
        return decision
    fragments = {
        fragment.kind: fragment.content
        for fragment in assembly.fragments
    }
    candidate = fragments.get("candidate_action_context")
    if not isinstance(candidate, dict):
        raise ValueError("selected_plan_id requires model-visible candidate_action_context")
    matches = [
        row
        for row in candidate.get("candidate_plans", [])
        if isinstance(row, dict) and row.get("plan_id") == plan_id
    ]
    if len(matches) != 1:
        raise ValueError(f"selected_plan_id {plan_id!r} is not one visible candidate plan")
    plan = matches[0]
    if plan.get("feasibility") != "supported":
        raise ValueError(
            f"selected_plan_id {plan_id!r} is not supported: {plan.get('feasibility')!r}"
        )
    if plan.get("unresolved_conditions"):
        raise ValueError(f"selected_plan_id {plan_id!r} still has unresolved conditions")

    expanded = [
        PlannedCapabilityInvocation.model_validate(row)
        for row in (plan.get("invocations") or [])
    ]
    if decision.stop and (expanded or decision.invocations):
        raise ValueError(
            f"selected_plan_id {plan_id!r} has effects and cannot be combined with stop=true"
        )
    merged: list[PlannedCapabilityInvocation] = []
    seen: set[tuple[str, str, str]] = set()
    for invocation in [*expanded, *decision.invocations]:
        key = (
            invocation.capability_id,
            invocation.resource,
            json.dumps(
                invocation.canonical_arguments,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
        )
        if key in seen:
            continue
        seen.add(key)
        merged.append(invocation)
    return decision.model_copy(update={"invocations": merged})


def invoke_consumer(
    *,
    assembly: PromptAssembly,
    consumer: PlannerConsumer,
    request_id: str,
) -> PlannerInvocationResult:
    request = ModelRequest(
        request_id=request_id,
        task_run_id=assembly.task_run_id,
        assembly_id=assembly.assembly_id,
        assembly_hash=assembly.assembly_hash,
        consumer_id=consumer.consumer_id,
        request_metadata={"context_manifest_revision": assembly.context_manifest_revision},
    )
    input_bytes = len(assembly.model_dump_json().encode("utf-8"))
    try:
        decision, usage = consumer.decide(request, assembly)
        usage = usage.model_copy(update={"input_bytes": max(usage.input_bytes, input_bytes)})
        # Ledger the model's actual parsed output before Runtime candidate-plan
        # expansion.  Token usage already comes from the backend itself.
        out = decision.model_dump(mode="json")
        output_bytes = len(json.dumps(out, ensure_ascii=False, sort_keys=True).encode("utf-8"))
        usage = usage.model_copy(update={"output_bytes": max(usage.output_bytes, output_bytes)})
        attempt = ModelAttempt(
            attempt_id=f"attempt:{request_id}:0",
            request_id=request_id,
            provider=consumer.provider,
            model=consumer.model,
            status=ModelAttemptStatus.SUCCEEDED,
            usage=usage,
            output_hash=_hash_json(out),
        )
        decision = _expand_selected_candidate_plan(decision, assembly)
        return PlannerInvocationResult(request=request, attempt=attempt, decision=decision)
    except Exception as exc:
        attempt = ModelAttempt(
            attempt_id=f"attempt:{request_id}:0",
            request_id=request_id,
            provider=consumer.provider,
            model=consumer.model,
            status=ModelAttemptStatus.FAILED,
            usage=ModelUsage(input_bytes=input_bytes),
            error_code=type(exc).__name__,
            error_detail=str(exc)[:500],
        )
        return PlannerInvocationResult(request=request, attempt=attempt, decision=None)


class CallablePlannerConsumer:
    """SDK-agnostic adapter for a model/API callable.

    The callable receives the serialized PromptAssembly and returns a dict matching
    PlannerDecision. Optional usage fields can be returned under ``_usage``.
    """

    def __init__(
        self,
        fn: Callable[[dict], dict],
        *,
        consumer_id: str,
        provider: str,
        model: str,
        input_renderer: Callable[[PromptAssembly], dict] | None = None,
    ) -> None:
        self.fn = fn
        self.consumer_id = consumer_id
        self.provider = provider
        self.model = model
        self.input_renderer = input_renderer

    def decide(self, request: ModelRequest, assembly: PromptAssembly) -> tuple[PlannerDecision, ModelUsage]:
        model_input = (
            self.input_renderer(assembly)
            if self.input_renderer is not None
            else assembly.model_dump(mode="json")
        )
        raw = self.fn(model_input)
        if not isinstance(raw, dict):
            raise TypeError("planner callable must return a dict")
        raw = dict(raw)
        usage_raw = raw.pop("_usage", {}) or {}
        proposal = PlannerDecisionProposal.model_validate(raw)
        decision = PlannerDecision(
            decision_id=f"decision:{request.request_id}",
            request_id=request.request_id,
            **proposal.model_dump(mode="python"),
        )
        usage = ModelUsage.model_validate(usage_raw)
        return decision, usage


def _parse_backend_json(text: str) -> dict:
    raw = (text or "").strip()
    if raw.startswith("```") and raw.endswith("```"):
        lines = raw.splitlines()
        if lines and lines[0].strip().lower() in {"```", "```json"}:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise TypeError("model backend must return one JSON object")
    return value


class BackendPlannerConsumer:
    """Adapter for any existing backend exposing ``complete(messages)``.

    This deliberately owns no HTTP/API client.  Existing OpenAI-compatible,
    local-vLLM, scripted, or provider-specific backends can be reused as-is.
    """

    def __init__(
        self,
        backend,
        *,
        consumer_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        if not callable(getattr(backend, "complete", None)):
            raise TypeError("backend must expose complete(messages)")
        self.backend = backend
        self.consumer_id = consumer_id or f"backend:{getattr(backend, 'name', 'unknown')}"
        self.provider = provider or str(getattr(backend, "name", "backend"))
        self.model = model or str(getattr(backend, "model", self.provider))

    @staticmethod
    def _usage_snapshot(backend) -> dict:
        raw = getattr(backend, "usage", None)
        return dict(raw) if isinstance(raw, dict) else {}

    @staticmethod
    def _usage_delta(before: dict, after: dict, latency_ms: float) -> ModelUsage:
        def delta(*names: str):
            for name in names:
                if name in after:
                    return max(0, int(after.get(name, 0) or 0) - int(before.get(name, 0) or 0))
            return None

        prompt = delta("prompt_tokens", "input_tokens")
        completion = delta("completion_tokens", "output_tokens")
        total = None
        if prompt is not None or completion is not None:
            total = int(prompt or 0) + int(completion or 0)
        return ModelUsage(
            input_tokens=prompt,
            output_tokens=completion,
            total_tokens=total,
            latency_ms=latency_ms,
        )

    def decide(self, request: ModelRequest, assembly: PromptAssembly) -> tuple[PlannerDecision, ModelUsage]:
        envelope = render_planner_protocol(assembly)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a communication-operations planner. Follow the supplied typed "
                    "protocol exactly and return one JSON object matching output_schema."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(envelope, ensure_ascii=False, sort_keys=True),
            },
        ]
        before = self._usage_snapshot(self.backend)
        t0 = time.perf_counter()
        raw_text = self.backend.complete(messages)
        latency_ms = (time.perf_counter() - t0) * 1000.0
        after = self._usage_snapshot(self.backend)
        raw = _parse_backend_json(raw_text)
        proposal = PlannerDecisionProposal.model_validate(raw)
        decision = PlannerDecision(
            decision_id=f"decision:{request.request_id}",
            request_id=request.request_id,
            **proposal.model_dump(mode="python"),
        )
        usage = self._usage_delta(before, after, latency_ms)
        return decision, usage


class BudgetedPlannerConsumer:
    """Hard cap on model/planner calls for live R3 runs.

    Exhaustion is explicit in PlannerDecision rather than silently falling back
    to another policy or backend.
    """

    def __init__(self, base: PlannerConsumer, max_calls: int) -> None:
        if int(max_calls) <= 0:
            raise ValueError("max_calls must be positive")
        self.base = base
        self.max_calls = int(max_calls)
        self.calls = 0
        self.consumer_id = f"budgeted:{base.consumer_id}:{self.max_calls}"
        self.provider = base.provider
        self.model = base.model

    def decide(self, request: ModelRequest, assembly: PromptAssembly) -> tuple[PlannerDecision, ModelUsage]:
        if self.calls >= self.max_calls:
            return (
                PlannerDecision(
                    decision_id=f"decision:{request.request_id}",
                    request_id=request.request_id,
                    stop=True,
                    invocations=[],
                    reason_codes=["model_call_budget_exhausted"],
                ),
                ModelUsage(),
            )
        self.calls += 1
        return self.base.decide(request, assembly)


class GoldPlannerConsumer:
    provider = "benchmark"
    model = "gold-reference"

    def __init__(self, decisions_by_assembly_hash: dict[str, dict], *, consumer_id: str = "gold") -> None:
        self.decisions = dict(decisions_by_assembly_hash)
        self.consumer_id = consumer_id

    def decide(self, request: ModelRequest, assembly: PromptAssembly) -> tuple[PlannerDecision, ModelUsage]:
        raw = self.decisions[assembly.assembly_hash]
        payload = dict(raw)
        payload["request_id"] = request.request_id
        payload.setdefault("decision_id", f"decision:{request.request_id}")
        return PlannerDecision.model_validate(payload), ModelUsage()


class DeterministicComplyPlannerConsumer:
    """Typed deterministic planner used to validate the live model boundary.

    It reads only PromptAssembly fragments: active TaskContract plus the selected
    evidence slice / InvestigationState. Runtime guards still own in-flight,
    dwell, generation stamping and physical execution.
    """

    consumer_id = "deterministic-comply-v1"
    provider = "runtime"
    model = "deterministic-comply"

    @staticmethod
    def _fragment(assembly: PromptAssembly, kind: str):
        for fragment in assembly.fragments:
            if fragment.kind == kind:
                return fragment.content
        return None

    def decide(self, request: ModelRequest, assembly: PromptAssembly) -> tuple[PlannerDecision, ModelUsage]:
        task = self._fragment(assembly, "runtime_task_contract") or {}
        state = self._fragment(assembly, "investigation_state") or {}
        inventory = self._fragment(assembly, "resource_inventory") or []
        evidence = self._fragment(assembly, "evidence_slice") or []
        desired = dict(task.get("desired_state") or {})
        period = int(desired["required_period_s"])
        targets = list(state.get("targets") or inventory or [])
        reports = {}
        for row in evidence:
            if row.get("proposition") != "communication.center.node_report":
                continue
            reports[row.get("subject_ref")] = dict(row.get("value") or {})

        invocations: list[PlannedCapabilityInvocation] = []
        for nid in targets:
            report = reports.get(nid) or {}
            # Legacy comply is a paired configuration decision: if either field
            # is not confirmed at target, resend *both* fields under one runtime
            # generation.  Keeping this exact semantics is what makes this
            # consumer a conformance baseline rather than a stronger new policy.
            if (
                report.get("sample_interval_s") != period
                or report.get("report_period_s") != period
            ):
                invocations.append(
                    PlannedCapabilityInvocation(
                        capability_id="communication.config.set_sampling_interval",
                        resource=nid,
                        canonical_arguments={"target_s": period},
                    )
                )
                invocations.append(
                    PlannedCapabilityInvocation(
                        capability_id="communication.config.set_report_period",
                        resource=nid,
                        canonical_arguments={"target_s": period},
                    )
                )
        decision = PlannerDecision(
            decision_id=f"decision:{request.request_id}",
            request_id=request.request_id,
            stop=not invocations,
            invocations=invocations,
            reason_codes=["task-profile-mismatch" if invocations else "task-profile-confirmed"],
        )
        return decision, ModelUsage()


class EvidenceAwareComplyPlannerConsumer(DeterministicComplyPlannerConsumer):
    """Multi-round deterministic reference consumer.

    Open owner-scoped EvidenceNeeds are resolved through typed observation
    capabilities before the ordinary comply action decision is emitted.  This is
    the reference implementation for the Evidence-use-tool -> Context revision ->
    Device-use-tool runtime loop; it is not an LLM.
    """

    consumer_id = "evidence-aware-comply-v1"
    model = "evidence-aware-deterministic-comply"

    def decide(self, request: ModelRequest, assembly: PromptAssembly) -> tuple[PlannerDecision, ModelUsage]:
        needs = self._fragment(assembly, "evidence_needs") or []
        specs = self._fragment(assembly, "capability_catalog") or []
        visible = {
            row.get("capability_id")
            for row in specs
            if isinstance(row, dict) and row.get("capability_id")
        }
        queries: list[PlannedCapabilityInvocation] = []
        for need in needs:
            if need.get("status") != "open":
                continue
            text = f"{need.get('proposition_or_question','')} {need.get('purpose','')}"
            for cid in (
                "communication.gateway.primary_health",
                "communication.gateway.receipt_summary",
            ):
                if cid in text and cid in visible and not any(q.capability_id == cid for q in queries):
                    queries.append(
                        PlannedCapabilityInvocation(
                            capability_id=cid,
                            resource="gw0",
                            canonical_arguments={"gateway_id": "gw0"},
                        )
                    )
        if queries:
            return (
                PlannerDecision(
                    decision_id=f"decision:{request.request_id}",
                    request_id=request.request_id,
                    stop=False,
                    invocations=queries,
                    reason_codes=["resolve-owner-scoped-evidence-needs"],
                ),
                ModelUsage(),
            )
        return super().decide(request, assembly)


class ActionConditionedReferencePlannerConsumer(DeterministicComplyPlannerConsumer):
    """Deterministic reference consumer for the action-conditioned method path.

    The selector owns candidate generation and evidence dependencies.  This
    consumer first resolves active unresolved dependencies, then executes the
    supported ordinary configuration candidate.  It exists to validate the
    end-to-end method path before a real model replaces plan selection.
    """

    consumer_id = "action-conditioned-reference-v1"
    model = "action-conditioned-reference"

    def decide(self, request: ModelRequest, assembly: PromptAssembly) -> tuple[PlannerDecision, ModelUsage]:
        candidate = self._fragment(assembly, "candidate_action_context") or {}
        specs = self._fragment(assembly, "capability_catalog") or []
        visible = {
            row.get("capability_id")
            for row in specs
            if isinstance(row, dict) and row.get("capability_id")
        }
        queries: list[PlannedCapabilityInvocation] = []
        for dep in candidate.get("dependencies", []):
            if dep.get("fresh") or dep.get("acquisition") != "active_capability":
                continue
            cid = str(dep.get("proposition", ""))
            subject = str(dep.get("subject", ""))
            if cid not in visible:
                continue
            if cid == "communication.gateway.node_report":
                args = {"node_id": subject}
            elif cid.startswith("communication.gateway."):
                args = {"gateway_id": subject}
            else:
                args = {}
            queries.append(
                PlannedCapabilityInvocation(
                    capability_id=cid,
                    resource=subject,
                    canonical_arguments=args,
                )
            )
        if queries:
            # Preserve order while removing duplicate dependency calls.
            unique: list[PlannedCapabilityInvocation] = []
            seen: set[tuple[str, str]] = set()
            for q in queries:
                key = (q.capability_id, q.resource)
                if key not in seen:
                    seen.add(key)
                    unique.append(q)
            return (
                PlannerDecision(
                    decision_id=f"decision:{request.request_id}",
                    request_id=request.request_id,
                    stop=False,
                    invocations=unique,
                    reason_codes=["resolve-action-conditioned-dependencies"],
                ),
                ModelUsage(),
            )

        plans = list(candidate.get("candidate_plans", []))
        install = next(
            (
                p
                for p in plans
                if p.get("plan_id") == "install_required_profile"
                and p.get("feasibility") == "supported"
            ),
            None,
        )
        if install is not None and install.get("invocations"):
            return (
                PlannerDecision(
                    decision_id=f"decision:{request.request_id}",
                    request_id=request.request_id,
                    stop=False,
                    invocations=[
                        PlannedCapabilityInvocation.model_validate(row)
                        for row in install.get("invocations", [])
                    ],
                    reason_codes=["execute-supported-action-conditioned-plan"],
                ),
                ModelUsage(),
            )
        return (
            PlannerDecision(
                decision_id=f"decision:{request.request_id}",
                request_id=request.request_id,
                stop=True,
                invocations=[],
                reason_codes=["supported-hold-or-await-passive-evidence"],
            ),
            ModelUsage(),
        )


class CompiledChecklistPlannerConsumer(DeterministicComplyPlannerConsumer):
    """Ordinary structured baseline over the same compact candidate interface.

    This consumer intentionally ignores ``decision_sufficiency`` and any
    Method-specific primary-plan certificate.  It applies one ordinary checklist:

    * consider only model-visible candidate plans;
    * a plan is ready when ``feasibility == supported`` and it has no unresolved
      conditions;
    * if exactly one ready plan exists, select that plan by ID;
    * a zero-effect ready plan means hold/stop;
    * otherwise do not invent a decision.

    The goal is to test how much of the current benchmark is already solved by
    ordinary compilation plus the shared candidate-plan interface, without an LLM.
    """

    consumer_id = "compiled-checklist-v1"
    provider = "runtime"
    model = "deterministic-compiled-checklist"

    def decide(
        self,
        request: ModelRequest,
        assembly: PromptAssembly,
    ) -> tuple[PlannerDecision, ModelUsage]:
        candidate = self._fragment(assembly, "candidate_action_context") or {}
        plans = [row for row in candidate.get("candidate_plans", []) if isinstance(row, dict)]
        ready = [
            row
            for row in plans
            if row.get("feasibility") == "supported"
            and not bool(row.get("unresolved_conditions"))
        ]
        if len(ready) == 1:
            plan = ready[0]
            plan_id = str(plan.get("plan_id") or "")
            if plan_id:
                has_effect = bool(plan.get("invocations"))
                return (
                    PlannerDecision(
                        decision_id=f"decision:{request.request_id}",
                        request_id=request.request_id,
                        stop=not has_effect,
                        selected_plan_id=plan_id,
                        invocations=[],
                        reason_codes=["compiled-checklist-unique-supported-plan"],
                    ),
                    ModelUsage(),
                )

        return (
            PlannerDecision(
                decision_id=f"decision:{request.request_id}",
                request_id=request.request_id,
                stop=True,
                invocations=[],
                reason_codes=[
                    "compiled-checklist-no-unique-supported-plan"
                    if not ready
                    else "compiled-checklist-ambiguous-supported-plans"
                ],
            ),
            ModelUsage(),
        )


class FixedOrderEagerPlannerConsumer(DeterministicComplyPlannerConsumer):
    """Eager fixed-order observation baseline.

    Whenever the center-side evidence fingerprint changes, the planner probes a
    fixed gateway capability sequence before ordinary comply.  It deliberately
    ignores EvidenceNeed relevance and therefore measures the overhead of a
    generic "always diagnose in this order" strategy without creating a query
    loop from gateway evidence revisions themselves.
    """

    consumer_id = "fixed-order-eager-v1"
    provider = "runtime"
    model = "deterministic-fixed-order-eager"

    def __init__(self) -> None:
        self._seen_center_fingerprints: set[tuple[str, tuple]] = set()

    def _center_fingerprint(self, assembly: PromptAssembly) -> tuple:
        evidence = self._fragment(assembly, "evidence_slice") or []
        observed = []
        for row in evidence:
            if not isinstance(row, dict):
                continue
            if row.get("owner_location") != "center":
                continue
            observed.append(int(row.get("observed_at_s", 0) or 0))
        # Fair fixed-cadence baseline: at most one eager probe sequence per
        # simulator hour.  Using individual evidence IDs here would turn normal
        # telemetry churn into hundreds of redundant query rounds and would be a
        # strawman rather than a useful baseline.
        latest_hour = (max(observed) // 3600) if observed else -1
        return (latest_hour,)

    def decide(self, request: ModelRequest, assembly: PromptAssembly) -> tuple[PlannerDecision, ModelUsage]:
        fingerprint = (request.task_run_id, self._center_fingerprint(assembly))
        if fingerprint not in self._seen_center_fingerprints:
            self._seen_center_fingerprints.add(fingerprint)
            specs = self._fragment(assembly, "capability_catalog") or []
            visible = {
                row.get("capability_id")
                for row in specs
                if isinstance(row, dict) and row.get("capability_id")
            }
            fixed_order = (
                "communication.gateway.primary_health",
                "communication.gateway.receipt_summary",
            )
            invocations = [
                PlannedCapabilityInvocation(
                    capability_id=cid,
                    resource="gw0",
                    canonical_arguments={"gateway_id": "gw0"},
                )
                for cid in fixed_order
                if cid in visible
            ]
            if invocations:
                return (
                    PlannerDecision(
                        decision_id=f"decision:{request.request_id}",
                        request_id=request.request_id,
                        stop=False,
                        invocations=invocations,
                        reason_codes=["fixed-order-eager-probe"],
                    ),
                    ModelUsage(),
                )
        return super().decide(request, assembly)


class DiagnosisFirstPlannerConsumer(DeterministicComplyPlannerConsumer):
    """Fixed-probe baseline: diagnose gateway state once per TaskRun, then comply.

    It intentionally ignores EvidenceNeed relevance.  This makes it a useful
    efficiency baseline against task-conditioned evidence acquisition: the same
    device policy is reached, but an unnecessary diagnosis phase may be paid.
    """

    consumer_id = "diagnosis-first-fixed-v1"
    provider = "runtime"
    model = "deterministic-diagnosis-first"

    def __init__(self) -> None:
        self._diagnosed_task_runs: set[str] = set()

    def decide(self, request: ModelRequest, assembly: PromptAssembly) -> tuple[PlannerDecision, ModelUsage]:
        if request.task_run_id not in self._diagnosed_task_runs:
            specs = self._fragment(assembly, "capability_catalog") or []
            visible = {
                row.get("capability_id")
                for row in specs
                if isinstance(row, dict) and row.get("capability_id")
            }
            fixed_order = [
                "communication.gateway.primary_health",
                "communication.gateway.receipt_summary",
            ]
            invocations = [
                PlannedCapabilityInvocation(
                    capability_id=cid,
                    resource="gw0",
                    canonical_arguments={"gateway_id": "gw0"},
                )
                for cid in fixed_order
                if cid in visible
            ]
            self._diagnosed_task_runs.add(request.task_run_id)
            if invocations:
                return (
                    PlannerDecision(
                        decision_id=f"decision:{request.request_id}",
                        request_id=request.request_id,
                        stop=False,
                        invocations=invocations,
                        reason_codes=["fixed-diagnosis-before-policy"],
                    ),
                    ModelUsage(),
                )
        return super().decide(request, assembly)


class GoldReplacementPlannerConsumer:
    """Wrap a candidate planner with executable cumulative gold replacement.

    Planner-level layers (selection/order/arguments/policy) are applied here and
    can be rerun through full R3 physics.  Upstream Task/EvidenceNeed/Percept/
    Context gold replacement is owned by frozen replay artifacts, not silently
    mixed into this wrapper.
    """

    provider = "benchmark"

    def __init__(
        self,
        base: PlannerConsumer,
        gold: PlannerConsumer,
        layers: list[GoldReplacementLayer],
        *,
        consumer_id: str | None = None,
    ) -> None:
        unsupported = set(layers) - {
            GoldReplacementLayer.CAPABILITY_SELECTION,
            GoldReplacementLayer.CAPABILITY_ORDER,
            GoldReplacementLayer.CAPABILITY_ARGUMENTS,
            GoldReplacementLayer.POLICY,
        }
        if unsupported:
            raise ValueError(
                "planner wrapper cannot replace upstream artifacts: "
                + ",".join(sorted(x.value for x in unsupported))
            )
        self.base = base
        self.gold = gold
        self.layers = list(layers)
        self.consumer_id = consumer_id or (
            f"gold-replacement:{base.consumer_id}:" + "+".join(x.value for x in layers)
        )
        self.model = f"{base.model}+gold-replacement"

    def decide(self, request: ModelRequest, assembly: PromptAssembly) -> tuple[PlannerDecision, ModelUsage]:
        candidate, usage = self.base.decide(request, assembly)
        gold_request = request.model_copy(update={"request_id": f"{request.request_id}:gold"})
        reference, _gold_usage = self.gold.decide(gold_request, assembly)
        outcome = apply_gold_replacement(
            decision_steps(candidate), decision_steps(reference), self.layers
        )
        decision = outcome_to_decision(
            outcome,
            request_id=request.request_id,
            decision_id=f"decision:{request.request_id}",
            reason_code=(
                "gold-replacement:" + "+".join(x.value for x in self.layers)
            ),
        )
        if outcome.unresolved_argument_slots:
            decision = decision.model_copy(
                update={
                    "state_patch": {
                        **dict(decision.state_patch),
                        "unresolved_argument_slots": list(outcome.unresolved_argument_slots),
                    }
                }
            )
        return decision, usage
