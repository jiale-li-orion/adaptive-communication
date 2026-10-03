#!/usr/bin/env python3
"""Freeze O5 recovery/task-transition model inputs for small-batch live-model testing."""
from __future__ import annotations

import hashlib
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
from agentic_communication.model_protocol import protocol_bytes, render_planner_protocol  # noqa: E402
from agentic_communication.planner import (  # noqa: E402
    DeterministicComplyPlannerConsumer,
)
from agentic_communication.replay import frozen_r1_inputs  # noqa: E402
from agentic_communication.run import run_agentic_episode  # noqa: E402


OUT = ROOT / "results" / "agentic" / "o5-context-transition-devset-v1"
CONSEQUENCE = ROOT / "results" / "agentic" / "o5-task-revision-consequence-v1" / "aggregate.json"
CONTEXTS = {
    "task_conditioned": DeterministicComplyPlannerConsumer,
    "full_dump": DeterministicComplyPlannerConsumer,
    "generic_react": DeterministicComplyPlannerConsumer,
    # All context arms deliberately share the same reference consumer so the
    # frozen model inputs are conditioned on one identical physical trajectory.
    "action_conditioned": DeterministicComplyPlannerConsumer,
    "action_conditioned_compact": DeterministicComplyPlannerConsumer,
    "action_candidates_full_dump": DeterministicComplyPlannerConsumer,
}
EVENTS = (
    (
        "backhaul_recovery_before_task_recovery",
        8 * 3600,
        "Primary backhaul has recovered, but Operational Task is still yellow until h9. "
        "Preserve/complete the 300 s monitoring profile; network recovery is not Task recovery.",
        "premature_blue_at_h8",
    ),
    (
        "task_recovery_revision",
        9 * 3600,
        "Operational Task changes from yellow/300 s to blue/3600 s. Reconcile installed state and roll back the dense profile where needed.",
        "stale_yellow_after_recovery",
    ),
    (
        "post_revision_reconciliation",
        10 * 3600,
        "Blue/3600 s is already authoritative. Complete remaining rollback/reconciliation and avoid carrying stale yellow state forward.",
        "late_blue_at_h10",
    ),
)


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> int:
    if not CONSEQUENCE.is_file():
        raise RuntimeError(
            f"missing consequence result: {CONSEQUENCE}; run run_o5_task_revision_consequence.py first"
        )
    consequence = json.loads(CONSEQUENCE.read_text(encoding="utf-8"))
    ep = benchmark_episode_catalog()["O5"]
    records_by_mode = {}
    for mode, consumer_cls in CONTEXTS.items():
        _result, policy, _, _ = run_agentic_episode(
            seed=0,
            operational_task=ep.task,
            context_mode=mode,
            planner_consumer=consumer_cls(),
            simulator_kwargs=ep.simulator_overrides,
        )
        records_by_mode[mode] = frozen_r1_inputs(policy.trace.events)

    # Anchor event times to the ordinary task-conditioned trace, then reuse the
    # exact simulator time across all Context modes.
    anchor = records_by_mode["task_conditioned"]
    event_rows = []
    manifest_rows = []
    for event_id, requested_t, expected_semantics, consequence_key in EVENTS:
        chosen = next((row for row in anchor if row.t_s >= requested_t), None)
        if chosen is None:
            raise RuntimeError(f"no O5 prompt at/after {requested_t}")
        selected_t = chosen.t_s
        event_rows.append(
            {
                "event_id": event_id,
                "requested_t_s": requested_t,
                "selected_t_s": selected_t,
                "expected_semantics": expected_semantics,
                "physical_consequence_ref": {
                    "result": str(CONSEQUENCE.relative_to(ROOT)),
                    "arm": consequence_key,
                    "delta_vs_correct": consequence["deltas_vs_correct"].get(consequence_key),
                },
            }
        )
        for mode in CONTEXTS:
            record = next((row for row in records_by_mode[mode] if row.t_s == selected_t), None)
            if record is None:
                raise RuntimeError(f"{mode}: no prompt at selected t={selected_t}")
            envelope = render_planner_protocol(record.assembly)
            raw = protocol_bytes(record.assembly)
            path = OUT / "inputs" / event_id / f"{mode}.json"
            dump(path, envelope)
            candidate = envelope.get("candidate_action_context") or {}
            manifest_rows.append(
                {
                    "event_id": event_id,
                    "context_mode": mode,
                    "selected_t_s": selected_t,
                    "protocol_bytes": len(raw),
                    "protocol_sha256": sha(raw),
                    "has_candidate_action_context": bool(candidate),
                    "candidate_phase_index": candidate.get("phase_index"),
                    "candidate_required_period_s": candidate.get("required_period_s"),
                    "candidate_plan_ids": [
                        row.get("plan_id") for row in candidate.get("candidate_plans", [])
                    ],
                    "input": str(path.relative_to(ROOT)),
                }
            )

    manifest = {
        "experiment": "o5-context-transition-devset-v1",
        "status": "frozen model development inputs",
        "seed": 0,
        "task": ep.task.model_dump(mode="json"),
        "simulator_overrides": ep.simulator_overrides,
        "events": event_rows,
        "contexts": list(CONTEXTS),
        "rows": manifest_rows,
        "physical_consequence_source": str(CONSEQUENCE.relative_to(ROOT)),
        "evaluation": {
            "r1": [
                "Task phase/revision grounding",
                "hold/install/rollback decision semantics",
                "capability legality and arguments",
                "stop correctness",
                "stale Task/config confusion",
            ],
            "r3": (
                "Only model/event combinations with legal executable decisions proceed to live continuation/full episode; "
                "communication metrics and energy/backup accounting decide value."
            ),
        },
        "claim_ceiling": (
            "Development-set freeze only. Event coordinates were chosen from Task/failure boundaries and deterministic consequence probes, "
            "not from observed model errors. All Context arms share DeterministicComplyPlannerConsumer so the underlying physical trajectory is identical."
        ),
    }
    dump(OUT / "manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
