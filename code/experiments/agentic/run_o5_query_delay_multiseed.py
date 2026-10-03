#!/usr/bin/env python3
"""Multi-seed robustness for remote-evidence delay vs control-opportunity slack.

No model API is called.  For each seed/backhaul-delay pair, run deterministic
one benchmark episode's action-conditioned control, find ticks where config commands were actually
submitted and a current PromptAssembly exists, then replace exactly that turn
with one gateway-owner evidence round.  The intervention is paired against the
same seed/delay baseline.

The primary diagnostic variable is whether the planner-visible evidence wait
crosses one or more Class-A opportunities for nodes whose config commands were
actually admitted at that baseline tick.  This tests the mechanism discovered
in the seed-0 threshold probe without assuming that every extra query is harmful.
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
    PlannedCapabilityInvocation,
    PlannerDecision,
    PlannerDecisionProposal,
)


DEFAULT_EPISODE = "O5"


def parse_seeds(text: str) -> list[int]:
    value = text.strip()
    if ":" in value:
        lo, hi = value.split(":", 1)
        return list(range(int(lo), int(hi)))
    return [int(x) for x in value.split(",") if x.strip()]


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


QUERY_CAPABILITIES = {
    "communication.gateway.primary_health",
    "communication.gateway.receipt_summary",
}


def _completed_query_capabilities(assembly) -> set[str]:
    completed: set[str] = set()
    for fragment in assembly.fragments:
        if fragment.kind != "recent_capability_outcomes":
            continue
        rows = fragment.content if isinstance(fragment.content, list) else []
        for row in rows:
            if not isinstance(row, dict):
                continue
            capability_id = str(row.get("capability_id", ""))
            if capability_id in QUERY_CAPABILITIES:
                completed.add(capability_id)
    return completed


class OneShotQueryConsumer:
    provider = "counterfactual"
    model = "deterministic-one-remote-evidence-round"

    def __init__(self, target_hash: str, label: str) -> None:
        self.base = DeterministicComplyPlannerConsumer()
        self.target_hash = target_hash
        self.consumer_id = f"o5-query-delay:{label}"
        self.injected = False
        self.waiting_for_remote_evidence = False
        self.resumed_after_evidence = False

    def decide(self, request, assembly):
        if not self.injected and assembly.assembly_hash == self.target_hash:
            self.injected = True
            self.waiting_for_remote_evidence = True
            proposal = query_proposal()
            return (
                PlannerDecision(
                    decision_id=f"decision:{request.request_id}:query-delay",
                    request_id=request.request_id,
                    **proposal.model_dump(mode="python"),
                ),
                ModelUsage(),
            )
        if self.waiting_for_remote_evidence:
            completed = _completed_query_capabilities(assembly)
            if QUERY_CAPABILITIES <= completed:
                self.waiting_for_remote_evidence = False
                self.resumed_after_evidence = True
            else:
                proposal = PlannerDecisionProposal(
                    stop=True,
                    invocations=[],
                    reason_codes=["waiting_for_remote_evidence"],
                )
                return (
                    PlannerDecision(
                        decision_id=f"decision:{request.request_id}:await-query-result",
                        request_id=request.request_id,
                        **proposal.model_dump(mode="python"),
                    ),
                    ModelUsage(),
                )
        return self.base.decide(request, assembly)


class OneShotScopedQueryConsumer:
    """Ordinary dependency-executor reference for nonblocking investigation.

    At the target decision, keep the deterministic ready device actions and add
    the same two gateway-owner observations used by ``OneShotQueryConsumer``.
    Remote results may arrive later, but unrelated ready actions are not held
    behind that evidence barrier.  Subsequent decisions immediately return to
    deterministic comply.

    This is deliberately a control/reference arm, not a claimed Agent method.
    It uses no future simulator information and relies only on the current
    PromptAssembly plus the existing deterministic comply decision.
    """

    provider = "counterfactual"
    model = "deterministic-scoped-remote-evidence-round"

    def __init__(self, target_hash: str, label: str) -> None:
        self.base = DeterministicComplyPlannerConsumer()
        self.target_hash = target_hash
        self.consumer_id = f"scoped-query-delay:{label}"
        self.injected = False

    def decide(self, request, assembly):
        if not self.injected and assembly.assembly_hash == self.target_hash:
            self.injected = True
            ready, _usage = self.base.decide(request, assembly)
            query = query_proposal()
            proposal = PlannerDecisionProposal(
                stop=False,
                invocations=[*ready.invocations, *query.invocations],
                state_patch=dict(ready.state_patch),
                reason_codes=[
                    *ready.reason_codes,
                    "nonblocking_remote_evidence_round",
                    "ready_actions_progress_while_unrelated_evidence_pending",
                ],
            )
            return (
                PlannerDecision(
                    decision_id=f"decision:{request.request_id}:scoped-query-delay",
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


def baseline(episode: str, seed: int, delay_s: int):
    ep = benchmark_episode_catalog()[episode]
    sim = dict(ep.simulator_overrides)
    sim["backhaul_delay_s"] = int(delay_s)
    return run_agentic_episode(
        seed=seed,
        operational_task=ep.task,
        context_mode="action_conditioned_compact",
        planner_consumer=DeterministicComplyPlannerConsumer(),
        simulator_kwargs=sim,
    )


def intervention(
    episode: str,
    seed: int,
    delay_s: int,
    target_hash: str,
    label: str,
    investigation_mode: str,
):
    ep = benchmark_episode_catalog()[episode]
    sim = dict(ep.simulator_overrides)
    sim["backhaul_delay_s"] = int(delay_s)
    if investigation_mode == "global_wait":
        consumer = OneShotQueryConsumer(target_hash, label)
    elif investigation_mode == "scoped_ready":
        consumer = OneShotScopedQueryConsumer(target_hash, label)
    else:
        raise ValueError(f"unsupported investigation_mode {investigation_mode!r}")
    result, policy, inst, obligations = run_agentic_episode(
        seed=seed,
        operational_task=ep.task,
        context_mode="action_conditioned_compact",
        planner_consumer=consumer,
        simulator_kwargs=sim,
    )
    if not consumer.injected:
        raise RuntimeError(f"query-delay target not reached: {label}")
    if isinstance(consumer, OneShotQueryConsumer):
        if consumer.waiting_for_remote_evidence:
            raise RuntimeError(f"remote evidence never completed before episode end: {label}")
        if not consumer.resumed_after_evidence:
            raise RuntimeError(f"planner never resumed after remote evidence: {label}")
    return result, policy, inst, obligations


def _aggregate_scope(rows: list[dict], delays: list[int]) -> dict:
    by_delay = {}
    for delay in delays:
        xs = [row for row in rows if row["backhaul_delay_s"] == delay]
        crossed = [row for row in xs if row["opportunity_crossed_count"] > 0]
        uncrossed = [row for row in xs if row["opportunity_crossed_count"] == 0]
        divergent = [row for row in xs if not row["physical_equal"]]
        crossed_div = [row for row in crossed if not row["physical_equal"]]
        uncrossed_div = [row for row in uncrossed if not row["physical_equal"]]
        by_delay[str(delay)] = {
            "candidate_points": len(xs),
            "points_crossing_class_a_opportunity": len(crossed),
            "physical_divergent_points": len(divergent),
            "divergence_rate": (len(divergent) / len(xs) if xs else None),
            "divergence_given_crossed": (
                len(crossed_div) / len(crossed) if crossed else None
            ),
            "divergence_given_not_crossed": (
                len(uncrossed_div) / len(uncrossed) if uncrossed else None
            ),
            "crossed_but_equal": len(crossed) - len(crossed_div),
            "not_crossed_but_divergent": len(uncrossed_div),
            "sum_crossed_opportunities": sum(row["opportunity_crossed_count"] for row in xs),
            "sum_abs_config_mismatch_delta_node_s": sum(
                abs(float(row["delta"].get("config_mismatch_node_s", 0.0) or 0.0))
                for row in xs
            ),
            "sum_abs_energy_delta_wh": sum(
                abs(float(row["delta"].get("total_consumed_wh", 0.0) or 0.0))
                for row in xs
            ),
        }
    return by_delay


def aggregate(rows: list[dict], seeds: list[int], delays: list[int], task_horizon_s: int) -> dict:
    interior = [row for row in rows if 0 < int(row["t_s"]) < int(task_horizon_s)]
    boundary = [row for row in rows if row not in interior]
    return {
        "seeds": seeds,
        "n_seeds": len(seeds),
        "backhaul_delay_s": delays,
        "primary_scope": "0 < t_s < task_horizon_s",
        "task_horizon_s": int(task_horizon_s),
        "interior_by_delay": _aggregate_scope(interior, delays),
        "boundary_diagnostic_by_delay": _aggregate_scope(boundary, delays),
        "all_rows_by_delay": _aggregate_scope(rows, delays),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", default=DEFAULT_EPISODE, choices=sorted(benchmark_episode_catalog()))
    ap.add_argument("--seeds", default="0:20")
    ap.add_argument("--backhaul-delays", default="0,180,240,300")
    ap.add_argument(
        "--investigation-mode",
        choices=("global_wait", "scoped_ready"),
        default="global_wait",
    )
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    episode = args.episode
    investigation_mode = args.investigation_mode
    seeds = parse_seeds(args.seeds)
    delays = [int(x) for x in args.backhaul_delays.split(",") if x.strip()]
    ep = benchmark_episode_catalog()[episode]
    out_path = (
        Path(args.out)
        if args.out
        else ROOT
        / "results"
        / "agentic"
        / (
            f"{episode.lower()}-query-delay-multiseed-v1"
            if investigation_mode == "global_wait"
            else f"{episode.lower()}-scoped-query-multiseed-v1"
        )
        / "result.json"
    )

    rows = []
    for seed in seeds:
        for delay in delays:
            base_result, base_policy, base_inst, _ = baseline(episode, seed, delay)
            before = communication_metrics(base_result)
            prompt_hashes = {
                int(row.t_s): row.assembly.assembly_hash
                for row in frozen_r1_inputs(base_policy.trace.events)
            }
            sent: dict[int, list[tuple]] = defaultdict(list)
            for row in base_inst.trace_events:
                if len(row) >= 6 and row[2] == "sent":
                    sent[int(row[0])].append(row)
            candidate_times = sorted(t for t in sent if t in prompt_hashes)

            for t_s in candidate_times:
                baseline_rows = sent[t_s]
                baseline_nodes = {str(row[1]) for row in baseline_rows}
                result, policy, _inst, _ = intervention(
                    episode,
                    seed,
                    delay,
                    prompt_hashes[t_s],
                    f"seed={seed}:delay={delay}:t={t_s}",
                    investigation_mode,
                )
                after = communication_metrics(result)
                remote_results = [
                    e for e in policy.trace.events
                    if e.event_type == "capability_result"
                    and e.t_s >= t_s
                    and str(e.payload.get("request_id", "")).startswith(
                        f"evidence:{seed}:{t_s}:"
                    )
                ]
                remote_visible_at = min((int(e.t_s) for e in remote_results), default=t_s)
                config_requests_during_wait = [
                    e for e in policy.trace.events
                    if e.event_type == "capability_request"
                    and t_s <= int(e.t_s) < remote_visible_at
                    and str(e.payload.get("capability_id", "")).startswith("communication.config.")
                ]
                if investigation_mode == "global_wait" and config_requests_during_wait:
                    raise RuntimeError(
                        f"investigation barrier leaked config actions: seed={seed} delay={delay} "
                        f"t={t_s} visible={remote_visible_at} n={len(config_requests_during_wait)}"
                    )
                crossed = heard_times(base_inst, t_s, remote_visible_at, baseline_nodes)
                resumed_config_requests = [
                    e for e in policy.trace.events
                    if e.event_type == "capability_request"
                    and int(e.t_s) == remote_visible_at
                    and str(e.payload.get("capability_id", "")).startswith("communication.config.")
                ]
                resumed_nodes = {
                    str(e.payload.get("resource")) for e in resumed_config_requests
                }
                admission_added = sorted(resumed_nodes - baseline_nodes)
                admission_removed = sorted(baseline_nodes - resumed_nodes)
                rows.append(
                    {
                        "seed": seed,
                        "backhaul_delay_s": delay,
                        "t_s": t_s,
                        "phase_required_period_s": int(
                            ep.task.phase_at(t_s).required_period_s
                        ),
                        "baseline_commands_submitted_this_tick": len(baseline_rows),
                        "baseline_nodes": sorted(baseline_nodes),
                        "resumed_config_requests": len(resumed_config_requests),
                        "resumed_nodes": sorted(resumed_nodes),
                        "runtime_admission_drift": bool(admission_added or admission_removed),
                        "runtime_admission_added_nodes": admission_added,
                        "runtime_admission_removed_nodes": admission_removed,
                        "evidence_visible_at_s": remote_visible_at,
                        "decision_visible_wait_s": remote_visible_at - t_s,
                        "investigation_barrier_s": remote_visible_at - t_s,
                        "config_requests_during_evidence_wait": len(config_requests_during_wait),
                        "same_tick_config_requests": sum(
                            int(e.t_s) == t_s for e in config_requests_during_wait
                        ),
                        "class_a_opportunities_crossed": crossed,
                        "opportunity_crossed_node_count": len(crossed),
                        "opportunity_crossed_count": sum(len(times) for times in crossed.values()),
                        "delta": metric_delta(after, before),
                        "physical_equal": physical_signature(result) == physical_signature(base_result),
                    }
                )

    out = {
        "experiment": (
            f"{episode.lower()}-query-delay-multiseed-v1"
            if investigation_mode == "global_wait"
            else f"{episode.lower()}-scoped-query-multiseed-v1"
        ),
        "episode": episode,
        "task_id": ep.task.task_id,
        "investigation_mode": investigation_mode,
        "intervention": (
            (
                "At each paired baseline tick with actual config submission and a PromptAssembly, "
                "replace the deterministic planner turn with gateway.primary_health + "
                "gateway.receipt_summary, hold action while those remote results are pending, then "
                "return to deterministic comply on the first Context that contains both outcomes."
            )
            if investigation_mode == "global_wait"
            else (
                "At each paired baseline tick with actual config submission and a PromptAssembly, "
                "emit the same gateway.primary_health + gateway.receipt_summary observations together "
                "with the current deterministic ready configuration actions. Remote evidence remains "
                "asynchronous, but it does not block those unrelated ready actions."
            )
        ),
        "claim_ceiling": (
            f"Multi-seed deterministic control/reference result for one evidence round in {episode}. "
            "No model API and no claim about model error frequency or dependency-construction novelty."
        ),
        "aggregate": aggregate(
            rows,
            seeds,
            delays,
            ep.task.task_horizon_s,
        ),
        "rows": rows,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(out_path)
    print(json.dumps(out["aggregate"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
