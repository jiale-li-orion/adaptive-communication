#!/usr/bin/env python3
"""Audit the current natural query-positive coverage gap for gateway fallback.

The diagnostic uses only already-registered capabilities and their public value
schema.  It does not create a hidden random guard or modify the benchmark.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
ROOT = HERE.parents[2]
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from agentic_communication.action_context import ActionConditionedContextSelector  # noqa: E402
from agentic_communication.contracts import (  # noqa: E402
    CommunicationEvidence,
    EvidenceStatus,
    EvidenceWorldSnapshot,
)
from agentic_communication.episodes import o3_backhaul_outage_sustainment_task  # noqa: E402
from agentic_communication.task_compiler import CommunicationTaskCompiler  # noqa: E402
from agentic_communication.timebase import sim_datetime  # noqa: E402


OUT = ROOT / "results" / "agentic" / "query-positive-closure-gap-v1.json"
T_S = 5 * 3600


def _ev(
    evidence_id: str,
    proposition: str,
    subject: str,
    value,
    *,
    source_role: str,
    owner_location: str,
) -> CommunicationEvidence:
    return CommunicationEvidence(
        evidence_id=evidence_id,
        proposition=proposition,
        subject_ref=subject,
        value=value,
        source_id=f"diagnostic:{proposition}",
        source_role=source_role,
        owner_location=owner_location,
        observed_at_s=T_S,
        world_revision=1,
        status=EvidenceStatus.CURRENT,
        freshness={"basis": "diagnostic-current-public-field"},
        provenance={"surface": "registered-capability-diagnostic"},
    )


def _select(evidence: list[CommunicationEvidence]) -> dict:
    task = o3_backhaul_outage_sustainment_task().model_copy(
        update={"task_id": "query-positive-closure-diagnostic", "target_node_ids": ["n02"]}
    )
    contract = CommunicationTaskCompiler().compile(task, 0)
    snapshot = EvidenceWorldSnapshot.build(revision=1, observed_at_s=T_S, evidence=evidence)
    selection = ActionConditionedContextSelector().select(
        operational_task=task,
        task=contract,
        task_run_id="query-positive-closure-diagnostic",
        evidence_world=snapshot,
        capability_ids=[
            "communication.center.node_report",
            "communication.center.delivery_status",
            "communication.gateway.primary_health",
            "communication.gateway.receipt_summary",
            "communication.fallback.gateway_backup",
            "communication.config.set_sampling_interval",
            "communication.config.set_report_period",
        ],
        resource_ids=["gw0", "n02", "n03"],
        recent_capability_outcomes=[],
        t_s=T_S,
        now=sim_datetime(T_S),
    )
    plans = {
        str(row.get("plan_id")): row
        for row in selection.candidate_context.get("candidate_plans", [])
        if isinstance(row, dict)
    }
    return {
        "backup_plan": plans["consider_gateway_backup"],
        "hold_plan": plans["hold_current_profile"],
        "install_plan": plans["install_required_profile"],
        "needs": [need.model_dump(mode="json") for need in selection.needs],
        "decision_sufficiency": selection.candidate_context.get("decision_sufficiency"),
        "gateway_dependency_rows": [
            row
            for row in selection.candidate_context.get("dependencies", [])
            if row.get("scope_reason") == "shared_gateway_path"
        ],
    }


def main() -> int:
    base = [
        _ev(
            "center-report-n02",
            "communication.center.node_report",
            "n02",
            {"sample_interval_s": 3600, "report_period_s": 3600},
            source_role="center",
            owner_location="center",
        ),
        _ev(
            "center-delivery-deficit-n02",
            "communication.center.delivery_status",
            "n02",
            {"newest_taken_at": T_S - 7200},
            source_role="center",
            owner_location="center",
        ),
    ]
    degraded = [
        *base,
        _ev(
            "gateway-primary-degraded",
            "communication.gateway.primary_health",
            "gw0",
            {
                "last_forward_ok_at": T_S - 7200,
                "pending_depth": 12,
                "oldest_pending_age_s": 7200,
                "query_path_reachable": True,
            },
            source_role="gateway",
            owner_location="gateway",
        ),
        _ev(
            "gateway-receipt-current",
            "communication.gateway.receipt_summary",
            "gw0",
            {
                "heard_nodes": ["n02"],
                "report_at": {"n02": T_S - 60},
                "newest_taken_at": {"n02": T_S - 60},
            },
            source_role="gateway",
            owner_location="gateway",
        ),
    ]
    healthy = [
        *base,
        _ev(
            "gateway-primary-healthy",
            "communication.gateway.primary_health",
            "gw0",
            {
                "last_forward_ok_at": T_S - 60,
                "pending_depth": 0,
                "oldest_pending_age_s": 0,
                "query_path_reachable": True,
            },
            source_role="gateway",
            owner_location="gateway",
        ),
        _ev(
            "gateway-receipt-current-healthy",
            "communication.gateway.receipt_summary",
            "gw0",
            {
                "heard_nodes": ["n02"],
                "report_at": {"n02": T_S - 60},
                "newest_taken_at": {"n02": T_S - 60},
            },
            source_role="gateway",
            owner_location="gateway",
        ),
    ]

    cases = {
        "before_query": _select(base),
        "after_query_primary_degraded": _select(degraded),
        "after_query_primary_healthy": _select(healthy),
    }
    before = cases["before_query"]
    degraded_result = cases["after_query_primary_degraded"]
    healthy_result = cases["after_query_primary_healthy"]
    audit = {
        "open_gateway_needs_before_query": len(before["needs"]),
        "open_gateway_needs_after_degraded": len(degraded_result["needs"]),
        "open_gateway_needs_after_healthy": len(healthy_result["needs"]),
        "backup_feasibility_before": before["backup_plan"]["feasibility"],
        "backup_feasibility_after_degraded": degraded_result["backup_plan"]["feasibility"],
        "backup_feasibility_after_healthy": healthy_result["backup_plan"]["feasibility"],
        "backup_unresolved_after_degraded": degraded_result["backup_plan"]["unresolved_conditions"],
        "backup_unresolved_after_healthy": healthy_result["backup_plan"]["unresolved_conditions"],
        "decision_status_after_degraded": degraded_result["decision_sufficiency"]["status"],
        "decision_status_after_healthy": healthy_result["decision_sufficiency"]["status"],
    }
    gap_confirmed = (
        audit["open_gateway_needs_before_query"] == 2
        and audit["open_gateway_needs_after_degraded"] == 0
        and audit["open_gateway_needs_after_healthy"] == 0
        and audit["backup_feasibility_after_degraded"] == "conditional"
        and audit["backup_feasibility_after_healthy"] == "conditional"
        and bool(audit["backup_unresolved_after_degraded"])
        and bool(audit["backup_unresolved_after_healthy"])
    )
    payload = {
        "experiment": "query-positive-closure-gap-v1",
        "status": "GAP_CONFIRMED" if gap_confirmed else "GAP_NOT_CONFIRMED",
        "task_semantics": (
            "O3 localized candidate diagnostic using already-registered primary_health, "
            "receipt_summary and gateway_backup capabilities; this is not yet a benchmark episode."
        ),
        "audit": audit,
        "cases": cases,
        "interpretation": (
            "The current selector can open and satisfy owner-scoped gateway EvidenceNeeds, but it does "
            "not yet evaluate the returned public primary-health/receipt values into a supported or rejected "
            "gateway-backup branch. Therefore this natural path is not yet a valid query-positive benchmark: "
            "the query answer cannot change the acceptable action region until ordinary guard evaluation / "
            "branch closure is implemented."
        ),
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], **audit}, ensure_ascii=False, indent=2))
    print(f"WROTE {OUT}")
    return 0 if gap_confirmed else 1


if __name__ == "__main__":
    raise SystemExit(main())

