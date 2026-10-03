#!/usr/bin/env python3
"""O5 consequence sweep for one remote-evidence round at real actuation points.

This experiment calls no model API.  It first runs the deterministic O5
action-conditioned reference, finds simulator ticks where configuration commands
were actually submitted *and* a planner PromptAssembly exists, then replaces
exactly that planner turn with two gateway-owner evidence reads.  The runtime's
simulator-authoritative remote-read barrier makes the next planner turn occur on
the following 60 s tick.

The sweep separates three layers that the transition R1 probe intentionally does
not collapse:

  planner semantic scope -> runtime execution eligibility -> physical opportunity.

It therefore measures when a one-round investigation delay really crosses a
Class-A opportunity instead of assuming every extra model/tool round is harmful.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
CODE = ROOT / "code"
for p in (
    CODE,
    CODE / "substrate" / "joint",
    CODE / "substrate" / "instance",
    CODE / "substrate" / "monitoring",
    CODE / "substrate" / "physics",
    CODE / "substrate" / "runtime",
    CODE / "evaluation" / "agentic",
    CODE / "legacy-communication" / "analysis",
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
    PlannedCapabilityInvocation,
    PlannerDecision,
    PlannerDecisionProposal,
)


OUT = ROOT / "results" / "agentic" / "o5-query-delay-backhaul-sweep-v1" / "result.json"


def query_proposal() -> PlannerDecisionProposal:
    return PlannerDecisionProposal(
        invocations=[
            PlannedCapabilityInvocation(
                capability_id="communication.gateway.primary_health",
                resource="gw0",
                canonical_arguments={},
            ),
            PlannedCapabilityInvocation(
                capability_id="communication.gateway.receipt_summary",
                resource="gw0",
                canonical_arguments={},
            ),
        ],
        reason_codes=["counterfactual_one_remote_evidence_round"],
    )


class OneShotQueryConsumer:
    provider = "counterfactual"
    model = "deterministic-one-remote-evidence-round"

    def __init__(self, target_hash: str) -> None:
        self.base = DeterministicComplyPlannerConsumer()
        self.target_hash = target_hash
        self.consumer_id = f"o5-query-delay:{target_hash[:12]}"
        self.injected = False

    def decide(self, request, assembly):
        if not self.injected and assembly.assembly_hash == self.target_hash:
            self.injected = True
            proposal = query_proposal()
            return (
                PlannerDecision(
                    decision_id=f"decision:{request.request_id}:query-delay",
                    request_id=request.request_id,
                    **proposal.model_dump(mode="python"),
                ),
                ModelUsage(),
            )
        return self.base.decide(request, assembly)


def heard_times(inst, start_s: int, end_s: int, nodes: set[str]) -> dict[str, list[int]]:
    out: dict[str, set[int]] = {node_id: set() for node_id in nodes}
    for transit in inst.log.transit.values():
        if transit.heard_at is None:
            continue
        heard_at = int(transit.heard_at)
        if heard_at < int(start_s) or heard_at >= int(end_s):
            continue
        sample = inst.log.samples.get(transit.sample_id)
        if sample is not None and sample.node_id in nodes:
            out[sample.node_id].add(heard_at)
    return {node_id: sorted(times) for node_id, times in out.items() if times}


def run_delay(backhaul_delay_s: int) -> list[dict]:
    ep = benchmark_episode_catalog()["O5"]
    sim = dict(ep.simulator_overrides)
    sim["backhaul_delay_s"] = int(backhaul_delay_s)
    base_result, base_policy, base_inst, _ = run_agentic_episode(
        seed=0,
        operational_task=ep.task,
        context_mode="action_conditioned_compact",
        planner_consumer=DeterministicComplyPlannerConsumer(),
        simulator_kwargs=sim,
    )
    hashes = {row.t_s: row.assembly.assembly_hash for row in frozen_r1_inputs(base_policy.trace.events)}
    sent: dict[int, list[tuple]] = defaultdict(list)
    for row in base_inst.trace_events:
        if len(row) >= 6 and row[2] == "sent":
            sent[int(row[0])].append(row)

    candidate_times = sorted(t for t in sent if t in hashes)
    before = communication_metrics(base_result)
    rows = []
    for t_s in candidate_times:
        baseline_rows = sent[t_s]
        baseline_nodes = {str(row[1]) for row in baseline_rows}
        consumer = OneShotQueryConsumer(hashes[t_s])
        result, policy, inst, _ = run_agentic_episode(
            seed=0,
            operational_task=ep.task,
            context_mode="action_conditioned_compact",
            planner_consumer=consumer,
            simulator_kwargs=sim,
        )
        if not consumer.injected:
            raise RuntimeError(f"target assembly not reached at t={t_s}")
        after = communication_metrics(result)

        remote_results = [
            e for e in policy.trace.events
            if e.event_type == "capability_result"
            and e.t_s >= t_s
            and e.payload.get("request_id", "").startswith(f"evidence:0:{t_s}:")
        ]
        remote_visible_at = min((e.t_s for e in remote_results), default=t_s)
        crossed = heard_times(base_inst, t_s, remote_visible_at, baseline_nodes)
        rows.append(
            {
                "backhaul_delay_s": int(backhaul_delay_s),
                "t_s": t_s,
                "phase_required_period_s": ep.task.phase_at(t_s).required_period_s,
                "baseline_commands_submitted_this_tick": len(baseline_rows),
                "baseline_nodes": sorted(baseline_nodes),
                "evidence_visible_at_s": remote_visible_at,
                "class_a_opportunities_crossed": crossed,
                "opportunity_crossed_node_count": len(crossed),
                "opportunity_crossed_count": sum(len(times) for times in crossed.values()),
                "remote_result_times": sorted({e.t_s for e in remote_results}),
                "remote_result_latencies_s": sorted(
                    {
                        int((e.payload.get("latency") or {}).get("simulated_s", 0) or 0)
                        for e in remote_results
                    }
                ),
                "baseline": before,
                "intervention": after,
                "delta": metric_delta(after, before),
                "physical_equal": physical_signature(result) == physical_signature(base_result),
            }
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--backhaul-delays",
        default="0,60,180,240,300,900",
        help="comma-separated existing ControlPlane.backhaul_delay_s sensitivity values",
    )
    args = ap.parse_args()
    delays = [int(x) for x in args.backhaul_delays.split(",") if x.strip()]
    rows = []
    for delay in delays:
        rows.extend(run_delay(delay))

    out = {
        "experiment": "o5-query-delay-backhaul-sweep-v1",
        "seed": 0,
        "context_mode": "action_conditioned_compact",
        "backhaul_delay_s": delays,
        "intervention": (
            "replace one deterministic planner turn at a real config-submission tick with "
            "gateway.primary_health + gateway.receipt_summary; remote evidence becomes visible "
            "according to existing ControlPlane.backhaul_delay_s plus Instance phase ordering"
        ),
        "candidate_rule": "ticks with baseline config submission and a current PromptAssembly",
        "rows": rows,
        "claim_ceiling": (
            "Single-seed paired backhaul-delay sensitivity and timing/mechanism probe. It establishes "
            "opportunity-conditioned physical consequences of one evidence round; delay values are "
            "scenario coordinates, not a claim about a specific deployment or a model error rate."
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(OUT)
    for row in rows:
        delta = row["delta"]
        nz = {
            k: delta.get(k)
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
            if delta.get(k) not in (None, 0, 0.0)
        }
        print(
            "backhaul_delay=", row["backhaul_delay_s"],
            row["t_s"],
            "sent=", row["baseline_commands_submitted_this_tick"],
            "crossed_nodes=", row["opportunity_crossed_node_count"],
            "equal=", row["physical_equal"],
            "delta=", nz,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
