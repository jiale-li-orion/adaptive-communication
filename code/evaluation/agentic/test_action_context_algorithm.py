#!/usr/bin/env python3
"""Unit-level semantics for action-conditioned Context contraction/expansion."""
from __future__ import annotations

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from agentic_communication.action_context import ActionConditionedContextSelector  # noqa: E402
from agentic_communication.capabilities import CommunicationCapabilityCatalog  # noqa: E402
from agentic_communication.context_runtime import CommunicationContextRuntime  # noqa: E402
from agentic_communication.contracts import (  # noqa: E402
    CommunicationEvidence,
    EvidenceStatus,
    EvidenceWorldSnapshot,
)
from agentic_communication.episodes import (  # noqa: E402
    o2_prealert_risk_escalation_task,
    o3_backhaul_outage_sustainment_task,
    o5_recovery_reconciliation_task,
    o6_compound_long_horizon_task,
)
from agentic_communication.task_compiler import CommunicationTaskCompiler  # noqa: E402
from agentic_communication.timebase import sim_datetime  # noqa: E402


def ev(
    prop: str,
    subject: str,
    value: dict,
    t_s: int,
    idx: int,
    *,
    owner: str = "center",
    generated_at_s: int | None = None,
) -> CommunicationEvidence:
    return CommunicationEvidence(
        evidence_id=f"test:{idx}:{prop}:{subject}",
        proposition=prop,
        subject_ref=subject,
        value=value,
        source_id="test",
        source_role=owner,
        owner_location=owner,
        generated_at_s=t_s if generated_at_s is None else generated_at_s,
        observed_at_s=t_s,
        world_revision=1,
        status=EvidenceStatus.CURRENT,
    )


def select(task, *, t_s: int, evidence: list[CommunicationEvidence], resources: list[str]):
    snapshot = EvidenceWorldSnapshot.build(revision=1, observed_at_s=t_s, evidence=evidence)
    contract = CommunicationTaskCompiler().compile(task, t_s)
    caps = CommunicationCapabilityCatalog()
    return ActionConditionedContextSelector().select(
        operational_task=task,
        task=contract,
        task_run_id="test-run",
        evidence_world=snapshot,
        capability_ids=[c.capability_id for c in caps.visible(contract)],
        resource_ids=resources,
        recent_capability_outcomes=[],
        t_s=t_s,
        now=sim_datetime(t_s),
    )


def plan(selection, plan_id: str) -> dict:
    return next(p for p in selection.candidate_context["candidate_plans"] if p["plan_id"] == plan_id)


def main() -> int:
    # Future-effective O2 notice: the runtime TaskContract changes at notice
    # time, and only then does the selector open preparation dependencies.
    prealert = o2_prealert_risk_escalation_task(notice_at_s=2 * 3600)
    compiler = CommunicationTaskCompiler()
    before_contract = compiler.compile(prealert, 1 * 3600)
    announced_contract = compiler.compile(prealert, 3 * 3600)
    assert before_contract.task_contract_id == "communication:o2-prealert-risk-escalation-v1:phase:0"
    assert announced_contract.task_contract_id.endswith(":phase:0:announced:1")
    assert not before_contract.desired_state.get("announced_future_phases")
    assert announced_contract.desired_state["announced_future_phases"][0]["effective_at_s"] == 6 * 3600

    before_notice = select(
        prealert,
        t_s=1 * 3600,
        resources=["n00", "n01"],
        evidence=[],
    )
    assert not {
        "wait_for_future_task_effective",
        "prepare_future_profile",
    } & {p["plan_id"] for p in before_notice.candidate_context["candidate_plans"]}

    after_notice = select(
        prealert,
        t_s=3 * 3600,
        resources=["n00", "n01"],
        evidence=[
            ev(
                "communication.center.node_report",
                nid,
                {"sample_interval_s": 3600, "report_period_s": 3600},
                3 * 3600,
                10 + i,
            )
            for i, nid in enumerate(("n00", "n01"))
        ],
    )
    prealert_ids = {p["plan_id"] for p in after_notice.candidate_context["candidate_plans"]}
    assert {"wait_for_future_task_effective", "prepare_future_profile"} <= prealert_ids
    prep_deps = [
        row for row in after_notice.candidate_context["dependencies"]
        if row["scope_reason"].startswith("preparation_")
    ]
    assert {(row["proposition"], row["subject"]) for row in prep_deps} == {
        ("communication.gateway.node_report", "n00"),
        ("communication.gateway.node_report", "n01"),
        ("communication.gateway.receipt_summary", "gw0"),
    }
    assert all(row["acquisition"] == "active_capability" for row in prep_deps)
    assert any(
        need.proposition_or_question
        == "What is the current communication.gateway.node_report for n00?"
        for need in after_notice.needs
    )

    with_gateway = select(
        prealert,
        t_s=3 * 3600,
        resources=["n00", "n01"],
        evidence=[
            ev(
                "communication.center.node_report",
                nid,
                {"sample_interval_s": 3600, "report_period_s": 3600},
                3 * 3600,
                20 + i,
            )
            for i, nid in enumerate(("n00", "n01"))
        ]
        + [
            ev(
                "communication.gateway.node_report",
                nid,
                {
                    "soc_wh": 0.04,
                    "sample_interval_s": 3600,
                    "report_period_s": 3600,
                    "read_at": 3 * 3600 - 60,
                },
                3 * 3600,
                30 + i,
                owner="gateway",
                generated_at_s=3 * 3600 - 60,
            )
            for i, nid in enumerate(("n00", "n01"))
        ]
        + [
            ev(
                "communication.gateway.receipt_summary",
                "gw0",
                {"heard_nodes": ["n00", "n01"]},
                3 * 3600,
                40,
                owner="gateway",
            )
        ],
    )
    assert not [
        n for n in with_gateway.needs
        if "communication.gateway.node_report" in n.proposition_or_question
        or "communication.gateway.receipt_summary" in n.proposition_or_question
    ]
    assert with_gateway.candidate_context["candidate_disagreement"]["action_closure"]["control_eligibility"] \
        == "shadow_only_until_preparation_guard_executor"

    # O5 healthy delivery: passive evidence closes the fallback branch, so the
    # shared gateway dependency never enters Context.
    healthy_t = 3 * 3600
    o5 = o5_recovery_reconciliation_task().model_copy(
        update={"task_id": "test-o5-local-n02", "target_node_ids": ["n02"]}
    )
    healthy = select(
        o5,
        t_s=healthy_t,
        resources=["n02", "n03"],
        evidence=[
            ev(
                "communication.center.node_report",
                "n02",
                {"sample_interval_s": 3600, "report_period_s": 3600},
                healthy_t,
                1,
            ),
            ev(
                "communication.center.delivery_status",
                "n02",
                {"newest_taken_at": healthy_t - 60},
                healthy_t,
                2,
            ),
        ],
    )
    assert plan(healthy, "consider_gateway_backup")["feasibility"] == "dominated"
    assert not any(
        row["scope_reason"] == "shared_gateway_path"
        for row in healthy.candidate_context["dependencies"]
    )
    assert set(healthy.candidate_context["evidence_scope"]) == {"n02"}

    # O5 delivery deficit: the fallback branch becomes live and opens the two
    # gateway-owner evidence needs without changing action authority.
    deficit_t = 4 * 3600
    deficit = select(
        o5,
        t_s=deficit_t,
        resources=["n02", "n03"],
        evidence=[
            ev(
                "communication.center.node_report",
                "n02",
                {"sample_interval_s": 3600, "report_period_s": 3600},
                deficit_t,
                3,
            ),
            ev(
                "communication.center.delivery_status",
                "n02",
                {"newest_taken_at": deficit_t - 1200},
                deficit_t,
                4,
            ),
        ],
    )
    assert plan(deficit, "consider_gateway_backup")["feasibility"] == "conditional"
    shared = [
        row
        for row in deficit.candidate_context["dependencies"]
        if row["scope_reason"] == "shared_gateway_path"
    ]
    assert len(shared) == 2 and all(row["subject"] == "gw0" for row in shared)
    assert {n.proposition_or_question for n in deficit.needs} >= {
        "What is the current communication.gateway.primary_health for gw0?",
        "What is the current communication.gateway.receipt_summary for gw0?",
    }
    # O5: the current 300 s Task profile still needs installation.  Gateway
    # evidence only gates the optional fallback branch, so it must not delay the
    # already-supported configuration action.
    o5_suff = deficit.candidate_context["decision_sufficiency"]
    assert o5_suff["status"] == "sufficient_for_primary_action", o5_suff
    assert o5_suff["primary_plan_id"] == "install_required_profile", o5_suff
    assert not o5_suff["blocking_need_ids"], o5_suff
    assert len(o5_suff["nonblocking_open_need_ids"]) == 2, o5_suff

    # O3 is the complementary safety case.  The required profile is already
    # installed, while delivery deficit keeps fallback live.  There is no
    # supported effect plan to execute, so the same gateway evidence remains
    # decision-relevant and Decision Sufficiency must stay undetermined.
    o3 = o3_backhaul_outage_sustainment_task().model_copy(
        update={"task_id": "test-o3-local-n02", "target_node_ids": ["n02"]}
    )
    o3_live_fallback = select(
        o3,
        t_s=5 * 3600,
        resources=["n02", "n03"],
        evidence=[
            ev(
                "communication.center.node_report",
                "n02",
                {"sample_interval_s": 3600, "report_period_s": 3600},
                5 * 3600,
                41,
            ),
            ev(
                "communication.center.delivery_status",
                "n02",
                {"newest_taken_at": 5 * 3600 - 7200},
                5 * 3600,
                42,
            ),
        ],
    )
    assert plan(o3_live_fallback, "hold_current_profile")["feasibility"] == "supported"
    assert plan(o3_live_fallback, "install_required_profile")["feasibility"] == "dominated"
    assert plan(o3_live_fallback, "consider_gateway_backup")["feasibility"] == "conditional"
    o3_suff = o3_live_fallback.candidate_context["decision_sufficiency"]
    assert o3_suff["status"] == "undetermined", o3_suff
    assert o3_suff["primary_plan_id"] is None, o3_suff
    assert {tuple(n.blocking_plan_ids) for n in o3_live_fallback.needs} >= {
        ("consider_gateway_backup",),
    }

    # Localized O6: target n02 can legitimately need peer evidence when an
    # access-assist alternative depends on a shared access-path pattern.
    o6 = o6_compound_long_horizon_task().model_copy(
        update={"task_id": "test-o6-local-n02", "target_node_ids": ["n02"]}
    )
    expanded = select(
        o6,
        t_s=6 * 3600,
        resources=["n02", "n03"],
        evidence=[
            ev(
                "communication.center.node_report",
                "n02",
                {"sample_interval_s": 3600, "report_period_s": 3600},
                6 * 3600,
                5,
            ),
            ev(
                "communication.center.delivery_status",
                "n02",
                {"newest_taken_at": 6 * 3600 - 1200},
                6 * 3600,
                6,
            ),
            ev(
                "communication.center.delivery_status",
                "n03",
                {"newest_taken_at": 6 * 3600 - 60},
                6 * 3600,
                7,
            ),
            ev(
                "communication.center.link_summary",
                "monitoring-network",
                {"heard_nodes": ["n02", "n03"], "n_reports": 2},
                6 * 3600,
                8,
            ),
        ],
    )
    assert expanded.candidate_context["action_scope"] == ["n02"]
    assert "n03" in expanded.candidate_context["evidence_scope"]
    assert any(
        row["scope_reason"] == "shared_access_peer_expansion" and row["subject"] == "n03"
        for row in expanded.candidate_context["dependencies"]
    )
    assert expanded.candidate_context["candidate_disagreement"]["plan_pairs"]
    assert (
        expanded.candidate_context["candidate_disagreement"]["action_closure"]["control_eligibility"]
        == "shadow_only_until_composed_candidate_closure"
    )
    compact = CommunicationContextRuntime._compact_candidate_projection(
        expanded.candidate_context
    )
    compact_plan_ids = {row["plan_id"] for row in compact["candidate_plans"]}
    assert "consider_access_assist" not in compact_plan_ids, compact
    assert "consider_terminal_dts" not in compact_plan_ids, compact
    assert set(compact["shadow_candidate_plan_ids"]) >= {
        "consider_access_assist",
        "consider_terminal_dts",
    }
    assert not [
        row
        for row in compact["unresolved_dependencies"]
        if row["scope_reason"] in {"shared_access_path", "shared_access_peer_expansion"}
    ], compact
    compact_needs = CommunicationContextRuntime._control_relevant_needs(
        expanded.candidate_context,
        expanded.needs,
    )
    assert not [
        need
        for need in compact_needs
        if set(need.blocking_plan_ids)
        <= {"consider_gateway_backup", "consider_terminal_dts", "consider_access_assist"}
    ], compact_needs
    print("PASS action-context algorithm: passive contraction, shared-path expansion, candidate disagreement")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
