"""WirelessOpsAgent-style action-assurance adaptation for this repository.

This is a comparative baseline, not a reproduction of the authors' released
code.  It follows the method contract described in WirelessOpsAgent §IV:

1. preserve public observations in a canonical evidence ledger;
2. treat model output as a proposal rather than executable truth;
3. diagnose schema/source/freshness/conflict/scope integrity;
4. repair only the affected proposal/dependency region using already legal
   evidence and the shared candidate-plan interface;
5. revalidate and route through an ordered APPLY/HOLD/RETRY/ESCALATE/ABSTAIN
   governor.

The adaptation deliberately shares this repository's TaskContract, compact
control-eligible candidate menu, plan-ID expander, persistent executor, semantic
replan gate, legal Evidence World and model budget.  It does *not* receive the
Method's explicit ``decision_sufficiency`` certificate.
"""
from __future__ import annotations

from copy import deepcopy
import json
from typing import Any

from agentic_communication.planner import PlannerConsumer
from agentic_communication.runtime_contracts import (
    ModelRequest,
    ModelUsage,
    PlannedCapabilityInvocation,
    PlannerDecision,
    PromptAssembly,
)


GOVERNOR_APPLY = "APPLY"
GOVERNOR_HOLD = "HOLD"
GOVERNOR_RETRY = "RETRY"
GOVERNOR_ESCALATE = "ESCALATE"
GOVERNOR_ABSTAIN = "ABSTAIN"


def _fragments(assembly: PromptAssembly) -> dict[str, Any]:
    return {row.kind: row.content for row in assembly.fragments}


def _effect_invocation_key(row: dict) -> tuple[str, str, str]:
    cid = str(row.get("capability_id") or "")
    resource = str(row.get("resource") or "")
    args = dict(row.get("canonical_arguments") or {})
    if cid.startswith("communication.config.") and args.get("node_id") == resource:
        args.pop("node_id", None)
    return cid, resource, json.dumps(args, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _is_effect_capability(capability_id: str) -> bool:
    return capability_id.startswith(("communication.config.", "communication.fallback."))


def _is_observation_capability(capability_id: str) -> bool:
    return capability_id.startswith(("communication.center.", "communication.gateway."))


class WirelessOpsStyleAssuranceConsumer:
    """Proposal -> evidence-linked assurance -> bounded repair -> governor."""

    def __init__(self, base: PlannerConsumer) -> None:
        self.base = base
        self.consumer_id = f"woa-style:{base.consumer_id}"
        self.provider = base.provider
        self.model = base.model
        self.records: list[dict] = []

    @staticmethod
    def _candidate_plans(fragments: dict[str, Any]) -> list[dict]:
        candidate = fragments.get("candidate_action_context") or {}
        if not isinstance(candidate, dict):
            return []
        return [row for row in candidate.get("candidate_plans", []) if isinstance(row, dict)]

    @staticmethod
    def _ready_plans(plans: list[dict]) -> list[dict]:
        return [
            row
            for row in plans
            if row.get("feasibility") == "supported"
            and not bool(row.get("unresolved_conditions"))
        ]

    @staticmethod
    def _capability_catalog(fragments: dict[str, Any]) -> dict[str, dict]:
        rows = fragments.get("capability_catalog") or []
        return {
            str(row.get("capability_id")): row
            for row in rows
            if isinstance(row, dict) and row.get("capability_id")
        }

    @staticmethod
    def _canonical_ledger(fragments: dict[str, Any]) -> dict:
        evidence = [row for row in (fragments.get("evidence_slice") or []) if isinstance(row, dict)]
        by_subject: dict[str, list[dict]] = {}
        by_key: dict[tuple[str, str], list[dict]] = {}
        for row in evidence:
            subject = str(row.get("subject_ref") or "")
            proposition = str(row.get("proposition") or "")
            by_subject.setdefault(subject, []).append(row)
            by_key.setdefault((subject, proposition), []).append(row)

        conflicts = []
        for (subject, proposition), rows in by_key.items():
            current = [row for row in rows if str(row.get("status")) == "current"]
            values = {
                json.dumps(row.get("value"), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                for row in current
            }
            if len(values) > 1:
                conflicts.append(
                    {
                        "subject_ref": subject,
                        "proposition": proposition,
                        "evidence_ids": [str(row.get("evidence_id")) for row in current],
                    }
                )
        return {
            "rows": evidence,
            "by_subject": by_subject,
            "by_key": by_key,
            "conflicts": conflicts,
        }

    @staticmethod
    def _raw_effects(decision: PlannerDecision) -> list[dict]:
        return [
            row.model_dump(mode="json")
            for row in decision.invocations
            if _is_effect_capability(row.capability_id)
        ]

    @staticmethod
    def _raw_observations(decision: PlannerDecision) -> list[dict]:
        return [
            row.model_dump(mode="json")
            for row in decision.invocations
            if _is_observation_capability(row.capability_id)
        ]

    @staticmethod
    def _plan_by_id(plans: list[dict], plan_id: str | None) -> dict | None:
        if not plan_id:
            return None
        rows = [row for row in plans if str(row.get("plan_id")) == str(plan_id)]
        return rows[0] if len(rows) == 1 else None

    @classmethod
    def _infer_plan_from_effects(cls, ready: list[dict], decision: PlannerDecision) -> dict | None:
        actual = {_effect_invocation_key(row) for row in cls._raw_effects(decision)}
        if not actual:
            return None
        exact = []
        supersets = []
        for plan in ready:
            expected = {
                _effect_invocation_key(row)
                for row in (plan.get("invocations") or [])
                if _is_effect_capability(str(row.get("capability_id") or ""))
            }
            if actual == expected:
                exact.append(plan)
            elif actual and actual < expected:
                supersets.append(plan)
        if len(exact) == 1:
            return exact[0]
        if len(supersets) == 1:
            return supersets[0]
        return None

    @staticmethod
    def _integrity_for_plan(
        *,
        plan: dict,
        fragments: dict[str, Any],
        ledger: dict,
        catalog: dict[str, dict],
    ) -> dict:
        plan_id = str(plan.get("plan_id") or "")
        invocations = [row for row in (plan.get("invocations") or []) if isinstance(row, dict)]
        affected = {str(row) for row in (plan.get("affected_resources") or [])}
        inventory = {str(row) for row in (fragments.get("resource_inventory") or [])}
        needs = [row for row in (fragments.get("evidence_needs") or []) if isinstance(row, dict)]
        blocking_needs = [
            row
            for row in needs
            if not row.get("blocking_plan_ids") or plan_id in set(row.get("blocking_plan_ids") or [])
        ]
        investigation = fragments.get("investigation_state") or {}
        state_conflicts = list(investigation.get("conflicts") or []) if isinstance(investigation, dict) else []

        schema_failures = []
        unit_failures = []
        authority_failures = []
        for invocation in invocations:
            cid = str(invocation.get("capability_id") or "")
            resource = str(invocation.get("resource") or "")
            args = dict(invocation.get("canonical_arguments") or {})
            spec = catalog.get(cid)
            if spec is None:
                schema_failures.append({"capability_id": cid, "reason": "capability_not_in_catalog"})
                continue
            if resource not in inventory:
                authority_failures.append({"resource": resource, "reason": "outside_resource_inventory"})
            schema = dict(spec.get("canonical_input_schema") or {})
            if "target_s" in schema:
                value = args.get("target_s")
                if not isinstance(value, int) or isinstance(value, bool) or value < 60:
                    schema_failures.append(
                        {"capability_id": cid, "resource": resource, "reason": "invalid_target_s"}
                    )
            # This repository exposes canonical seconds and has no alternate unit
            # aliases on these device-effect plans.  Record that the WOA unit
            # check is applicable only through the canonical schema.
            if any("unit" in str(key).lower() for key in args):
                unit_failures.append(
                    {"capability_id": cid, "resource": resource, "reason": "unexpected_unit_field"}
                )

        relevant_rows = []
        for subject in affected:
            relevant_rows.extend(ledger["by_subject"].get(subject, []))
        if "monitoring-network" in set(
            str(row) for row in ((fragments.get("candidate_action_context") or {}).get("evidence_scope") or [])
        ):
            relevant_rows.extend(ledger["by_subject"].get("monitoring-network", []))

        source_failures = []
        freshness_failures = []
        for evidence in relevant_rows:
            if not evidence.get("source_id") or not evidence.get("source_role"):
                source_failures.append(
                    {"evidence_id": evidence.get("evidence_id"), "reason": "missing_source_binding"}
                )
            if not isinstance(evidence.get("provenance"), dict) or not evidence.get("provenance"):
                source_failures.append(
                    {"evidence_id": evidence.get("evidence_id"), "reason": "missing_provenance"}
                )
            if str(evidence.get("status")) not in {"current", "negative_observation"}:
                freshness_failures.append(
                    {
                        "evidence_id": evidence.get("evidence_id"),
                        "status": evidence.get("status"),
                        "reason": "noncurrent_support",
                    }
                )

        # A supported hold means the compiler claims the currently installed
        # profile is confirmed.  Require one current center node report for every
        # affected resource before authorizing that no-op decision.
        hold_support_failures = []
        if not invocations and str(plan.get("kind")) == "hold":
            for subject in sorted(affected):
                rows = ledger["by_key"].get((subject, "communication.center.node_report"), [])
                if not any(str(row.get("status")) == "current" for row in rows):
                    hold_support_failures.append(
                        {"subject_ref": subject, "reason": "missing_current_hold_confirmation"}
                    )

        scope_failures = []
        invocation_resources = {str(row.get("resource") or "") for row in invocations}
        if invocations and not invocation_resources <= affected:
            scope_failures.append(
                {
                    "reason": "invocation_outside_affected_resources",
                    "resources": sorted(invocation_resources - affected),
                }
            )

        conflict_failures = [*state_conflicts, *ledger["conflicts"]]
        valid = not any(
            (
                schema_failures,
                unit_failures,
                authority_failures,
                source_failures,
                freshness_failures,
                hold_support_failures,
                scope_failures,
                conflict_failures,
                blocking_needs,
                plan.get("unresolved_conditions"),
            )
        ) and plan.get("feasibility") == "supported"
        return {
            "valid": valid,
            "schema_ok": not schema_failures,
            "unit_ok": not unit_failures,
            "source_ok": not source_failures,
            "fresh": not freshness_failures and not hold_support_failures,
            "conflict_free": not conflict_failures,
            "scope_complete": not scope_failures,
            "authority_ok": not authority_failures,
            "blocking_need_count": len(blocking_needs),
            "violations": {
                "schema": schema_failures,
                "unit": unit_failures,
                "authority": authority_failures,
                "source": source_failures,
                "freshness": [*freshness_failures, *hold_support_failures],
                "conflict": conflict_failures,
                "scope": scope_failures,
                "blocking_needs": blocking_needs,
                "unresolved_conditions": list(plan.get("unresolved_conditions") or []),
            },
            "used_evidence_ids": sorted(
                {
                    str(row.get("evidence_id"))
                    for row in relevant_rows
                    if row.get("evidence_id")
                }
            ),
        }

    @staticmethod
    def _query_invocations_for_needs(
        needs: list[dict],
        catalog: dict[str, dict],
    ) -> list[PlannedCapabilityInvocation]:
        out: list[PlannedCapabilityInvocation] = []
        seen: set[tuple[str, str]] = set()
        for need in sorted(needs, key=lambda row: -int(row.get("priority") or 0)):
            text = " ".join(
                [
                    str(need.get("proposition_or_question") or ""),
                    str(need.get("purpose") or ""),
                ]
            )
            capability_id = next(
                (
                    cid
                    for cid in catalog
                    if cid.startswith(("communication.center.", "communication.gateway."))
                    and cid in text
                ),
                None,
            )
            if capability_id is None:
                continue
            for resource in need.get("target_objects") or ["gw0"]:
                key = (capability_id, str(resource))
                if key in seen:
                    continue
                seen.add(key)
                args = {}
                if capability_id.endswith("node_report"):
                    args = {"node_id": str(resource)}
                out.append(
                    PlannedCapabilityInvocation(
                        capability_id=capability_id,
                        resource=str(resource),
                        canonical_arguments=args,
                    )
                )
        return out

    def decide(
        self,
        request: ModelRequest,
        assembly: PromptAssembly,
    ) -> tuple[PlannerDecision, ModelUsage]:
        raw, usage = self.base.decide(request, assembly)
        fragments = _fragments(assembly)
        plans = self._candidate_plans(fragments)
        ready = self._ready_plans(plans)
        catalog = self._capability_catalog(fragments)
        ledger = self._canonical_ledger(fragments)
        needs = [row for row in (fragments.get("evidence_needs") or []) if isinstance(row, dict)]
        investigation = fragments.get("investigation_state") or {}

        proposal_plan = self._plan_by_id(plans, raw.selected_plan_id)
        inferred_plan = self._infer_plan_from_effects(ready, raw)
        repairs: list[dict] = []
        unresolved_risks: list[dict] = []
        governor = GOVERNOR_ABSTAIN
        selected: dict | None = None

        if proposal_plan in ready:
            selected = proposal_plan
        elif inferred_plan is not None:
            selected = inferred_plan
            repairs.append(
                {
                    "type": "bind_effect_subset_to_candidate_plan",
                    "from_selected_plan_id": raw.selected_plan_id,
                    "to_selected_plan_id": selected.get("plan_id"),
                }
            )
        elif len(ready) == 1:
            selected = ready[0]
            repairs.append(
                {
                    "type": "repair_to_unique_supported_plan",
                    "from_selected_plan_id": raw.selected_plan_id,
                    "to_selected_plan_id": selected.get("plan_id"),
                }
            )

        integrity = None
        final: PlannerDecision
        if selected is not None:
            integrity = self._integrity_for_plan(
                plan=selected,
                fragments=fragments,
                ledger=ledger,
                catalog=catalog,
            )
            if integrity["valid"]:
                has_effect = bool(selected.get("invocations"))
                governor = GOVERNOR_APPLY if has_effect else GOVERNOR_HOLD
                raw_effects = self._raw_effects(raw)
                raw_observations = self._raw_observations(raw)
                expected_effects = list(selected.get("invocations") or [])
                if (
                    raw_effects
                    and {_effect_invocation_key(row) for row in raw_effects}
                    != {_effect_invocation_key(row) for row in expected_effects}
                ):
                    repairs.append(
                        {
                            "type": "repair_effect_scope_to_candidate_plan",
                            "dropped_effect_invocations": raw_effects,
                        }
                    )
                if raw_observations:
                    repairs.append(
                        {
                            "type": "drop_nonblocking_observation_calls",
                            "dropped_observation_invocations": raw_observations,
                        }
                    )
                expected_stop = not has_effect
                if bool(raw.stop) != expected_stop:
                    repairs.append(
                        {
                            "type": "repair_stop_semantics",
                            "from_stop": bool(raw.stop),
                            "to_stop": expected_stop,
                        }
                    )
                final = PlannerDecision(
                    decision_id=raw.decision_id,
                    request_id=raw.request_id,
                    stop=expected_stop,
                    selected_plan_id=str(selected.get("plan_id")),
                    invocations=[],
                    state_patch=dict(raw.state_patch),
                    reason_codes=[
                        f"woa_governor:{governor}",
                        "woa_integrity_revalidated",
                        *(["woa_dependency_scoped_repair"] if repairs else []),
                    ],
                )
            else:
                unresolved_risks.extend(
                    {
                        "type": kind,
                        "detail": detail,
                    }
                    for kind, rows in integrity["violations"].items()
                    for detail in (rows if isinstance(rows, list) else [rows])
                    if rows
                )
                conflicts = integrity["violations"].get("conflict") or []
                blocking = integrity["violations"].get("blocking_needs") or []
                retry_invocations = self._query_invocations_for_needs(blocking, catalog)
                if conflicts:
                    governor = GOVERNOR_ESCALATE
                    final = PlannerDecision(
                        decision_id=raw.decision_id,
                        request_id=raw.request_id,
                        stop=True,
                        invocations=[],
                        reason_codes=["woa_governor:ESCALATE", "woa_unresolved_conflict"],
                    )
                elif retry_invocations:
                    governor = GOVERNOR_RETRY
                    final = PlannerDecision(
                        decision_id=raw.decision_id,
                        request_id=raw.request_id,
                        stop=False,
                        invocations=retry_invocations,
                        reason_codes=["woa_governor:RETRY", "woa_retry_blocking_support"],
                    )
                else:
                    governor = GOVERNOR_HOLD
                    final = PlannerDecision(
                        decision_id=raw.decision_id,
                        request_id=raw.request_id,
                        stop=True,
                        invocations=[],
                        reason_codes=["woa_governor:HOLD", "woa_support_not_current"],
                    )
        else:
            conflicts = list(investigation.get("conflicts") or []) if isinstance(investigation, dict) else []
            retry_invocations = self._query_invocations_for_needs(needs, catalog)
            if conflicts or len(ready) > 1:
                governor = GOVERNOR_ESCALATE
                unresolved_risks.extend(conflicts)
                final = PlannerDecision(
                    decision_id=raw.decision_id,
                    request_id=raw.request_id,
                    stop=True,
                    invocations=[],
                    reason_codes=["woa_governor:ESCALATE", "woa_ambiguous_authorization_state"],
                )
            elif retry_invocations:
                governor = GOVERNOR_RETRY
                final = PlannerDecision(
                    decision_id=raw.decision_id,
                    request_id=raw.request_id,
                    stop=False,
                    invocations=retry_invocations,
                    reason_codes=["woa_governor:RETRY", "woa_retry_required_source"],
                )
            elif needs:
                governor = GOVERNOR_HOLD
                unresolved_risks.extend(needs)
                final = PlannerDecision(
                    decision_id=raw.decision_id,
                    request_id=raw.request_id,
                    stop=True,
                    invocations=[],
                    reason_codes=["woa_governor:HOLD", "woa_required_state_not_current"],
                )
            else:
                governor = GOVERNOR_ABSTAIN
                final = PlannerDecision(
                    decision_id=raw.decision_id,
                    request_id=raw.request_id,
                    stop=True,
                    invocations=[],
                    reason_codes=["woa_governor:ABSTAIN", "woa_no_supported_action"],
                )

        record = {
            "request_id": request.request_id,
            "assembly_id": assembly.assembly_id,
            "world_revision": (
                investigation.get("last_world_revision") if isinstance(investigation, dict) else None
            ),
            "raw_proposal": raw.model_dump(mode="json"),
            "ready_supported_plan_ids": [str(row.get("plan_id")) for row in ready],
            "selected_plan_id_after_repair": final.selected_plan_id,
            "integrity": deepcopy(integrity),
            "repairs": repairs,
            "unresolved_risks": unresolved_risks,
            "governor": governor,
            "used_sources": (
                [] if integrity is None else list(integrity.get("used_evidence_ids") or [])
            ),
            "final_decision": final.model_dump(mode="json"),
        }
        self.records.append(record)
        return final, usage

