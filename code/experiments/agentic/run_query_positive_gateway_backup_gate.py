#!/usr/bin/env python3
"""Deterministic full-simulator gate for the natural query-positive O3 branch."""
from __future__ import annotations

from collections import Counter
import argparse
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
ROOT = HERE.parents[2]
for path in (
    CODE,
    CODE / "v3joint",
    CODE / "instance",
    CODE / "monitoring",
    CODE / "runtime",
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from joint_run import run_joint  # noqa: E402

from agentic_communication.episodes import benchmark_episode_catalog  # noqa: E402
from agentic_communication.metrics import (  # noqa: E402
    agent_metrics,
    communication_metrics,
    configuration_execution_metrics,
    physical_signature,
)
from agentic_communication.planner import CompiledChecklistPlannerConsumer  # noqa: E402
from agentic_communication.query_positive import (  # noqa: E402
    GATEWAY_BACKUP_PLAN_ID,
    QueryPositiveAgenticCommunicationPolicy,
)
from agentic_communication.run import DEFAULT_FULLSIM, _delivery_oracles  # noqa: E402
from agentic_communication.runtime_contracts import (  # noqa: E402
    ModelUsage,
    PlannedCapabilityInvocation,
    PlannerDecision,
)


OUT = ROOT / "results" / "agentic" / "query-positive-gateway-backup-v1" / "deterministic-gate.json"
SEED_DIR = OUT.parent / "deterministic-seeds"
SEEDS = tuple(range(5))
SIMULATOR = {
    "outage_start_h": 0.0,
    "outage_hours": 0.0,
    "enable_backup": False,
    "backhaul_delay_s": 3600,
    "mission_policy_placement": "gateway",
}


def query_positive_task():
    base = benchmark_episode_catalog()["O3"].task
    metadata = dict(base.metadata)
    # The query-positive deployment starts with backup disabled.  Remove only
    # the benchmark-specific statement that the effect was pre-enabled; action
    # authorization and the O3 mission remain unchanged.
    metadata["benchmark_pre_enabled_effects"] = []
    metadata["query_positive_coordinate"] = {
        "initial_gateway_backup": False,
        "primary_backhaul_delay_s": SIMULATOR["backhaul_delay_s"],
        "guard_authority": "Operational Task required_period_s + gateway owner evidence",
    }
    return base.model_copy(
        update={
            "task_id": "o3-gateway-backup-query-positive-v1",
            "metadata": metadata,
        }
    )


class QueryPositiveReferenceConsumer:
    consumer_id = "query-positive-reference-v1"
    provider = "runtime"
    model = "deterministic-query-positive-reference"

    def decide(self, request, assembly):
        fragments = {row.kind: row.content for row in assembly.fragments}
        candidate = fragments.get("candidate_action_context") or {}
        plans = [row for row in candidate.get("candidate_plans", []) if isinstance(row, dict)]
        sufficiency = candidate.get("decision_sufficiency") or {}
        status = str(sufficiency.get("status") or "")
        primary_id = sufficiency.get("primary_plan_id")
        primary = next(
            (row for row in plans if row.get("plan_id") == primary_id),
            None,
        )
        if primary is not None and status in {
            "sufficient_for_primary_action",
            "sufficient_for_no_action",
        }:
            has_effect = bool(primary.get("invocations"))
            return (
                PlannerDecision(
                    decision_id=f"decision:{request.request_id}",
                    request_id=request.request_id,
                    stop=not has_effect,
                    selected_plan_id=str(primary_id),
                    invocations=[],
                    reason_codes=["query-positive-reference:commit-closed-plan"],
                ),
                ModelUsage(),
            )

        invocations = []
        for need in fragments.get("evidence_needs") or []:
            if not isinstance(need, dict):
                continue
            if str(need.get("status") or "").lower() != "open":
                continue
            if GATEWAY_BACKUP_PLAN_ID not in set(need.get("blocking_plan_ids") or []):
                continue
            question = str(need.get("proposition_or_question") or "")
            for capability_id in (
                "communication.gateway.primary_health",
                "communication.gateway.receipt_summary",
            ):
                if capability_id in question:
                    invocations.append(
                        PlannedCapabilityInvocation(
                            capability_id=capability_id,
                            resource="gw0",
                            canonical_arguments={},
                        )
                    )
        if invocations:
            return (
                PlannerDecision(
                    decision_id=f"decision:{request.request_id}",
                    request_id=request.request_id,
                    stop=False,
                    invocations=invocations,
                    reason_codes=["query-positive-reference:resolve-blocking-owner-evidence"],
                ),
                ModelUsage(),
            )

        return (
            PlannerDecision(
                decision_id=f"decision:{request.request_id}",
                request_id=request.request_id,
                stop=True,
                invocations=[],
                reason_codes=["query-positive-reference:no-ready-action-or-reachable-open-need"],
            ),
            ModelUsage(),
        )


def _run_policy(*, seed: int, consumer):
    task = query_positive_task()
    policy = QueryPositiveAgenticCommunicationPolicy(
        task,
        seed=seed,
        context_mode="action_conditioned_compact_v7",
        planner_consumer=consumer,
        planner_replan_mode="decision_state",
    )
    kw = dict(DEFAULT_FULLSIM)
    kw.update(SIMULATOR)
    kw["trace"] = True
    result, inst, obligations = run_joint(
        seed=seed,
        arm="local",
        mission_schedule=task.mission_schedule(),
        mission_scope=(task.target_node_ids or None),
        mission_policy_obj=policy,
        **kw,
    )
    end_s = int((kw["task_hours"] + kw["tail_hours"]) * 3600)
    policy.finalize(t_s=end_s, physical_result=result)
    result["evaluator_oracles"] = _delivery_oracles(
        inst, obligations, int(kw["task_hours"] + kw["tail_hours"])
    )
    result["configuration_execution"] = configuration_execution_metrics(inst, task)
    result["agentic"] = {
        "operational_task": task.model_dump(mode="json"),
        "context_mode": "action_conditioned_compact_v7",
        "method_variant": "gateway-backup-query-positive-v1",
        "planner_replan_mode": "decision_state",
        "communication_metrics": communication_metrics(result),
        "agent_metrics": agent_metrics(policy),
    }
    return result, policy, inst


def _trace_audit(policy) -> dict:
    query_requests = []
    backup_effects = []
    guard_counts = Counter()
    guard_timeline = []
    for event in policy.trace.events:
        if event.event_type == "capability_request":
            capability_id = str(event.payload.get("capability_id") or "")
            if capability_id in {
                "communication.gateway.primary_health",
                "communication.gateway.receipt_summary",
            }:
                query_requests.append(
                    {
                        "t_s": int(event.t_s),
                        "capability_id": capability_id,
                        "request_id": event.payload.get("request_id"),
                    }
                )
        elif event.event_type == "physical_effect":
            if event.payload.get("capability_id") == "communication.fallback.gateway_backup":
                backup_effects.append(dict(event.payload))
        elif event.event_type == "prompt_assembly":
            fragments = {
                row.get("kind"): row.get("content")
                for row in event.payload.get("fragments", [])
                if isinstance(row, dict)
            }
            candidate = fragments.get("candidate_action_context") or {}
            qp = candidate.get("query_positive_gateway_backup") or {}
            guard = str(qp.get("guard_result") or "")
            if guard:
                guard_counts[guard] += 1
                if guard in {"needs_evidence", "supported", "rejected", "already_enabled"}:
                    guard_timeline.append(
                        {
                            "t_s": int(event.t_s),
                            "guard_result": guard,
                            "guard_inputs": qp.get("guard_inputs") or {},
                            "decision_sufficiency": candidate.get("decision_sufficiency") or {},
                        }
                    )
    return {
        "query_request_count": len(query_requests),
        "query_requests": query_requests,
        "backup_effect_count": len(backup_effects),
        "backup_effects": backup_effects,
        "guard_counts": dict(sorted(guard_counts.items())),
        "guard_timeline": guard_timeline,
    }


def _run_seed(seed: int) -> dict:
    dynamic, dynamic_policy, dynamic_inst = _run_policy(
        seed=seed,
        consumer=QueryPositiveReferenceConsumer(),
    )
    control, _, control_inst = _run_policy(
        seed=seed,
        consumer=CompiledChecklistPlannerConsumer(),
    )
    dm = dynamic["agentic"]["communication_metrics"]
    cm = control["agentic"]["communication_metrics"]
    return {
        "seed": seed,
        "dynamic": dm,
        "no_acquisition_control": cm,
        "dynamic_backup_final": bool(dynamic_inst.plane.enable_backup),
        "control_backup_final": bool(control_inst.plane.enable_backup),
        "query_audit": _trace_audit(dynamic_policy),
        "delta_dynamic_minus_control": {
            "timely_delivery_rate": dm["timely_delivery_rate"] - cm["timely_delivery_rate"],
            "aoi_mean_s": dm["aoi_mean_s"] - cm["aoi_mean_s"],
            "backup_packets": dm["backup_packets"] - cm["backup_packets"],
            "backup_bytes": dm["backup_bytes"] - cm["backup_bytes"],
        },
    }


def _write_seed(seed: int) -> int:
    row = _run_seed(seed)
    SEED_DIR.mkdir(parents=True, exist_ok=True)
    path = SEED_DIR / f"seed-{seed:03d}.json"
    path.write_text(json.dumps(row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "seed": seed,
                "dynamic_backup_final": row["dynamic_backup_final"],
                "control_backup_final": row["control_backup_final"],
                "queries": row["query_audit"]["query_request_count"],
                "backup_effects": row["query_audit"]["backup_effect_count"],
                "tdr_delta": row["delta_dynamic_minus_control"]["timely_delivery_rate"],
                "aoi_delta_s": row["delta_dynamic_minus_control"]["aoi_mean_s"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def _aggregate() -> int:
    rows = []
    missing = []
    for seed in SEEDS:
        path = SEED_DIR / f"seed-{seed:03d}.json"
        if not path.is_file():
            missing.append(seed)
            continue
        rows.append(json.loads(path.read_text(encoding="utf-8")))
    if missing:
        print(f"missing deterministic seed artifacts: {missing}", file=sys.stderr)
        return 3

    mean_tdr_delta = sum(row["delta_dynamic_minus_control"]["timely_delivery_rate"] for row in rows) / len(rows)
    mean_aoi_delta = sum(row["delta_dynamic_minus_control"]["aoi_mean_s"] for row in rows) / len(rows)
    passed = bool(
        all(row["query_audit"]["query_request_count"] >= 2 for row in rows)
        and all(row["query_audit"]["backup_effect_count"] >= 1 for row in rows)
        and all(row["dynamic_backup_final"] for row in rows)
        and all(not row["control_backup_final"] for row in rows)
        and any(row["delta_dynamic_minus_control"]["timely_delivery_rate"] > 0 for row in rows)
        and mean_tdr_delta > 0
        and mean_aoi_delta < 0
    )
    payload = {
        "experiment": "query-positive-gateway-backup-v1-deterministic-gate",
        "status": "PASS" if passed else "FAIL",
        "task": query_positive_task().model_dump(mode="json"),
        "simulator": SIMULATOR,
        "guard": (
            "pending_depth>0 AND oldest_pending_age_s>=required_period_s AND receipt_summary.heard_nodes nonempty"
        ),
        "seeds": list(SEEDS),
        "mean_delta_dynamic_minus_control": {
            "timely_delivery_rate": mean_tdr_delta,
            "aoi_mean_s": mean_aoi_delta,
        },
        "rows": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "mean_delta": payload["mean_delta_dynamic_minus_control"],
                "per_seed": [
                    {
                        "seed": row["seed"],
                        "queries": row["query_audit"]["query_request_count"],
                        "backup_effects": row["query_audit"]["backup_effect_count"],
                        "guard_counts": row["query_audit"]["guard_counts"],
                        "tdr_delta": row["delta_dynamic_minus_control"]["timely_delivery_rate"],
                        "aoi_delta_s": row["delta_dynamic_minus_control"]["aoi_mean_s"],
                    }
                    for row in rows
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print(f"WROTE {OUT}")
    return 0 if passed else 2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, choices=SEEDS)
    args = ap.parse_args()
    if args.seed is not None:
        return _write_seed(args.seed)
    return _aggregate()


if __name__ == "__main__":
    raise SystemExit(main())

