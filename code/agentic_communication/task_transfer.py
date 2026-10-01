"""Source-derived Operational Task schedules for secondary transfer experiments.

These adapters never turn the communication Agent into a hazard predictor.  A
published monitoring record is interpreted by an *external authority* and only
the ordered monitoring regime reaches the Agent as an OperationalTask.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from .contracts import OperationalTask, OperationalTaskFamily, OperationalTaskPhase


class SourcePhase(BaseModel):
    label: str
    real_period: str
    source_ref: str
    source_observation: str
    benchmark_start_s: int = Field(ge=0)
    required_period_s: int = Field(gt=0)
    level: str


class SourceDerivedTaskProfile(BaseModel):
    profile_id: str
    source_site: str
    source_refs: list[str]
    transform_rule: str
    claim_boundary: str
    phases: list[SourcePhase]

    def to_operational_task(self, *, task_hours: int = 12) -> OperationalTask:
        horizon = int(task_hours * 3600)
        if any(phase.benchmark_start_s >= horizon for phase in self.phases):
            raise ValueError("source-derived phase lies outside requested task horizon")
        return OperationalTask(
            task_id=f"transfer:{self.profile_id}:{task_hours}h",
            family=OperationalTaskFamily.RISK_ESCALATION,
            phases=[
                OperationalTaskPhase(
                    start_s=phase.benchmark_start_s,
                    required_period_s=phase.required_period_s,
                    level=phase.level,
                )
                for phase in self.phases
            ],
            task_horizon_s=horizon,
            authorized_effects=[
                "communication.config.set_sampling_interval",
                "communication.config.set_report_period",
            ],
            source_refs=list(self.source_refs),
            scoring_profile_ref="communication-physical-v1",
            metadata={
                "risk_authority": "external-source-derived",
                "source_site": self.source_site,
                "source_profile_id": self.profile_id,
                "transform_rule": self.transform_rule,
                "claim_boundary": self.claim_boundary,
                "source_phases": [phase.model_dump(mode="json") for phase in self.phases],
            },
        )


def qili_2016_rainfall_deformation_profile() -> SourceDerivedTaskProfile:
    """Three-regime task authority derived from the published Qili monitoring record.

    The paper reports increased deformation during 21 Apr--7 Jun 2016, when
    accumulated rainfall was 637 mm, followed by stabilization.  The secondary
    benchmark preserves only the *ordered regime sequence*.  Each regime is
    mapped to four simulator hours so the transfer remains computationally
    comparable to the 12 h primary benchmark; that compression is not a physical
    time model.
    """
    return SourceDerivedTaskProfile(
        profile_id="qili-2016-rainfall-deformation-v1",
        source_site="Qili connection-line monitored high-steep slopes, Zhejiang, China",
        source_refs=["S14"],
        transform_rule=(
            "ordered-regime transfer: published pre-heavy-rain / heavy-rain deformation-acceleration / "
            "post-heavy-rain stabilization sequence -> three equal 4 h benchmark phases"
        ),
        claim_boundary=(
            "source-derived phase ordering only; 3600 s/300 s communication profiles and equal-duration "
            "compression are benchmark A-layer choices, not Qili field warning thresholds"
        ),
        phases=[
            SourcePhase(
                label="pre-heavy-rain relative stability",
                real_period="2016-01-31/2016-04-20",
                source_ref="S14",
                source_observation="reported deformation was relatively stable before the heavy-rain interval",
                benchmark_start_s=0,
                required_period_s=3600,
                level="blue",
            ),
            SourcePhase(
                label="heavy-rain deformation acceleration",
                real_period="2016-04-21/2016-06-07",
                source_ref="S14",
                source_observation="637 mm heavy rainfall and increased GPS deformation rates were reported",
                benchmark_start_s=4 * 3600,
                required_period_s=300,
                level="yellow",
            ),
            SourcePhase(
                label="post-heavy-rain stabilization",
                real_period="after 2016-06-07",
                source_ref="S14",
                source_observation="reported deformation rate subsequently stabilized",
                benchmark_start_s=8 * 3600,
                required_period_s=3600,
                level="blue",
            ),
        ],
    )
