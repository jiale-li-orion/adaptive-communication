#!/usr/bin/env python3
"""Audit O5 planner semantics -> runtime eligibility -> physical submission.

R1 model evaluation intentionally scores the model-facing candidate/action
semantics.  The full runtime then applies execution backpressure (in-flight,
dwell, already-at-target) before any command reaches the physical control plane.
This audit makes those layers explicit at the three frozen O5 transition events
so an exact R1 action-scope score is never misread as "all of these commands
should be transmitted immediately".
"""
from __future__ import annotations

import json
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
from agentic_communication.planner import DeterministicComplyPlannerConsumer  # noqa: E402
from agentic_communication.run import run_agentic_episode  # noqa: E402


DEVSET = ROOT / "results" / "agentic" / "o5-context-transition-devset-v1"
OUT = ROOT / "results" / "agentic" / "o5-execution-layer-audit-v1" / "result.json"


def semantic_gold(env: dict) -> list[dict]:
    out = []
    for plan in (env.get("candidate_action_context") or {}).get("candidate_plans", []):
        if plan.get("feasibility") != "supported":
            continue
        for inv in plan.get("invocations", []):
            if str(inv.get("capability_id", "")).startswith("communication.config."):
                out.append(inv)
    return out


def config_invocations(payload: dict) -> list[dict]:
    return [
        inv for inv in payload.get("invocations", [])
        if str(inv.get("capability_id", "")).startswith("communication.config.")
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


def main() -> int:
    manifest = json.loads((DEVSET / "manifest.json").read_text(encoding="utf-8"))
    ep = benchmark_episode_catalog()["O5"]
    _result, policy, inst, _ = run_agentic_episode(
        seed=0,
        operational_task=ep.task,
        context_mode="action_conditioned_compact",
        planner_consumer=DeterministicComplyPlannerConsumer(),
        simulator_kwargs=ep.simulator_overrides,
    )

    rows = []
    for event in manifest["events"]:
        event_id = event["event_id"]
        t_s = int(event["selected_t_s"])
        env = json.loads(
            (DEVSET / "inputs" / event_id / "action_conditioned_compact.json").read_text(
                encoding="utf-8"
            )
        )
        gold = semantic_gold(env)
        planner_rows = [
            e for e in policy.trace.events
            if e.t_s == t_s and e.event_type == "planner_decision"
        ]
        planner_inv = [] if not planner_rows else config_invocations(planner_rows[-1].payload)
        admitted = [
            e.payload for e in policy.trace.events
            if e.t_s == t_s
            and e.event_type == "capability_request"
            and str(e.payload.get("capability_id", "")).startswith("communication.config.")
        ]
        accepted = [
            row for row in inst.trace_events
            if len(row) >= 6 and int(row[0]) == t_s and row[2] == "sent"
        ]
        admitted_nodes = sorted({str(row.get("resource")) for row in admitted})
        gold_nodes = sorted({str(row.get("resource")) for row in gold})
        rows.append(
            {
                "event_id": event_id,
                "t_s": t_s,
                "required_period_s": int(env["task_contract"]["desired_state"]["required_period_s"]),
                "planner_semantic_gold_config_invocations": len(gold),
                "planner_semantic_gold_nodes": gold_nodes,
                "deterministic_planner_config_invocations": len(planner_inv),
                "runtime_admitted_config_requests": len(admitted),
                "runtime_admitted_nodes": admitted_nodes,
                "control_plane_accepted_commands": len(accepted),
                "next_class_a_opportunity_slack_s_by_admitted_node": {
                    node_id: next_heard_slack(inst, t_s, node_id)
                    for node_id in admitted_nodes
                },
                "layer_semantics": {
                    "planner_semantic_gold": "supported candidate-action invocations in frozen R1 context",
                    "deterministic_planner": "reference PlannerConsumer proposal before runtime backpressure",
                    "runtime_admitted": "config CapabilityRequest rows surviving in_flight/dwell/at_target gates",
                    "control_plane_accepted": "commands accepted by the center->gateway submission path",
                },
            }
        )

    out = {
        "experiment": "o5-execution-layer-audit-v1",
        "seed": 0,
        "rows": rows,
        "claim_ceiling": (
            "Evaluator/audit artifact only. Planner semantic correctness, runtime eligibility and "
            "physical submission are distinct layers and must not be substituted for one another."
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(OUT)
    for row in rows:
        print(
            row["event_id"],
            "gold=", row["planner_semantic_gold_config_invocations"],
            "planner=", row["deterministic_planner_config_invocations"],
            "runtime=", row["runtime_admitted_config_requests"],
            "accepted=", row["control_plane_accepted_commands"],
            "slack=", row["next_class_a_opportunity_slack_s_by_admitted_node"],
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
