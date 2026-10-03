"""Machine-readable baseline/oracle registry for Agentic Communication experiments.

The registry points to existing implementations instead of cloning historical
controllers.  Every entry declares its information boundary so an evaluator-only
oracle cannot accidentally be reported as an online Agent baseline.
"""
from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field

from .contracts import OperationalTaskFamily


class BaselineClass(StrEnum):
    ONLINE_COMMUNICATION = "online_communication"
    ONLINE_AGENT = "online_agent"
    CONTEXT_ABLATION = "context_ablation"
    EVALUATOR_ONLY_ORACLE = "evaluator_only_oracle"
    REFERENCE = "reference"


class BaselineSpec(BaseModel):
    baseline_id: str
    baseline_class: BaselineClass
    implementation_ref: str
    task_families: list[OperationalTaskFamily] = Field(default_factory=list)
    information_boundary: str
    capability_boundary: str
    purpose: str
    online_legal: bool


ALL_TASKS = list(OperationalTaskFamily)


def baseline_registry() -> dict[str, BaselineSpec]:
    entries = [
        BaselineSpec(
            baseline_id="comm.local_policy",
            baseline_class=BaselineClass.ONLINE_COMMUNICATION,
            implementation_ref="code/substrate/instance/center.py::LocalPolicy",
            task_families=ALL_TASKS,
            information_boundary="local autonomy / no center reconfiguration",
            capability_boundary="existing local sampling/report behavior only",
            purpose="no-agent/local-autonomy floor",
            online_legal=True,
        ),
        BaselineSpec(
            baseline_id="agent.generic_react_context",
            baseline_class=BaselineClass.CONTEXT_ABLATION,
            implementation_ref="code/agentic_communication/context_runtime.py::context_mode=generic_react",
            task_families=ALL_TASKS,
            information_boundary=(
                "Runtime TaskContract + resource inventory + all legally acquired raw evidence + "
                "capability catalog/outcomes; EvidenceNeed and InvestigationState omitted"
            ),
            capability_boundary="same task-visible typed capabilities and same R3 tool loop",
            purpose="generic tool-calling/ReAct-style context baseline without harness cognitive artifacts",
            online_legal=True,
        ),
        BaselineSpec(
            baseline_id="agent.fixed_order_eager",
            baseline_class=BaselineClass.ONLINE_AGENT,
            implementation_ref="code/agentic_communication/planner.py::FixedOrderEagerPlannerConsumer",
            task_families=ALL_TASKS,
            information_boundary="typed PromptAssembly; fixed gateway probe order on each new center-evidence fingerprint",
            capability_boundary="same task-visible capabilities as proposed runtime",
            purpose="fixed-capability-order / eager-probing Agent baseline",
            online_legal=True,
        ),
        BaselineSpec(
            baseline_id="agent.deterministic_comply",
            baseline_class=BaselineClass.ONLINE_AGENT,
            implementation_ref="code/agentic_communication/planner.py::DeterministicComplyPlannerConsumer",
            task_families=ALL_TASKS,
            information_boundary="typed PromptAssembly; no evaluator truth",
            capability_boundary="task-visible typed capabilities; ordinary comply policy",
            purpose="strong deterministic planner/reference inside the Agent runtime",
            online_legal=True,
        ),
        BaselineSpec(
            baseline_id="agent.evidence_aware_comply",
            baseline_class=BaselineClass.ONLINE_AGENT,
            implementation_ref="code/agentic_communication/planner.py::EvidenceAwareComplyPlannerConsumer",
            task_families=ALL_TASKS,
            information_boundary="typed PromptAssembly + open EvidenceNeeds",
            capability_boundary="task-visible observation/device capabilities",
            purpose="task-conditioned evidence-use reference consumer",
            online_legal=True,
        ),
        BaselineSpec(
            baseline_id="agent.diagnosis_first_fixed",
            baseline_class=BaselineClass.ONLINE_AGENT,
            implementation_ref="code/agentic_communication/planner.py::DiagnosisFirstPlannerConsumer",
            task_families=ALL_TASKS,
            information_boundary="typed PromptAssembly; fixed gateway diagnosis once per TaskRun",
            capability_boundary="same task-visible capabilities as proposed runtime",
            purpose="fixed-probe / diagnosis-first Agent baseline",
            online_legal=True,
        ),
        BaselineSpec(
            baseline_id="comm.mission_comply",
            baseline_class=BaselineClass.REFERENCE,
            implementation_ref="code/substrate/joint/mission_policy.py::MissionChangePolicy(mode=comply)",
            task_families=ALL_TASKS,
            information_boundary="external Operational Task + CenterView",
            capability_boundary="sampling/report configuration",
            purpose="deterministic task execution reference and runtime-conformance target",
            online_legal=True,
        ),
        BaselineSpec(
            baseline_id="comm.energy_aware",
            baseline_class=BaselineClass.ONLINE_COMMUNICATION,
            implementation_ref="code/substrate/instance/center.py::EnergyAwarePolicy",
            task_families=[
                OperationalTaskFamily.ENERGY_CONSTRAINED_MONITORING,
                OperationalTaskFamily.COMPOUND_LONG_HORIZON,
            ],
            information_boundary="CenterView-reported SoC/config only",
            capability_boundary="sampling/report configuration",
            purpose="strong ordinary energy-aware controller",
            online_legal=True,
        ),
        BaselineSpec(
            baseline_id="comm.aoi",
            baseline_class=BaselineClass.ONLINE_COMMUNICATION,
            implementation_ref="code/substrate/instance/center.py::AoiPolicy",
            task_families=[
                OperationalTaskFamily.MONITORING_CONTINUITY,
                OperationalTaskFamily.RISK_ESCALATION,
                OperationalTaskFamily.COMPOUND_LONG_HORIZON,
            ],
            information_boundary="CenterView AoI/report history",
            capability_boundary="sampling/report configuration",
            purpose="ordinary freshness-driven controller",
            online_legal=True,
        ),
        BaselineSpec(
            baseline_id="comm.backup_edf",
            baseline_class=BaselineClass.ONLINE_COMMUNICATION,
            implementation_ref="code/substrate/joint/joint_plane.py::JointControlPlane(chooser=edf)",
            task_families=[
                OperationalTaskFamily.BACKHAUL_OUTAGE_SUSTAINMENT,
                OperationalTaskFamily.RECOVERY_RECONCILIATION,
                OperationalTaskFamily.COMPOUND_LONG_HORIZON,
            ],
            information_boundary="gateway pending records + public obligation timing",
            capability_boundary="existing gateway backup path",
            purpose="ordinary deadline-first backup packing",
            online_legal=True,
        ),
        BaselineSpec(
            baseline_id="comm.backup_maxcov",
            baseline_class=BaselineClass.ONLINE_COMMUNICATION,
            implementation_ref="code/substrate/joint/joint_plane.py::JointControlPlane(chooser=maxcov)",
            task_families=[
                OperationalTaskFamily.BACKHAUL_OUTAGE_SUSTAINMENT,
                OperationalTaskFamily.RECOVERY_RECONCILIATION,
                OperationalTaskFamily.COMPOUND_LONG_HORIZON,
            ],
            information_boundary="gateway pending records + public obligation timing",
            capability_boundary="existing gateway backup path",
            purpose="strong deterministic coverage/recency backup baseline",
            online_legal=True,
        ),
        BaselineSpec(
            baseline_id="agent.full_dump",
            baseline_class=BaselineClass.CONTEXT_ABLATION,
            implementation_ref="code/agentic_communication/context_runtime.py::context_mode=full_dump",
            task_families=ALL_TASKS,
            information_boundary="all legally acquired Evidence World records, no hidden truth",
            capability_boundary="same capabilities as task-conditioned runtime",
            purpose="context/materialization baseline",
            online_legal=True,
        ),
        BaselineSpec(
            baseline_id="agent.task_conditioned",
            baseline_class=BaselineClass.ONLINE_AGENT,
            implementation_ref="code/agentic_communication/context_runtime.py::context_mode=task_conditioned",
            task_families=ALL_TASKS,
            information_boundary="task-selected legally acquired Evidence World records",
            capability_boundary="task-visible typed capabilities",
            purpose="proposed context/runtime arm",
            online_legal=True,
        ),
        BaselineSpec(
            baseline_id="oracle.dynamic_energy",
            baseline_class=BaselineClass.EVALUATOR_ONLY_ORACLE,
            implementation_ref="code/substrate/instance/oracle.py::dynamic_oracle",
            task_families=[
                OperationalTaskFamily.ENERGY_CONSTRAINED_MONITORING,
                OperationalTaskFamily.COMPOUND_LONG_HORIZON,
            ],
            information_boundary="full future harvest/obligation trace",
            capability_boundary="offline upper bound; delivery relaxed by design",
            purpose="energy/sampling upper bound",
            online_legal=False,
        ),
        BaselineSpec(
            baseline_id="oracle.delivery",
            baseline_class=BaselineClass.EVALUATOR_ONLY_ORACLE,
            implementation_ref="code/substrate/instance/oracle.py::delivery_oracle",
            task_families=ALL_TASKS,
            information_boundary="evaluator-side realized samples/link opportunities",
            capability_boundary="offline delivery upper bound",
            purpose="separate physical infeasibility from online delivery-policy loss",
            online_legal=False,
        ),
    ]
    return {x.baseline_id: x for x in entries}


def registry_for_task(family: OperationalTaskFamily, *, online_only: bool = False) -> list[BaselineSpec]:
    rows = [x for x in baseline_registry().values() if family in x.task_families]
    if online_only:
        rows = [x for x in rows if x.online_legal]
    return sorted(rows, key=lambda x: x.baseline_id)


def validate_implementation_refs(repo_root: str | Path) -> list[str]:
    root = Path(repo_root)
    failures: list[str] = []
    for spec in baseline_registry().values():
        path = spec.implementation_ref.split("::", 1)[0]
        if not (root / path).is_file():
            failures.append(f"{spec.baseline_id}:missing:{path}")
    return failures
