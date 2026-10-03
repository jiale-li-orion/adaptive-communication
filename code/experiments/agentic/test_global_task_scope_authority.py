#!/usr/bin/env python3
"""Global Operational Task scope must come from deployment authority, not reports."""
from __future__ import annotations

from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from agentic_communication.action_context import ActionConditionedContextSelector  # noqa: E402
from agentic_communication.capabilities import CommunicationCapabilityCatalog  # noqa: E402
from agentic_communication.contracts import EvidenceWorldSnapshot  # noqa: E402
from agentic_communication.episodes import benchmark_episode_catalog  # noqa: E402
from agentic_communication.metrics import physical_signature  # noqa: E402
from agentic_communication.planner import ActionConditionedReferencePlannerConsumer  # noqa: E402
from agentic_communication.run import run_agentic_episode, run_reference_comply  # noqa: E402
from agentic_communication.task_compiler import CommunicationTaskCompiler  # noqa: E402
from agentic_communication.timebase import sim_datetime  # noqa: E402


def main() -> int:
    catalog = CommunicationCapabilityCatalog()
    o5 = benchmark_episode_catalog()["O5"]
    contract = CommunicationTaskCompiler().compile(o5.task, 0)
    visible = [cap.capability_id for cap in catalog.visible(contract)]
    assert "communication.center.full_dump" not in visible, visible

    resources = ["gw0", "n00", "n01"]
    empty = EvidenceWorldSnapshot.build(revision=1, observed_at_s=0, evidence=[])
    selection = ActionConditionedContextSelector().select(
        operational_task=o5.task,
        task=contract,
        task_run_id="test-global-scope",
        evidence_world=empty,
        capability_ids=visible,
        resource_ids=resources,
        recent_capability_outcomes=[],
        t_s=0,
        now=sim_datetime(0),
    )
    candidate = selection.candidate_context
    assert candidate["action_scope"] == resources, candidate["action_scope"]
    install = next(
        row
        for row in candidate["candidate_plans"]
        if row["plan_id"] == "install_required_profile"
    )
    assert install["feasibility"] == "supported", install
    assert install["affected_resources"] == resources, install
    assert len(install["invocations"]) == 2 * len(resources), install
    sufficiency = candidate["decision_sufficiency"]
    assert sufficiency["status"] == "sufficient_for_primary_action", sufficiency
    assert sufficiency["primary_plan_id"] == "install_required_profile", sufficiency

    # The declared candidate semantics are evaluator gold only if they reproduce
    # the benchmark's ordinary global comply semantics. Lock that identity over
    # multiple simulator seeds for both dynamic global tasks used in the main table.
    for episode_name in ("O5", "O6"):
        episode = benchmark_episode_catalog()[episode_name]
        for seed in range(5):
            legacy, _, _ = run_reference_comply(
                seed=seed,
                operational_task=episode.task,
                simulator_kwargs=episode.simulator_overrides,
            )
            candidate_run, _, _, _ = run_agentic_episode(
                seed=seed,
                operational_task=episode.task,
                context_mode="action_conditioned_compact",
                planner_consumer=ActionConditionedReferencePlannerConsumer(),
                planner_replan_mode="decision_state",
                simulator_kwargs=episode.simulator_overrides,
            )
            assert physical_signature(candidate_run) == physical_signature(legacy), (
                episode_name,
                seed,
                "candidate reference must preserve global Operational Task physics",
            )

    print(
        "PASS global task scope authority: inventory-defined scope, FullDump baseline-only, "
        "O5/O6 candidate reference == legacy across 5 seeds"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

