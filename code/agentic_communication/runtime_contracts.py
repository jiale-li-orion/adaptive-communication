"""Self-contained generic Agent runtime contracts for Agentic Communication.

This module is part of the public method implementation.  It intentionally has
no cross-repository dependency: Operational Task, Evidence World, Context,
Capability and runtime-trace semantics are implemented inside this repository.
"""
from __future__ import annotations

import json
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, Field, JsonValue, model_validator


class TaskKind(StrEnum):
    DIRECT = "direct"
    RETRIEVE = "retrieve"
    VERIFY = "verify"
    RESOLVE_CONFLICT = "resolve_conflict"
    INVESTIGATE = "investigate"
    WATCH = "watch"
    OBSERVE_LIVE_STATE = "observe_live_state"
    CONTROL = "control"


class EffectCeiling(StrEnum):
    READ_ONLY = "read_only"
    INTERNAL_STATE = "internal_state"
    EXTERNAL_SIDE_EFFECT = "external_side_effect"


_EFFECT_RANK = {
    EffectCeiling.READ_ONLY: 0,
    EffectCeiling.INTERNAL_STATE: 1,
    EffectCeiling.EXTERNAL_SIDE_EFFECT: 2,
}


def effect_within_ceiling(effect: EffectCeiling, ceiling: EffectCeiling) -> bool:
    return _EFFECT_RANK[effect] <= _EFFECT_RANK[ceiling]


class TaskContract(BaseModel):
    task_contract_id: str
    contract_revision: int = Field(ge=1)
    principal: str
    task_kind: TaskKind
    target_resources: list[str] = Field(default_factory=list)
    desired_state: dict[str, JsonValue]
    evidence_contract: dict[str, JsonValue] = Field(default_factory=dict)
    output_contract: dict[str, JsonValue] = Field(default_factory=dict)
    temporal_contract: dict[str, JsonValue] = Field(default_factory=dict)
    effect_ceiling: EffectCeiling
    completion_predicate: dict[str, JsonValue]
    policy_revision: str

    @model_validator(mode="after")
    def validate_contract(self) -> "TaskContract":
        if not self.task_contract_id.strip() or not self.principal.strip():
            raise ValueError("TaskContract requires non-empty identity/principal")
        if not self.desired_state or not self.completion_predicate:
            raise ValueError("TaskContract requires desired_state/completion_predicate")
        return self


class TaskRunStatus(StrEnum):
    SUBMITTED = "submitted"
    RUNNING = "running"
    WAITING_INPUT = "waiting_input"
    WAITING_DEPENDENCY = "waiting_dependency"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


class TaskRun(BaseModel):
    run_id: str
    task_contract_id: str
    operational_task_id: str
    context_manifest_ref: str
    status: TaskRunStatus = TaskRunStatus.SUBMITTED
    base_context_revision: int = Field(ge=1)
    result_ref: str | None = None
    stop_reason: str | None = None


class ProposedState(StrEnum):
    CONFIRMED = "confirmed"
    TENTATIVE = "tentative"
    CONFLICT = "conflict"
    UNKNOWN = "unknown"
    HYPOTHESIS = "hypothesis"


class EvidenceNeedStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    BLOCKED = "blocked"
    ABANDONED = "abandoned"


class EvidenceNeedContract(BaseModel):
    require_evidence: bool = True
    required_source_roles: list[str] = Field(default_factory=list)
    min_independent_sources: int = Field(default=1, ge=1)
    accepted_states: list[ProposedState] = Field(
        default_factory=lambda: [ProposedState.CONFIRMED, ProposedState.UNKNOWN]
    )


class EvidenceNeed(BaseModel):
    need_id: str
    task_run_id: str
    proposition_or_question: str
    purpose: str
    target_objects: list[str] = Field(default_factory=list)
    evidence_contract: EvidenceNeedContract = Field(default_factory=EvidenceNeedContract)
    preferred_source_roles: list[str] = Field(default_factory=list)
    freshness_requirement: dict[str, JsonValue] = Field(default_factory=dict)
    completion_predicate: dict[str, JsonValue] = Field(default_factory=dict)
    blocking_plan_ids: list[str] = Field(default_factory=list)
    priority: int = Field(default=50, ge=0, le=100)
    status: EvidenceNeedStatus = EvidenceNeedStatus.OPEN
    resolution_evidence_refs: list[str] = Field(default_factory=list)
    opened_revision: int = Field(ge=0)
    updated_revision: int = Field(ge=0)
    opened_at: datetime
    updated_at: datetime


class InvestigationStateItem(BaseModel):
    proposition: str
    target_ref: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    writer: str
    reason_code: str
    updated_revision: int = Field(ge=1)


class InvestigationState(BaseModel):
    task_run_id: str
    state_revision: int = Field(ge=0)
    goal: str
    targets: list[str] = Field(default_factory=list)
    confirmed: list[InvestigationStateItem] = Field(default_factory=list)
    tentative: list[InvestigationStateItem] = Field(default_factory=list)
    conflicts: list[InvestigationStateItem] = Field(default_factory=list)
    unknowns: list[InvestigationStateItem] = Field(default_factory=list)
    hypotheses: list[InvestigationStateItem] = Field(default_factory=list)
    evidence_need_ids: list[str] = Field(default_factory=list)
    current_decision: dict[str, JsonValue] | None = None
    last_world_revision: int | None = Field(default=None, ge=0)
    last_perception_at: datetime | None = None
    updated_at: datetime


class EffectSemantics(StrEnum):
    OBSERVATION = "observation"
    INTERNAL_STATE = "internal_state"
    EXTERNAL_SIDE_EFFECT = "external_side_effect"


_EFFECT_TO_CEILING = {
    EffectSemantics.OBSERVATION: EffectCeiling.READ_ONLY,
    EffectSemantics.INTERNAL_STATE: EffectCeiling.INTERNAL_STATE,
    EffectSemantics.EXTERNAL_SIDE_EFFECT: EffectCeiling.EXTERNAL_SIDE_EFFECT,
}


class ExecutionClass(StrEnum):
    LOCAL_READ = "local_read"
    LOCAL_ACTION = "local_action"
    INTERMITTENT_REMOTE_READ = "intermittent_remote_read"
    INTERMITTENT_REMOTE_ACTION = "intermittent_remote_action"


class CapabilityContract(BaseModel):
    capability_id: str
    contract_revision: int = Field(ge=1)
    action: str
    applicable_resource_types: list[str]
    canonical_input_schema: dict[str, JsonValue] = Field(default_factory=dict)
    canonical_output_schema: dict[str, JsonValue] = Field(default_factory=dict)
    observation_semantics: str
    effect_semantics: EffectSemantics
    authority_semantics: list[str] = Field(default_factory=list)
    preconditions: list[str] = Field(default_factory=list)
    postconditions: list[str] = Field(default_factory=list)
    idempotency: str
    reversibility: str
    failure_semantics: list[str] = Field(default_factory=list)
    risk_class: str

    @property
    def required_effect_ceiling(self) -> EffectCeiling:
        return _EFFECT_TO_CEILING[self.effect_semantics]


class CapabilityBinding(BaseModel):
    binding_id: str
    binding_revision: int = Field(ge=1)
    capability_id: str
    contract_revision: int = Field(ge=1)
    implementation_ref: str
    execution_class: ExecutionClass
    owner_location: str
    required_path: list[str] = Field(default_factory=list)
    return_path: list[str] = Field(default_factory=list)
    freshness_semantics: dict[str, JsonValue] = Field(default_factory=dict)
    latency_model: dict[str, JsonValue] = Field(default_factory=dict)
    cost_model: dict[str, JsonValue] = Field(default_factory=dict)
    opportunity_dependency: list[str] = Field(default_factory=list)
    fallback_rank: int = Field(default=100, ge=0)


class CapabilityRequest(BaseModel):
    request_id: str
    task_contract_id: str
    task_run_id: str
    principal: str
    capability_id: str
    contract_revision: int = Field(ge=1)
    action: str
    resource: str
    resource_type: str
    canonical_arguments: dict[str, JsonValue] = Field(default_factory=dict)
    intended_effect: EffectSemantics
    evidence_purpose: str | None = None
    execution_context: dict[str, JsonValue] = Field(default_factory=dict)


class CapabilityResultStatus(StrEnum):
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"
    BLOCKED = "blocked"
    TIMED_OUT = "timed_out"


class CapabilityResult(BaseModel):
    request_id: str
    status: CapabilityResultStatus
    canonical_output: dict[str, JsonValue] = Field(default_factory=dict)
    effect_receipt: dict[str, JsonValue] = Field(default_factory=dict)
    observation_class: str
    provenance: dict[str, JsonValue] = Field(default_factory=dict)
    latency: dict[str, JsonValue] = Field(default_factory=dict)
    cost: dict[str, JsonValue] = Field(default_factory=dict)
    failure_code: str | None = None
    failure_detail: str | None = None


def capability_visible_for_task(task: TaskContract, capability: CapabilityContract) -> bool:
    return effect_within_ceiling(capability.required_effect_ceiling, task.effect_ceiling)


class ObservedProposition(BaseModel):
    statement: str
    support_refs: list[str] = Field(default_factory=list)
    refute_refs: list[str] = Field(default_factory=list)
    source_groups: list[str] = Field(default_factory=list)
    freshness: dict[str, JsonValue] = Field(default_factory=dict)


class Percept(BaseModel):
    percept_id: str
    request_id: str
    target_refs: list[str] = Field(default_factory=list)
    observed_propositions: list[ObservedProposition] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    source_roles: list[str] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)
    cost: dict[str, JsonValue] = Field(default_factory=dict)


class ContextManifest(BaseModel):
    context_id: str
    context_revision: int = Field(ge=1)
    parent_context_id: str | None = None
    task_contract_ref: str
    investigation_state_ref: str
    evidence_refs: list[str] = Field(default_factory=list)
    capability_refs: list[str] = Field(default_factory=list)
    policy_context_ref: str
    budget_ref: str
    world_revision: int = Field(ge=1)


class FragmentCacheClass(StrEnum):
    STATIC = "static"
    TASK_STABLE = "task_stable"
    STATE_DYNAMIC = "state_dynamic"
    EPHEMERAL = "ephemeral"


class FragmentTrustClass(StrEnum):
    PLATFORM_INVARIANT = "platform_invariant"
    RUNTIME_CONTROL = "runtime_control"
    DURABLE_STATE = "durable_state"
    EVIDENCE_REFERENCE = "evidence_reference"
    UNTRUSTED_EXTERNAL = "untrusted_external"


def _content_hash(value: JsonValue) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


class MaterializedFragment(BaseModel):
    fragment_id: str
    kind: str
    source_ref: str
    source_revision: str
    selection_reason: str | None = None
    trust_class: FragmentTrustClass
    cache_class: FragmentCacheClass
    content_hash: str
    content: JsonValue

    @classmethod
    def build(
        cls,
        *,
        kind: str,
        source_ref: str,
        source_revision: str,
        trust_class: FragmentTrustClass,
        cache_class: FragmentCacheClass,
        content: JsonValue,
        selection_reason: str | None = None,
    ) -> "MaterializedFragment":
        digest = _content_hash(content)
        identity = _content_hash(
            {
                "kind": kind,
                "source_ref": source_ref,
                "source_revision": source_revision,
                "selection_reason": selection_reason,
                "trust_class": trust_class.value,
                "cache_class": cache_class.value,
                "content_hash": digest,
            }
        )
        return cls(
            fragment_id=str(uuid5(NAMESPACE_URL, f"agentic-communication:{identity}")),
            kind=kind,
            source_ref=source_ref,
            source_revision=source_revision,
            selection_reason=selection_reason,
            trust_class=trust_class,
            cache_class=cache_class,
            content_hash=digest,
            content=content,
        )


class PromptAssembly(BaseModel):
    assembly_id: str
    task_contract_id: str
    task_run_id: str
    context_manifest_revision: int = Field(ge=1)
    fragments: list[MaterializedFragment]
    percept_refs: list[str] = Field(default_factory=list)
    assembly_hash: str

    @classmethod
    def build(
        cls,
        *,
        task_contract_id: str,
        task_run_id: str,
        context_manifest_revision: int,
        fragments: list[MaterializedFragment],
        percept_refs: list[str] | None = None,
    ) -> "PromptAssembly":
        digest = _content_hash([f.model_dump(mode="json") for f in fragments])
        return cls(
            assembly_id=str(uuid5(NAMESPACE_URL, f"agentic-communication:assembly:{digest}")),
            task_contract_id=task_contract_id,
            task_run_id=task_run_id,
            context_manifest_revision=context_manifest_revision,
            fragments=fragments,
            percept_refs=list(percept_refs or []),
            assembly_hash=digest,
        )


class ModelRequest(BaseModel):
    request_id: str
    task_run_id: str
    assembly_id: str
    assembly_hash: str
    consumer_id: str
    response_schema: str = "PlannerDecision"
    request_metadata: dict[str, JsonValue] = Field(default_factory=dict)


class ModelAttemptStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    INVALID_OUTPUT = "invalid_output"


class ModelUsage(BaseModel):
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    input_bytes: int = Field(default=0, ge=0)
    output_bytes: int = Field(default=0, ge=0)
    latency_ms: float | None = Field(default=None, ge=0.0)


class ModelAttempt(BaseModel):
    attempt_id: str
    request_id: str
    provider: str
    model: str
    status: ModelAttemptStatus
    usage: ModelUsage = Field(default_factory=ModelUsage)
    output_hash: str | None = None
    error_code: str | None = None
    error_detail: str | None = None


class PlannedCapabilityInvocation(BaseModel):
    capability_id: str
    resource: str
    canonical_arguments: dict[str, JsonValue] = Field(default_factory=dict)


class PlannerDecisionProposal(BaseModel):
    """Model-facing decision schema before runtime-owned IDs are attached."""

    stop: bool = False
    selected_plan_id: str | None = Field(
        default=None,
        description=(
            "Optional Runtime-generated candidate plan to execute. When supplied, Runtime expands "
            "that supported candidate's declared invocations; the model need not copy them."
        ),
    )
    invocations: list[PlannedCapabilityInvocation] = Field(default_factory=list)
    state_patch: dict[str, JsonValue] = Field(default_factory=dict)
    reason_codes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_proposal(self) -> "PlannerDecisionProposal":
        if self.stop and self.invocations:
            raise ValueError("PlannerDecisionProposal cannot stop and invoke capabilities simultaneously")
        return self


class PlannerDecision(BaseModel):
    decision_id: str
    request_id: str
    stop: bool = False
    selected_plan_id: str | None = None
    invocations: list[PlannedCapabilityInvocation] = Field(default_factory=list)
    state_patch: dict[str, JsonValue] = Field(default_factory=dict)
    reason_codes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_decision(self) -> "PlannerDecision":
        if self.stop and self.invocations:
            raise ValueError("PlannerDecision cannot stop and invoke capabilities simultaneously")
        return self
