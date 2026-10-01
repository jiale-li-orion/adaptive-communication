"""Evidence World -> InvestigationState -> ContextManifest -> PromptAssembly."""
from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from .contracts import EvidenceWorldSnapshot, OperationalTask, OperationalTaskFamily
from .runtime_contracts import (
    ContextManifest,
    EvidenceNeed,
    EvidenceNeedContract,
    EvidenceNeedStatus,
    FragmentCacheClass,
    FragmentTrustClass,
    InvestigationState,
    InvestigationStateItem,
    MaterializedFragment,
    PromptAssembly,
    ProposedState,
    TaskContract,
)
from .timebase import sim_datetime


class CommunicationContextRuntime:
    revision = "communication-context-runtime-v1"

    def build(
        self,
        *,
        operational_task: OperationalTask,
        task: TaskContract,
        task_run_id: str,
        evidence_world: EvidenceWorldSnapshot,
        capability_ids: list[str],
        capability_specs: list[dict] | None = None,
        resource_ids: list[str] | None = None,
        recent_capability_outcomes: list[dict] | None = None,
        t_s: int,
        context_revision: int,
        parent_context_id: str | None,
        context_mode: str = "task_conditioned",
    ) -> tuple[InvestigationState, list[EvidenceNeed], ContextManifest, PromptAssembly, dict]:
        phase = operational_task.phase_at(t_s)
        targets = set(operational_task.target_node_ids)
        if not targets:
            targets = set(resource_ids or ())
        if not targets:
            targets = {
                e.subject_ref
                for e in evidence_world.evidence
                if e.proposition == "communication.center.node_report"
            }

        reports = {
            e.subject_ref: e
            for e in evidence_world.evidence
            if e.proposition == "communication.center.node_report" and e.subject_ref in targets
        }
        now = sim_datetime(t_s)
        needs: list[EvidenceNeed] = []
        confirmed: list[InvestigationStateItem] = []
        unknowns: list[InvestigationStateItem] = []
        required_refs: list[str] = []
        recent_outcomes = list(recent_capability_outcomes or [])
        blocked_observations: dict[tuple[str, str], dict] = {}
        for row in recent_outcomes:
            if not isinstance(row, dict):
                continue
            result = row.get("result") or {}
            if result.get("status") in {"blocked", "timed_out", "failed", "partial"}:
                blocked_observations[(str(row.get("capability_id", "")), str(row.get("resource", "")))] = row

        gateway_needed = operational_task.family in {
            OperationalTaskFamily.BACKHAUL_OUTAGE_SUSTAINMENT,
            OperationalTaskFamily.RECOVERY_RECONCILIATION,
            OperationalTaskFamily.COMPOUND_LONG_HORIZON,
        }
        gateway_max_age_s = 3600
        gateway_props = {
            e.proposition: e
            for e in evidence_world.evidence
            if e.proposition
            in {
                "communication.gateway.primary_health",
                "communication.gateway.receipt_summary",
            }
            and int(t_s) - int(e.observed_at_s) <= gateway_max_age_s
        }
        if gateway_needed:
            for prop, purpose in (
                (
                    "communication.gateway.primary_health",
                    "determine whether primary backhaul recovery/outage changes the legal communication plan",
                ),
                (
                    "communication.gateway.receipt_summary",
                    "distinguish access-side receipt from center-side delivery loss",
                ),
            ):
                ev = gateway_props.get(prop)
                if ev is None:
                    blocked = blocked_observations.get((prop, "gw0"))
                    need_status = (
                        EvidenceNeedStatus.BLOCKED if blocked is not None else EvidenceNeedStatus.OPEN
                    )
                    needs.append(
                        EvidenceNeed(
                            need_id=f"need:{task_run_id}:{prop}",
                            task_run_id=task_run_id,
                            proposition_or_question=f"What is the current {prop}?",
                            purpose=purpose,
                            target_objects=["gw0"],
                            evidence_contract=EvidenceNeedContract(
                                required_source_roles=["gateway"],
                                min_independent_sources=1,
                                accepted_states=[ProposedState.CONFIRMED, ProposedState.UNKNOWN],
                            ),
                            preferred_source_roles=["gateway"],
                            freshness_requirement={"max_age_s": gateway_max_age_s},
                            completion_predicate={"type": "gateway_owner_observation_or_blocked"},
                            priority=90,
                            status=need_status,
                            opened_revision=evidence_world.revision,
                            updated_revision=evidence_world.revision,
                            opened_at=now,
                            updated_at=now,
                        )
                    )
                    unknowns.append(
                        InvestigationStateItem(
                            proposition=(
                                f"{prop} query blocked in current runtime round"
                                if blocked is not None
                                else f"{prop} unavailable at center"
                            ),
                            target_ref="gw0",
                            evidence_refs=[],
                            writer="communication-context-runtime",
                            reason_code=(
                                "gateway_owner_query_blocked"
                                if blocked is not None
                                else "missing_gateway_owner_evidence"
                            ),
                            updated_revision=evidence_world.revision,
                        )
                    )
                else:
                    required_refs.append(ev.evidence_id)
                    confirmed.append(
                        InvestigationStateItem(
                            proposition=f"gateway owner evidence available: {prop}",
                            target_ref="gw0",
                            evidence_refs=[ev.evidence_id],
                            writer="communication-context-runtime",
                            reason_code="gateway_owner_observation",
                            updated_revision=evidence_world.revision,
                        )
                    )

        for nid in sorted(targets):
            ev = reports.get(nid)
            if ev is None:
                need_id = f"need:{task_run_id}:{nid}:confirmed_config"
                needs.append(
                    EvidenceNeed(
                        need_id=need_id,
                        task_run_id=task_run_id,
                        proposition_or_question=f"What configuration is currently confirmed for {nid}?",
                        purpose="decide whether the authorized monitoring profile still needs installation",
                        target_objects=[nid],
                        evidence_contract=EvidenceNeedContract(
                            required_source_roles=["center", "monitoring_node"],
                            min_independent_sources=1,
                            accepted_states=[ProposedState.CONFIRMED, ProposedState.UNKNOWN],
                        ),
                        preferred_source_roles=["center"],
                        freshness_requirement={"max_age_s": max(phase.required_period_s, 600)},
                        completion_predicate={"type": "confirmed_node_report_or_blocked"},
                        priority=80,
                        status=EvidenceNeedStatus.OPEN,
                        opened_revision=evidence_world.revision,
                        updated_revision=evidence_world.revision,
                        opened_at=now,
                        updated_at=now,
                    )
                )
                unknowns.append(
                    InvestigationStateItem(
                        proposition=f"confirmed configuration for {nid} is unknown",
                        target_ref=nid,
                        evidence_refs=[],
                        writer="communication-context-runtime",
                        reason_code="missing_center_node_report",
                        updated_revision=evidence_world.revision,
                    )
                )
                continue
            required_refs.append(ev.evidence_id)
            value = dict(ev.value) if isinstance(ev.value, dict) else {}
            confirmed.append(
                InvestigationStateItem(
                    proposition=(
                        f"{nid} confirmed sample={value.get('sample_interval_s')}s "
                        f"report={value.get('report_period_s')}s"
                    ),
                    target_ref=nid,
                    evidence_refs=[ev.evidence_id],
                    writer="communication-context-runtime",
                    reason_code="center_confirmed_node_report",
                    updated_revision=evidence_world.revision,
                )
            )

        state = InvestigationState(
            task_run_id=task_run_id,
            # Runtime cognitive state can advance after a tool outcome even when
            # factual EvidenceWorld does not. Keep the two revision domains separate.
            state_revision=context_revision,
            goal=(
                f"execute {operational_task.family.value} at {phase.required_period_s}s "
                f"for phase {operational_task.phase_index(t_s)}"
            ),
            targets=sorted(targets),
            confirmed=confirmed,
            unknowns=unknowns,
            evidence_need_ids=[n.need_id for n in needs],
            last_world_revision=evidence_world.revision,
            last_perception_at=now,
            updated_at=now,
        )

        if context_mode in {"full_dump", "generic_react"}:
            selected = list(evidence_world.evidence)
        elif context_mode == "task_conditioned":
            selected = [
                e
                for e in evidence_world.evidence
                if (
                    e.subject_ref in targets
                    and e.proposition
                    in {"communication.center.node_report", "communication.center.delivery_status"}
                )
                or e.proposition == "communication.center.link_summary"
                or (gateway_needed and e.proposition in {
                    "communication.gateway.primary_health",
                    "communication.gateway.receipt_summary",
                })
            ]
        else:
            raise ValueError(f"unknown context_mode {context_mode!r}")

        context_id = str(
            uuid5(
                NAMESPACE_URL,
                f"agentic-communication:context:{task_run_id}:{context_revision}:{evidence_world.digest}",
            )
        )
        manifest = ContextManifest(
            context_id=context_id,
            context_revision=context_revision,
            parent_context_id=parent_context_id,
            task_contract_ref=task.task_contract_id,
            investigation_state_ref=f"investigation:{task_run_id}:{state.state_revision}",
            evidence_refs=[e.evidence_id for e in selected],
            capability_refs=list(capability_ids),
            policy_context_ref="policy:agentic-communication-v1",
            budget_ref="budget:physical-scorer-v1",
            world_revision=evidence_world.revision,
        )

        materialized_evidence = []
        for e in selected:
            row = e.model_dump(mode="json")
            basis_t = e.generated_at_s if e.generated_at_s is not None else e.observed_at_s
            row["freshness_at_materialization"] = {
                "age_s": max(0, int(t_s) - int(basis_t)),
                "materialized_at_s": int(t_s),
            }
            if e.proposition == "communication.center.delivery_status" and isinstance(e.value, dict):
                newest = e.value.get("newest_taken_at")
                if newest is not None:
                    row["freshness_at_materialization"]["aoi_s"] = max(
                        0, int(t_s) - int(newest)
                    )
            materialized_evidence.append(row)

        fragments = [
            MaterializedFragment.build(
                kind="resource_inventory",
                source_ref="communication-resource-inventory",
                source_revision="1",
                trust_class=FragmentTrustClass.PLATFORM_INVARIANT,
                cache_class=FragmentCacheClass.STATIC,
                content=sorted(targets),
                selection_reason="operational_task_target_inventory",
            ),
            MaterializedFragment.build(
                kind="runtime_task_contract",
                source_ref=task.task_contract_id,
                source_revision=str(task.contract_revision),
                trust_class=FragmentTrustClass.RUNTIME_CONTROL,
                cache_class=FragmentCacheClass.TASK_STABLE,
                content=task.model_dump(mode="json"),
                selection_reason="active_runtime_task",
            ),
            MaterializedFragment.build(
                kind="evidence_slice",
                source_ref=f"evidence-world:{evidence_world.revision}",
                source_revision=str(evidence_world.revision),
                trust_class=FragmentTrustClass.EVIDENCE_REFERENCE,
                cache_class=FragmentCacheClass.STATE_DYNAMIC,
                content=materialized_evidence,
                selection_reason=context_mode,
            ),
            MaterializedFragment.build(
                kind="recent_capability_outcomes",
                source_ref=f"runtime-capability-outcomes:{task_run_id}",
                source_revision=str(context_revision),
                trust_class=FragmentTrustClass.RUNTIME_CONTROL,
                cache_class=FragmentCacheClass.EPHEMERAL,
                content=recent_outcomes,
                selection_reason="latest_runtime_tool_outcomes",
            ),
            MaterializedFragment.build(
                kind="capability_catalog",
                source_ref="communication-capability-catalog",
                source_revision="0.1",
                trust_class=FragmentTrustClass.PLATFORM_INVARIANT,
                cache_class=FragmentCacheClass.STATIC,
                content=(list(capability_specs) if capability_specs is not None else list(capability_ids)),
                selection_reason="task_visible_capabilities",
            ),
        ]
        if context_mode != "generic_react":
            # Harness-specific cognitive artifacts.  The generic ReAct baseline
            # deliberately omits them while preserving the same legal raw
            # evidence, TaskContract, capability surface and physical runtime.
            fragments[2:2] = [
                MaterializedFragment.build(
                    kind="investigation_state",
                    source_ref=state.task_run_id,
                    source_revision=str(state.state_revision),
                    trust_class=FragmentTrustClass.DURABLE_STATE,
                    cache_class=FragmentCacheClass.STATE_DYNAMIC,
                    content=state.model_dump(mode="json"),
                    selection_reason="current_task_state",
                ),
                MaterializedFragment.build(
                    kind="evidence_needs",
                    source_ref=f"evidence-needs:{task_run_id}",
                    source_revision=str(evidence_world.revision),
                    trust_class=FragmentTrustClass.DURABLE_STATE,
                    cache_class=FragmentCacheClass.STATE_DYNAMIC,
                    content=[n.model_dump(mode="json") for n in needs],
                    selection_reason="open_task_evidence_requirements",
                ),
            ]
        assembly = PromptAssembly.build(
            task_contract_id=task.task_contract_id,
            task_run_id=task_run_id,
            context_manifest_revision=context_revision,
            fragments=fragments,
            percept_refs=[
                str((row.get("percept") or {}).get("percept_id"))
                for row in recent_outcomes
                if isinstance(row, dict) and (row.get("percept") or {}).get("percept_id")
            ],
        )
        selected_ids = {e.evidence_id for e in selected}
        stats = {
            "evidence_world_count": len(evidence_world.evidence),
            "selected_evidence_count": len(selected),
            "required_evidence_count": len(required_refs),
            "required_selected_count": sum(ref in selected_ids for ref in required_refs),
            "evidence_needs": len(needs),
            "open_evidence_needs": sum(n.status == EvidenceNeedStatus.OPEN for n in needs),
            "blocked_evidence_needs": sum(n.status == EvidenceNeedStatus.BLOCKED for n in needs),
            "fragment_count": len(fragments),
            "materialized_bytes": len(assembly.model_dump_json().encode("utf-8")),
            "harness_cognitive_fragments_exposed": context_mode != "generic_react",
        }
        return state, needs, manifest, assembly, stats
