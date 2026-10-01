"""DORA-style trajectory diagnostics adapted to typed communication capabilities.

Final physical outcome remains primary.  These metrics localize failures in tool
selection/order/arguments without requiring one unique trajectory to be the only
valid solution.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable

from .contracts import RuntimeTraceEvent
from .runtime_contracts import CapabilityRequest


class GoldReplacementLayer(StrEnum):
    TASK = "gold_task"
    EVIDENCE_NEED = "gold_evidence_need"
    CAPABILITY_SELECTION = "gold_capability_selection"
    CAPABILITY_ORDER = "gold_capability_order"
    CAPABILITY_ARGUMENTS = "gold_capability_arguments"
    PERCEPT = "gold_percept"
    CONTEXT = "gold_context"
    POLICY = "gold_policy"
    PHYSICAL_ORACLE = "physical_oracle"


@dataclass(frozen=True)
class CapabilityStep:
    capability_id: str
    action: str
    resource: str
    canonical_arguments: dict


def capability_steps(events: Iterable[RuntimeTraceEvent], *, include_observation: bool = True) -> list[CapabilityStep]:
    out: list[CapabilityStep] = []
    for event in events:
        if event.event_type != "capability_request":
            continue
        req = CapabilityRequest.model_validate(event.payload)
        if not include_observation and req.intended_effect.value == "observation":
            continue
        out.append(
            CapabilityStep(
                capability_id=req.capability_id,
                action=req.action,
                resource=req.resource,
                canonical_arguments=dict(req.canonical_arguments),
            )
        )
    return out


def _lcs_len(a: list[str], b: list[str]) -> int:
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0]
        for j, y in enumerate(b, 1):
            cur.append(prev[j - 1] + 1 if x == y else max(prev[j], cur[-1]))
        prev = cur
    return prev[-1]


def trajectory_metrics(predicted: list[CapabilityStep], gold: list[CapabilityStep]) -> dict:
    pids = [s.capability_id for s in predicted]
    gids = [s.capability_id for s in gold]
    pc, gc = Counter(pids), Counter(gids)
    overlap = sum(min(pc[k], gc[k]) for k in set(pc) | set(gc))
    any_order_precision = overlap / len(pids) if pids else (1.0 if not gids else 0.0)
    any_order_recall = overlap / len(gids) if gids else (1.0 if not pids else 0.0)
    lcs = _lcs_len(pids, gids)
    # Empty-vs-empty is a correct no-tool trajectory, not zero ordering quality.
    # Stopping correctness is reported separately, but order diagnostics must not
    # penalize a planner for correctly choosing no capability invocation.
    order_score = (
        1.0
        if not pids and not gids
        else lcs / max(len(pids), len(gids), 1)
    )
    exact = pids == gids

    # Argument grounding is measured only for aligned capability occurrences in
    # sequence order.  Separate selection/order metrics prevent wrong-tool calls
    # from being hidden inside parameter accuracy.
    matched_args = 0
    matched_steps = 0
    for p, g in zip(predicted, gold):
        if p.capability_id != g.capability_id:
            continue
        matched_steps += 1
        matched_args += int(
            p.resource == g.resource and p.canonical_arguments == g.canonical_arguments
        )
    arg_acc = matched_args / matched_steps if matched_steps else None
    return {
        "predicted_steps": len(predicted),
        "gold_steps": len(gold),
        "tool_any_order_precision": any_order_precision,
        "tool_any_order_recall": any_order_recall,
        "tool_in_order_lcs": lcs,
        "tool_in_order_normalized": order_score,
        "tool_exact_match": exact,
        "argument_grounding_accuracy": arg_acc,
        "aligned_capability_steps": matched_steps,
    }


def gold_replacement_registry() -> list[dict]:
    return [
        {
            "layer": layer.value,
            "replaces": {
                GoldReplacementLayer.TASK: "Operational Task -> Runtime TaskContract interpretation",
                GoldReplacementLayer.EVIDENCE_NEED: "EvidenceNeed set / stop decision",
                GoldReplacementLayer.CAPABILITY_SELECTION: "capability identity set",
                GoldReplacementLayer.CAPABILITY_ORDER: "capability invocation order",
                GoldReplacementLayer.CAPABILITY_ARGUMENTS: "resource/arguments for selected capabilities",
                GoldReplacementLayer.PERCEPT: "CapabilityResult -> Percept interpretation",
                GoldReplacementLayer.CONTEXT: "ContextManifest / materialization",
                GoldReplacementLayer.POLICY: "communication-device policy decision",
                GoldReplacementLayer.PHYSICAL_ORACLE: "full physical action trajectory under evaluator truth",
            }[layer],
        }
        for layer in GoldReplacementLayer
    ]
