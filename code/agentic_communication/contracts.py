"""Operational Task, communication evidence and experiment/trace contracts."""
from __future__ import annotations

from enum import StrEnum
from hashlib import sha256
import json

from pydantic import BaseModel, Field, JsonValue, model_validator


class OperationalTaskFamily(StrEnum):
    MONITORING_CONTINUITY = "monitoring_continuity"
    RISK_ESCALATION = "risk_escalation"
    BACKHAUL_OUTAGE_SUSTAINMENT = "backhaul_outage_sustainment"
    ENERGY_CONSTRAINED_MONITORING = "energy_constrained_monitoring"
    RECOVERY_RECONCILIATION = "recovery_reconciliation"
    COMPOUND_LONG_HORIZON = "compound_long_horizon"


class OperationalTaskPhase(BaseModel):
    start_s: int = Field(ge=0)
    required_period_s: int = Field(ge=60)
    level: str

    @model_validator(mode="after")
    def validate_level(self) -> "OperationalTaskPhase":
        if not self.level.strip():
            raise ValueError("OperationalTaskPhase level cannot be empty")
        return self


class OperationalTask(BaseModel):
    task_id: str
    task_revision: int = Field(default=1, ge=1)
    family: OperationalTaskFamily
    principal: str = "external-emergency-monitoring-authority"
    target_node_ids: list[str] = Field(default_factory=list)
    measurands: list[str] = Field(default_factory=lambda: ["displacement"])
    phases: list[OperationalTaskPhase]
    task_horizon_s: int = Field(gt=0)
    authorized_effects: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    scoring_profile_ref: str = "communication-physical-v1"
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_task(self) -> "OperationalTask":
        if not self.task_id.strip() or not self.principal.strip():
            raise ValueError("OperationalTask requires non-empty task_id/principal")
        if not self.phases:
            raise ValueError("OperationalTask requires at least one phase")
        starts = [p.start_s for p in self.phases]
        if starts != sorted(starts) or len(starts) != len(set(starts)):
            raise ValueError("OperationalTask phases must have unique ascending start_s")
        if starts[0] != 0:
            raise ValueError("OperationalTask first phase must start at t=0")
        if starts[-1] >= self.task_horizon_s:
            raise ValueError("OperationalTask phase starts must lie inside task horizon")
        return self

    def phase_index(self, t_s: int) -> int:
        idx = 0
        for i, phase in enumerate(self.phases):
            if t_s >= phase.start_s:
                idx = i
            else:
                break
        return idx

    def phase_at(self, t_s: int) -> OperationalTaskPhase:
        return self.phases[self.phase_index(t_s)]

    def mission_schedule(self) -> list[tuple[int, int, str]]:
        return [(p.start_s, p.required_period_s, p.level) for p in self.phases]


class EvidenceStatus(StrEnum):
    CURRENT = "current"
    STALE = "stale"
    NONE_RECENT = "none_recent"
    UNREACHABLE = "unreachable"
    TIMEOUT = "timeout"
    NEGATIVE_OBSERVATION = "negative_observation"


class CommunicationEvidence(BaseModel):
    evidence_id: str
    proposition: str
    subject_ref: str
    value: JsonValue
    source_id: str
    source_role: str
    owner_location: str
    generated_at_s: int | None = None
    observed_at_s: int
    world_revision: int = Field(ge=1)
    status: EvidenceStatus
    freshness: dict[str, JsonValue] = Field(default_factory=dict)
    provenance: dict[str, JsonValue] = Field(default_factory=dict)


class EvidenceWorldSnapshot(BaseModel):
    revision: int = Field(ge=1)
    observed_at_s: int
    evidence: list[CommunicationEvidence] = Field(default_factory=list)
    digest: str

    @classmethod
    def build(
        cls,
        *,
        revision: int,
        observed_at_s: int,
        evidence: list[CommunicationEvidence],
    ) -> "EvidenceWorldSnapshot":
        payload = [
            e.model_dump(mode="json", exclude={"world_revision"})
            for e in sorted(evidence, key=lambda x: x.evidence_id)
        ]
        digest = sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        return cls(
            revision=revision,
            observed_at_s=observed_at_s,
            evidence=evidence,
            digest=digest,
        )

    def by_id(self) -> dict[str, CommunicationEvidence]:
        return {e.evidence_id: e for e in self.evidence}


class RuntimeTraceEvent(BaseModel):
    seq: int = Field(ge=1)
    t_s: int = Field(ge=0)
    event_type: str
    task_run_id: str | None = None
    payload: dict[str, JsonValue] = Field(default_factory=dict)


class ExperimentSpec(BaseModel):
    experiment_id: str
    design_revision: str = "experiment-design-v1"
    scenario_ref: str = "spec/instance-v1-manifest.md"
    operational_task: OperationalTask
    arm: str
    seeds: list[int]
    context_mode: str = "task_conditioned"
    capability_registry_ref: str = "research/COMMUNICATION-DOMAIN-REGISTRY.v0.1.json"
    scorer_ref: str = "code/instance/scoring.py::evaluate"
    fullsim_ref: str = "code/v3joint/joint_run.py::run_joint"
    source_refs: list[str] = Field(default_factory=list)
    simulator_kwargs: dict[str, JsonValue] = Field(default_factory=dict)
