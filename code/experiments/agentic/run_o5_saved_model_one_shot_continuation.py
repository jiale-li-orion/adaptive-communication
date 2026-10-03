#!/usr/bin/env python3
"""Replay saved DeepSeek O5 decisions as one-shot R3 interventions.

No model API is called.  For each frozen development event we rerun the same
seed-0 O5 episode with DeterministicComplyPlannerConsumer, identify the current
PromptAssembly at that event time, replace exactly one planner decision with the
already-saved DeepSeek output, then immediately return to deterministic comply.

This estimates the physical consequence of the *observed model action* rather
than assigning an artificial stale-task controller error to it.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CODE = ROOT / "code"
for p in (
    CODE,
    CODE / "v3joint",
    CODE / "instance",
    CODE / "monitoring",
    CODE / "physics",
    CODE / "runtime",
    CODE / "experiments",
    CODE / "analysis",
):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from agentic_communication.episodes import benchmark_episode_catalog  # noqa: E402
from agentic_communication.metrics import communication_metrics, metric_delta, physical_signature  # noqa: E402
from agentic_communication.planner import DeterministicComplyPlannerConsumer  # noqa: E402
from agentic_communication.replay import frozen_r1_inputs  # noqa: E402
from agentic_communication.run import run_agentic_episode  # noqa: E402
from agentic_communication.runtime_contracts import (  # noqa: E402
    ModelUsage,
    PlannerDecision,
    PlannerDecisionProposal,
)


DEVSET = ROOT / "results" / "agentic" / "o5-context-transition-devset-v1" / "manifest.json"
MODEL_ROOT = ROOT / "results" / "agentic" / "o5-transition-context-model-probe-v2-decision-sufficient" / "r1"
UPDATE_ROOT = ROOT / "results" / "agentic" / "o5-context-update-model-probe-v2-decision-sufficient" / "r1"
OUT = ROOT / "results" / "agentic" / "o5-saved-model-one-shot-continuation-v2-decision-sufficient" / "result.json"

EVENT_CONTEXTS = (
    "task_conditioned",
    "full_dump",
    "generic_react",
    "action_conditioned_compact",
)
UPDATE_VARIANTS = (
    "fresh_rebuild",
    "full_history",
    "naive_incremental_cache",
    "revision_aware_update",
)
UPDATE_TARGETS = {
    "backhaul_recovery_before_task_recovery__to__task_recovery_revision": "task_recovery_revision",
    "task_recovery_revision__to__post_revision_reconciliation": "post_revision_reconciliation",
}


def parse_saved_proposal(path: Path) -> PlannerDecisionProposal:
    row = json.loads(path.read_text(encoding="utf-8"))
    if row.get("error"):
        raise RuntimeError(f"saved model result is invalid: {path}: {row['error']}")
    raw = str(row.get("raw_output") or "").strip()
    if raw.startswith("```") and raw.endswith("```"):
        lines = raw.splitlines()
        if lines and lines[0].strip().lower() in {"```", "```json"}:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    return PlannerDecisionProposal.model_validate(json.loads(raw))


class OneShotDecisionConsumer:
    provider = "saved-model-intervention"
    model = "deepseek-flash:saved-one-shot"

    def __init__(self, *, target_hash: str, proposal: PlannerDecisionProposal, label: str) -> None:
        self.base = DeterministicComplyPlannerConsumer()
        self.target_hash = target_hash
        self.proposal = proposal
        self.label = label
        self.consumer_id = f"one-shot:{label}"
        self.injected = False
        self.injected_request_id: str | None = None

    def decide(self, request, assembly):
        if not self.injected and assembly.assembly_hash == self.target_hash:
            self.injected = True
            self.injected_request_id = request.request_id
            return (
                PlannerDecision(
                    decision_id=f"decision:{request.request_id}:saved-model",
                    request_id=request.request_id,
                    **self.proposal.model_dump(mode="python"),
                ),
                ModelUsage(),
            )
        return self.base.decide(request, assembly)


def decision_shape(proposal: PlannerDecisionProposal) -> dict:
    counts = {"query": 0, "config": 0, "fallback": 0, "other": 0}
    for inv in proposal.invocations:
        cid = inv.capability_id
        if cid.startswith("communication.config."):
            counts["config"] += 1
        elif cid.startswith("communication.fallback."):
            counts["fallback"] += 1
        elif cid.startswith("communication.gateway.") or cid.startswith("communication.center."):
            counts["query"] += 1
        else:
            counts["other"] += 1
    return {"stop": proposal.stop, "invocations": len(proposal.invocations), **counts}


def run_base(ep, mode: str):
    return run_agentic_episode(
        seed=0,
        operational_task=ep.task,
        context_mode=mode,
        planner_consumer=DeterministicComplyPlannerConsumer(),
        simulator_kwargs=ep.simulator_overrides,
    )


def event_hash(policy, selected_t_s: int) -> str:
    rows = frozen_r1_inputs(policy.trace.events)
    record = next((row for row in rows if row.t_s == selected_t_s), None)
    if record is None:
        raise RuntimeError(f"no current prompt at t={selected_t_s}")
    return record.assembly.assembly_hash


def intervention(ep, mode: str, target_hash: str, proposal: PlannerDecisionProposal, label: str):
    consumer = OneShotDecisionConsumer(target_hash=target_hash, proposal=proposal, label=label)
    result, policy, inst, obligations = run_agentic_episode(
        seed=0,
        operational_task=ep.task,
        context_mode=mode,
        planner_consumer=consumer,
        simulator_kwargs=ep.simulator_overrides,
    )
    if not consumer.injected:
        raise RuntimeError(f"one-shot target was not reached: {label}")
    return result, policy, inst, obligations, consumer


def main() -> int:
    manifest = json.loads(DEVSET.read_text(encoding="utf-8"))
    events = {row["event_id"]: row for row in manifest["events"]}
    ep = benchmark_episode_catalog()["O5"]

    # One deterministic reference trajectory per real Context mode.  These runs
    # also provide the event-specific assembly hashes for the *current* runtime.
    bases = {}
    hashes = {}
    for mode in EVENT_CONTEXTS:
        result, policy, inst, obligations = run_base(ep, mode)
        bases[mode] = (result, policy, inst, obligations)
        hashes[mode] = {
            event_id: event_hash(policy, int(event["selected_t_s"]))
            for event_id, event in events.items()
        }

    rows = []
    for event_id, event in events.items():
        for mode in EVENT_CONTEXTS:
            saved = MODEL_ROOT / event_id / f"{mode}.json"
            proposal = parse_saved_proposal(saved)
            base_result = bases[mode][0]
            result, _policy, _inst, _obligations, consumer = intervention(
                ep,
                mode,
                hashes[mode][event_id],
                proposal,
                f"{event_id}:{mode}",
            )
            before = communication_metrics(base_result)
            after = communication_metrics(result)
            rows.append(
                {
                    "family": "event_context",
                    "event_id": event_id,
                    "selected_t_s": event["selected_t_s"],
                    "context_mode": mode,
                    "saved_result": str(saved.relative_to(ROOT)),
                    "decision_shape": decision_shape(proposal),
                    "injected_request_id": consumer.injected_request_id,
                    "baseline": before,
                    "intervention": after,
                    "delta": metric_delta(after, before),
                    "physical_equal": physical_signature(result) == physical_signature(base_result),
                }
            )

    # Context-update variants are alternative model outputs for the same current
    # action-conditioned physical event. Inject only the saved decision; the
    # physical prefix and all subsequent decisions remain deterministic comply.
    base_mode = "action_conditioned_compact"
    base_result = bases[base_mode][0]
    before = communication_metrics(base_result)
    for transition, event_id in UPDATE_TARGETS.items():
        event = events[event_id]
        for variant in UPDATE_VARIANTS:
            saved = UPDATE_ROOT / transition / f"{variant}.json"
            proposal = parse_saved_proposal(saved)
            result, _policy, _inst, _obligations, consumer = intervention(
                ep,
                base_mode,
                hashes[base_mode][event_id],
                proposal,
                f"context_update:{transition}:{variant}",
            )
            after = communication_metrics(result)
            rows.append(
                {
                    "family": "context_update",
                    "transition": transition,
                    "event_id": event_id,
                    "selected_t_s": event["selected_t_s"],
                    "context_mode": variant,
                    "saved_result": str(saved.relative_to(ROOT)),
                    "decision_shape": decision_shape(proposal),
                    "injected_request_id": consumer.injected_request_id,
                    "baseline": before,
                    "intervention": after,
                    "delta": metric_delta(after, before),
                    "physical_equal": physical_signature(result) == physical_signature(base_result),
                }
            )

    out = {
        "experiment": "o5-saved-model-one-shot-continuation-v2-decision-sufficient",
        "seed": 0,
        "model": "deepseek-flash",
        "semantics": (
            "Inject exactly one saved DeepSeek decision-sufficiency R1 output at the equivalent O5 event assembly; "
            "all prefix and post-intervention planner decisions use DeterministicComplyPlannerConsumer. No model API call."
        ),
        "rows": rows,
        "claim_ceiling": (
            "Single-seed development consequence probe. It labels saved model actions under one-shot continuation; "
            "it is not a general model-error rate or final method result."
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(OUT)
    for row in rows:
        d = row["delta"]
        print(
            row["family"],
            row["event_id"],
            row["context_mode"],
            row["decision_shape"],
            "equal=", row["physical_equal"],
            "delta_tdr=", d.get("timely_delivery_rate"),
            "delta_energy=", d.get("total_consumed_wh"),
            "delta_backup=", d.get("backup_bytes"),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
