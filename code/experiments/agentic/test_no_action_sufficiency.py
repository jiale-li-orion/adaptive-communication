#!/usr/bin/env python3
"""Compact control projection must mark closed zero-effect states as sufficient."""
from __future__ import annotations

from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from agentic_communication.episodes import benchmark_episode_catalog  # noqa: E402
from agentic_communication.planner import DeterministicComplyPlannerConsumer  # noqa: E402
from agentic_communication.run import run_agentic_episode  # noqa: E402


def main() -> int:
    episode = benchmark_episode_catalog()["O6"]
    _, policy, _, _ = run_agentic_episode(
        seed=1,
        operational_task=episode.task,
        context_mode="action_conditioned_compact",
        planner_consumer=DeterministicComplyPlannerConsumer(),
        planner_replan_mode="decision_state",
        simulator_kwargs=episode.simulator_overrides,
    )

    rows = []
    for event in policy.trace.events:
        if event.event_type != "prompt_assembly" or int(event.t_s) != 3660:
            continue
        fragments = {
            row.get("kind"): row.get("content")
            for row in event.payload.get("fragments", [])
            if isinstance(row, dict)
        }
        candidate = fragments.get("candidate_action_context") or {}
        rows.append((candidate, fragments.get("evidence_needs") or []))

    assert rows, "expected O6 seed1 t=3660 compact prompt"
    for candidate, needs in rows:
        sufficiency = candidate.get("decision_sufficiency") or {}
        assert sufficiency.get("status") == "sufficient_for_no_action", sufficiency
        assert sufficiency.get("primary_plan_id") == "hold_current_profile", sufficiency
        assert sufficiency.get("blocking_need_ids") == [], sufficiency
        assert needs == [], needs
        visible = {
            row.get("plan_id"): row
            for row in candidate.get("candidate_plans", [])
            if isinstance(row, dict)
        }
        assert visible["hold_current_profile"]["feasibility"] == "supported", visible
        assert visible["hold_current_profile"].get("invocations") == [], visible
        assert visible["install_required_profile"]["feasibility"] == "dominated", visible

    print(
        "PASS no-action sufficiency: O6 seed1 t=3660 compact surface selects hold, "
        "has no blocking needs, and is not labeled undetermined"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

