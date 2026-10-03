"""Action-conditioned context selection for Agentic Communication.

The selector starts from *legal candidate communication actions* and traces
backward to the evidence that can distinguish those candidates.  It is a method
component, not another runtime contract: existing Task/Evidence/Context/
Capability schemas remain unchanged.

The first executable coordinate is localized O2.  There the selector compares
"hold the confirmed profile" against "install the task-required profile" and
therefore needs confirmed configuration evidence for the authorised targets,
but not unrelated delivery/AoI telemetry.  The same selector already declares
shared gateway/access dependencies for O3/O5/O6 so later coordinates can expand
evidence scope beyond action scope without widening action authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from .contracts import CommunicationEvidence, EvidenceWorldSnapshot, OperationalTask
from .runtime_contracts import (
    EvidenceNeed,
    EvidenceNeedContract,
    EvidenceNeedStatus,
    InvestigationStateItem,
    ProposedState,
    TaskContract,
)


ACTIVE_OBSERVATION_CAPABILITIES = {
    "communication.gateway.primary_health",
    "communication.gateway.receipt_summary",
    "communication.gateway.node_report",
}


@dataclass(frozen=True)
class _Dependency:
    proposition: str
    subjects: tuple[str, ...]
    purpose: str
    max_age_s: int
    source_roles: tuple[str, ...]
    scope_reason: str
    blocking_plan_ids: tuple[str, ...] = ()
    freshness_basis: str = "observed_at_s"


@dataclass
class ActionContextSelection:
    selected: list[CommunicationEvidence]
    compact_selected: list[CommunicationEvidence]
    required_refs: list[str]
    needs: list[EvidenceNeed]
    confirmed: list[InvestigationStateItem]
    unknowns: list[InvestigationStateItem]
    candidate_context: dict


class ActionConditionedContextSelector:
    revision = "action-conditioned-context-v1"

    @staticmethod
    def _greedy_guard_cover(
        disagreement_pairs: list[dict], dep_states: list[dict]
    ) -> dict:
        """Shadow acquisition planner over candidate-plan disagreement guards.

        This deliberately avoids probabilities and arbitrary acquisition costs.
        A candidate pair is already separated when at least one of its guard
        families is fully supported by fresh evidence.  Remaining pairs are
        greedily covered by unresolved guard families that have a real active
        observation capability. Passive-refresh and currently unwired guards are
        reported separately rather than being assigned a made-up utility.
        """

        by_guard: dict[str, list[dict]] = {}
        for row in dep_states:
            by_guard.setdefault(str(row.get("scope_reason", "")), []).append(row)

        ready: set[str] = set()
        active: set[str] = set()
        passive: set[str] = set()
        blocked: set[str] = set()
        for guard, rows in by_guard.items():
            if rows and all(bool(row.get("fresh")) for row in rows):
                ready.add(guard)
                continue
            acquisitions = {str(row.get("acquisition", "")) for row in rows}
            if "active_capability" in acquisitions:
                active.add(guard)
            if "passive_runtime_refresh" in acquisitions:
                passive.add(guard)
            if "blocked_recently" in acquisitions:
                blocked.add(guard)

        pair_rows: list[dict] = []
        for idx, pair in enumerate(disagreement_pairs):
            separators = set(pair.get("separating_guard_families") or [])
            pair_id = f"{pair['left_plan']}::{pair['right_plan']}"
            pair_rows.append(
                {
                    "pair_id": pair_id,
                    "pair_index": idx,
                    "separators": sorted(separators),
                    "already_separated": bool(separators & ready),
                }
            )

        unresolved_ids = {
            row["pair_id"] for row in pair_rows if not row["already_separated"]
        }
        guard_to_pairs: dict[str, set[str]] = {}
        for guard in active:
            guard_to_pairs[guard] = {
                row["pair_id"]
                for row in pair_rows
                if guard in row["separators"] and row["pair_id"] in unresolved_ids
            }

        remaining = set(unresolved_ids)
        greedy: list[dict] = []
        while remaining:
            ranked = sorted(
                (
                    (len(pairs & remaining), guard, sorted(pairs & remaining))
                    for guard, pairs in guard_to_pairs.items()
                ),
                key=lambda x: (-x[0], x[1]),
            )
            if not ranked or ranked[0][0] <= 0:
                break
            gain, guard, covered = ranked[0]
            greedy.append(
                {
                    "guard_family": guard,
                    "new_pair_coverage": gain,
                    "covered_pairs": covered,
                }
            )
            remaining.difference_update(covered)

        all_guards = {
            guard
            for pair in disagreement_pairs
            for guard in pair.get("separating_guard_families", [])
        }
        unwired = sorted(all_guards - set(by_guard))
        passive_only = sorted((passive - active) - ready)
        blocked_only = sorted(blocked - ready)
        return {
            "ready_guard_families": sorted(ready),
            "active_guard_families": sorted(active),
            "passive_refresh_guard_families": passive_only,
            "blocked_guard_families": blocked_only,
            "unwired_guard_families": unwired,
            "candidate_pairs": pair_rows,
            "initial_unresolved_pair_count": len(unresolved_ids),
            "greedy_active_cover": greedy,
            "remaining_uncovered_pairs": sorted(remaining),
            "interpretation": (
                "shadow greedy set cover over candidate-plan disagreement pairs; active guards are chosen "
                "by marginal pair coverage only, with no probability/cost assumption"
            ),
        }

    @staticmethod
    def _targets(
        operational_task: OperationalTask,
        evidence_world: EvidenceWorldSnapshot,
        resource_ids: list[str] | None,
    ) -> list[str]:
        if operational_task.target_node_ids:
            return sorted(set(operational_task.target_node_ids))
        # A global Operational Task is authoritative over the known deployment
        # inventory, not merely over resources that have already produced a
        # center-visible report.  Evidence availability determines whether a
        # target is matched/mismatched/unknown; it must not silently redefine
        # Task scope.  ``resource_ids`` is the legally materialized runtime
        # inventory (CenterView.node_ids), so using it does not expose hidden
        # simulator truth.
        if resource_ids:
            return sorted(set(resource_ids))
        report_nodes = {
            e.subject_ref
            for e in evidence_world.evidence
            if e.proposition == "communication.center.node_report"
        }
        return sorted(report_nodes)

    @staticmethod
    def _latest(
        evidence: Iterable[CommunicationEvidence], proposition: str, subject: str
    ) -> CommunicationEvidence | None:
        rows = [
            e
            for e in evidence
            if e.proposition == proposition and e.subject_ref == subject
        ]
        if not rows:
            return None
        return max(rows, key=lambda e: (int(e.observed_at_s), int(e.world_revision)))

    @staticmethod
    def _blocked_outcomes(recent_capability_outcomes: list[dict] | None) -> set[tuple[str, str]]:
        blocked: set[tuple[str, str]] = set()
        for row in recent_capability_outcomes or []:
            if not isinstance(row, dict):
                continue
            result = row.get("result") or {}
            if result.get("status") in {"blocked", "timed_out", "failed", "partial"}:
                blocked.add((str(row.get("capability_id", "")), str(row.get("resource", ""))))
        return blocked

    @staticmethod
    def _dependency_rows(
        *,
        dependencies: list[_Dependency],
        evidence_world: EvidenceWorldSnapshot,
        capability_ids: list[str],
        task_run_id: str,
        t_s: int,
        now: datetime,
        blocked: set[tuple[str, str]],
    ) -> tuple[
        list[CommunicationEvidence],
        list[str],
        list[EvidenceNeed],
        list[InvestigationStateItem],
        list[InvestigationStateItem],
        list[dict],
    ]:
        selected: list[CommunicationEvidence] = []
        required_refs: list[str] = []
        needs: list[EvidenceNeed] = []
        confirmed: list[InvestigationStateItem] = []
        unknowns: list[InvestigationStateItem] = []
        states: list[dict] = []
        selected_ids: set[str] = set()

        visible = set(capability_ids)
        for dep in dependencies:
            for subject in dep.subjects:
                ev = ActionConditionedContextSelector._latest(
                    evidence_world.evidence, dep.proposition, subject
                )
                if ev is None:
                    age_s = None
                elif dep.freshness_basis == "generated_at_s" and ev.generated_at_s is not None:
                    age_s = max(0, int(t_s) - int(ev.generated_at_s))
                else:
                    age_s = max(0, int(t_s) - int(ev.observed_at_s))
                fresh = ev is not None and age_s is not None and age_s <= dep.max_age_s
                if ev is not None and ev.evidence_id not in selected_ids:
                    selected.append(ev)
                    selected_ids.add(ev.evidence_id)
                is_blocked = (dep.proposition, subject) in blocked
                acquisition = (
                    "active_capability"
                    if dep.proposition in ACTIVE_OBSERVATION_CAPABILITIES
                    and dep.proposition in visible
                    else "passive_runtime_refresh"
                )
                if is_blocked and acquisition == "active_capability":
                    acquisition = "blocked_recently"
                state = {
                    "proposition": dep.proposition,
                    "subject": subject,
                    "purpose": dep.purpose,
                    "scope_reason": dep.scope_reason,
                    # Audit-only dependency scope used by offline expressiveness
                    # probes. Compact model-facing Context deliberately omits
                    # this field; active EvidenceNeeds expose the same binding
                    # through their typed blocking_plan_ids contract.
                    "blocking_plan_ids": list(dep.blocking_plan_ids),
                    "max_age_s": dep.max_age_s,
                    "freshness_basis": dep.freshness_basis,
                    "evidence_ref": None if ev is None else ev.evidence_id,
                    "age_s": age_s,
                    "fresh": bool(fresh),
                    "acquisition": acquisition,
                    "blocked_recently": is_blocked,
                }
                states.append(state)
                if fresh and ev is not None:
                    required_refs.append(ev.evidence_id)
                    confirmed.append(
                        InvestigationStateItem(
                            proposition=(
                                f"candidate-action dependency available: {dep.proposition}"
                            ),
                            target_ref=subject,
                            evidence_refs=[ev.evidence_id],
                            writer="action-conditioned-context-selector",
                            reason_code="candidate_dependency_satisfied",
                            updated_revision=evidence_world.revision,
                        )
                    )
                    continue

                reason = "missing" if ev is None else "stale"
                unknowns.append(
                    InvestigationStateItem(
                        proposition=(
                            f"candidate-action dependency {dep.proposition} for {subject} "
                            f"is {'blocked' if is_blocked else reason}"
                        ),
                        target_ref=subject,
                        evidence_refs=[] if ev is None else [ev.evidence_id],
                        writer="action-conditioned-context-selector",
                        reason_code=(
                            "candidate_dependency_blocked"
                            if is_blocked
                            else f"candidate_dependency_{reason}"
                        ),
                        updated_revision=evidence_world.revision,
                    )
                )
                # Passive evidence (e.g. center link/delivery summaries) is still
                # a decision dependency, but there is no active tool that can
                # manufacture a fresher observation in the current runtime.
                if acquisition != "active_capability":
                    continue
                needs.append(
                    EvidenceNeed(
                        need_id=f"need:{task_run_id}:action:{dep.proposition}:{subject}",
                        task_run_id=task_run_id,
                        proposition_or_question=(
                            f"What is the current {dep.proposition} for {subject}?"
                        ),
                        purpose=dep.purpose,
                        target_objects=[subject],
                        evidence_contract=EvidenceNeedContract(
                            required_source_roles=list(dep.source_roles),
                            min_independent_sources=1,
                            accepted_states=[ProposedState.CONFIRMED, ProposedState.UNKNOWN],
                        ),
                        preferred_source_roles=list(dep.source_roles),
                        freshness_requirement={"max_age_s": dep.max_age_s},
                        completion_predicate={
                            "type": "candidate_dependency_observation_or_blocked"
                        },
                        blocking_plan_ids=list(dep.blocking_plan_ids),
                        priority=90,
                        status=(
                            EvidenceNeedStatus.BLOCKED if is_blocked else EvidenceNeedStatus.OPEN
                        ),
                        opened_revision=evidence_world.revision,
                        updated_revision=evidence_world.revision,
                        opened_at=now,
                        updated_at=now,
                    )
                )
        return selected, required_refs, needs, confirmed, unknowns, states

    def select(
        self,
        *,
        operational_task: OperationalTask,
        task: TaskContract,
        task_run_id: str,
        evidence_world: EvidenceWorldSnapshot,
        capability_ids: list[str],
        resource_ids: list[str] | None,
        recent_capability_outcomes: list[dict] | None,
        t_s: int,
        now: datetime,
    ) -> ActionContextSelection:
        targets = self._targets(operational_task, evidence_world, resource_ids)
        all_nodes = sorted(set(resource_ids or targets))
        period = int(operational_task.phase_at(t_s).required_period_s)
        # Confirmed configuration is persistent control state in this simulator;
        # a report remains decision-relevant across the TaskRun unless later
        # evidence replaces it. Delivery/AoI evidence keeps a much shorter age.
        config_max_age = int(operational_task.task_horizon_s) + 3600
        delivery_max_age = max(period, 600)
        authorized = set(operational_task.authorized_effects)
        pre_enabled_effects = {
            str(effect)
            for effect in operational_task.metadata.get(
                "benchmark_pre_enabled_effects", []
            )
        }
        controllable_effects = authorized - pre_enabled_effects
        announced_future = [
            dict(row)
            for row in (task.desired_state.get("announced_future_phases") or [])
            if isinstance(row, dict)
        ]
        preparation_phase = next(
            (
                row
                for row in sorted(
                    announced_future, key=lambda r: int(r.get("effective_at_s", 10**18))
                )
                if int(row.get("effective_at_s", -1)) > int(t_s)
                and int(row.get("required_period_s", period)) < period
            ),
            None,
        )

        base_deps: list[_Dependency] = []
        if {
            "communication.config.set_sampling_interval",
            "communication.config.set_report_period",
        } & authorized:
            base_deps.append(
                _Dependency(
                    proposition="communication.center.node_report",
                    subjects=tuple(targets),
                    purpose=(
                        "distinguish hold-current-profile from installing the task-required profile"
                    ),
                    max_age_s=config_max_age,
                    source_roles=("center",),
                    scope_reason="action_target_configuration",
                    blocking_plan_ids=("hold_current_profile",),
                )
            )

        if preparation_phase is not None:
            # Future-effective Task intent is already authoritative, but execution
            # has not started. Preparation uses owner-local state rather than
            # assuming center telemetry is fresh enough for early staging.
            base_deps.extend(
                [
                    _Dependency(
                        proposition="communication.gateway.node_report",
                        subjects=tuple(targets),
                        purpose=(
                            "evaluate resource/configuration readiness before staging the "
                            "announced future monitoring profile"
                        ),
                        max_age_s=3600,
                        source_roles=("gateway",),
                        scope_reason="preparation_resource_state",
                        blocking_plan_ids=("prepare_future_profile",),
                    ),
                    _Dependency(
                        proposition="communication.gateway.receipt_summary",
                        subjects=("gw0",),
                        purpose=(
                            "confirm the gateway has current owner-local receipt context before "
                            "using future-task preparation opportunities"
                        ),
                        max_age_s=3600,
                        source_roles=("gateway",),
                        scope_reason="preparation_gateway_receipt",
                        blocking_plan_ids=("prepare_future_profile",),
                    ),
                ]
            )

        fallback_caps = {
            "communication.fallback.gateway_backup",
            "communication.fallback.terminal_dts",
            "communication.fallback.access_assist",
        } & controllable_effects
        if fallback_caps:
            # Stage 1: screen fallback relevance using already-held center evidence.
            # Shared/remote evidence is pulled only when the current delivery state
            # leaves a fallback candidate live.
            base_deps.append(
                _Dependency(
                    proposition="communication.center.delivery_status",
                    subjects=tuple(targets),
                    purpose="screen whether current target delivery leaves a fallback communication plan relevant",
                    max_age_s=delivery_max_age,
                    source_roles=("center",),
                    scope_reason="fallback_relevance_screen",
                    blocking_plan_ids=(
                        "consider_gateway_backup",
                        "consider_terminal_dts",
                        "consider_access_assist",
                    ),
                )
            )

        blocked = self._blocked_outcomes(recent_capability_outcomes)
        (
            selected,
            required_refs,
            needs,
            confirmed,
            unknowns,
            dep_states,
        ) = self._dependency_rows(
            dependencies=base_deps,
            evidence_world=evidence_world,
            capability_ids=capability_ids,
            task_run_id=task_run_id,
            t_s=t_s,
            now=now,
            blocked=blocked,
        )

        def _delivery_deficit() -> bool:
            if not fallback_caps:
                return False
            for nid in targets:
                ev = self._latest(
                    selected, "communication.center.delivery_status", nid
                )
                if ev is None or int(t_s) - int(ev.observed_at_s) > delivery_max_age:
                    return True
                value = dict(ev.value) if isinstance(ev.value, dict) else {}
                newest = value.get("newest_taken_at")
                if newest is None or int(t_s) - int(newest) > period:
                    return True
            return False

        fallback_relevant = _delivery_deficit()
        expanded_deps: list[_Dependency] = []
        if fallback_relevant and "communication.fallback.gateway_backup" in fallback_caps:
            expanded_deps.extend(
                [
                    _Dependency(
                        proposition="communication.gateway.primary_health",
                        subjects=("gw0",),
                        purpose="compare primary-path continuation with gateway-backup execution",
                        max_age_s=3600,
                        source_roles=("gateway",),
                        scope_reason="shared_gateway_path",
                        blocking_plan_ids=("consider_gateway_backup",),
                    ),
                    _Dependency(
                        proposition="communication.gateway.receipt_summary",
                        subjects=("gw0",),
                        purpose="separate access receipt from center-side delivery loss before fallback",
                        max_age_s=3600,
                        source_roles=("gateway",),
                        scope_reason="shared_gateway_path",
                        blocking_plan_ids=("consider_gateway_backup",),
                    ),
                ]
            )

        if fallback_relevant and "communication.fallback.access_assist" in fallback_caps:
            expanded_deps.extend(
                [
                    _Dependency(
                        proposition="communication.center.link_summary",
                        subjects=("monitoring-network",),
                        purpose="detect whether a shared access-path intervention is a relevant alternative",
                        max_age_s=3600,
                        source_roles=("center",),
                        scope_reason="shared_access_path",
                        blocking_plan_ids=("consider_access_assist",),
                    ),
                    # Action scope can be local while evidence scope expands to
                    # peers sharing the same access path.
                    _Dependency(
                        proposition="communication.center.delivery_status",
                        subjects=tuple(all_nodes),
                        purpose="compare target degradation with peer nodes sharing the access path",
                        max_age_s=delivery_max_age,
                        source_roles=("center",),
                        scope_reason="shared_access_peer_expansion",
                        blocking_plan_ids=("consider_access_assist",),
                    ),
                ]
            )
        if expanded_deps:
            (
                selected,
                required_refs,
                needs,
                confirmed,
                unknowns,
                dep_states,
            ) = self._dependency_rows(
                dependencies=[*base_deps, *expanded_deps],
                evidence_world=evidence_world,
                capability_ids=capability_ids,
                task_run_id=task_run_id,
                t_s=t_s,
                now=now,
                blocked=blocked,
            )

        # Configuration candidates are executable ordinary-rule plans.  They are
        # the first method coordinate because localized O2 already creates a real
        # context-selection difference without changing the physical action set.
        fresh_report: dict[str, CommunicationEvidence] = {}
        for nid in targets:
            ev = self._latest(
                selected, "communication.center.node_report", nid
            )
            if ev is None or int(t_s) - int(ev.observed_at_s) > config_max_age:
                continue
            fresh_report[nid] = ev

        matched: list[str] = []
        mismatched: list[str] = []
        unresolved: list[str] = []
        for nid in targets:
            ev = fresh_report.get(nid)
            if ev is None or not isinstance(ev.value, dict):
                unresolved.append(nid)
                continue
            value = dict(ev.value)
            if (
                value.get("sample_interval_s") == period
                and value.get("report_period_s") == period
            ):
                matched.append(nid)
            else:
                mismatched.append(nid)

        plans: list[dict] = []
        hold_feasibility = "supported" if not mismatched and not unresolved else "rejected"
        plans.append(
            {
                "plan_id": "hold_current_profile",
                "kind": "wait_or_keep",
                "feasibility": hold_feasibility,
                "decision_guards": {
                    "action_target_configuration": "all_targets_match_required_profile"
                },
                "affected_resources": list(targets),
                "invocations": [],
                "support_refs": [fresh_report[n].evidence_id for n in matched],
                "unresolved_conditions": [
                    f"fresh confirmed configuration for {nid}" for nid in unresolved
                ],
                "contradicted_by": [fresh_report[n].evidence_id for n in mismatched],
                "reason": "all authorised targets already satisfy the current task profile",
            }
        )

        if {
            "communication.config.set_sampling_interval",
            "communication.config.set_report_period",
        } <= authorized:
            install_invocations: list[dict] = []
            # Missing confirmed state does not force diagnosis here.  Installing
            # the authorised target profile is the ordinary safe action across
            # the remaining states; the runtime still skips a write if its live
            # CenterView already confirms the target.
            install_targets = sorted(set(mismatched + unresolved))
            for nid in install_targets:
                install_invocations.extend(
                    [
                        {
                            "capability_id": "communication.config.set_sampling_interval",
                            "resource": nid,
                            "canonical_arguments": {"target_s": period},
                        },
                        {
                            "capability_id": "communication.config.set_report_period",
                            "resource": nid,
                            "canonical_arguments": {"target_s": period},
                        },
                    ]
                )
            plans.append(
                {
                    "plan_id": "install_required_profile",
                    "kind": "configuration_update",
                    "feasibility": "supported" if install_targets else "dominated",
                    "decision_guards": {
                        "action_target_configuration": "any_target_mismatch_or_unknown"
                    },
                    "affected_resources": install_targets,
                    "invocations": install_invocations,
                    "support_refs": [fresh_report[n].evidence_id for n in mismatched],
                    "unresolved_conditions": [],
                    "reason": "install the Operational Task profile where confirmed configuration mismatches",
                }
            )

        if preparation_phase is not None:
            future_period = int(preparation_phase["required_period_s"])
            effective_at_s = int(preparation_phase["effective_at_s"])
            prep_rows = [
                row
                for row in dep_states
                if str(row.get("scope_reason", "")).startswith("preparation_")
            ]
            prep_open = [row for row in prep_rows if not bool(row.get("fresh"))]
            plans.extend(
                [
                    {
                        "plan_id": "wait_for_future_task_effective",
                        "kind": "wait_or_keep",
                        "feasibility": "supported",
                        "decision_guards": {
                            "preparation_timing": "remaining control/install slack is sufficient without early staging"
                        },
                        "affected_resources": list(targets),
                        "invocations": [],
                        "support_refs": [],
                        "unresolved_conditions": [],
                        "future_required_period_s": future_period,
                        "effective_at_s": effective_at_s,
                        "reason": "retain the current authorised profile until the future Task becomes effective",
                    },
                    {
                        "plan_id": "prepare_future_profile",
                        "kind": "future_task_preparation",
                        "feasibility": "conditional",
                        "decision_guards": {
                            "preparation_resource_state": "owner-local node state supports early staging",
                            "preparation_gateway_receipt": "gateway has current receipt context",
                            "preparation_timing": "remaining Class-A/control slack makes early staging valuable",
                        },
                        "affected_resources": list(targets),
                        # Shadow-only until an ordinary preparation guard/executor
                        # is exposed as a model-invocable capability.
                        "invocations": [],
                        "support_refs": [
                            str(row["evidence_ref"])
                            for row in prep_rows
                            if row.get("evidence_ref")
                        ],
                        "unresolved_conditions": [
                            f"{row['scope_reason']}:{row['subject']}"
                            for row in prep_open
                        ],
                        "future_required_period_s": future_period,
                        "effective_at_s": effective_at_s,
                        "reason": (
                            "stage the announced denser profile only when owner-local evidence and "
                            "remaining control slack support preparation"
                        ),
                    },
                ]
            )

        # Fallback candidates are represented now so the same selector can expand
        # into O3/O5/O6.  Their physical value remains for the planner/continuation
        # evaluator; the selector only states the evidence needed to compare them.
        if "communication.fallback.gateway_backup" in authorized:
            backup_pre_enabled = (
                "communication.fallback.gateway_backup" in pre_enabled_effects
            )
            plans.append(
                {
                    "plan_id": "consider_gateway_backup",
                    "kind": "fallback",
                    "feasibility": (
                        "dominated"
                        if backup_pre_enabled
                        else ("conditional" if fallback_relevant else "dominated")
                    ),
                    "decision_guards": {
                        "fallback_relevance_screen": "target_delivery_deficit_or_uncertainty",
                        "shared_gateway_path": "gateway_path_state_supports_backup_value",
                    },
                    "affected_resources": ["gw0"],
                    "invocations": (
                        []
                        if backup_pre_enabled
                        else [
                            {
                                "capability_id": "communication.fallback.gateway_backup",
                                "resource": "gw0",
                                "canonical_arguments": {"enabled": True},
                            }
                        ]
                    ),
                    "support_refs": [],
                    "unresolved_conditions": (
                        ["compare gateway primary health and receipt summary with current delivery state"]
                        if fallback_relevant and not backup_pre_enabled
                        else []
                    ),
                    "reason": (
                        "gateway backup is already enabled by the frozen benchmark deployment"
                        if backup_pre_enabled
                        else "shared backhaul alternative"
                    ),
                }
            )
        if "communication.fallback.terminal_dts" in authorized:
            plans.append(
                {
                    "plan_id": "consider_terminal_dts",
                    "kind": "fallback",
                    "feasibility": "conditional" if fallback_relevant else "dominated",
                    "decision_guards": {
                        "fallback_relevance_screen": "target_delivery_deficit_or_uncertainty",
                        "terminal_opportunity": "terminal_specific_contact_and_energy_support_action",
                    },
                    "affected_resources": list(targets),
                    "invocations": [],
                    "support_refs": [],
                    "unresolved_conditions": (
                        ["identify terminal-specific opportunity for the observed target delivery deficit"]
                        if fallback_relevant
                        else []
                    ),
                    "reason": "terminal return-path alternative",
                }
            )
        if "communication.fallback.access_assist" in authorized:
            plans.append(
                {
                    "plan_id": "consider_access_assist",
                    "kind": "fallback",
                    "feasibility": "conditional" if fallback_relevant else "dominated",
                    "decision_guards": {
                        "fallback_relevance_screen": "target_delivery_deficit_or_uncertainty",
                        "shared_access_path": "shared_access_degradation_supports_assist",
                        "shared_access_peer_expansion": "peer_pattern_changes_target_interpretation",
                    },
                    "affected_resources": list(targets),
                    "invocations": [],
                    "support_refs": [],
                    "unresolved_conditions": (
                        ["compare target delivery degradation with peers sharing the access path"]
                        if fallback_relevant
                        else []
                    ),
                    "reason": "shared access-path alternative",
                }
            )

        live_plans = [
            p for p in plans if p.get("feasibility") not in {"dominated", "rejected"}
        ]
        disagreement_pairs: list[dict] = []
        guard_scores: dict[str, int] = {}
        for i, left in enumerate(live_plans):
            left_guards = dict(left.get("decision_guards") or {})
            for right in live_plans[i + 1 :]:
                right_guards = dict(right.get("decision_guards") or {})
                separators = sorted(
                    key
                    for key in set(left_guards) | set(right_guards)
                    if left_guards.get(key) != right_guards.get(key)
                )
                if not separators:
                    continue
                disagreement_pairs.append(
                    {
                        "left_plan": left["plan_id"],
                        "right_plan": right["plan_id"],
                        "separating_guard_families": separators,
                    }
                )
                for key in separators:
                    guard_scores[key] = guard_scores.get(key, 0) + 1

        unresolved_guard_families = {
            row["scope_reason"]
            for row in dep_states
            if not bool(row.get("fresh"))
        }
        ranked_unresolved_guards = [
            {
                "guard_family": key,
                "candidate_pair_coverage": score,
                "has_unresolved_dependency": key in unresolved_guard_families,
            }
            for key, score in sorted(
                guard_scores.items(), key=lambda kv: (-kv[1], kv[0])
            )
            if key in unresolved_guard_families
        ]
        greedy_guard_cover = self._greedy_guard_cover(disagreement_pairs, dep_states)

        unresolved_needs = [
            need
            for need in needs
            if need.status in {EvidenceNeedStatus.OPEN, EvidenceNeedStatus.BLOCKED}
        ]
        supported_effect_plans = [
            plan
            for plan in live_plans
            if plan.get("feasibility") == "supported"
            and bool(plan.get("invocations"))
            and not bool(plan.get("unresolved_conditions"))
        ]
        decision_sufficiency: dict = {
            "status": "undetermined",
            "primary_plan_id": None,
            "blocking_need_ids": [],
            "nonblocking_open_need_ids": [],
        }
        if len(supported_effect_plans) == 1:
            primary_plan_id = str(supported_effect_plans[0]["plan_id"])
            blocking_need_ids: list[str] = []
            nonblocking_need_ids: list[str] = []
            for need in unresolved_needs:
                scoped = list(need.blocking_plan_ids)
                if not scoped or primary_plan_id in scoped:
                    blocking_need_ids.append(need.need_id)
                else:
                    nonblocking_need_ids.append(need.need_id)
            decision_sufficiency = {
                "status": (
                    "sufficient_for_primary_action"
                    if not blocking_need_ids
                    else "blocked_for_primary_action"
                ),
                "primary_plan_id": primary_plan_id,
                "primary_plan_feasibility": "supported",
                "blocking_need_ids": sorted(blocking_need_ids),
                "nonblocking_open_need_ids": sorted(nonblocking_need_ids),
                "interpretation": (
                    "open evidence needs attached only to alternative plans do not delay a supported "
                    "primary action whose own guards are already resolved"
                ),
            }

        context = {
            "selector_revision": self.revision,
            "operational_task_id": operational_task.task_id,
            "task_contract_id": task.task_contract_id,
            "phase_index": operational_task.phase_index(t_s),
            "required_period_s": period,
            "announced_future_phases": announced_future,
            "action_scope": targets,
            "evidence_scope": sorted({e.subject_ref for e in selected}),
            "candidate_plans": plans,
            "dependencies": dep_states,
            "decision_sufficiency": decision_sufficiency,
            "fallback_relevance": {
                "authorized": sorted(
                    {
                        "communication.fallback.gateway_backup",
                        "communication.fallback.terminal_dts",
                        "communication.fallback.access_assist",
                    }
                    & authorized
                ),
                "controllable": sorted(fallback_caps),
                "pre_enabled": sorted(
                    pre_enabled_effects
                    & {
                        "communication.fallback.gateway_backup",
                        "communication.fallback.terminal_dts",
                        "communication.fallback.access_assist",
                    }
                ),
                "delivery_deficit_or_uncertainty": bool(fallback_relevant),
                "screening_rule": (
                    "expand to shared/remote fallback evidence only when target delivery is missing, "
                    "stale, or older than the current Operational Task period"
                ),
            },
            "candidate_disagreement": {
                "action_closure": {
                    "closed_for_current_candidate_family": not bool(fallback_caps or preparation_phase),
                    "scope": (
                        "future-task wait/preparation alternatives"
                        if preparation_phase is not None and not fallback_caps
                        else (
                            "hold/install configuration alternatives"
                            if not fallback_caps
                            else "exploratory fallback/preparation candidates; safe action compositions are not yet enumerated"
                        )
                    ),
                    "control_eligibility": (
                        "shadow_only_until_preparation_guard_executor"
                        if preparation_phase is not None
                        else (
                            "eligible"
                            if not fallback_caps
                            else "shadow_only_until_composed_candidate_closure"
                        )
                    ),
                },
                "live_plan_ids": [p["plan_id"] for p in live_plans],
                "plan_pairs": disagreement_pairs,
                "guard_family_pair_coverage": guard_scores,
                "ranked_unresolved_guards": ranked_unresolved_guards,
                "greedy_guard_cover": greedy_guard_cover,
                "interpretation": (
                    "guard families rank how many currently live candidate-plan pairs they can distinguish; "
                    "the rank is a symbolic coverage signal, not a calibrated value-of-information score"
                ),
            },
            "open_dependency_count": sum(not bool(row["fresh"]) for row in dep_states),
            "selection_rule": (
                "retain evidence that can change candidate feasibility/choice; bind unresolved evidence "
                "to the candidate plans it can block; expand along shared communication dependencies; "
                "stop expanding when a supported primary action has no blocking evidence need"
            ),
        }
        # Compact materialization treats deterministic guard evaluation as a
        # Context compiler: evidence already reduced into a closed configuration
        # candidate (match/mismatch/affected resources) need not be repeated as
        # raw telemetry to the model. Likewise, target delivery rows used only to
        # screen whether a fallback branch is live are represented by the
        # fallback_relevance result. Raw evidence is retained where the model
        # still has a genuine conditional choice among shared/owner-scoped paths.
        summarized_scope_reasons = {
            "action_target_configuration",
            "fallback_relevance_screen",
        }
        compact_refs = {
            str(row["evidence_ref"])
            for row in dep_states
            if row.get("evidence_ref")
            and row.get("scope_reason") not in summarized_scope_reasons
        }
        compact_selected = [
            evidence for evidence in selected if evidence.evidence_id in compact_refs
        ]
        return ActionContextSelection(
            selected=selected,
            compact_selected=compact_selected,
            required_refs=required_refs,
            needs=needs,
            confirmed=confirmed,
            unknowns=unknowns,
            candidate_context=context,
        )
