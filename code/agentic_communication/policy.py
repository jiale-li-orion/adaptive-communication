"""Task-conditioned Agent runtime policy for the existing full simulator.

The first public implementation is deliberately deterministic: it must reproduce
the existing ``mission=comply`` physical behavior while emitting the complete
Evidence/Context/Capability/Action trace.  Model planners plug into the same
runtime after this conformance slice is stable.
"""
from __future__ import annotations

from pathlib import Path
import sys

_CODE = Path(__file__).resolve().parents[1]
for _p in (_CODE / "instance", _CODE / "v3joint"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from center import (  # noqa: E402
    CenterPolicy,
    OP_SET_REPORT_PERIOD,
    OP_SET_SAMPLING_INTERVAL,
)

from .capabilities import CommunicationCapabilityCatalog
from .context_runtime import CommunicationContextRuntime
from .contracts import OperationalTask
from .contracts import OperationalTaskFamily
from .evidence_world import CommunicationEvidenceWorld
from .runtime_contracts import (
    CapabilityRequest,
    CapabilityResult,
    CapabilityResultStatus,
    EffectSemantics,
    ObservedProposition,
    Percept,
    TaskRun,
    TaskRunStatus,
    PlannerDecision,
)
from .planner import PlannerConsumer, invoke_consumer
from .task_compiler import CommunicationTaskCompiler
from .trace import RuntimeTrace


_ACTION_CAPABILITY = {
    OP_SET_SAMPLING_INTERVAL: "communication.config.set_sampling_interval",
    OP_SET_REPORT_PERIOD: "communication.config.set_report_period",
}


class AgenticCommunicationPolicy(CenterPolicy):
    """Deterministic first consumer of the Agentic Communication runtime.

    ``planner_mode='comply'`` intentionally matches ``MissionChangePolicy``'s
    comply arm.  That exact physical equivalence is the first R3 harness check.
    """

    name = "agentic-communication"

    def __init__(
        self,
        operational_task: OperationalTask,
        *,
        seed: int,
        context_mode: str = "task_conditioned",
        planner_mode: str = "comply",
        planner_consumer: PlannerConsumer | None = None,
        dwell_s: int = 1800,
    ) -> None:
        super().__init__()
        self.operational_task = operational_task
        self.seed = int(seed)
        self.context_mode = context_mode
        self.planner_mode = planner_mode
        self.planner_consumer = planner_consumer
        self.dwell_s = int(dwell_s)
        self.catalog = CommunicationCapabilityCatalog()
        self.compiler = CommunicationTaskCompiler()
        self.evidence_world = CommunicationEvidenceWorld()
        self.context_runtime = CommunicationContextRuntime()
        self.trace = RuntimeTrace()
        self.context_stats: list[dict] = []
        self._last_cmd_at: dict[str, int] = {}
        self._active_contract_id: str | None = None
        self._active_run_id: str | None = None
        self._context_revision = 0
        self._parent_context_id: str | None = None
        self._last_context_world_revision: int | None = None
        self._request_seq = 0
        self._request_key_to_id: dict[tuple[str, str, int], str] = {}
        self._requests: dict[str, CapabilityRequest] = {}
        self._accepted: dict[str, dict] = {}
        self._confirmed: set[str] = set()
        self._operational_task_traced = False
        self._instance = None
        self._observation_provider = None
        self._action_provider = None
        self._last_gateway_query_hour: int | None = None
        self._latest_assembly = None
        self._latest_planner_decision: PlannerDecision | None = None
        self._model_request_seq = 0

    def bind_instance(self, inst) -> None:
        # Stored only for end-of-run audit; planning never reads simulator truth.
        self._instance = inst

    def bind_observation_provider(self, provider) -> None:
        self._observation_provider = provider

    def bind_action_provider(self, provider) -> None:
        self._action_provider = provider

    def _execute_runtime_device_action(self, view, contract, invocation) -> None:
        if self._action_provider is None:
            return
        cap_id = invocation.capability_id
        cap = self.catalog.get(cap_id)
        self._request_seq += 1
        request_id = f"action:{self.seed}:{view.t_s}:{self._request_seq}:{invocation.resource}:{cap_id}"
        req = CapabilityRequest(
            request_id=request_id,
            task_contract_id=contract.task_contract_id,
            task_run_id=self._active_run_id or "",
            principal=contract.principal,
            capability_id=cap_id,
            contract_revision=cap.contract_revision,
            action=cap.action,
            resource=invocation.resource,
            resource_type=cap.applicable_resource_types[0],
            canonical_arguments=dict(invocation.canonical_arguments),
            intended_effect=EffectSemantics.EXTERNAL_SIDE_EFFECT,
            execution_context={"t_s": view.t_s},
        )
        self.trace.append("capability_request", view.t_s, req, task_run_id=self._active_run_id)
        raw = self._action_provider(
            cap_id, invocation.resource, dict(invocation.canonical_arguments)
        )
        status_map = {
            "succeeded": CapabilityResultStatus.SUCCEEDED,
            "partial": CapabilityResultStatus.PARTIAL,
            "blocked": CapabilityResultStatus.BLOCKED,
            "failed": CapabilityResultStatus.FAILED,
            "timed_out": CapabilityResultStatus.TIMED_OUT,
        }
        result = CapabilityResult(
            request_id=request_id,
            status=status_map.get(raw.get("status"), CapabilityResultStatus.FAILED),
            canonical_output=dict(raw.get("effect_receipt") or {}),
            effect_receipt=dict(raw.get("effect_receipt") or {}),
            observation_class=raw.get("observation_class", "device_action_result"),
            provenance={"owner": self.catalog.binding(cap_id).owner_location},
            latency={"simulated_s": 0},
            cost=dict(raw.get("cost") or {}),
            failure_code=raw.get("failure_code"),
        )
        self.trace.append("capability_result", view.t_s, result, task_run_id=self._active_run_id)
        if result.status == CapabilityResultStatus.SUCCEEDED:
            self.trace.append(
                "physical_effect",
                view.t_s,
                {
                    "request_id": request_id,
                    "capability_id": cap_id,
                    "resource": invocation.resource,
                    **dict(result.effect_receipt),
                },
                task_run_id=self._active_run_id,
            )

    def _query_gateway_evidence(self, view, contract, snapshot):
        if self.operational_task.family not in {
            OperationalTaskFamily.BACKHAUL_OUTAGE_SUSTAINMENT,
            OperationalTaskFamily.RECOVERY_RECONCILIATION,
            OperationalTaskFamily.COMPOUND_LONG_HORIZON,
        }:
            return snapshot
        hour = int(view.t_s // 3600)
        if self._last_gateway_query_hour == hour:
            return snapshot
        self._last_gateway_query_hour = hour
        if self._observation_provider is None:
            return snapshot

        for cap_id in (
            "communication.gateway.primary_health",
            "communication.gateway.receipt_summary",
        ):
            cap = self.catalog.get(cap_id)
            self._request_seq += 1
            request_id = f"evidence:{self.seed}:{view.t_s}:{self._request_seq}:gw0:{cap_id}"
            req = CapabilityRequest(
                request_id=request_id,
                task_contract_id=contract.task_contract_id,
                task_run_id=self._active_run_id or "",
                principal=contract.principal,
                capability_id=cap_id,
                contract_revision=cap.contract_revision,
                action=cap.action,
                resource="gw0",
                resource_type=cap.applicable_resource_types[0],
                canonical_arguments={"gateway_id": "gw0"},
                intended_effect=EffectSemantics.OBSERVATION,
                evidence_purpose="resolve owner-scoped gateway evidence for current Operational Task",
                execution_context={"world_revision": snapshot.revision, "t_s": view.t_s},
            )
            self.trace.append("capability_request", view.t_s, req, task_run_id=self._active_run_id)
            raw = self._observation_provider(cap_id, "gw0")
            if raw.get("status") == "succeeded" and raw.get("view") is not None:
                snapshot = self.evidence_world.merge_gateway_observation(
                    capability_id=cap_id,
                    view=raw["view"],
                )
                result = CapabilityResult(
                    request_id=request_id,
                    status=CapabilityResultStatus.SUCCEEDED,
                    canonical_output={
                        "evidence_refs": [
                            e.evidence_id for e in snapshot.evidence if e.proposition == cap_id
                        ]
                    },
                    observation_class=raw.get("observation_class", "gateway_owner_observation"),
                    provenance={"owner": "gateway", "world_revision": snapshot.revision},
                    latency={"simulated_s": 0},
                    cost=dict(raw.get("cost") or {}),
                )
                refs = list(result.canonical_output.get("evidence_refs") or [])
                percept = Percept(
                    percept_id=f"percept:{request_id}",
                    request_id=request_id,
                    target_refs=["gw0"],
                    observed_propositions=[
                        ObservedProposition(
                            statement=f"gateway owner observation acquired: {cap_id}",
                            support_refs=refs,
                            source_groups=["gateway"],
                            freshness={"world_revision": snapshot.revision},
                        )
                    ],
                    evidence_refs=refs,
                    source_roles=["gateway"],
                    cost=dict(result.cost),
                )
            else:
                result = CapabilityResult(
                    request_id=request_id,
                    status=CapabilityResultStatus.BLOCKED,
                    canonical_output={"evidence_refs": []},
                    observation_class=raw.get("observation_class", "unreachable"),
                    provenance={"owner": "gateway", "world_revision": snapshot.revision},
                    latency={"simulated_s": 0},
                    cost=dict(raw.get("cost") or {}),
                    failure_code=raw.get("failure_code", "unreachable"),
                )
                percept = Percept(
                    percept_id=f"percept:{request_id}",
                    request_id=request_id,
                    target_refs=["gw0"],
                    observed_propositions=[],
                    evidence_refs=[],
                    source_roles=["gateway"],
                    unresolved=[cap_id],
                    cost=dict(result.cost),
                )
            self.trace.append("capability_result", view.t_s, result, task_run_id=self._active_run_id)
            self.trace.append("percept", view.t_s, percept, task_run_id=self._active_run_id)
        return snapshot

    def _targets(self, view) -> list[str]:
        if self.operational_task.target_node_ids:
            allowed = set(view.node_ids)
            return [nid for nid in self.operational_task.target_node_ids if nid in allowed]
        return list(view.node_ids)

    def _ensure_task_run(self, view):
        contract = self.compiler.compile(self.operational_task, view.t_s)
        new_run = contract.task_contract_id != self._active_contract_id
        if new_run:
            self._active_contract_id = contract.task_contract_id
            phase_idx = self.operational_task.phase_index(view.t_s)
            self._active_run_id = (
                f"taskrun:{self.operational_task.task_id}:phase:{phase_idx}:seed:{self.seed}"
            )
            self._context_revision = 0
            self._parent_context_id = None
            self._last_context_world_revision = None
            if not self._operational_task_traced:
                self.trace.append(
                    "operational_task",
                    view.t_s,
                    self.operational_task,
                    task_run_id=self._active_run_id,
                )
                self._operational_task_traced = True
            self.trace.append(
                "runtime_task_contract",
                view.t_s,
                contract,
                task_run_id=self._active_run_id,
            )
        return contract, new_run

    def _evidence_use_trace(self, view, contract, snapshot) -> list[str]:
        """Execute local evidence-use capabilities against the Evidence World.

        This is intentionally a real CapabilityRequest/Result/Percept path even
        though the first binding is a zero-network-cost center-local lookup.
        """
        percept_refs: list[str] = []
        targets = self._targets(view)
        by_subject = {}
        for e in snapshot.evidence:
            by_subject.setdefault((e.proposition, e.subject_ref), []).append(e)

        for nid in targets:
            self._request_seq += 1
            request_id = f"evidence:{self.seed}:{view.t_s}:{self._request_seq}:{nid}"
            cap = self.catalog.get("communication.center.node_report")
            req = CapabilityRequest(
                request_id=request_id,
                task_contract_id=contract.task_contract_id,
                task_run_id=self._active_run_id or "",
                principal=contract.principal,
                capability_id=cap.capability_id,
                contract_revision=cap.contract_revision,
                action=cap.action,
                resource=nid,
                resource_type="center_node_report",
                canonical_arguments={"node_id": nid},
                intended_effect=EffectSemantics.OBSERVATION,
                evidence_purpose="construct task-conditioned communication context",
                execution_context={"world_revision": snapshot.revision},
            )
            self.trace.append("capability_request", view.t_s, req, task_run_id=self._active_run_id)
            rows = by_subject.get(("communication.center.node_report", nid), [])
            if rows:
                result = CapabilityResult(
                    request_id=request_id,
                    status=CapabilityResultStatus.SUCCEEDED,
                    canonical_output={"evidence_refs": [r.evidence_id for r in rows]},
                    observation_class="center_confirmed_report",
                    provenance={"owner": "center", "world_revision": snapshot.revision},
                    latency={"simulated_s": 0},
                    cost={"network_bytes": 0, "airtime_s": 0.0, "energy_wh": 0.0},
                )
                props = [
                    ObservedProposition(
                        statement=f"center has a confirmed node report for {nid}",
                        support_refs=[r.evidence_id for r in rows],
                        source_groups=["center"],
                        freshness={"world_revision": snapshot.revision},
                    )
                ]
                evidence_refs = [r.evidence_id for r in rows]
                unresolved = []
            else:
                result = CapabilityResult(
                    request_id=request_id,
                    status=CapabilityResultStatus.PARTIAL,
                    canonical_output={"evidence_refs": []},
                    observation_class="none_recent",
                    provenance={"owner": "center", "world_revision": snapshot.revision},
                    latency={"simulated_s": 0},
                    cost={"network_bytes": 0, "airtime_s": 0.0, "energy_wh": 0.0},
                    failure_code="none_recent",
                )
                props = []
                evidence_refs = []
                unresolved = [f"confirmed node report for {nid}"]
            self.trace.append("capability_result", view.t_s, result, task_run_id=self._active_run_id)
            percept = Percept(
                percept_id=f"percept:{request_id}",
                request_id=request_id,
                target_refs=[nid],
                observed_propositions=props,
                evidence_refs=evidence_refs,
                source_roles=["center"],
                unresolved=unresolved,
                cost=dict(result.cost),
            )
            self.trace.append("percept", view.t_s, percept, task_run_id=self._active_run_id)
            percept_refs.append(percept.percept_id)
        return percept_refs

    def _refresh_context(
        self,
        view,
        contract,
        snapshot,
        force: bool,
        recent_capability_outcomes: list[dict] | None = None,
    ) -> None:
        if not force and snapshot.revision == self._last_context_world_revision:
            return
        # The legacy deterministic path records center-local EvidenceWorld reads
        # as explicit capability calls.  A typed PlannerConsumer chooses its own
        # evidence-use capabilities, so auto-calling them here would double count
        # tool selection and make multi-round attribution impossible.
        if self.planner_consumer is None:
            self._evidence_use_trace(view, contract, snapshot)
        self._context_revision += 1
        visible = [c.capability_id for c in self.catalog.visible(contract)]
        capability_specs = self.catalog.planner_specs(contract)
        state, needs, manifest, assembly, stats = self.context_runtime.build(
            operational_task=self.operational_task,
            task=contract,
            task_run_id=self._active_run_id or "",
            evidence_world=snapshot,
            capability_ids=visible,
            capability_specs=capability_specs,
            resource_ids=list(view.node_ids),
            recent_capability_outcomes=recent_capability_outcomes,
            t_s=view.t_s,
            context_revision=self._context_revision,
            parent_context_id=self._parent_context_id,
            context_mode=self.context_mode,
        )
        self.trace.append("investigation_state", view.t_s, state, task_run_id=self._active_run_id)
        for need in needs:
            self.trace.append("evidence_need", view.t_s, need, task_run_id=self._active_run_id)
        self.trace.append("context_manifest", view.t_s, manifest, task_run_id=self._active_run_id)
        self.trace.append("prompt_assembly", view.t_s, assembly, task_run_id=self._active_run_id)
        self._latest_assembly = assembly
        if self.planner_consumer is not None:
            self._model_request_seq += 1
            inv = invoke_consumer(
                assembly=assembly,
                consumer=self.planner_consumer,
                request_id=f"model:{self.seed}:{view.t_s}:{self._model_request_seq}",
            )
            self.trace.append("model_request", view.t_s, inv.request, task_run_id=self._active_run_id)
            self.trace.append("model_attempt", view.t_s, inv.attempt, task_run_id=self._active_run_id)
            self.trace.append(
                "model_usage",
                view.t_s,
                inv.attempt.usage.model_dump(mode="json"),
                task_run_id=self._active_run_id,
            )
            if inv.decision is not None:
                self._latest_planner_decision = inv.decision
                self.trace.append(
                    "planner_decision", view.t_s, inv.decision, task_run_id=self._active_run_id
                )
            else:
                self._latest_planner_decision = None
        self.context_stats.append({"t_s": view.t_s, **stats})
        self._parent_context_id = manifest.context_id
        self._last_context_world_revision = snapshot.revision

    def _execute_planner_observation(self, view, contract, invocation, snapshot):
        cap_id = invocation.capability_id
        cap = self.catalog.get(cap_id)
        self._request_seq += 1
        request_id = f"evidence:{self.seed}:{view.t_s}:{self._request_seq}:{invocation.resource}:{cap_id}"
        req = CapabilityRequest(
            request_id=request_id,
            task_contract_id=contract.task_contract_id,
            task_run_id=self._active_run_id or "",
            principal=contract.principal,
            capability_id=cap_id,
            contract_revision=cap.contract_revision,
            action=cap.action,
            resource=invocation.resource,
            resource_type=cap.applicable_resource_types[0],
            canonical_arguments=dict(invocation.canonical_arguments),
            intended_effect=EffectSemantics.OBSERVATION,
            evidence_purpose="planner-requested evidence acquisition",
            execution_context={"world_revision": snapshot.revision, "t_s": view.t_s},
        )
        self.trace.append("capability_request", view.t_s, req, task_run_id=self._active_run_id)

        if cap_id in {
            "communication.gateway.primary_health",
            "communication.gateway.receipt_summary",
        } and self._observation_provider is not None:
            raw = self._observation_provider(cap_id, invocation.resource)
            if raw.get("status") == "succeeded" and raw.get("view") is not None:
                new_snapshot = self.evidence_world.merge_gateway_observation(
                    capability_id=cap_id,
                    view=raw["view"],
                )
                refs = [e.evidence_id for e in new_snapshot.evidence if e.proposition == cap_id]
                result = CapabilityResult(
                    request_id=request_id,
                    status=CapabilityResultStatus.SUCCEEDED,
                    canonical_output={"evidence_refs": refs},
                    observation_class=raw.get("observation_class", "gateway_owner_observation"),
                    provenance={"owner": "gateway", "world_revision": new_snapshot.revision},
                    latency={"simulated_s": 0},
                    cost=dict(raw.get("cost") or {}),
                )
                percept = Percept(
                    percept_id=f"percept:{request_id}",
                    request_id=request_id,
                    target_refs=[invocation.resource],
                    observed_propositions=[
                        ObservedProposition(
                            statement=f"planner acquired {cap_id}",
                            support_refs=refs,
                            source_groups=["gateway"],
                            freshness={"world_revision": new_snapshot.revision},
                        )
                    ],
                    evidence_refs=refs,
                    source_roles=["gateway"],
                    cost=dict(result.cost),
                )
            else:
                new_snapshot = snapshot
                result = CapabilityResult(
                    request_id=request_id,
                    status=CapabilityResultStatus.BLOCKED,
                    canonical_output={"evidence_refs": []},
                    observation_class=raw.get("observation_class", "unreachable"),
                    provenance={"owner": "gateway", "world_revision": snapshot.revision},
                    latency={"simulated_s": 0},
                    cost=dict(raw.get("cost") or {}),
                    failure_code=raw.get("failure_code", "unreachable"),
                )
                percept = Percept(
                    percept_id=f"percept:{request_id}",
                    request_id=request_id,
                    target_refs=[invocation.resource],
                    observed_propositions=[],
                    evidence_refs=[],
                    source_roles=["gateway"],
                    unresolved=[cap_id],
                    cost=dict(result.cost),
                )
        else:
            # Planner-requested center reads can be resolved from the already
            # acquired Evidence World without creating another world revision.
            rows = [
                e for e in snapshot.evidence
                if e.proposition == cap_id and e.subject_ref == invocation.resource
            ]
            new_snapshot = snapshot
            result = CapabilityResult(
                request_id=request_id,
                status=(CapabilityResultStatus.SUCCEEDED if rows else CapabilityResultStatus.PARTIAL),
                canonical_output={"evidence_refs": [e.evidence_id for e in rows]},
                observation_class=("evidence_world_read" if rows else "none_recent"),
                provenance={"owner": "center", "world_revision": snapshot.revision},
                latency={"simulated_s": 0},
                cost={"network_bytes": 0, "airtime_s": 0.0, "energy_wh": 0.0},
                failure_code=(None if rows else "none_recent"),
            )
            percept = Percept(
                percept_id=f"percept:{request_id}",
                request_id=request_id,
                target_refs=[invocation.resource],
                observed_propositions=[],
                evidence_refs=[e.evidence_id for e in rows],
                source_roles=["center"],
                unresolved=([] if rows else [cap_id]),
                cost=dict(result.cost),
            )
        self.trace.append("capability_result", view.t_s, result, task_run_id=self._active_run_id)
        self.trace.append("percept", view.t_s, percept, task_run_id=self._active_run_id)
        return new_snapshot, result, percept

    def _run_planner_evidence_rounds(self, view, contract, snapshot, *, max_rounds: int = 4):
        attempted_without_revision: set[tuple[str, str]] = set()
        for _round in range(max_rounds):
            decision = self._latest_planner_decision
            if decision is None or decision.stop:
                break
            observation_invocations = []
            for invocation in decision.invocations:
                try:
                    cap = self.catalog.get(invocation.capability_id)
                except KeyError:
                    continue
                if cap.effect_semantics == EffectSemantics.OBSERVATION:
                    observation_invocations.append(invocation)
            if not observation_invocations:
                break
            before = snapshot.revision
            attempted_any = False
            recent_outcomes: list[dict] = []
            for invocation in observation_invocations:
                key = (invocation.capability_id, invocation.resource)
                if key in attempted_without_revision:
                    continue
                attempted_any = True
                snapshot, result, percept = self._execute_planner_observation(
                    view, contract, invocation, snapshot
                )
                recent_outcomes.append(
                    {
                        "capability_id": invocation.capability_id,
                        "resource": invocation.resource,
                        "result": result.model_dump(mode="json"),
                        "percept": percept.model_dump(mode="json"),
                    }
                )
                if snapshot.revision == before:
                    attempted_without_revision.add(key)
            if not attempted_any:
                break
            if snapshot.revision != before:
                self.trace.append(
                    "evidence_world_revision",
                    view.t_s,
                    snapshot,
                    task_run_id=self._active_run_id,
                )
            # A CapabilityResult/Percept is itself new runtime information.  It
            # must advance reasoning even when factual EvidenceWorld is unchanged
            # (e.g. UNREACHABLE/TIMEOUT). Never fabricate evidence to get a revision.
            self._refresh_context(
                view,
                contract,
                snapshot,
                force=True,
                recent_capability_outcomes=recent_outcomes,
            )
        return snapshot

    def _update_confirmations(self, view) -> None:
        for request_id, meta in list(self._accepted.items()):
            if request_id in self._confirmed:
                continue
            snap = view.reports.get(meta["node_id"]) or {}
            if not snap:
                continue
            if meta["op"] == OP_SET_SAMPLING_INTERVAL:
                matched = snap.get("sample_interval_s") == meta["target"]
            elif meta["op"] == OP_SET_REPORT_PERIOD:
                matched = snap.get("report_period_s") == meta["target"]
            else:
                matched = False
            report_generation = snap.get("config_generation")
            if report_generation is not None:
                matched = matched and int(report_generation) >= int(meta["generation"])
            if matched:
                self.trace.append(
                    "physical_effect",
                    view.t_s,
                    {
                        "request_id": request_id,
                        "node_id": meta["node_id"],
                        "op": meta["op"],
                        "target": meta["target"],
                        "generation": meta["generation"],
                        "lifecycle_stage": "applied_confirmed",
                        "accepted_at_s": meta["accepted_at_s"],
                        "confirmed_at_s": view.t_s,
                    },
                    task_run_id=meta["task_run_id"],
                )
                self._confirmed.add(request_id)

    def _register_action_request(self, view, contract, nid: str, payload: dict) -> None:
        op = payload["op"]
        cap_id = _ACTION_CAPABILITY[op]
        cap = self.catalog.get(cap_id)
        self._request_seq += 1
        request_id = f"action:{self.seed}:{view.t_s}:{self._request_seq}:{nid}:{op}"
        if op == OP_SET_SAMPLING_INTERVAL:
            target = int(payload["interval_s"])
        else:
            target = int(payload["period_s"])
        req = CapabilityRequest(
            request_id=request_id,
            task_contract_id=contract.task_contract_id,
            task_run_id=self._active_run_id or "",
            principal=contract.principal,
            capability_id=cap_id,
            contract_revision=cap.contract_revision,
            action=cap.action,
            resource=nid,
            resource_type="monitoring_node_config",
            canonical_arguments={
                "node_id": nid,
                "target_s": target,
                "generation": int(payload["generation"]),
            },
            intended_effect=EffectSemantics.EXTERNAL_SIDE_EFFECT,
            execution_context={"t_s": view.t_s},
        )
        key = (nid, op, int(payload["generation"]))
        self._request_key_to_id[key] = request_id
        self._requests[request_id] = req
        self.trace.append("capability_request", view.t_s, req, task_run_id=self._active_run_id)

    def plan(self, view):
        self._skip_t = view.t_s
        self._update_confirmations(view)
        contract, new_run = self._ensure_task_run(view)
        snapshot = self.evidence_world.observe(view)
        if self.planner_consumer is None:
            snapshot = self._query_gateway_evidence(view, contract, snapshot)
        if new_run or snapshot.revision != self._last_context_world_revision:
            self.trace.append(
                "evidence_world_revision",
                view.t_s,
                snapshot,
                task_run_id=self._active_run_id,
            )
        self._refresh_context(view, contract, snapshot, force=new_run)

        if self.planner_consumer is not None:
            snapshot = self._run_planner_evidence_rounds(view, contract, snapshot)
            return self._actions_from_planner_decision(view, contract)

        if self.planner_mode != "comply":
            raise ValueError(f"unsupported planner_mode {self.planner_mode!r}")

        req_period = self.operational_task.phase_at(view.t_s).required_period_s
        targets = self._targets(view)
        actions: list[tuple[str, dict]] = []
        for nid in targets:
            if nid in view.in_flight:
                self._skip("in_flight", nid)
                continue
            last = self._last_cmd_at.get(nid)
            if last is not None and view.t_s - last < self.dwell_s:
                self._skip("dwell", nid)
                continue
            snap = view.reports.get(nid) or {}
            if (
                snap.get("sample_interval_s") == req_period
                and snap.get("report_period_s") == req_period
            ):
                self._skip("at_target", nid)
                continue
            self._last_cmd_at[nid] = view.t_s
            left, right = self.stamp_pair(
                nid,
                {"op": OP_SET_SAMPLING_INTERVAL, "interval_s": req_period},
                {"op": OP_SET_REPORT_PERIOD, "period_s": req_period},
            )
            actions.extend([(nid, left), (nid, right)])
            self._register_action_request(view, contract, nid, left)
            self._register_action_request(view, contract, nid, right)

        if actions:
            self.trace.append(
                "planner_decision",
                view.t_s,
                {
                    "planner": "deterministic_comply",
                    "context_revision": self._context_revision,
                    "required_period_s": req_period,
                    "actions": [{"node_id": n, **p} for n, p in actions],
                },
                task_run_id=self._active_run_id,
            )
        return actions

    def _actions_from_planner_decision(self, view, contract):
        decision = self._latest_planner_decision
        if decision is None or decision.stop:
            return []
        allowed = set(self.operational_task.authorized_effects)
        per_node: dict[str, dict[str, int]] = {}
        for invocation in decision.invocations:
            if invocation.capability_id not in allowed:
                continue
            if invocation.capability_id in {
                "communication.fallback.gateway_backup",
                "communication.fallback.terminal_dts",
                "communication.fallback.access_assist",
            }:
                self._execute_runtime_device_action(view, contract, invocation)
                continue
            if invocation.resource not in self._targets(view):
                continue
            target_s = invocation.canonical_arguments.get("target_s")
            if target_s is None:
                continue
            per_node.setdefault(invocation.resource, {})[invocation.capability_id] = int(target_s)

        actions: list[tuple[str, dict]] = []
        for nid, wants in sorted(per_node.items()):
            if nid in view.in_flight:
                self._skip("in_flight", nid)
                continue
            last = self._last_cmd_at.get(nid)
            if last is not None and view.t_s - last < self.dwell_s:
                self._skip("dwell", nid)
                continue
            snap = view.reports.get(nid) or {}
            sample = wants.get("communication.config.set_sampling_interval")
            report = wants.get("communication.config.set_report_period")
            payloads: list[dict] = []
            if sample is not None and report is not None:
                # Preserve the planner's paired configuration intent.  If either
                # field is not confirmed, both fields are resent under the same
                # generation.  The runtime must not silently optimize a typed
                # pair into a single-field write, because that changes generation
                # semantics and the physical retry trajectory.
                if (
                    snap.get("sample_interval_s") != sample
                    or snap.get("report_period_s") != report
                ):
                    payloads = [
                        {"op": OP_SET_SAMPLING_INTERVAL, "interval_s": sample},
                        {"op": OP_SET_REPORT_PERIOD, "period_s": report},
                    ]
            else:
                if sample is not None and snap.get("sample_interval_s") != sample:
                    payloads.append({"op": OP_SET_SAMPLING_INTERVAL, "interval_s": sample})
                if report is not None and snap.get("report_period_s") != report:
                    payloads.append({"op": OP_SET_REPORT_PERIOD, "period_s": report})
            if not payloads:
                self._skip("at_target", nid)
                continue
            self._last_cmd_at[nid] = view.t_s
            stamped: list[dict]
            if len(payloads) == 2:
                left, right = self.stamp_pair(nid, payloads[0], payloads[1])
                stamped = [left, right]
            else:
                stamped = [self.stamp(nid, **payloads[0])]
            for payload in stamped:
                actions.append((nid, payload))
                self._register_action_request(view, contract, nid, payload)
        return actions

    def _request_for_payload(self, node_id: str, payload: dict) -> CapabilityRequest | None:
        key = (node_id, payload["op"], int(payload.get("generation", -1)))
        request_id = self._request_key_to_id.get(key)
        return None if request_id is None else self._requests.get(request_id)

    def note_command_sent(self, node_id: str, payload: dict) -> None:
        req = self._request_for_payload(node_id, payload)
        if req is None:
            return
        target = (
            int(payload["interval_s"])
            if payload["op"] == OP_SET_SAMPLING_INTERVAL
            else int(payload["period_s"])
        )
        result = CapabilityResult(
            request_id=req.request_id,
            status=CapabilityResultStatus.SUCCEEDED,
            canonical_output={"submission": "accepted_unconfirmed"},
            effect_receipt={
                "lifecycle_stage": "accepted",
                "node_id": node_id,
                "generation": int(payload["generation"]),
            },
            observation_class="accepted_unconfirmed",
            provenance={"surface": "CenterPolicy.note_command_sent"},
            latency={"submission_s": 0},
            cost={"authority": "full_simulator_counters"},
        )
        self.trace.append("capability_result", self._skip_t, result, task_run_id=req.task_run_id)
        self._accepted[req.request_id] = {
            "node_id": node_id,
            "op": payload["op"],
            "target": target,
            "generation": int(payload["generation"]),
            "accepted_at_s": self._skip_t,
            "task_run_id": req.task_run_id,
        }

    def note_command_refused(self, node_id: str, payload: dict) -> None:
        req = self._request_for_payload(node_id, payload)
        if req is None:
            return
        result = CapabilityResult(
            request_id=req.request_id,
            status=CapabilityResultStatus.BLOCKED,
            canonical_output={"submission": "refused"},
            effect_receipt={"lifecycle_stage": "refused", "node_id": node_id},
            observation_class="unreachable",
            provenance={"surface": "CenterPolicy.note_command_refused"},
            latency={"submission_s": 0},
            cost={"authority": "full_simulator_counters"},
            failure_code="control_path_unavailable",
        )
        self.trace.append("capability_result", self._skip_t, result, task_run_id=req.task_run_id)

    def finalize(self, *, t_s: int, physical_result: dict) -> None:
        if self._active_run_id is None:
            return
        self.trace.append(
            "task_completion",
            t_s,
            {
                "status": TaskRunStatus.COMPLETED.value,
                "routine": physical_result.get("routine", {}),
                "survival": physical_result.get("survival", {}),
                "command_counters": physical_result.get("command_counters", {}),
                "unconfirmed_requests": sorted(
                    rid for rid in self._accepted if rid not in self._confirmed
                ),
            },
            task_run_id=self._active_run_id,
        )

    def trace_summary(self) -> dict:
        contexts = self.context_stats
        return {
            "events": len(self.trace.events),
            "runtime_task_contracts": self.trace.count("runtime_task_contract"),
            "evidence_world_revisions": self.trace.count("evidence_world_revision"),
            "evidence_needs": self.trace.count("evidence_need"),
            "capability_requests": self.trace.count("capability_request"),
            "capability_results": self.trace.count("capability_result"),
            "percepts": self.trace.count("percept"),
            "context_manifests": self.trace.count("context_manifest"),
            "planner_decisions": self.trace.count("planner_decision"),
            "model_requests": self.trace.count("model_request"),
            "model_attempts": self.trace.count("model_attempt"),
            "model_usage_records": self.trace.count("model_usage"),
            "physical_effects_confirmed": self.trace.count("physical_effect"),
            "accepted_requests": len(self._accepted),
            "confirmed_requests": len(self._confirmed),
            "unconfirmed_requests": len(self._accepted) - len(self._confirmed),
            "contexts": len(contexts),
            "mean_selected_evidence": (
                sum(x["selected_evidence_count"] for x in contexts) / len(contexts)
                if contexts else 0.0
            ),
            "mean_materialized_bytes": (
                sum(x["materialized_bytes"] for x in contexts) / len(contexts)
                if contexts else 0.0
            ),
            "required_evidence_recall": (
                sum(x["required_selected_count"] for x in contexts)
                / max(1, sum(x["required_evidence_count"] for x in contexts))
            ),
        }
