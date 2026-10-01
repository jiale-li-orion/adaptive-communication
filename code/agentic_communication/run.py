"""Full-simulator experiment wiring for Agentic Communication."""
from __future__ import annotations

from pathlib import Path
import sys

_CODE = Path(__file__).resolve().parents[1]
for _p in (
    _CODE,
    _CODE / "v3joint",
    _CODE / "instance",
    _CODE / "monitoring",
    _CODE / "physics",
    _CODE / "runtime",
    _CODE / "experiments",
    _CODE / "analysis",
):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from joint_run import run_joint  # noqa: E402
from oracle import delivery_oracle  # noqa: E402

from .contracts import OperationalTask
from .metrics import agent_metrics, communication_metrics, configuration_execution_metrics
from .policy import AgenticCommunicationPolicy


DEFAULT_FULLSIM = {
    "task_hours": 12,
    "tail_hours": 1,
    "groups": 2,
    "sample_interval_s": 3600,
    "report_period_s": 3600,
    "routine_period_s": 3600,
    "harvest_mode": "irradiance",
    "harvest_peak_wh_per_hour": 0.01,
    "irradiance_year": 2023,
    "irradiance_start_hour": 24 * 151,  # early June; source-derived weather window
    "capacity_wh": 0.05,
    "initial_soc": 1.0,
    "outage_start_h": 4.0,
    "outage_hours": 4.0,
    "enable_backup": True,
    "backup_rate_s": 120,
    "backup_bytes": 200,
    "execution_feedback": True,
}


def _delivery_oracles(inst, obligations, total_hours: int) -> dict:
    extra_paths = []
    if bool(getattr(inst.plane, "enable_backup", False)):
        extra_paths.append("gateway_backup")
    if getattr(inst, "terminal_dts", None) is not None:
        extra_paths.append("terminal_dts")
    if (
        getattr(inst, "access_assist_windows", ())
        or getattr(inst, "agent_access_assist_windows", ())
        or getattr(inst, "access_assist_controller", None) is not None
    ):
        extra_paths.append("access_assist")
    if extra_paths:
        return {
            "applicable": False,
            "reason": (
                "existing delivery_oracle is primary-path-only and is not a valid full-system "
                "upper bound when additional communication paths are enabled"
            ),
            "unmodeled_paths": extra_paths,
            "semantics": (
                "N/A by construction; do not compare actual delivery against this oracle until "
                "a multi-path evaluator oracle is implemented."
            ),
        }
    fixed = delivery_oracle(
        obligations, inst.log, int(total_hours), plane=inst.plane
    )
    free_sample = delivery_oracle(
        obligations,
        inst.log,
        int(total_hours),
        plane=inst.plane,
        free_transmit=True,
        require_sample=True,
    )
    free = delivery_oracle(
        obligations,
        inst.log,
        int(total_hours),
        plane=inst.plane,
        free_transmit=True,
    )
    return {
        "applicable": True,
        "delivery_fixed_send": fixed,
        "delivery_free_send_require_sample": free_sample,
        "delivery_link_opportunity_ceiling": free,
        "semantics": (
            "Evaluator-only primary-path delivery opportunity decomposition. The free-send ceiling relaxes "
            "sample availability/energy and is not a full Feasible-Obligation denominator."
        ),
    }


def run_agentic_episode(
    *,
    seed: int,
    operational_task: OperationalTask,
    context_mode: str = "task_conditioned",
    planner_mode: str = "comply",
    planner_consumer=None,
    simulator_kwargs: dict | None = None,
) -> tuple[dict, AgenticCommunicationPolicy, object, object]:
    policy = AgenticCommunicationPolicy(
        operational_task,
        seed=seed,
        context_mode=context_mode,
        planner_mode=planner_mode,
        planner_consumer=planner_consumer,
    )
    kw = dict(DEFAULT_FULLSIM)
    kw.update(simulator_kwargs or {})
    # Required only for evaluator-side desired-vs-applied configuration metrics;
    # trace_events never enter Agent Context or planner inputs.
    kw["trace"] = True
    result, inst, obligations = run_joint(
        seed=seed,
        arm="local",
        mission_schedule=operational_task.mission_schedule(),
        mission_scope=(operational_task.target_node_ids or None),
        mission_policy_obj=policy,
        **kw,
    )
    end_s = int((kw["task_hours"] + kw["tail_hours"]) * 3600)
    policy.finalize(t_s=end_s, physical_result=result)
    evaluator_oracles = _delivery_oracles(
        inst, obligations, int(kw["task_hours"] + kw["tail_hours"])
    )
    result["evaluator_oracles"] = evaluator_oracles
    result["configuration_execution"] = configuration_execution_metrics(inst, operational_task)
    result["agentic"] = {
        "operational_task": operational_task.model_dump(mode="json"),
        "context_mode": context_mode,
        "planner_mode": planner_mode,
        "communication_metrics": communication_metrics(result),
        "agent_metrics": agent_metrics(policy),
        "evaluator_oracles": evaluator_oracles,
    }
    return result, policy, inst, obligations


def run_reference_comply(
    *,
    seed: int,
    operational_task: OperationalTask,
    simulator_kwargs: dict | None = None,
) -> tuple[dict, object, object]:
    kw = dict(DEFAULT_FULLSIM)
    kw.update(simulator_kwargs or {})
    # Same evaluator-only physical trace as the Agentic arm; legacy policy still
    # receives no additional online information.
    kw["trace"] = True
    result, inst, obligations = run_joint(
        seed=seed,
        arm="local",
        mission_schedule=operational_task.mission_schedule(),
        mission_scope=(operational_task.target_node_ids or None),
        mission_mode="comply",
        **kw,
    )
    evaluator_oracles = _delivery_oracles(
        inst, obligations, int(kw["task_hours"] + kw["tail_hours"])
    )
    result["evaluator_oracles"] = evaluator_oracles
    result["configuration_execution"] = configuration_execution_metrics(inst, operational_task)
    result["agentic"] = {
        "operational_task": operational_task.model_dump(mode="json"),
        "context_mode": None,
        "planner_mode": "legacy_comply_reference",
        "communication_metrics": communication_metrics(result),
        "agent_metrics": None,
        "evaluator_oracles": evaluator_oracles,
    }
    return result, inst, obligations
