#!/usr/bin/env python3
"""Model may select a Runtime candidate plan without copying its invocations."""
from __future__ import annotations

from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from agentic_communication.episodes import benchmark_episode_catalog  # noqa: E402
from agentic_communication.metrics import physical_signature  # noqa: E402
from agentic_communication.planner import _expand_selected_candidate_plan  # noqa: E402
from agentic_communication.run import run_agentic_episode, run_reference_comply  # noqa: E402
from agentic_communication.runtime_contracts import (  # noqa: E402
    FragmentCacheClass,
    FragmentTrustClass,
    MaterializedFragment,
    ModelUsage,
    PlannerDecision,
    PromptAssembly,
)


class PlanIdReferenceConsumer:
    consumer_id = "plan-id-reference"
    provider = "test"
    model = "plan-id-reference"

    @staticmethod
    def _candidate(assembly) -> dict:
        for fragment in assembly.fragments:
            if fragment.kind == "candidate_action_context":
                return dict(fragment.content)
        raise AssertionError("candidate_action_context missing")

    def decide(self, request, assembly):
        candidate = self._candidate(assembly)
        sufficiency = candidate.get("decision_sufficiency") or {}
        plan_id = sufficiency.get("primary_plan_id")
        if plan_id:
            selected = next(
                row
                for row in candidate.get("candidate_plans", [])
                if row.get("plan_id") == plan_id
            )
            zero_effect = not (selected.get("invocations") or [])
            # Deliberately return zero explicit invocations. invoke_consumer must
            # expand the Runtime-owned candidate plan after model output ledgering.
            return (
                PlannerDecision(
                    decision_id=f"decision:{request.request_id}:plan-id",
                    request_id=request.request_id,
                    stop=zero_effect,
                    selected_plan_id=str(plan_id),
                    invocations=[],
                    reason_codes=["select_runtime_candidate_plan"],
                ),
                ModelUsage(),
            )
        return (
            PlannerDecision(
                decision_id=f"decision:{request.request_id}:stop",
                request_id=request.request_id,
                stop=True,
                invocations=[],
                reason_codes=["no_supported_effect_plan"],
            ),
            ModelUsage(),
        )


def main() -> int:
    episode = benchmark_episode_catalog()["O5"]
    legacy, _, _ = run_reference_comply(
        seed=0,
        operational_task=episode.task,
        simulator_kwargs=episode.simulator_overrides,
    )
    result, policy, _, _ = run_agentic_episode(
        seed=0,
        operational_task=episode.task,
        context_mode="action_conditioned_compact",
        planner_consumer=PlanIdReferenceConsumer(),
        planner_replan_mode="decision_state",
        simulator_kwargs=episode.simulator_overrides,
    )
    assert physical_signature(result) == physical_signature(legacy)

    selected = [
        event
        for event in policy.trace.events
        if event.event_type == "planner_decision"
        and event.payload.get("selected_plan_id") == "install_required_profile"
    ]
    assert selected, "expected at least one plan-id selection"
    assert all(event.payload.get("invocations") for event in selected), (
        "Runtime must expand selected candidate plan before execution trace"
    )
    assert any(len(event.payload["invocations"]) >= 18 for event in selected), (
        "large global plan should be expanded without model-side enumeration"
    )
    hold_fragment = MaterializedFragment.build(
        kind="candidate_action_context",
        source_ref="test:candidate",
        source_revision="1",
        trust_class=FragmentTrustClass.RUNTIME_CONTROL,
        cache_class=FragmentCacheClass.STATE_DYNAMIC,
        content={
            "candidate_plans": [
                {
                    "plan_id": "hold_current_profile",
                    "kind": "hold",
                    "feasibility": "supported",
                    "unresolved_conditions": [],
                    "invocations": [],
                },
                {
                    "plan_id": "install_required_profile",
                    "kind": "install",
                    "feasibility": "supported",
                    "unresolved_conditions": [],
                    "invocations": [
                        {
                            "capability_id": "communication.config.set_report_period",
                            "resource": "n00",
                            "canonical_arguments": {"target_s": 3600},
                        }
                    ],
                },
            ]
        },
    )
    assembly = PromptAssembly.build(
        task_contract_id="task:test",
        task_run_id="run:test",
        context_manifest_revision=1,
        fragments=[hold_fragment],
    )
    hold = PlannerDecision(
        decision_id="decision:hold",
        request_id="request:hold",
        stop=True,
        selected_plan_id="hold_current_profile",
        invocations=[],
    )
    expanded_hold = _expand_selected_candidate_plan(hold, assembly)
    assert expanded_hold.stop is True
    assert expanded_hold.selected_plan_id == "hold_current_profile"
    assert expanded_hold.invocations == []

    effect_stop = PlannerDecision(
        decision_id="decision:install-stop",
        request_id="request:install-stop",
        stop=True,
        selected_plan_id="install_required_profile",
        invocations=[],
    )
    try:
        _expand_selected_candidate_plan(effect_stop, assembly)
    except ValueError as exc:
        assert "cannot be combined with stop=true" in str(exc)
    else:
        raise AssertionError("effect-bearing candidate must reject stop=true")
    print(
        "PASS candidate plan selection: plan-id-only semantic choice expands to typed effects "
        "and preserves O5 legacy physics"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

