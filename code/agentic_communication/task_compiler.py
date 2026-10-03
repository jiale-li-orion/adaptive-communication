"""Operational Task -> canonical Runtime TaskContract."""
from __future__ import annotations

from .contracts import OperationalTask, OperationalTaskFamily
from .runtime_contracts import EffectCeiling, TaskContract, TaskKind


_KIND_MAP: dict[OperationalTaskFamily, TaskKind] = {
    OperationalTaskFamily.MONITORING_CONTINUITY: TaskKind.WATCH,
    OperationalTaskFamily.RISK_ESCALATION: TaskKind.CONTROL,
    OperationalTaskFamily.BACKHAUL_OUTAGE_SUSTAINMENT: TaskKind.WATCH,
    OperationalTaskFamily.ENERGY_CONSTRAINED_MONITORING: TaskKind.CONTROL,
    OperationalTaskFamily.RECOVERY_RECONCILIATION: TaskKind.RESOLVE_CONFLICT,
    OperationalTaskFamily.COMPOUND_LONG_HORIZON: TaskKind.WATCH,
}


class CommunicationTaskCompiler:
    revision = "communication-task-compiler-v1"

    def compile(self, task: OperationalTask, t_s: int) -> TaskContract:
        phase_idx = task.phase_index(t_s)
        phase = task.phases[phase_idx]
        next_start = (
            task.phases[phase_idx + 1].start_s
            if phase_idx + 1 < len(task.phases)
            else task.task_horizon_s
        )
        announced = task.announced_future_phases(t_s)
        notice_key = ",".join(str(row["phase_index"]) for row in announced)
        contract_id = f"communication:{task.task_id}:phase:{phase_idx}"
        if notice_key:
            contract_id += f":announced:{notice_key}"
        targets = task.target_node_ids or ["monitoring-network"]
        desired_state = {
            "domain": "pre_disaster_mountain_monitoring",
            "operational_task_id": task.task_id,
            "operational_task_family": task.family.value,
            "phase_index": phase_idx,
            "monitoring_level": phase.level,
            "required_period_s": phase.required_period_s,
            "measurands": list(task.measurands),
            "scoring_profile_ref": task.scoring_profile_ref,
        }
        temporal_contract = {
            "phase_start_s": phase.start_s,
            "phase_end_s": next_start,
            "task_horizon_s": task.task_horizon_s,
        }
        if announced:
            desired_state["announced_future_phases"] = announced
            temporal_contract["announced_future_phases"] = announced
        return TaskContract(
            task_contract_id=contract_id,
            contract_revision=task.task_revision,
            principal=task.principal,
            task_kind=_KIND_MAP[task.family],
            target_resources=list(targets),
            desired_state=desired_state,
            evidence_contract={
                "authority": "communication_evidence_world",
                "truth_access": "forbidden",
                "required_status_semantics": [
                    "current",
                    "stale",
                    "none_recent",
                    "unreachable",
                    "timeout",
                    "negative_observation",
                ],
            },
            output_contract={
                "type": "communication_policy_decision",
                "physical_outcome_primary": True,
            },
            temporal_contract=temporal_contract,
            effect_ceiling=EffectCeiling.EXTERNAL_SIDE_EFFECT,
            completion_predicate={
                "type": "operational_phase_execution",
                "required_period_s": phase.required_period_s,
                "until_s": next_start,
                "score_ref": task.scoring_profile_ref,
            },
            policy_revision="agentic-communication-policy-v1",
        )
