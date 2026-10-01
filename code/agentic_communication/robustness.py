"""Canonical paired robustness coordinates for Agentic Communication.

The first matrix is deliberately axis-wise rather than a Cartesian product.  It
checks that each benchmark axis reaches the real simulator/runtime while keeping
the number of full-sim episodes auditable and cheap enough for routine gates.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from .contracts import OperationalTask
from .episodes import (
    o1_monitoring_continuity_task,
    o2_localized_risk_escalation_task,
    o2_risk_escalation_task,
    o3_backhaul_outage_sustainment_task,
    o4_energy_constrained_monitoring_task,
)


class RobustnessCoordinate(BaseModel):
    coordinate_id: str
    axis: str
    level: str
    task_key: str
    task_hours: int = Field(ge=1)
    seed: int = Field(default=0, ge=0)
    simulator_overrides: dict
    expected_owner_classes: list[str] = Field(default_factory=list)
    notes: str = ""


def robustness_coordinates() -> list[RobustnessCoordinate]:
    return [
        RobustnessCoordinate(
            coordinate_id="weather:early",
            axis="weather_window",
            level="early",
            task_key="O4",
            task_hours=4,
            simulator_overrides={
                "task_hours": 4,
                "tail_hours": 1,
                "harvest_mode": "irradiance",
                "irradiance_year": 2023,
                "irradiance_start_hour": 30 * 24 + 8,
                "harvest_peak_wh_per_hour": 0.003,
                "capacity_wh": 0.03,
                "initial_soc": 0.1,
                "outage_hours": 0.0,
                "backhaul_p_good": 1.0,
                "execution_feedback": True,
            },
            expected_owner_classes=["center"],
            notes="A-layer weather-window coordinate over source-grounded NASA POWER input",
        ),
        RobustnessCoordinate(
            coordinate_id="weather:late",
            axis="weather_window",
            level="late",
            task_key="O4",
            task_hours=4,
            simulator_overrides={
                "task_hours": 4,
                "tail_hours": 1,
                "harvest_mode": "irradiance",
                "irradiance_year": 2023,
                "irradiance_start_hour": 270 * 24 + 8,
                "harvest_peak_wh_per_hour": 0.003,
                "capacity_wh": 0.03,
                "initial_soc": 0.1,
                "outage_hours": 0.0,
                "backhaul_p_good": 1.0,
                "execution_feedback": True,
            },
            expected_owner_classes=["center"],
            notes="same task/deployment, different source-data window",
        ),
        RobustnessCoordinate(
            coordinate_id="outage:short-early",
            axis="backhaul_outage",
            level="short_early",
            task_key="O3",
            task_hours=4,
            simulator_overrides={
                "task_hours": 4,
                "tail_hours": 1,
                "harvest_mode": "uniform",
                "harvest_wh_per_hour": 3.0,
                "backhaul_p_good": 1.0,
                "outage_start_h": 0.5,
                "outage_hours": 1.0,
                "enable_backup": True,
                "execution_feedback": True,
            },
            expected_owner_classes=["center", "gateway"],
        ),
        RobustnessCoordinate(
            coordinate_id="outage:long-late",
            axis="backhaul_outage",
            level="long_late",
            task_key="O3",
            task_hours=6,
            simulator_overrides={
                "task_hours": 6,
                "tail_hours": 1,
                "harvest_mode": "uniform",
                "harvest_wh_per_hour": 3.0,
                "backhaul_p_good": 1.0,
                "outage_start_h": 2.0,
                "outage_hours": 3.0,
                "enable_backup": True,
                "execution_feedback": True,
            },
            expected_owner_classes=["center", "gateway"],
        ),
        RobustnessCoordinate(
            coordinate_id="scope:global",
            axis="target_scope",
            level="global",
            task_key="O2",
            task_hours=12,
            simulator_overrides={},
            expected_owner_classes=["center"],
        ),
        RobustnessCoordinate(
            coordinate_id="scope:localized",
            axis="target_scope",
            level="localized",
            task_key="O2_LOCAL",
            task_hours=12,
            simulator_overrides={},
            expected_owner_classes=["center"],
        ),
        RobustnessCoordinate(
            coordinate_id="owner:center-only",
            axis="evidence_owner",
            level="center_only",
            task_key="O1",
            task_hours=4,
            simulator_overrides={
                "task_hours": 4,
                "tail_hours": 1,
                "harvest_mode": "uniform",
                "harvest_wh_per_hour": 3.0,
                "outage_hours": 0.0,
                "backhaul_p_good": 1.0,
                "execution_feedback": True,
            },
            expected_owner_classes=["center"],
        ),
        RobustnessCoordinate(
            coordinate_id="owner:center-gateway",
            axis="evidence_owner",
            level="center_gateway",
            task_key="O3",
            task_hours=4,
            simulator_overrides={
                "task_hours": 4,
                "tail_hours": 1,
                "harvest_mode": "uniform",
                "harvest_wh_per_hour": 3.0,
                "outage_hours": 0.0,
                "backhaul_p_good": 1.0,
                "enable_backup": True,
                "execution_feedback": True,
            },
            expected_owner_classes=["center", "gateway"],
        ),
        RobustnessCoordinate(
            coordinate_id="scale:one-group",
            axis="deployment_scale",
            level="one_group",
            task_key="O1",
            task_hours=4,
            simulator_overrides={
                "task_hours": 4,
                "tail_hours": 1,
                "groups": 1,
                "harvest_mode": "uniform",
                "harvest_wh_per_hour": 3.0,
                "outage_hours": 0.0,
                "backhaul_p_good": 1.0,
                "execution_feedback": True,
            },
            expected_owner_classes=["center"],
        ),
        RobustnessCoordinate(
            coordinate_id="scale:two-group",
            axis="deployment_scale",
            level="two_group",
            task_key="O1",
            task_hours=4,
            simulator_overrides={
                "task_hours": 4,
                "tail_hours": 1,
                "groups": 2,
                "harvest_mode": "uniform",
                "harvest_wh_per_hour": 3.0,
                "outage_hours": 0.0,
                "backhaul_p_good": 1.0,
                "execution_feedback": True,
            },
            expected_owner_classes=["center"],
        ),
    ]


def task_for_coordinate(c: RobustnessCoordinate) -> OperationalTask:
    if c.task_key == "O1":
        return o1_monitoring_continuity_task(task_hours=c.task_hours)
    if c.task_key == "O2":
        return o2_risk_escalation_task(task_hours=c.task_hours)
    if c.task_key == "O2_LOCAL":
        return o2_localized_risk_escalation_task(task_hours=c.task_hours)
    if c.task_key == "O3":
        return o3_backhaul_outage_sustainment_task(task_hours=c.task_hours)
    if c.task_key == "O4":
        return o4_energy_constrained_monitoring_task(task_hours=c.task_hours)
    raise KeyError(c.task_key)


def robustness_summary(rows: list[RobustnessCoordinate]) -> dict:
    axes = sorted({row.axis for row in rows})
    return {
        axis: {
            "n_coordinates": sum(row.axis == axis for row in rows),
            "levels": [row.level for row in rows if row.axis == axis],
        }
        for axis in axes
    }
