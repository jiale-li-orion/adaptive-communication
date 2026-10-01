"""Cumulative R1 attribution across upstream runtime and planner-owned layers.

Layers 1--4 replace model-input artifacts and therefore rerun the candidate
planner.  Layers 5--7 replace planner outputs post-hoc on the latest rerun
decision.  Gold Policy / Physical Oracle are R3 concepts and intentionally stay
outside this frozen-input evaluator.
"""
from __future__ import annotations

from dataclasses import dataclass

from .gold_replacement import apply_gold_replacement, decision_steps
from .planner import PlannerConsumer, invoke_consumer
from .runtime_contracts import PlannerDecision, PromptAssembly
from .trajectory_eval import GoldReplacementLayer, trajectory_metrics
from .upstream_gold import apply_upstream_gold_replacement


UPSTREAM_ORDER = (
    GoldReplacementLayer.TASK,
    GoldReplacementLayer.EVIDENCE_NEED,
    GoldReplacementLayer.PERCEPT,
    GoldReplacementLayer.CONTEXT,
)

PLANNER_ORDER = (
    GoldReplacementLayer.CAPABILITY_SELECTION,
    GoldReplacementLayer.CAPABILITY_ORDER,
    GoldReplacementLayer.CAPABILITY_ARGUMENTS,
)


@dataclass(frozen=True)
class AttributionMatrixRow:
    cumulative_layers: tuple[str, ...]
    assembly_hash: str
    assembly_matches_gold: bool
    candidate_status: str
    stop_correct: bool | None
    unresolved_argument_slots: tuple[int, ...]
    trajectory: dict


def _row(
    *,
    layers: list[GoldReplacementLayer],
    assembly: PromptAssembly,
    gold_assembly: PromptAssembly,
    candidate_status: str,
    decision: PlannerDecision | None,
    gold_decision: PlannerDecision | None,
    unresolved_argument_slots: tuple[int, ...] = (),
) -> AttributionMatrixRow:
    if decision is None or gold_decision is None:
        stop_correct = None
        trajectory = {
            "predicted_steps": None,
            "gold_steps": None,
            "tool_any_order_precision": None,
            "tool_any_order_recall": None,
            "tool_in_order_lcs": None,
            "tool_in_order_normalized": None,
            "tool_exact_match": None,
            "argument_grounding_accuracy": None,
            "aligned_capability_steps": None,
        }
    else:
        stop_correct = decision.stop == gold_decision.stop
        trajectory = trajectory_metrics(
            decision_steps(decision), decision_steps(gold_decision)
        )
    return AttributionMatrixRow(
        cumulative_layers=tuple(x.value for x in layers),
        assembly_hash=assembly.assembly_hash,
        assembly_matches_gold=assembly.assembly_hash == gold_assembly.assembly_hash,
        candidate_status=candidate_status,
        stop_correct=stop_correct,
        unresolved_argument_slots=tuple(unresolved_argument_slots),
        trajectory=trajectory,
    )


def evaluate_cumulative_r1_attribution(
    *,
    candidate_assembly: PromptAssembly,
    gold_assembly: PromptAssembly,
    candidate_consumer: PlannerConsumer,
    gold_consumer: PlannerConsumer,
    request_prefix: str = "attribution",
) -> list[AttributionMatrixRow]:
    """Evaluate base + cumulative layers 1--7 on a single frozen turn."""
    gold_inv = invoke_consumer(
        assembly=gold_assembly,
        consumer=gold_consumer,
        request_id=f"{request_prefix}:gold",
    )
    gold_decision = gold_inv.decision

    rows: list[AttributionMatrixRow] = []
    active_assembly = candidate_assembly
    active_inv = invoke_consumer(
        assembly=active_assembly,
        consumer=candidate_consumer,
        request_id=f"{request_prefix}:base",
    )
    active_decision = active_inv.decision
    rows.append(
        _row(
            layers=[],
            assembly=active_assembly,
            gold_assembly=gold_assembly,
            candidate_status=active_inv.attempt.status.value,
            decision=active_decision,
            gold_decision=gold_decision,
        )
    )

    cumulative_upstream: list[GoldReplacementLayer] = []
    for idx, layer in enumerate(UPSTREAM_ORDER, 1):
        cumulative_upstream.append(layer)
        active_assembly = apply_upstream_gold_replacement(
            candidate_assembly,
            gold_assembly,
            cumulative_upstream,
        ).assembly
        active_inv = invoke_consumer(
            assembly=active_assembly,
            consumer=candidate_consumer,
            request_id=f"{request_prefix}:upstream:{idx}",
        )
        active_decision = active_inv.decision
        rows.append(
            _row(
                layers=list(cumulative_upstream),
                assembly=active_assembly,
                gold_assembly=gold_assembly,
                candidate_status=active_inv.attempt.status.value,
                decision=active_decision,
                gold_decision=gold_decision,
            )
        )

    # Planner layers operate on the decision produced after *all* upstream
    # replacements. They do not rerun the model and therefore cannot alter the
    # assembly hash.
    planner_layers: list[GoldReplacementLayer] = []
    if active_decision is not None and gold_decision is not None:
        candidate_steps = decision_steps(active_decision)
        gold_steps = decision_steps(gold_decision)
        for layer in PLANNER_ORDER:
            planner_layers.append(layer)
            outcome = apply_gold_replacement(
                candidate_steps,
                gold_steps,
                planner_layers,
            )
            replaced = PlannerDecision(
                decision_id=active_decision.decision_id,
                request_id=active_decision.request_id,
                stop=(not outcome.steps),
                invocations=[
                    {
                        "capability_id": step.capability_id,
                        "resource": step.resource,
                        "canonical_arguments": step.canonical_arguments,
                    }
                    for step in outcome.steps
                ],
                state_patch=dict(active_decision.state_patch),
                reason_codes=[
                    *active_decision.reason_codes,
                    "posthoc:" + "+".join(x.value for x in planner_layers),
                ],
            )
            rows.append(
                _row(
                    layers=[*UPSTREAM_ORDER, *planner_layers],
                    assembly=active_assembly,
                    gold_assembly=gold_assembly,
                    candidate_status=active_inv.attempt.status.value,
                    decision=replaced,
                    gold_decision=gold_decision,
                    unresolved_argument_slots=outcome.unresolved_argument_slots,
                )
            )
    return rows
