#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(os.path.dirname(HERE))
if CODE not in sys.path:
    sys.path.insert(0, CODE)

from agentic_communication.contracts import OperationalTask, OperationalTaskFamily, OperationalTaskPhase  # noqa: E402
from agentic_communication.episodes import benchmark_episode_catalog  # noqa: E402
from agentic_communication.metrics import physical_signature  # noqa: E402
from agentic_communication.planner import (  # noqa: E402
    ActionConditionedReferencePlannerConsumer,
    DeterministicComplyPlannerConsumer,
)
from agentic_communication.run import run_agentic_episode, run_reference_comply  # noqa: E402
from agentic_communication.runtime_contracts import (  # noqa: E402
    ModelUsage,
    PlannedCapabilityInvocation,
    PlannerDecision,
)


class SparseSemanticComplyPlannerConsumer:
    """Emit config effects only when TaskContract authority changes.

    Later model turns intentionally return stop=true. Runtime-owned persistent
    execution intent must continue ordinary admission/retry without requiring
    the planner to restate the same config plan every Context refresh.
    """

    provider = "runtime-test"
    model = "sparse-semantic-comply"
    consumer_id = "sparse-semantic-comply"

    def __init__(self) -> None:
        self.base = DeterministicComplyPlannerConsumer()
        self.last_contract_id: str | None = None
        self.effect_turns = 0
        self.noop_turns = 0

    @staticmethod
    def _fragment(assembly, kind: str):
        for fragment in assembly.fragments:
            if fragment.kind == kind:
                return fragment.content
        return {}

    def decide(self, request, assembly):
        task = self._fragment(assembly, "runtime_task_contract") or {}
        contract_id = str(task.get("task_contract_id", ""))
        if contract_id != self.last_contract_id:
            self.last_contract_id = contract_id
            decision, usage = self.base.decide(request, assembly)
            if any(
                invocation.capability_id.startswith("communication.config.")
                for invocation in decision.invocations
            ):
                self.effect_turns += 1
            return decision, usage

        self.noop_turns += 1
        return (
            PlannerDecision(
                decision_id=f"decision:{request.request_id}:no-semantic-change",
                request_id=request.request_id,
                stop=True,
                invocations=[],
                reason_codes=["no_semantic_plan_revision"],
            ),
            ModelUsage(),
        )


class QueryAfterPlanConsumer(SparseSemanticComplyPlannerConsumer):
    """Emit one observation-only turn after selecting a config plan."""

    model = "query-after-plan"
    consumer_id = "query-after-plan"

    def __init__(self) -> None:
        super().__init__()
        self.query_turns = 0

    def decide(self, request, assembly):
        task = self._fragment(assembly, "runtime_task_contract") or {}
        contract_id = str(task.get("task_contract_id", ""))
        if contract_id != self.last_contract_id:
            return super().decide(request, assembly)
        if self.query_turns == 0:
            self.query_turns += 1
            return (
                PlannerDecision(
                    decision_id=f"decision:{request.request_id}:observation-only",
                    request_id=request.request_id,
                    stop=False,
                    invocations=[
                        PlannedCapabilityInvocation(
                            capability_id="communication.gateway.primary_health",
                            resource="gw0",
                            canonical_arguments={"gateway_id": "gw0"},
                        )
                    ],
                    reason_codes=["observation_only_followup"],
                ),
                ModelUsage(),
            )
        return super().decide(request, assembly)


def main() -> int:
    task = OperationalTask(
        task_id="live-planner-smoke",
        family=OperationalTaskFamily.RISK_ESCALATION,
        phases=[
            OperationalTaskPhase(start_s=0, required_period_s=3600, level="blue"),
            OperationalTaskPhase(start_s=3600, required_period_s=300, level="yellow"),
        ],
        task_horizon_s=2 * 3600,
        authorized_effects=[
            "communication.config.set_sampling_interval",
            "communication.config.set_report_period",
        ],
    )
    sim = {
        "task_hours": 2,
        "tail_hours": 1,
        "harvest_mode": "uniform",
        "harvest_wh_per_hour": 3.0,
        "outage_hours": 0.0,
        "backhaul_p_good": 1.0,
        "enable_backup": True,
        "execution_feedback": True,
    }
    ref, _, _ = run_reference_comply(seed=0, operational_task=task, simulator_kwargs=sim)
    cur, policy, _, _ = run_agentic_episode(
        seed=0,
        operational_task=task,
        context_mode="task_conditioned",
        planner_consumer=DeterministicComplyPlannerConsumer(),
        simulator_kwargs=sim,
    )
    assert physical_signature(ref) == physical_signature(cur), "live planner boundary changed physics"
    summary = policy.trace_summary()
    assert summary["model_requests"] > 0, summary
    assert summary["model_requests"] == summary["model_attempts"] == summary["model_usage_records"]
    assert summary["planner_decisions"] == summary["model_requests"]

    sparse_consumer = SparseSemanticComplyPlannerConsumer()
    sparse, sparse_policy, _, _ = run_agentic_episode(
        seed=0,
        operational_task=task,
        context_mode="task_conditioned",
        planner_consumer=sparse_consumer,
        simulator_kwargs=sim,
    )
    assert physical_signature(ref) == physical_signature(sparse), (
        "persistent config intent must preserve comply physics when later model turns "
        "do not restate the semantic plan"
    )
    assert sparse_consumer.effect_turns == 2, sparse_consumer.effect_turns
    assert sparse_consumer.noop_turns > 0, sparse_consumer.noop_turns
    assert all(
        target in {300, 3600}
        for wants in sparse_policy._persistent_config_intent.values()
        for target in wants.values()
    ), sparse_policy._persistent_config_intent

    query_consumer = QueryAfterPlanConsumer()
    query_run, _, _, _ = run_agentic_episode(
        seed=0,
        operational_task=task,
        context_mode="task_conditioned",
        planner_consumer=query_consumer,
        simulator_kwargs=sim,
    )
    assert query_consumer.query_turns == 1
    assert physical_signature(ref) == physical_signature(query_run), (
        "an observation-only planner turn must not cancel unrelated persistent config intent"
    )

    for episode_name in ("O5", "O6"):
        episode = benchmark_episode_catalog()[episode_name]
        every_result, every_policy, _, _ = run_agentic_episode(
            seed=0,
            operational_task=episode.task,
            context_mode="action_conditioned_compact",
            planner_consumer=ActionConditionedReferencePlannerConsumer(),
            planner_replan_mode="every_context",
            simulator_kwargs=episode.simulator_overrides,
        )
        gated_result, gated_policy, _, _ = run_agentic_episode(
            seed=0,
            operational_task=episode.task,
            context_mode="action_conditioned_compact",
            planner_consumer=ActionConditionedReferencePlannerConsumer(),
            planner_replan_mode="decision_state",
            simulator_kwargs=episode.simulator_overrides,
        )
        assert physical_signature(every_result) == physical_signature(gated_result), episode_name
        assert gated_policy.trace_summary()["model_requests"] < every_policy.trace_summary()[
            "model_requests"
        ], episode_name

        shared_rows = []
        for context_mode in (
            "task_conditioned",
            "full_dump",
            "generic_react",
            "action_conditioned_compact",
        ):
            shared_result, shared_policy, _, _ = run_agentic_episode(
                seed=0,
                operational_task=episode.task,
                context_mode=context_mode,
                planner_consumer=DeterministicComplyPlannerConsumer(),
                planner_replan_mode="decision_state",
                simulator_kwargs=episode.simulator_overrides,
            )
            shared_rows.append(
                (
                    context_mode,
                    shared_policy.trace_summary()["model_requests"],
                    physical_signature(shared_result),
                )
            )
            semantic_refs = [
                event
                for event in shared_policy.trace.events
                if event.event_type == "planner_semantic_reference"
            ]
            assert semantic_refs, (episode_name, context_mode, "missing shared semantic reference")
            assert all(
                event.payload.get("source") == "hidden_shared_candidate_surface"
                for event in semantic_refs
            ), (episode_name, context_mode)
            if context_mode != "action_conditioned_compact":
                for event in shared_policy.trace.events:
                    if event.event_type != "prompt_assembly":
                        continue
                    kinds = {
                        row.get("kind")
                        for row in event.payload.get("fragments", [])
                        if isinstance(row, dict)
                    }
                    assert "candidate_action_context" not in kinds, (
                        episode_name,
                        context_mode,
                        "hidden semantic reference leaked into model Context",
                    )
        expected_calls = shared_rows[0][1]
        expected_signature = shared_rows[0][2]
        assert all(row[1] == expected_calls for row in shared_rows), shared_rows
        assert all(row[2] == expected_signature for row in shared_rows), shared_rows
    print("PASS live PlannerConsumer: typed model ledger + physical equivalence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
