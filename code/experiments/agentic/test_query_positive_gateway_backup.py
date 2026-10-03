#!/usr/bin/env python3
"""Three-state conformance for the query-positive gateway-backup compiler."""
from __future__ import annotations

from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from agentic_communication.contracts import (  # noqa: E402
    CommunicationEvidence,
    EvidenceStatus,
    EvidenceWorldSnapshot,
)
from agentic_communication.episodes import benchmark_episode_catalog  # noqa: E402
from agentic_communication.query_positive import (  # noqa: E402
    GATEWAY_BACKUP_PLAN_ID,
    GatewayBackupQueryPositiveSelector,
    QueryPositiveContextRuntime,
)
from agentic_communication.task_compiler import CommunicationTaskCompiler  # noqa: E402
from agentic_communication.timebase import sim_datetime  # noqa: E402


T_S = 7200
PERIOD = 3600
CAPABILITIES = [
    "communication.center.node_report",
    "communication.center.delivery_status",
    "communication.config.set_sampling_interval",
    "communication.config.set_report_period",
    "communication.gateway.primary_health",
    "communication.gateway.receipt_summary",
    "communication.fallback.gateway_backup",
    "communication.fallback.terminal_dts",
]


def _evidence(
    idx: int,
    proposition: str,
    subject: str,
    value,
    *,
    source_role: str,
    owner: str,
) -> CommunicationEvidence:
    return CommunicationEvidence(
        evidence_id=f"query-positive-e{idx}",
        proposition=proposition,
        subject_ref=subject,
        value=value,
        source_id=f"query-positive-source-{idx}",
        source_role=source_role,
        owner_location=owner,
        observed_at_s=T_S,
        world_revision=1,
        status=EvidenceStatus.CURRENT,
        freshness={"basis": "query-positive-conformance"},
        provenance={"surface": "query-positive-conformance"},
    )


def _task():
    base = benchmark_episode_catalog()["O3"].task
    metadata = dict(base.metadata)
    metadata["benchmark_pre_enabled_effects"] = []
    return base.model_copy(
        update={
            "task_id": "o3-query-positive-conformance",
            "target_node_ids": ["n02"],
            "metadata": metadata,
        }
    )


def _base_rows():
    return [
        _evidence(
            1,
            "communication.center.node_report",
            "n02",
            {"sample_interval_s": PERIOD, "report_period_s": PERIOD},
            source_role="center",
            owner="center",
        ),
        _evidence(
            2,
            "communication.center.delivery_status",
            "n02",
            {"newest_taken_at": 0},
            source_role="center",
            owner="center",
        ),
    ]


def _select(extra):
    task = _task()
    contract = CommunicationTaskCompiler().compile(task, T_S)
    snapshot = EvidenceWorldSnapshot.build(
        revision=1,
        observed_at_s=T_S,
        evidence=[*_base_rows(), *extra],
    )
    selector = GatewayBackupQueryPositiveSelector()
    return selector.select(
        operational_task=task,
        task=contract,
        task_run_id="run:query-positive-conformance",
        evidence_world=snapshot,
        capability_ids=CAPABILITIES,
        resource_ids=["n02", "gw0"],
        recent_capability_outcomes=[],
        t_s=T_S,
        now=sim_datetime(T_S),
    )


def _plan(selection, plan_id):
    return next(
        row for row in selection.candidate_context["candidate_plans"] if row["plan_id"] == plan_id
    )


def _project(selection):
    runtime = QueryPositiveContextRuntime()
    needs = runtime._control_relevant_needs(selection.candidate_context, selection.needs)
    return runtime._compact_candidate_projection(
        selection.candidate_context,
        needs,
        retire_inactive_unresolved=True,
    ), needs


def main() -> int:
    # 1) Before owner evidence: the branch is genuinely live and queryable.
    before = _select([])
    backup = _plan(before, GATEWAY_BACKUP_PLAN_ID)
    assert backup["feasibility"] == "conditional", backup
    assert before.candidate_context["query_positive_gateway_backup"]["guard_result"] == "needs_evidence"
    compact, needs = _project(before)
    assert {n.blocking_plan_ids[0] for n in needs} == {GATEWAY_BACKUP_PLAN_ID}
    assert len(needs) == 2, needs
    visible_ids = {row["plan_id"] for row in compact["candidate_plans"]}
    assert GATEWAY_BACKUP_PLAN_ID in visible_ids, visible_ids
    assert "consider_terminal_dts" not in visible_ids, visible_ids
    assert compact["decision_sufficiency"]["status"] == "undetermined", compact

    # 2) Negative query result: no gateway backlog => backup is rejected and a
    #    supported hold becomes decision-complete.
    negative = _select(
        [
            _evidence(
                3,
                "communication.gateway.primary_health",
                "gw0",
                {
                    "last_forward_ok_at": T_S,
                    "pending_depth": 0,
                    "oldest_pending_age_s": None,
                    "query_path_reachable": True,
                },
                source_role="gateway",
                owner="gateway",
            ),
            _evidence(
                4,
                "communication.gateway.receipt_summary",
                "gw0",
                {"heard_nodes": ["n02"], "report_at": {"n02": T_S}},
                source_role="gateway",
                owner="gateway",
            ),
        ]
    )
    backup = _plan(negative, GATEWAY_BACKUP_PLAN_ID)
    assert backup["feasibility"] == "rejected", backup
    assert negative.candidate_context["query_positive_gateway_backup"]["guard_result"] == "rejected"
    compact, needs = _project(negative)
    assert not needs, needs
    assert compact["decision_sufficiency"]["status"] == "sufficient_for_no_action", compact
    assert compact["decision_sufficiency"]["primary_plan_id"] == "hold_current_profile", compact

    # 3) Positive query result: gateway has received data but primary backlog has
    #    aged at least one Task period => backup becomes the unique ready effect.
    positive = _select(
        [
            _evidence(
                5,
                "communication.gateway.primary_health",
                "gw0",
                {
                    "last_forward_ok_at": 0,
                    "pending_depth": 18,
                    "oldest_pending_age_s": PERIOD,
                    "query_path_reachable": True,
                },
                source_role="gateway",
                owner="gateway",
            ),
            _evidence(
                6,
                "communication.gateway.receipt_summary",
                "gw0",
                {"heard_nodes": ["n02"], "report_at": {"n02": T_S - PERIOD}},
                source_role="gateway",
                owner="gateway",
            ),
        ]
    )
    backup = _plan(positive, GATEWAY_BACKUP_PLAN_ID)
    hold = _plan(positive, "hold_current_profile")
    assert backup["feasibility"] == "supported", backup
    assert hold["feasibility"] == "dominated", hold
    assert positive.candidate_context["query_positive_gateway_backup"]["guard_result"] == "supported"
    compact, needs = _project(positive)
    assert not needs, needs
    assert compact["decision_sufficiency"]["status"] == "sufficient_for_primary_action", compact
    assert compact["decision_sufficiency"]["primary_plan_id"] == GATEWAY_BACKUP_PLAN_ID, compact

    print(
        "PASS query-positive gateway backup: conditional+2 needs -> negative hold closure / "
        "positive backup closure; terminal fallback remains shadow"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

