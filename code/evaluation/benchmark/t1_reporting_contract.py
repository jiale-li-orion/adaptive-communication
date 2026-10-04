#!/usr/bin/env python3
"""Source-aware reporting obligations for T1 Monitoring Information Continuity.

The communication benchmark begins when a report payload is available from the
upstream monitoring subsystem. This module deliberately does not use the
historical sampling-window + research-grace scorer.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


class T1ReportingContractError(ValueError):
    pass


@dataclass(frozen=True)
class ReportObligation:
    obligation_id: str
    protected_subject: str
    release_at_s: int
    deadline_s: int
    authority_owner: str
    source_ref_ids: tuple[str, ...]
    source_interval_s: int

    def __post_init__(self) -> None:
        if self.source_interval_s <= 0:
            raise T1ReportingContractError("source_interval_s must be positive")
        if self.deadline_s <= self.release_at_s:
            raise T1ReportingContractError("deadline must be after release")
        if self.deadline_s - self.release_at_s != self.source_interval_s:
            raise T1ReportingContractError(
                "reporting obligation deadline must equal one source interval; "
                "no historical research grace may be added"
            )


@dataclass(frozen=True)
class DeliveryOutcome:
    obligation_id: str
    release_at_s: int
    deadline_s: int
    delivered_at_s: int | None
    completed_on_time: bool
    late: bool
    missing: bool


def compile_periodic_reporting_obligations(
    case: Mapping[str, Any],
    *,
    cycles: int,
) -> list[ReportObligation]:
    """Compile a source-resolved DB44 T1 case into recurring report obligations.

    cycles is a coverage/horizon control chosen by the higher-level case
    generator and must receive its own provenance when frozen into a benchmark
    case. This function does not claim that the horizon itself is source-fixed.
    """

    if cycles <= 0:
        raise T1ReportingContractError("cycles must be positive")
    if case.get("family") != "T1_MONITORING_INFORMATION_CONTINUITY":
        raise T1ReportingContractError("T1 reporting compiler received non-T1 case")
    world = case.get("world", {})
    if not isinstance(world, Mapping):
        raise T1ReportingContractError("case world must be an object")
    interval = world.get("report_interval_s")
    if not isinstance(interval, int) or interval <= 0:
        raise T1ReportingContractError(
            "T1 periodic reporting requires source-resolved report_interval_s"
        )

    templates = case.get("obligations")
    if not isinstance(templates, Sequence) or not templates:
        raise T1ReportingContractError("case requires at least one obligation template")

    template = templates[0]
    if not isinstance(template, Mapping):
        raise T1ReportingContractError("obligation template must be an object")
    if template.get("completion_predicate", {}).get("kind") != "timely_complete_report":
        raise T1ReportingContractError(
            "periodic reporting compiler only accepts timely_complete_report"
        )
    timing = template.get("timing_semantics", {})
    if timing.get("max_interval_s") != interval:
        raise T1ReportingContractError(
            "case report_interval_s and obligation timing semantics disagree"
        )

    refs = tuple(map(str, template.get("source_ref_ids", [])))
    if not refs:
        raise T1ReportingContractError("report obligation requires source refs")

    out: list[ReportObligation] = []
    for i in range(cycles):
        release = i * interval
        deadline = release + interval
        out.append(
            ReportObligation(
                obligation_id=f"{case['case_id']}::report::{i:04d}",
                protected_subject=str(template["protected_subject"]),
                release_at_s=release,
                deadline_s=deadline,
                authority_owner=str(template["authority_owner"]),
                source_ref_ids=refs,
                source_interval_s=interval,
            )
        )
    return out


def evaluate_report_deliveries(
    obligations: Sequence[ReportObligation],
    delivered_at_by_obligation: Mapping[str, int | None],
) -> dict[str, Any]:
    """Evaluate raw report-delivery outcomes without scalar reward."""

    outcomes: list[DeliveryOutcome] = []
    for obligation in obligations:
        delivered_at = delivered_at_by_obligation.get(obligation.obligation_id)
        on_time = (
            isinstance(delivered_at, int)
            and obligation.release_at_s <= delivered_at <= obligation.deadline_s
        )
        late = isinstance(delivered_at, int) and delivered_at > obligation.deadline_s
        missing = delivered_at is None
        outcomes.append(
            DeliveryOutcome(
                obligation_id=obligation.obligation_id,
                release_at_s=obligation.release_at_s,
                deadline_s=obligation.deadline_s,
                delivered_at_s=delivered_at,
                completed_on_time=on_time,
                late=late,
                missing=missing,
            )
        )

    return {
        "n_obligations": len(outcomes),
        "completed_on_time": sum(x.completed_on_time for x in outcomes),
        "late": sum(x.late for x in outcomes),
        "missing": sum(x.missing for x in outcomes),
        "rows": [
            {
                "obligation_id": x.obligation_id,
                "release_at_s": x.release_at_s,
                "deadline_s": x.deadline_s,
                "delivered_at_s": x.delivered_at_s,
                "completed_on_time": x.completed_on_time,
                "late": x.late,
                "missing": x.missing,
            }
            for x in outcomes
        ],
        "note": (
            "No scalar reward and no historical grace. "
            "Completion is source-interval delivery only."
        ),
    }
