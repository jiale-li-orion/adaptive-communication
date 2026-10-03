"""Evidence World -> InvestigationState -> ContextManifest -> PromptAssembly."""
from __future__ import annotations

import hashlib
import json
from uuid import NAMESPACE_URL, uuid5

from .action_context import ActionConditionedContextSelector
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

    def __init__(self) -> None:
        self.action_selector = ActionConditionedContextSelector()

    @staticmethod
    def _shadow_plan_ids(candidate_context: dict) -> set[str]:
        disagreement = candidate_context.get("candidate_disagreement") or {}
        closure = disagreement.get("action_closure") or {}
        eligibility = str(closure.get("control_eligibility") or "eligible")
        if not eligibility.startswith("shadow_only"):
            return set()
        return {
            str(row.get("plan_id"))
            for row in candidate_context.get("candidate_plans", [])
            if isinstance(row, dict)
            and row.get("plan_id")
            and row.get("kind") in {"fallback", "future_task_preparation"}
        }

    @classmethod
    def _control_relevant_needs(
        cls,
        candidate_context: dict,
        needs: list[EvidenceNeed],
    ) -> list[EvidenceNeed]:
        """Drop acquisition needs that can only refine a shadow-only branch."""
        shadow_ids = cls._shadow_plan_ids(candidate_context)
        if not shadow_ids:
            return list(needs)
        visible_plan_ids = {
            str(row.get("plan_id"))
            for row in candidate_context.get("candidate_plans", [])
            if isinstance(row, dict)
            and row.get("plan_id")
            and str(row.get("plan_id")) not in shadow_ids
        }
        out: list[EvidenceNeed] = []
        for need in needs:
            scoped = set(need.blocking_plan_ids)
            if scoped and not (scoped & visible_plan_ids):
                continue
            out.append(need)
        return out

    @classmethod
    def _compact_candidate_projection(
        cls,
        candidate_context: dict,
        needs: list[EvidenceNeed] | None = None,
        *,
        retire_inactive_unresolved: bool = False,
    ) -> dict:
        """Project the full candidate audit object into model-facing Context.

        The full action-context object intentionally carries enough detail for
        audit/replay (all dependency rows, pair graph, greedy shadow cover).  A
        model does not need resolved audit rows after deterministic guard
        evaluation.  Compact mode keeps executable candidate semantics,
        unresolved evidence dependencies and a digest of the full audit object.
        """
        canonical = json.dumps(
            candidate_context,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        shadow_ids = cls._shadow_plan_ids(candidate_context)
        visible_plan_ids = {
            str(row.get("plan_id"))
            for row in candidate_context.get("candidate_plans", [])
            if isinstance(row, dict)
            and row.get("plan_id")
            and str(row.get("plan_id")) not in shadow_ids
        }
        plans: list[dict] = []
        for row in candidate_context.get("candidate_plans", []):
            if str(row.get("plan_id")) in shadow_ids:
                continue
            projected = {
                key: row[key]
                for key in (
                    "plan_id",
                    "kind",
                    "feasibility",
                    "decision_guards",
                    "affected_resources",
                    "invocations",
                    "unresolved_conditions",
                    "contradicted_by",
                    "reason",
                )
                if key in row
            }
            if (
                retire_inactive_unresolved
                and projected.get("feasibility") in {"rejected", "dominated"}
            ):
                projected.pop("unresolved_conditions", None)
            plans.append(projected)

        control_needs = cls._control_relevant_needs(candidate_context, list(needs or []))
        ready_supported = [
            plan
            for plan in plans
            if plan.get("feasibility") == "supported"
            and not bool(plan.get("unresolved_conditions"))
        ]
        live_visible = [
            plan
            for plan in plans
            if plan.get("feasibility") not in {"dominated", "rejected"}
        ]
        decision_sufficiency: dict = {
            "status": "undetermined",
            "primary_plan_id": None,
            "blocking_need_ids": [],
            "nonblocking_open_need_ids": [],
        }
        if len(ready_supported) == 1:
            primary = ready_supported[0]
            primary_plan_id = str(primary.get("plan_id"))
            has_effect = bool(primary.get("invocations"))
            # A supported effect may be safely committed while a different
            # conditional branch remains unresolved, provided its open needs do
            # not block the primary plan. A zero-effect hold is stronger: it is
            # only decision-complete when no other control-visible live plan
            # remains, otherwise evidence may still justify a real effect.
            zero_effect_closed = has_effect or len(live_visible) == 1
            if zero_effect_closed:
                blocking_need_ids: list[str] = []
                nonblocking_need_ids: list[str] = []
                for need in control_needs:
                    scoped = list(need.blocking_plan_ids)
                    if not scoped or primary_plan_id in scoped:
                        blocking_need_ids.append(need.need_id)
                    else:
                        nonblocking_need_ids.append(need.need_id)
                if has_effect:
                    status = (
                        "sufficient_for_primary_action"
                        if not blocking_need_ids
                        else "blocked_for_primary_action"
                    )
                else:
                    status = (
                        "sufficient_for_no_action"
                        if not blocking_need_ids
                        else "blocked_for_no_action"
                    )
                decision_sufficiency = {
                    "status": status,
                    "primary_plan_id": primary_plan_id,
                    "primary_plan_feasibility": "supported",
                    "blocking_need_ids": sorted(blocking_need_ids),
                    "nonblocking_open_need_ids": sorted(nonblocking_need_ids),
                    "interpretation": (
                        "model-visible control surface is decision-complete for the primary plan; "
                        "open evidence attached only to alternative plans does not block that plan"
                    ),
                }
            if row.get("support_refs"):
                plans[-1]["support_ref_count"] = len(row["support_refs"])

        unresolved_dependencies = []
        for row in candidate_context.get("dependencies", []):
            if bool(row.get("fresh")):
                continue
            scoped = set(str(x) for x in (row.get("blocking_plan_ids") or []))
            if scoped and not (scoped & visible_plan_ids):
                continue
            unresolved_dependencies.append(
                {
                    key: row.get(key)
                    for key in (
                        "proposition",
                        "subject",
                        "purpose",
                        "scope_reason",
                        "evidence_ref",
                        "age_s",
                        "acquisition",
                        "blocked_recently",
                    )
                }
            )

        disagreement = candidate_context.get("candidate_disagreement") or {}
        return {
            "selector_revision": candidate_context.get("selector_revision"),
            "operational_task_id": candidate_context.get("operational_task_id"),
            "task_contract_id": candidate_context.get("task_contract_id"),
            "phase_index": candidate_context.get("phase_index"),
            "required_period_s": candidate_context.get("required_period_s"),
            "action_scope": candidate_context.get("action_scope", []),
            "evidence_scope": candidate_context.get("evidence_scope", []),
            "candidate_plans": plans,
            "shadow_candidate_plan_ids": sorted(shadow_ids),
            "decision_sufficiency": decision_sufficiency,
            "fallback_relevance": (
                None if shadow_ids else candidate_context.get("fallback_relevance")
            ),
            "unresolved_dependencies": unresolved_dependencies,
            "open_dependency_count": len(unresolved_dependencies),
            "action_closure": {
                "model_control_surface": "eligible_plans_only",
                "shadow_candidate_count": len(shadow_ids),
                "full_audit_control_eligibility": (
                    (disagreement.get("action_closure") or {}).get("control_eligibility")
                ),
            },
            "selection_rule": candidate_context.get("selection_rule"),
            "full_candidate_audit_sha256": hashlib.sha256(canonical).hexdigest(),
        }

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

        action_mode = context_mode in {
            "action_conditioned",
            "action_conditioned_compact",
            "action_conditioned_compact_v7",
            "action_candidates_full_dump",
            "woa_style",
        }
        candidate_context: dict | None = None
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
        if action_mode:
            selection = self.action_selector.select(
                operational_task=operational_task,
                task=task,
                task_run_id=task_run_id,
                evidence_world=evidence_world,
                capability_ids=capability_ids,
                resource_ids=resource_ids,
                recent_capability_outcomes=recent_outcomes,
                t_s=t_s,
                now=now,
            )
            needs = selection.needs
            confirmed = selection.confirmed
            unknowns = selection.unknowns
            required_refs = selection.required_refs
            candidate_context = selection.candidate_context
            if context_mode in {
                "action_conditioned_compact",
                "action_conditioned_compact_v7",
                "woa_style",
            }:
                needs = self._control_relevant_needs(candidate_context, needs)
        elif gateway_needed:
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

        for nid in ([] if action_mode else sorted(targets)):
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

        if context_mode in {"full_dump", "generic_react", "action_candidates_full_dump", "woa_style"}:
            selected = list(evidence_world.evidence)
        elif context_mode in {"action_conditioned_compact", "action_conditioned_compact_v7"}:
            selected = list(selection.compact_selected)
        elif context_mode == "action_conditioned":
            selected = list(selection.selected)
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
        if candidate_context is not None:
            model_candidate_context = (
                self._compact_candidate_projection(
                    candidate_context,
                    needs,
                    retire_inactive_unresolved=(context_mode == "action_conditioned_compact_v7"),
                )
                if context_mode
                in {"action_conditioned_compact", "action_conditioned_compact_v7", "woa_style"}
                else candidate_context
            )
            if context_mode == "woa_style":
                # Strong WirelessOpsAgent-style baseline: share the exact same
                # control-eligible candidate menu, but do not expose the Method's
                # explicit decision-sufficiency certificate.  The assurance layer
                # must reconstruct authorization from public evidence, candidate
                # state and execution contract instead.
                model_candidate_context = dict(model_candidate_context)
                model_candidate_context.pop("decision_sufficiency", None)
            fragments.insert(
                2,
                MaterializedFragment.build(
                    kind="candidate_action_context",
                    source_ref=f"action-context:{task_run_id}",
                    source_revision=self.action_selector.revision,
                    trust_class=FragmentTrustClass.RUNTIME_CONTROL,
                    cache_class=FragmentCacheClass.STATE_DYNAMIC,
                    content=model_candidate_context,
                    selection_reason="candidate_action_backward_evidence_tracing",
                ),
            )
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
            "candidate_action_plans": (
                0
                if candidate_context is None
                else len(candidate_context.get("candidate_plans", []))
            ),
            "candidate_dependencies": (
                0
                if candidate_context is None
                else len(candidate_context.get("dependencies", []))
            ),
        }
        return state, needs, manifest, assembly, stats
