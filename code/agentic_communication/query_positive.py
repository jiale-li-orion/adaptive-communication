"""Query-positive gateway-backup compiler layered on the frozen v7 runtime.

This module intentionally leaves the v7 selector/runtime/policy byte-for-byte
untouched.  It closes one already-registered branch only:

    delivery deficit -> gateway owner evidence -> gateway_backup feasibility

No new capability, hidden state, learned scorer, or arbitrary threshold is
introduced.  The guard threshold is the current Operational Task period.
"""
from __future__ import annotations

from copy import deepcopy

from .action_context import ActionConditionedContextSelector, ActionContextSelection
from .context_runtime import CommunicationContextRuntime
from .policy import AgenticCommunicationPolicy
from .runtime_contracts import EvidenceNeed


GATEWAY_BACKUP_PLAN_ID = "consider_gateway_backup"
PRIMARY_HEALTH = "communication.gateway.primary_health"
RECEIPT_SUMMARY = "communication.gateway.receipt_summary"


def _decision_sufficiency_for_control_surface(
    *,
    plans: list[dict],
    needs: list[EvidenceNeed],
    eligible_plan_ids: set[str],
) -> dict:
    """Recompute the same ordinary sufficiency rule over eligible plans only."""
    visible = [
        row
        for row in plans
        if str(row.get("plan_id")) in eligible_plan_ids
    ]
    ready = [
        row
        for row in visible
        if row.get("feasibility") == "supported"
        and not bool(row.get("unresolved_conditions"))
    ]
    live = [
        row
        for row in visible
        if row.get("feasibility") not in {"dominated", "rejected"}
    ]
    result = {
        "status": "undetermined",
        "primary_plan_id": None,
        "blocking_need_ids": [],
        "nonblocking_open_need_ids": [],
    }
    if len(ready) != 1:
        return result

    primary = ready[0]
    primary_id = str(primary.get("plan_id"))
    has_effect = bool(primary.get("invocations"))
    # A no-op hold is only closed when no other live eligible alternative can
    # still become a real effect.  Effect-bearing actions keep plan-local
    # blocking semantics from v6/v7.
    if not has_effect and len(live) != 1:
        return result

    blocking: list[str] = []
    nonblocking: list[str] = []
    for need in needs:
        scoped = list(need.blocking_plan_ids)
        if not scoped or primary_id in scoped:
            blocking.append(need.need_id)
        elif set(scoped) & eligible_plan_ids:
            nonblocking.append(need.need_id)
    if has_effect:
        status = "sufficient_for_primary_action" if not blocking else "blocked_for_primary_action"
    else:
        status = "sufficient_for_no_action" if not blocking else "blocked_for_no_action"
    return {
        "status": status,
        "primary_plan_id": primary_id,
        "primary_plan_feasibility": "supported",
        "blocking_need_ids": sorted(blocking),
        "nonblocking_open_need_ids": sorted(nonblocking),
        "interpretation": (
            "query-positive control surface is decision-complete for the primary plan; "
            "open evidence attached only to other eligible plans does not block that plan"
        ),
    }


class GatewayBackupQueryPositiveSelector(ActionConditionedContextSelector):
    """Close the existing gateway-backup candidate from public owner evidence."""

    revision = "action-conditioned-context-v8-gateway-backup-query-positive"

    def __init__(self) -> None:
        super().__init__()
        # Runtime-owned execution state.  It is advanced only after this Agent's
        # gateway-backup effect is observed as applied; it is not simulator truth
        # and is not smuggled into the Operational Task.
        self.backup_enabled_by_agent = False

    def select(self, **kwargs) -> ActionContextSelection:  # type: ignore[override]
        selection = super().select(**kwargs)
        operational_task = kwargs["operational_task"]
        t_s = int(kwargs["t_s"])
        period = int(operational_task.phase_at(t_s).required_period_s)

        context = deepcopy(selection.candidate_context)
        plans = [deepcopy(row) for row in context.get("candidate_plans", [])]
        by_id = {str(row.get("plan_id")): row for row in plans if row.get("plan_id")}
        backup = by_id.get(GATEWAY_BACKUP_PLAN_ID)
        hold = by_id.get("hold_current_profile")
        install = by_id.get("install_required_profile")

        fallback = context.get("fallback_relevance") or {}
        pre_enabled = "communication.fallback.gateway_backup" in set(fallback.get("pre_enabled") or [])
        effectively_enabled = pre_enabled or self.backup_enabled_by_agent
        backup_authorized = "communication.fallback.gateway_backup" in set(
            fallback.get("authorized") or []
        )
        fallback_relevant = bool(fallback.get("delivery_deficit_or_uncertainty"))
        config_closed = bool(
            hold is not None
            and hold.get("feasibility") == "supported"
            and not bool(hold.get("unresolved_conditions"))
            and (
                install is None
                or install.get("feasibility") in {"dominated", "rejected"}
            )
        )
        control_eligible = bool(
            backup is not None
            and backup_authorized
            and not effectively_enabled
            and fallback_relevant
            and config_closed
        )

        selected = list(selection.selected)
        primary = self._latest(selected, PRIMARY_HEALTH, "gw0")
        receipt = self._latest(selected, RECEIPT_SUMMARY, "gw0")
        gateway_max_age_s = 3600
        primary_fresh = bool(
            primary is not None and t_s - int(primary.observed_at_s) <= gateway_max_age_s
        )
        receipt_fresh = bool(
            receipt is not None and t_s - int(receipt.observed_at_s) <= gateway_max_age_s
        )

        guard_result = "inactive"
        support_refs: list[str] = []
        guard_inputs: dict = {
            "required_period_s": period,
            "primary_health_fresh": primary_fresh,
            "receipt_summary_fresh": receipt_fresh,
        }
        needs = list(selection.needs)
        if self.backup_enabled_by_agent and backup is not None:
            guard_result = "already_enabled"
            backup["feasibility"] = "dominated"
            backup["invocations"] = []
            backup["unresolved_conditions"] = []
            backup["reason"] = "gateway backup was already applied by the current Agent execution state"
            needs = [
                need
                for need in needs
                if set(need.blocking_plan_ids) != {GATEWAY_BACKUP_PLAN_ID}
            ]
        elif control_eligible and backup is not None:
            if primary_fresh and receipt_fresh:
                primary_value = dict(primary.value) if isinstance(primary.value, dict) else {}
                receipt_value = dict(receipt.value) if isinstance(receipt.value, dict) else {}
                pending_depth = int(primary_value.get("pending_depth") or 0)
                oldest_pending_age_s = primary_value.get("oldest_pending_age_s")
                heard_nodes = list(receipt_value.get("heard_nodes") or [])
                query_path_reachable = primary_value.get("query_path_reachable")
                support_refs = [primary.evidence_id, receipt.evidence_id]
                guard_inputs.update(
                    {
                        "pending_depth": pending_depth,
                        "oldest_pending_age_s": oldest_pending_age_s,
                        "heard_node_count": len(heard_nodes),
                        "query_path_reachable": query_path_reachable,
                    }
                )
                supports_backup = bool(
                    query_path_reachable is not False
                    and pending_depth > 0
                    and oldest_pending_age_s is not None
                    and int(oldest_pending_age_s) >= period
                    and heard_nodes
                )
                backup["unresolved_conditions"] = []
                backup["support_refs"] = support_refs
                if supports_backup:
                    guard_result = "supported"
                    backup["feasibility"] = "supported"
                    backup["reason"] = (
                        "gateway owner evidence shows received data waiting behind the primary "
                        "backhaul for at least one current Task period"
                    )
                    # The current global decision is now an effect, not a no-op.
                    # Config is already closed, so hold becomes dominated rather
                    # than coexisting as another ready plan.
                    hold["feasibility"] = "dominated"
                    hold["reason"] = (
                        "current device profile is correct, but a supported gateway-backup effect "
                        "is required by the resolved backhaul guard"
                    )
                else:
                    guard_result = "rejected"
                    backup["feasibility"] = "rejected"
                    backup["contradicted_by"] = support_refs
                    backup["reason"] = (
                        "fresh gateway owner evidence does not show Task-period primary-backhaul "
                        "backlog with received data"
                    )
            else:
                guard_result = "needs_evidence"
                backup["feasibility"] = "conditional"
                backup["unresolved_conditions"] = [
                    "compare gateway primary health and receipt summary with current delivery state"
                ]

        context["candidate_plans"] = plans
        context["query_positive_gateway_backup"] = {
            "control_eligible": control_eligible,
            "guard_result": guard_result,
            "guard_rule": (
                "enable gateway backup iff gateway has received data and primary pending backlog "
                "has aged at least the current Operational Task period"
            ),
            "support_refs": support_refs,
            "guard_inputs": guard_inputs,
        }

        eligible_ids = {
            str(row.get("plan_id"))
            for row in plans
            if row.get("plan_id")
            and row.get("kind") not in {"fallback", "future_task_preparation"}
        }
        if control_eligible:
            eligible_ids.add(GATEWAY_BACKUP_PLAN_ID)
        context["decision_sufficiency"] = _decision_sufficiency_for_control_surface(
            plans=plans,
            needs=needs,
            eligible_plan_ids=eligible_ids,
        )

        return ActionContextSelection(
            selected=selection.selected,
            compact_selected=selection.compact_selected,
            required_refs=selection.required_refs,
            needs=needs,
            confirmed=selection.confirmed,
            unknowns=selection.unknowns,
            candidate_context=context,
        )


class QueryPositiveContextRuntime(CommunicationContextRuntime):
    """v7 compact runtime with gateway-backup as the only unshadowed fallback."""

    revision = "communication-context-runtime-v8-gateway-backup-query-positive"

    def __init__(self) -> None:
        super().__init__()
        self.action_selector = GatewayBackupQueryPositiveSelector()

    @staticmethod
    def _shadow_plan_ids(candidate_context: dict) -> set[str]:
        # Preserve all frozen-v7 shadow behavior except for the one branch whose
        # guard and executor are now both closed by this module.
        disagreement = candidate_context.get("candidate_disagreement") or {}
        closure = disagreement.get("action_closure") or {}
        eligibility = str(closure.get("control_eligibility") or "eligible")
        if not eligibility.startswith("shadow_only"):
            shadow: set[str] = set()
        else:
            shadow = {
                str(row.get("plan_id"))
                for row in candidate_context.get("candidate_plans", [])
                if isinstance(row, dict)
                and row.get("plan_id")
                and row.get("kind") in {"fallback", "future_task_preparation"}
            }
        qp = candidate_context.get("query_positive_gateway_backup") or {}
        if qp.get("control_eligible"):
            shadow.discard(GATEWAY_BACKUP_PLAN_ID)
        return shadow

    @classmethod
    def _compact_candidate_projection(cls, candidate_context, needs=None, **kwargs):
        projected = super()._compact_candidate_projection(
            candidate_context,
            needs,
            **kwargs,
        )
        qp = deepcopy(candidate_context.get("query_positive_gateway_backup") or {})
        if qp:
            projected["query_positive_gateway_backup"] = qp
            projected.setdefault("action_closure", {})[
                "gateway_backup_control_eligibility"
            ] = (
                "eligible_via_owner_evidence_guard"
                if qp.get("control_eligible")
                else "shadow_until_configuration_and_delivery_screen_close"
            )
        return projected


class QueryPositiveAgenticCommunicationPolicy(AgenticCommunicationPolicy):
    """Frozen Agentic runtime with only the query-positive compiler swapped in."""

    name = "agentic-communication-query-positive"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.context_runtime = QueryPositiveContextRuntime()

    def _execute_runtime_device_action(self, view, contract, invocation) -> None:
        before = len(self.trace.events)
        super()._execute_runtime_device_action(view, contract, invocation)
        if (
            invocation.capability_id == "communication.fallback.gateway_backup"
            and bool(invocation.canonical_arguments.get("enabled", True))
        ):
            applied = any(
                event.event_type == "physical_effect"
                and event.t_s == int(view.t_s)
                and event.payload.get("capability_id") == invocation.capability_id
                and event.payload.get("resource") == invocation.resource
                and event.payload.get("lifecycle_stage") == "applied"
                for event in self.trace.events[before:]
            )
            if applied:
                self.context_runtime.action_selector.backup_enabled_by_agent = True

