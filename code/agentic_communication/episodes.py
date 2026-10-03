"""Source-grounded Operational Task episode definitions.

Task families are benchmark/business semantics.  Simulator stressors are kept in
``EpisodeTemplate.simulator_overrides`` so a task definition never silently
changes physical conditions or evaluation denominators.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .contracts import OperationalTask, OperationalTaskFamily, OperationalTaskPhase


@dataclass(frozen=True)
class EpisodeTemplate:
    template_id: str
    task: OperationalTask
    simulator_overrides: dict = field(default_factory=dict)
    difficulty_axes: dict = field(default_factory=dict)
    claim_boundary: str = "benchmark episode; parameters not explicitly source-backed are A-layer"


def _with_pre_enabled_effects(
    task: OperationalTask, effects: list[str]
) -> OperationalTask:
    """Freeze benchmark-known deployment effects without changing Task semantics.

    ``enable_backup`` is a simulator initial condition: when true, the gateway
    backup leg is already armed and JointControlPlane will fail over
    automatically.  The Agent must not spend evidence/action budget deciding to
    enable the same effect again.  Keep this fact in benchmark metadata rather
    than teaching the selector to peek at simulator state.
    """
    metadata = dict(task.metadata)
    metadata["benchmark_pre_enabled_effects"] = sorted(set(effects))
    return task.model_copy(update={"metadata": metadata})


def o1_monitoring_continuity_task(*, task_hours: int = 12) -> OperationalTask:
    return OperationalTask(
        task_id="o1-monitoring-continuity-v1",
        family=OperationalTaskFamily.MONITORING_CONTINUITY,
        phases=[OperationalTaskPhase(start_s=0, required_period_s=3600, level="blue")],
        task_horizon_s=int(task_hours * 3600),
        authorized_effects=[
            "communication.config.set_sampling_interval",
            "communication.config.set_report_period",
        ],
        source_refs=["S04", "task-contract-v1.1"],
        scoring_profile_ref="communication-physical-v1",
        metadata={"risk_authority": "external", "task_semantics": "steady monitoring continuity"},
    )


def o2_prealert_risk_escalation_task(
    *, task_hours: int = 12, notice_at_s: int = 2 * 3600
) -> OperationalTask:
    """O2 variant where external authority announces the h6 escalation earlier.

    ``notice_at_s`` is an A-layer benchmark coordinate.  S15/S16/S17 support the
    existence of condition-dependent intensified monitoring, forecast-driven
    pre-alert, and remotely configurable monitoring periods; none calibrates this
    exact lead time.
    """
    base = o2_risk_escalation_task(task_hours=task_hours)
    metadata = dict(base.metadata)
    metadata.update(
        {
            "phase_notices": {"1": int(notice_at_s)},
            "notice_coordinate_layer": "A",
            "notice_semantics": "future-effective external risk-escalation authorization",
        }
    )
    return base.model_copy(
        update={
            "task_id": "o2-prealert-risk-escalation-v1",
            "source_refs": ["S04", "S15", "S16", "S17", "task-contract-v1.1"],
            "metadata": metadata,
        }
    )


def o3_backhaul_outage_sustainment_task(*, task_hours: int = 12) -> OperationalTask:
    return OperationalTask(
        task_id="o3-backhaul-outage-sustainment-v1",
        family=OperationalTaskFamily.BACKHAUL_OUTAGE_SUSTAINMENT,
        phases=[OperationalTaskPhase(start_s=0, required_period_s=3600, level="blue")],
        task_horizon_s=int(task_hours * 3600),
        authorized_effects=[
            "communication.fallback.gateway_backup",
            "communication.fallback.terminal_dts",
            "communication.config.set_sampling_interval",
            "communication.config.set_report_period",
        ],
        source_refs=["S01", "S02", "S06", "S07", "task-contract-v1.1"],
        scoring_profile_ref="communication-physical-v1",
        metadata={
            "risk_authority": "external",
            "task_semantics": "maintain monitoring delivery during intermittent primary backhaul",
        },
    )


def o4_energy_constrained_monitoring_task(*, task_hours: int = 12) -> OperationalTask:
    return OperationalTask(
        task_id="o4-energy-constrained-monitoring-v1",
        family=OperationalTaskFamily.ENERGY_CONSTRAINED_MONITORING,
        phases=[OperationalTaskPhase(start_s=0, required_period_s=3600, level="blue")],
        task_horizon_s=int(task_hours * 3600),
        authorized_effects=[
            "communication.config.set_sampling_interval",
            "communication.config.set_report_period",
            "communication.fallback.gateway_backup",
        ],
        source_refs=["S07", "S08", "S09", "spec/datasets.md"],
        scoring_profile_ref="communication-physical-v1",
        metadata={
            "risk_authority": "external",
            "task_semantics": "preserve authorized monitoring under low harvest / battery pressure",
        },
    )


def o5_recovery_reconciliation_task(*, task_hours: int = 12) -> OperationalTask:
    return OperationalTask(
        task_id="o5-recovery-reconciliation-v1",
        family=OperationalTaskFamily.RECOVERY_RECONCILIATION,
        phases=[
            OperationalTaskPhase(start_s=0, required_period_s=3600, level="blue"),
            OperationalTaskPhase(start_s=4 * 3600, required_period_s=300, level="yellow"),
            OperationalTaskPhase(start_s=9 * 3600, required_period_s=3600, level="blue"),
        ],
        task_horizon_s=int(task_hours * 3600),
        authorized_effects=[
            "communication.config.set_sampling_interval",
            "communication.config.set_report_period",
            "communication.fallback.gateway_backup",
        ],
        source_refs=["S04", "S06", "task-contract-v1.1"],
        scoring_profile_ref="communication-physical-v1",
        metadata={
            "risk_authority": "external",
            "task_semantics": "reconcile configuration and historical delivery after path recovery",
            "phase_schedule_layer": "A",
        },
    )


def o6_compound_long_horizon_task(*, task_hours: int = 12) -> OperationalTask:
    return OperationalTask(
        task_id="o6-compound-long-horizon-v1",
        family=OperationalTaskFamily.COMPOUND_LONG_HORIZON,
        phases=[
            OperationalTaskPhase(start_s=0, required_period_s=3600, level="blue"),
            OperationalTaskPhase(start_s=5 * 3600, required_period_s=300, level="yellow"),
            OperationalTaskPhase(start_s=10 * 3600, required_period_s=3600, level="blue"),
        ],
        task_horizon_s=int(task_hours * 3600),
        authorized_effects=[
            "communication.config.set_sampling_interval",
            "communication.config.set_report_period",
            "communication.fallback.gateway_backup",
            "communication.fallback.terminal_dts",
            "communication.fallback.access_assist",
        ],
        source_refs=["S04", "S06", "S07", "S08", "S09", "task-contract-v1.1"],
        scoring_profile_ref="communication-physical-v1",
        metadata={
            "risk_authority": "external",
            "task_semantics": "task revision + access/backhaul interruption + energy pressure + recovery",
            "phase_schedule_layer": "A",
        },
    )


def benchmark_episode_catalog(*, task_hours: int = 12) -> dict[str, EpisodeTemplate]:
    """Canonical O1--O6 benchmark templates.

    These templates freeze *what differs* across task families without inventing a
    single weighted objective.  All use the same deployment, scorer and legal
    information boundary.
    """
    return {
        "O1": EpisodeTemplate(
            "O1",
            o1_monitoring_continuity_task(task_hours=task_hours),
            simulator_overrides={"outage_hours": 0.0},
            difficulty_axes={"task_revisions": 0, "backhaul_outage": 0, "energy_pressure": "normal"},
        ),
        "O2": EpisodeTemplate(
            "O2",
            o2_risk_escalation_task(task_hours=task_hours),
            simulator_overrides={"outage_start_h": 4.0, "outage_hours": 4.0},
            difficulty_axes={"task_revisions": 1, "backhaul_outage": 1, "energy_pressure": "normal"},
        ),
        "O3": EpisodeTemplate(
            "O3",
            _with_pre_enabled_effects(
                o3_backhaul_outage_sustainment_task(task_hours=task_hours),
                ["communication.fallback.gateway_backup"],
            ),
            simulator_overrides={"outage_start_h": 3.0, "outage_hours": 6.0, "enable_backup": True},
            difficulty_axes={"task_revisions": 0, "backhaul_outage": 1, "evidence_owners": 2},
        ),
        "O4": EpisodeTemplate(
            "O4",
            _with_pre_enabled_effects(
                o4_energy_constrained_monitoring_task(task_hours=task_hours),
                ["communication.fallback.gateway_backup"],
            ),
            simulator_overrides={
                "harvest_mode": "irradiance",
                "harvest_peak_wh_per_hour": 0.003,
                "capacity_wh": 0.03,
            },
            difficulty_axes={"task_revisions": 0, "energy_pressure": "low_harvest"},
        ),
        "O5": EpisodeTemplate(
            "O5",
            _with_pre_enabled_effects(
                o5_recovery_reconciliation_task(task_hours=task_hours),
                ["communication.fallback.gateway_backup"],
            ),
            simulator_overrides={"outage_start_h": 3.0, "outage_hours": 5.0, "enable_backup": True},
            difficulty_axes={"task_revisions": 2, "backhaul_outage": 1, "recovery": 1},
        ),
        "O6": EpisodeTemplate(
            "O6",
            _with_pre_enabled_effects(
                o6_compound_long_horizon_task(task_hours=task_hours),
                ["communication.fallback.gateway_backup"],
            ),
            simulator_overrides={
                "outage_start_h": 4.0,
                "outage_hours": 4.0,
                "access_outage_start_h": 6.0,
                "access_outage_hours": 2.0,
                "harvest_peak_wh_per_hour": 0.005,
                "enable_backup": True,
            },
            difficulty_axes={
                "task_revisions": 2,
                "backhaul_outage": 1,
                "access_outage": 1,
                "energy_pressure": "medium",
                "recovery": 1,
            },
        ),
    }


def o2_risk_escalation_task(*, task_hours: int = 12) -> OperationalTask:
    """Blue -> yellow escalation used by the first full-sim vertical slice.

    The 3600 s normal and 300 s risk periods are already part of the repository's
    frozen task/monitoring contract.  Risk authority is exogenous; the Agent only
    executes the communication task.
    """
    horizon = int(task_hours * 3600)
    return OperationalTask(
        task_id="o2-risk-escalation-v1",
        family=OperationalTaskFamily.RISK_ESCALATION,
        phases=[
            OperationalTaskPhase(start_s=0, required_period_s=3600, level="blue"),
            OperationalTaskPhase(start_s=6 * 3600, required_period_s=300, level="yellow"),
        ],
        task_horizon_s=horizon,
        authorized_effects=[
            "communication.config.set_sampling_interval",
            "communication.config.set_report_period",
        ],
        source_refs=["S04", "task-contract-v1.1"],
        scoring_profile_ref="communication-physical-v1",
        metadata={
            "risk_authority": "external",
            "primary_metric": "timely_obligation_delivery_rate",
        },
    )


def o2_localized_risk_escalation_task(*, task_hours: int = 12) -> OperationalTask:
    """Externally authorized escalation for the active nodes of the far slope group.

    The target set is determined by the frozen deployment after its marginal-link exclusion.
    The choice to escalate this slope group is a benchmark Operational-Task parameter (A-layer),
    not a claim that a particular real site issued this exact authorization.
    """
    horizon = int(task_hours * 3600)
    return OperationalTask(
        task_id="o2-localized-risk-escalation-v1",
        family=OperationalTaskFamily.RISK_ESCALATION,
        target_node_ids=["n10", "n11", "n13", "n15", "n16"],
        phases=[
            OperationalTaskPhase(start_s=0, required_period_s=3600, level="blue"),
            OperationalTaskPhase(start_s=6 * 3600, required_period_s=300, level="yellow"),
        ],
        task_horizon_s=horizon,
        authorized_effects=[
            "communication.config.set_sampling_interval",
            "communication.config.set_report_period",
        ],
        source_refs=["S04", "spec/instance-v1-manifest.md", "task-contract-v1.1"],
        scoring_profile_ref="communication-physical-v1",
        metadata={
            "risk_authority": "external",
            "scope_semantics": "benchmark-authorized far-slope active-node subset",
            "scope_evidence_layer": "A",
            "primary_metric": "timely_obligation_delivery_rate",
        },
    )
