#!/usr/bin/env python3
"""Replay observed DeepSeek O5 decisions across backhaul-delay sensitivity.

No model API is called.  The saved DeepSeek proposal from the formal O5 R1
matrix is held fixed.  For each backhaul-delay coordinate we rerun a paired
deterministic baseline, select the first current PromptAssembly at/after the
same external event request time, inject the saved proposal once, and then
return to deterministic comply.

This is a consequence sensitivity, not a claim about what DeepSeek would output
if it were freshly prompted under the altered transport delay.  That distinction
is recorded explicitly because the current Context can change with transport.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
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
from agentic_communication.runtime_contracts import ModelUsage, PlannerDecision, PlannerDecisionProposal  # noqa: E402


DEVSET = ROOT / "results" / "agentic" / "o5-context-transition-devset-v1" / "manifest.json"
MODEL_ROOT = ROOT / "results" / "agentic" / "o5-transition-context-model-probe-v2-decision-sufficient" / "r1"
OUT = ROOT / "results" / "agentic" / "o5-saved-model-backhaul-sensitivity-v1" / "result.json"
CONTEXTS = (
    "task_conditioned",
    "full_dump",
    "generic_react",
    "action_conditioned_compact",
)


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


class OneShotSavedConsumer:
    provider = "saved-model-consequence-sensitivity"
    model = "deepseek-flash:saved-output"

    def __init__(self, *, target_hash: str, proposal: PlannerDecisionProposal, label: str) -> None:
        self.base = DeterministicComplyPlannerConsumer()
        self.target_hash = target_hash
        self.proposal = proposal
        self.consumer_id = f"saved-sensitivity:{label}"
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


def select_event_record(policy, requested_t_s: int):
    rows = frozen_r1_inputs(policy.trace.events)
    candidates = [row for row in rows if int(row.t_s) >= int(requested_t_s)]
    if not candidates:
        raise RuntimeError(f"no PromptAssembly at/after requested t={requested_t_s}")
    return min(candidates, key=lambda row: int(row.t_s))


def runtime_config_requests(policy, t_s: int) -> list[dict]:
    return [
        e.payload
        for e in policy.trace.events
        if e.t_s == int(t_s)
        and e.event_type == "capability_request"
        and str(e.payload.get("capability_id", "")).startswith("communication.config.")
    ]


def next_heard_slack(inst, t_s: int, node_id: str) -> int | None:
    times = []
    for transit in inst.log.transit.values():
        if transit.heard_at is None or int(transit.heard_at) < int(t_s):
            continue
        sample = inst.log.samples.get(transit.sample_id)
        if sample is not None and sample.node_id == node_id:
            times.append(int(transit.heard_at))
    return None if not times else min(times) - int(t_s)


def run_base(ep, mode: str, delay_s: int):
    sim = dict(ep.simulator_overrides)
    sim["backhaul_delay_s"] = int(delay_s)
    return run_agentic_episode(
        seed=0,
        operational_task=ep.task,
        context_mode=mode,
        planner_consumer=DeterministicComplyPlannerConsumer(),
        simulator_kwargs=sim,
    )


def run_intervention(ep, mode: str, delay_s: int, target_hash: str,
                     proposal: PlannerDecisionProposal, label: str):
    sim = dict(ep.simulator_overrides)
    sim["backhaul_delay_s"] = int(delay_s)
    consumer = OneShotSavedConsumer(
        target_hash=target_hash,
        proposal=proposal,
        label=label,
    )
    result, policy, inst, obligations = run_agentic_episode(
        seed=0,
        operational_task=ep.task,
        context_mode=mode,
        planner_consumer=consumer,
        simulator_kwargs=sim,
    )
    if not consumer.injected:
        raise RuntimeError(f"saved decision target not reached: {label}")
    return result, policy, inst, obligations, consumer


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backhaul-delays", default="0,180,240,300")
    args = ap.parse_args()
    delays = [int(x) for x in args.backhaul_delays.split(",") if x.strip()]

    manifest = json.loads(DEVSET.read_text(encoding="utf-8"))
    ep = benchmark_episode_catalog()["O5"]
    rows = []
    baseline_index = {}

    for delay_s in delays:
        for mode in CONTEXTS:
            base_result, base_policy, base_inst, _ = run_base(ep, mode, delay_s)
            before = communication_metrics(base_result)
            for event in manifest["events"]:
                event_id = event["event_id"]
                requested_t_s = int(event["requested_t_s"])
                record = select_event_record(base_policy, requested_t_s)
                selected_t_s = int(record.t_s)
                admitted = runtime_config_requests(base_policy, selected_t_s)
                admitted_nodes = sorted({str(row.get("resource")) for row in admitted})
                baseline_key = (delay_s, mode, event_id)
                baseline_index[baseline_key] = {
                    "selected_t_s": selected_t_s,
                    "assembly_hash": record.assembly.assembly_hash,
                    "runtime_admitted_config_requests": len(admitted),
                    "runtime_admitted_nodes": admitted_nodes,
                    "next_class_a_opportunity_slack_s_by_admitted_node": {
                        node_id: next_heard_slack(base_inst, selected_t_s, node_id)
                        for node_id in admitted_nodes
                    },
                }

                saved = MODEL_ROOT / event_id / f"{mode}.json"
                proposal = parse_saved_proposal(saved)
                result, policy, inst, _obligations, consumer = run_intervention(
                    ep,
                    mode,
                    delay_s,
                    record.assembly.assembly_hash,
                    proposal,
                    f"delay={delay_s}:{event_id}:{mode}",
                )
                after = communication_metrics(result)
                b = baseline_index[baseline_key]
                remote_results = [
                    e for e in policy.trace.events
                    if e.event_type == "capability_result"
                    and e.t_s >= selected_t_s
                    and str(e.payload.get("request_id", "")).startswith(
                        f"evidence:0:{selected_t_s}:"
                    )
                ]
                rows.append(
                    {
                        "backhaul_delay_s": delay_s,
                        "event_id": event_id,
                        "requested_t_s": requested_t_s,
                        "selected_t_s": selected_t_s,
                        "context_mode": mode,
                        "saved_result": str(saved.relative_to(ROOT)),
                        "saved_decision_shape": decision_shape(proposal),
                        "runtime_admitted_config_requests_baseline": b[
                            "runtime_admitted_config_requests"
                        ],
                        "runtime_admitted_nodes_baseline": b["runtime_admitted_nodes"],
                        "next_class_a_opportunity_slack_s_by_admitted_node": b[
                            "next_class_a_opportunity_slack_s_by_admitted_node"
                        ],
                        "remote_result_times_after_injection": sorted(
                            {int(e.t_s) for e in remote_results}
                        ),
                        "remote_result_latencies_s_after_injection": sorted(
                            {
                                int((e.payload.get("latency") or {}).get("simulated_s", 0) or 0)
                                for e in remote_results
                            }
                        ),
                        "injected_request_id": consumer.injected_request_id,
                        "baseline": before,
                        "intervention": after,
                        "delta": metric_delta(after, before),
                        "physical_equal": physical_signature(result) == physical_signature(base_result),
                    }
                )

    out = {
        "experiment": "o5-saved-model-backhaul-sensitivity-v1",
        "seed": 0,
        "model": "deepseek-flash",
        "backhaul_delay_s": delays,
        "contexts": list(CONTEXTS),
        "semantics": (
            "Hold each already-observed DeepSeek proposal fixed and replay it once at the first "
            "current PromptAssembly at/after the same external event request time under each paired "
            "backhaul-delay coordinate. No model API call."
        ),
        "claim_ceiling": (
            "Consequence sensitivity of saved decisions only. The altered-delay Context is not sent "
            "back to DeepSeek, so these rows do not estimate model accuracy or behavior under the "
            "altered transport condition."
        ),
        "rows": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(OUT)
    for row in rows:
        d = row["delta"]
        nonzero = {
            k: d.get(k)
            for k in (
                "timely_delivery_rate",
                "collection_rate",
                "commands_sent",
                "commands_delivered",
                "downlink_attempts",
                "downlink_airtime_h",
                "config_mismatch_node_s",
                "total_consumed_wh",
                "backup_bytes",
            )
            if d.get(k) not in (None, 0, 0.0)
        }
        print(
            row["backhaul_delay_s"],
            row["event_id"],
            row["context_mode"],
            row["saved_decision_shape"],
            "selected=", row["selected_t_s"],
            "runtime_admitted=", row["runtime_admitted_config_requests_baseline"],
            "equal=", row["physical_equal"],
            "delta=", nonzero,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
