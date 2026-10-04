#!/usr/bin/env python3
"""Owner-aware evidence/context/computation accounting for Layer-1 experiments.

This module deliberately keeps three ledgers separate:
1. local context/read work;
2. remote evidence acquisition;
3. planner/search computation.

It reuses runtime contracts instead of inventing benchmark-only transport costs.
Unknown transport/cost fields remain unknown rather than being coerced to zero.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Iterable, Mapping

from agentic_communication.contracts import CommunicationEvidence
from agentic_communication.runtime_contracts import CapabilityBinding, CapabilityResult


class EvidenceCostClass(StrEnum):
    LOCAL_CONTEXT = "local_context"
    REMOTE_ACQUISITION = "remote_acquisition"


@dataclass(frozen=True)
class FreshnessRequirement:
    proposition: str
    subject_ref: str
    max_age_s: int
    basis: str = "observed_at_s"


@dataclass(frozen=True)
class FreshnessState:
    evidence_id: str
    age_s: int
    max_age_s: int
    fresh: bool
    expires_at_s: int
    basis: str


@dataclass(frozen=True)
class EvidenceCharge:
    capability_id: str
    owner_location: str
    planner_location: str
    cost_class: EvidenceCostClass
    simulated_latency_s: float | None
    network_bytes: float | None
    airtime_s: float | None
    energy_wh: float | None
    transport_cost_unknown: bool


@dataclass(frozen=True)
class PlannerComputationCharge:
    subset_solves: int = 0
    preprocessing_solves: int = 0
    memo_nodes: int = 0
    context_bytes: int = 0
    planner_calls: int = 0


@dataclass
class EvidenceLedger:
    local_reads: list[EvidenceCharge] = field(default_factory=list)
    remote_acquisitions: list[EvidenceCharge] = field(default_factory=list)
    computation: list[PlannerComputationCharge] = field(default_factory=list)

    def add_evidence_charge(self, charge: EvidenceCharge) -> None:
        if charge.cost_class == EvidenceCostClass.LOCAL_CONTEXT:
            self.local_reads.append(charge)
        else:
            self.remote_acquisitions.append(charge)

    def add_computation(self, charge: PlannerComputationCharge) -> None:
        self.computation.append(charge)

    @staticmethod
    def _sum_known(rows: Iterable[EvidenceCharge], field_name: str) -> float:
        total = 0.0
        for row in rows:
            value = getattr(row, field_name)
            if value is not None:
                total += float(value)
        return total

    def summary(self) -> dict[str, Any]:
        return {
            "local_context": {
                "read_count": len(self.local_reads),
                "simulated_latency_s_known_total": self._sum_known(self.local_reads, "simulated_latency_s"),
            },
            "remote_acquisition": {
                "request_count": len(self.remote_acquisitions),
                "simulated_latency_s_known_total": self._sum_known(self.remote_acquisitions, "simulated_latency_s"),
                "network_bytes_known_total": self._sum_known(self.remote_acquisitions, "network_bytes"),
                "airtime_s_known_total": self._sum_known(self.remote_acquisitions, "airtime_s"),
                "energy_wh_known_total": self._sum_known(self.remote_acquisitions, "energy_wh"),
                "unknown_transport_cost_count": sum(x.transport_cost_unknown for x in self.remote_acquisitions),
            },
            "planner_computation": {
                "subset_solves": sum(x.subset_solves for x in self.computation),
                "preprocessing_solves": sum(x.preprocessing_solves for x in self.computation),
                "memo_nodes": sum(x.memo_nodes for x in self.computation),
                "context_bytes": sum(x.context_bytes for x in self.computation),
                "planner_calls": sum(x.planner_calls for x in self.computation),
            },
        }


def _numeric(cost: Mapping[str, Any], key: str) -> float | None:
    value = cost.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def classify_observation(
    *,
    binding: CapabilityBinding,
    planner_location: str,
    result: CapabilityResult | None = None,
) -> EvidenceCharge:
    """Classify an observation by owner/planner placement.

    Binding.execution_class is intentionally not used as the final locality
    label because the same gateway-owned observation is remote for a center
    planner but local for a gateway-resident planner.
    """

    local = str(binding.owner_location) == str(planner_location)
    latency = None
    cost: Mapping[str, Any] = {}
    if result is not None:
        raw_latency = result.latency.get("simulated_s")
        if isinstance(raw_latency, (int, float)):
            latency = float(raw_latency)
        cost = result.cost

    unknown_transport = bool(
        not local
        and (
            cost.get("transport_cost") == "unmodeled"
            or not any(k in cost for k in ("network_bytes", "airtime_s", "energy_wh"))
        )
    )

    return EvidenceCharge(
        capability_id=binding.capability_id,
        owner_location=binding.owner_location,
        planner_location=planner_location,
        cost_class=(
            EvidenceCostClass.LOCAL_CONTEXT
            if local
            else EvidenceCostClass.REMOTE_ACQUISITION
        ),
        simulated_latency_s=latency,
        network_bytes=_numeric(cost, "network_bytes"),
        airtime_s=_numeric(cost, "airtime_s"),
        energy_wh=_numeric(cost, "energy_wh"),
        transport_cost_unknown=unknown_transport,
    )


def freshness_state(
    evidence: CommunicationEvidence,
    *,
    at_s: int,
    requirement: FreshnessRequirement,
) -> FreshnessState:
    if evidence.proposition != requirement.proposition:
        raise ValueError("freshness requirement proposition mismatch")
    if evidence.subject_ref != requirement.subject_ref:
        raise ValueError("freshness requirement subject mismatch")
    if requirement.max_age_s < 0:
        raise ValueError("max_age_s must be non-negative")

    if requirement.basis == "generated_at_s":
        basis_t = evidence.generated_at_s
        if basis_t is None:
            basis_t = evidence.observed_at_s
    elif requirement.basis == "observed_at_s":
        basis_t = evidence.observed_at_s
    else:
        raise ValueError(f"unsupported freshness basis {requirement.basis!r}")

    age = max(0, int(at_s) - int(basis_t))
    expires = int(basis_t) + int(requirement.max_age_s)
    return FreshnessState(
        evidence_id=evidence.evidence_id,
        age_s=age,
        max_age_s=int(requirement.max_age_s),
        fresh=age <= requirement.max_age_s,
        expires_at_s=expires,
        basis=requirement.basis,
    )


def next_context_expiry(
    evidence_rows: Iterable[CommunicationEvidence],
    requirements: Iterable[FreshnessRequirement],
    *,
    at_s: int,
) -> int | None:
    latest: dict[tuple[str, str], CommunicationEvidence] = {}
    for evidence in evidence_rows:
        key = (evidence.proposition, evidence.subject_ref)
        current = latest.get(key)
        if current is None or evidence.observed_at_s > current.observed_at_s:
            latest[key] = evidence

    candidates: list[int] = []
    for req in requirements:
        ev = latest.get((req.proposition, req.subject_ref))
        if ev is None:
            continue
        state = freshness_state(ev, at_s=at_s, requirement=req)
        if state.fresh:
            # Fresh through expires_at_s; the first stale integer time is +1.
            candidates.append(state.expires_at_s + 1)
    return min(candidates) if candidates else None
