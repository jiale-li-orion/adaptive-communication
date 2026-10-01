"""Executable layer-wise gold replacement for Agent failure attribution.

This module keeps capability identity/order/arguments separate.  In particular,
gold tool selection does **not** silently inject gold arguments: a gold-selected
tool for which the candidate produced no matching call remains an unresolved
argument slot until the GOLD_CAPABILITY_ARGUMENTS layer is applied.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .runtime_contracts import PlannedCapabilityInvocation, PlannerDecision
from .trajectory_eval import CapabilityStep, GoldReplacementLayer


@dataclass(frozen=True)
class ReplacementOutcome:
    steps: tuple[CapabilityStep, ...]
    unresolved_argument_slots: tuple[int, ...] = ()
    notes: tuple[str, ...] = ()

    @property
    def executable(self) -> bool:
        return not self.unresolved_argument_slots


def decision_steps(decision: PlannerDecision) -> list[CapabilityStep]:
    return [
        CapabilityStep(
            capability_id=x.capability_id,
            action=x.capability_id,
            resource=x.resource,
            canonical_arguments=dict(x.canonical_arguments),
        )
        for x in decision.invocations
    ]


def _match_occurrences(source: list[CapabilityStep], ids: list[str]) -> tuple[list[CapabilityStep], list[int]]:
    used: set[int] = set()
    out: list[CapabilityStep] = []
    missing: list[int] = []
    for slot, capability_id in enumerate(ids):
        idx = next(
            (i for i, row in enumerate(source) if i not in used and row.capability_id == capability_id),
            None,
        )
        if idx is None:
            out.append(
                CapabilityStep(
                    capability_id=capability_id,
                    action=capability_id,
                    resource="",
                    canonical_arguments={},
                )
            )
            missing.append(slot)
        else:
            used.add(idx)
            out.append(source[idx])
    return out, missing


def apply_gold_replacement(
    candidate: Iterable[CapabilityStep],
    gold: Iterable[CapabilityStep],
    layers: Iterable[GoldReplacementLayer],
) -> ReplacementOutcome:
    """Apply cumulative planner-level gold layers.

    Supported executable layers:
      * CAPABILITY_SELECTION: gold multiset, candidate args where candidate selected the same tool;
      * CAPABILITY_ORDER: gold order for selected identities, candidate args preserved;
      * CAPABILITY_ARGUMENTS: gold resource/arguments for identity-aligned slots;
      * POLICY: entire gold capability trajectory.

    TASK/EVIDENCE_NEED/PERCEPT/CONTEXT are upstream runtime-artifact replacements
    and are handled by replay/frozen-artifact APIs rather than this step transformer.
    """
    cand = list(candidate)
    ref = list(gold)
    selected = set(layers)
    notes: list[str] = []
    unresolved: list[int] = []

    if GoldReplacementLayer.POLICY in selected:
        return ReplacementOutcome(tuple(ref), (), ("gold policy replaces full capability trajectory",))

    cur = list(cand)
    if GoldReplacementLayer.CAPABILITY_SELECTION in selected:
        cur, unresolved = _match_occurrences(cur, [x.capability_id for x in ref])
        if unresolved:
            notes.append("gold selection exposed missing downstream argument slots")

    if GoldReplacementLayer.CAPABILITY_ORDER in selected:
        # Reorder only identities that exist in the current trajectory. Missing
        # gold identities stay explicit only when selection replacement was used.
        wanted = [x.capability_id for x in ref]
        ordered, missing_order = _match_occurrences(cur, wanted)
        if GoldReplacementLayer.CAPABILITY_SELECTION not in selected:
            ordered = [x for i, x in enumerate(ordered) if i not in set(missing_order)]
            extras = list(cur)
            for x in ordered:
                try:
                    extras.remove(x)
                except ValueError:
                    pass
            ordered.extend(extras)
        else:
            unresolved = sorted(set(unresolved) | set(missing_order))
        cur = ordered

    if GoldReplacementLayer.CAPABILITY_ARGUMENTS in selected:
        # Arguments are replaced only for capability-aligned occurrences.  This
        # is intentionally after selection/order and resolves missing slots that
        # were created by gold selection.
        ref_by_id: dict[str, list[CapabilityStep]] = {}
        for row in ref:
            ref_by_id.setdefault(row.capability_id, []).append(row)
        seen: dict[str, int] = {}
        replaced: list[CapabilityStep] = []
        unresolved_now: list[int] = []
        for idx, row in enumerate(cur):
            occurrence = seen.get(row.capability_id, 0)
            seen[row.capability_id] = occurrence + 1
            candidates = ref_by_id.get(row.capability_id, [])
            if occurrence >= len(candidates):
                replaced.append(row)
                unresolved_now.append(idx)
                continue
            g = candidates[occurrence]
            replaced.append(
                CapabilityStep(
                    capability_id=row.capability_id,
                    action=g.action,
                    resource=g.resource,
                    canonical_arguments=dict(g.canonical_arguments),
                )
            )
        cur = replaced
        unresolved = unresolved_now

    return ReplacementOutcome(tuple(cur), tuple(sorted(set(unresolved))), tuple(notes))


def outcome_to_decision(
    outcome: ReplacementOutcome,
    *,
    request_id: str,
    decision_id: str,
    reason_code: str = "gold-replacement",
) -> PlannerDecision:
    return PlannerDecision(
        decision_id=decision_id,
        request_id=request_id,
        stop=not outcome.steps,
        invocations=[
            PlannedCapabilityInvocation(
                capability_id=x.capability_id,
                resource=x.resource,
                canonical_arguments=dict(x.canonical_arguments),
            )
            for x in outcome.steps
        ],
        reason_codes=[reason_code, *outcome.notes],
    )
