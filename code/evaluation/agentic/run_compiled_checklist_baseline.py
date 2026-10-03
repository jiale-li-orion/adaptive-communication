#!/usr/bin/env python3
"""Run the ordinary compiled-checklist strong baseline over the v6 task set."""
from __future__ import annotations

import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
ROOT = HERE.parents[2]
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from agentic_communication.episodes import (  # noqa: E402
    benchmark_episode_catalog,
    o2_localized_risk_escalation_task,
)
from agentic_communication.metrics import (  # noqa: E402
    communication_metrics,
    metric_delta,
    physical_signature,
)
from agentic_communication.planner import CompiledChecklistPlannerConsumer  # noqa: E402
from agentic_communication.run import run_agentic_episode, run_reference_comply  # noqa: E402


OUT = ROOT / "results" / "agentic" / "compiled-checklist-v1" / "result.json"


def _tasks():
    catalog = benchmark_episode_catalog()
    return (
        ("localized-o2", o2_localized_risk_escalation_task(), {}),
        ("o5", catalog["O5"].task, catalog["O5"].simulator_overrides),
        ("o6", catalog["O6"].task, catalog["O6"].simulator_overrides),
    )


def _prompt_activation(policy) -> dict:
    assemblies: dict[str, dict] = {}
    requested_assembly_ids: list[str] = []
    for event in policy.trace.events:
        if event.event_type == "prompt_assembly":
            assembly_id = str(event.payload.get("assembly_id") or "")
            if not assembly_id:
                continue
            fragments = {
                row.get("kind"): row.get("content")
                for row in event.payload.get("fragments", [])
                if isinstance(row, dict)
            }
            candidate = fragments.get("candidate_action_context") or {}
            plans = [row for row in candidate.get("candidate_plans", []) if isinstance(row, dict)]
            ready = [
                row
                for row in plans
                if row.get("feasibility") == "supported"
                and not bool(row.get("unresolved_conditions"))
            ]
            visible_needs = [
                row
                for row in (fragments.get("evidence_needs") or [])
                if isinstance(row, dict)
            ]
            assemblies[assembly_id] = {
                "t_s": int(event.t_s),
                "ready_supported_plan_ids": [str(row.get("plan_id")) for row in ready],
                "visible_evidence_need_ids": [str(row.get("need_id")) for row in visible_needs],
            }
        elif event.event_type == "model_request":
            assembly_id = str(event.payload.get("assembly_id") or "")
            if assembly_id:
                requested_assembly_ids.append(assembly_id)

    rows = [assemblies[assembly_id] for assembly_id in requested_assembly_ids if assembly_id in assemblies]
    return {
        "planner_requests": len(requested_assembly_ids),
        "matched_request_assemblies": len(rows),
        "rows_with_exactly_one_ready_supported_plan": sum(
            len(row["ready_supported_plan_ids"]) == 1 for row in rows
        ),
        "rows_with_visible_evidence_need": sum(
            bool(row["visible_evidence_need_ids"]) for row in rows
        ),
        "rows_with_ambiguous_ready_plans": sum(
            len(row["ready_supported_plan_ids"]) > 1 for row in rows
        ),
        "rows_with_no_ready_plan": sum(
            len(row["ready_supported_plan_ids"]) == 0 for row in rows
        ),
    }


def main() -> int:
    episodes = []
    all_physical_equal = True
    for task_name, task, simulator_kwargs in _tasks():
        for seed in range(5):
            result, policy, _, _ = run_agentic_episode(
                seed=seed,
                operational_task=task,
                context_mode="action_conditioned_compact",
                planner_consumer=CompiledChecklistPlannerConsumer(),
                planner_replan_mode="decision_state",
                simulator_kwargs=simulator_kwargs,
            )
            legacy, _, _ = run_reference_comply(
                seed=seed,
                operational_task=task,
                simulator_kwargs=simulator_kwargs,
            )
            equal = physical_signature(result) == physical_signature(legacy)
            all_physical_equal = all_physical_equal and equal
            activation = _prompt_activation(policy)
            trace_summary = policy.trace_summary()
            episodes.append(
                {
                    "task": task_name,
                    "seed": seed,
                    "physical_equal_legacy": equal,
                    "communication_metrics": communication_metrics(result),
                    "delta_vs_legacy": metric_delta(
                        communication_metrics(result), communication_metrics(legacy)
                    ),
                    "planner_requests": int(trace_summary.get("model_requests") or 0),
                    "capability_requests": int(trace_summary.get("capability_requests") or 0),
                    "activation": activation,
                }
            )

    aggregate = {
        "experiment": "compiled-checklist-v1",
        "context_mode": "action_conditioned_compact",
        "consumer": "compiled-checklist-v1",
        "seeds": list(range(5)),
        "tasks": [name for name, _, _ in _tasks()],
        "episodes": len(episodes),
        "all_physical_equal_legacy": all_physical_equal,
        "physical_equal_legacy_count": sum(row["physical_equal_legacy"] for row in episodes),
        "planner_requests": sum(row["activation"]["planner_requests"] for row in episodes),
        "matched_request_assemblies": sum(
            row["activation"]["matched_request_assemblies"] for row in episodes
        ),
        "rows_with_exactly_one_ready_supported_plan": sum(
            row["activation"]["rows_with_exactly_one_ready_supported_plan"] for row in episodes
        ),
        "rows_with_visible_evidence_need": sum(
            row["activation"]["rows_with_visible_evidence_need"] for row in episodes
        ),
        "rows_with_ambiguous_ready_plans": sum(
            row["activation"]["rows_with_ambiguous_ready_plans"] for row in episodes
        ),
        "rows_with_no_ready_plan": sum(
            row["activation"]["rows_with_no_ready_plan"] for row in episodes
        ),
    }
    payload = {"aggregate": aggregate, "episodes": episodes}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(aggregate, ensure_ascii=False, indent=2))
    print(f"WROTE {OUT}")
    return 0 if all_physical_equal else 2


if __name__ == "__main__":
    raise SystemExit(main())

