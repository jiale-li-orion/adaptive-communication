"""Frozen-input Agent diagnostics for planner/model consumers.

R1 answers a narrow question: given the *same* PromptAssembly, where does a
candidate planner differ from a gold/reference planner?  Physics is not rerun,
so capability selection/order/arguments and stopping are not confounded by the
candidate having already changed the world.
"""
from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean
from typing import Iterable

from .contracts import RuntimeTraceEvent
from .gold_replacement import decision_steps
from .planner import PlannerConsumer, invoke_consumer
from .replay import frozen_r1_inputs
from .trajectory_eval import trajectory_metrics


@dataclass(frozen=True)
class R1TurnEvaluation:
    seq: int
    t_s: int
    task_run_id: str
    assembly_hash: str
    candidate_status: str
    gold_status: str
    stop_correct: bool | None
    metrics: dict
    candidate_usage: dict
    candidate_decision: dict | None
    gold_decision: dict | None


def evaluate_r1_consumers(
    events: Iterable[RuntimeTraceEvent],
    *,
    candidate: PlannerConsumer,
    gold: PlannerConsumer,
    limit: int | None = None,
) -> tuple[list[R1TurnEvaluation], dict]:
    turns: list[R1TurnEvaluation] = []
    records = frozen_r1_inputs(events)
    if limit is not None:
        records = records[: max(0, int(limit))]
    for idx, record in enumerate(records, 1):
        c = invoke_consumer(
            assembly=record.assembly,
            consumer=candidate,
            request_id=f"eval:candidate:{record.task_run_id}:{record.seq}:{idx}",
        )
        g = invoke_consumer(
            assembly=record.assembly,
            consumer=gold,
            request_id=f"eval:gold:{record.task_run_id}:{record.seq}:{idx}",
        )
        if c.decision is None or g.decision is None:
            metrics = {
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
            stop_correct = None
        else:
            metrics = trajectory_metrics(
                decision_steps(c.decision), decision_steps(g.decision)
            )
            stop_correct = c.decision.stop == g.decision.stop
        turns.append(
            R1TurnEvaluation(
                seq=record.seq,
                t_s=record.t_s,
                task_run_id=record.task_run_id,
                assembly_hash=record.assembly.assembly_hash,
                candidate_status=c.attempt.status.value,
                gold_status=g.attempt.status.value,
                stop_correct=stop_correct,
                metrics=metrics,
                candidate_usage=c.attempt.usage.model_dump(mode="json"),
                candidate_decision=(
                    c.decision.model_dump(mode="json") if c.decision is not None else None
                ),
                gold_decision=(
                    g.decision.model_dump(mode="json") if g.decision is not None else None
                ),
            )
        )

    def mean_metric(key: str):
        vals = [
            float(turn.metrics[key])
            for turn in turns
            if isinstance(turn.metrics.get(key), (int, float))
            and not isinstance(turn.metrics.get(key), bool)
        ]
        return fmean(vals) if vals else None

    stop_rows = [turn.stop_correct for turn in turns if turn.stop_correct is not None]
    exact_rows = [
        bool(turn.metrics["tool_exact_match"])
        for turn in turns
        if turn.metrics.get("tool_exact_match") is not None
    ]
    input_tokens = [
        int(turn.candidate_usage["input_tokens"])
        for turn in turns
        if turn.candidate_usage.get("input_tokens") is not None
    ]
    output_tokens = [
        int(turn.candidate_usage["output_tokens"])
        for turn in turns
        if turn.candidate_usage.get("output_tokens") is not None
    ]
    latencies = [
        float(turn.candidate_usage["latency_ms"])
        for turn in turns
        if turn.candidate_usage.get("latency_ms") is not None
    ]
    aggregate = {
        "turns": len(turns),
        "candidate_success_rate": (
            sum(turn.candidate_status == "succeeded" for turn in turns) / len(turns)
            if turns else None
        ),
        "gold_success_rate": (
            sum(turn.gold_status == "succeeded" for turn in turns) / len(turns)
            if turns else None
        ),
        "stopping_correctness": (
            sum(bool(x) for x in stop_rows) / len(stop_rows) if stop_rows else None
        ),
        "tool_exact_match_rate": (
            sum(exact_rows) / len(exact_rows) if exact_rows else None
        ),
        "tool_any_order_precision": mean_metric("tool_any_order_precision"),
        "tool_any_order_recall": mean_metric("tool_any_order_recall"),
        "tool_in_order_normalized": mean_metric("tool_in_order_normalized"),
        "argument_grounding_accuracy": mean_metric("argument_grounding_accuracy"),
        "candidate_input_tokens": sum(input_tokens) if input_tokens else None,
        "candidate_output_tokens": sum(output_tokens) if output_tokens else None,
        "candidate_latency_mean_ms": fmean(latencies) if latencies else None,
    }
    return turns, aggregate
