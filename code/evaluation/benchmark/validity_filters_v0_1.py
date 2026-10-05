#!/usr/bin/env python3
"""Automatic V0-V7 validity filters for the Layer-1 compositional IR.

This module is deliberately pre-baseline: V8 shortcut audit and V9 evaluator
soundness remain separate stages.  It consumes the frozen world/evidence IR and
exact references; it never invents a scalar reward or a sacrifice priority.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping

from causal_evidence_process_v0_1 import attach_causal_evidence
from exact_reference_oracle_v0_1 import (
    FINAL_ACK_DELAY_S,
    SATELLITE_COMPLETION_DELAY_S,
    hindsight_bundle_reference,
    solve_observation_matched,
)


@dataclass(frozen=True)
class AssignmentOption:
    resource_id: str
    path: str
    send_at_s: int


def _earliest_send(o: Mapping[str, Any], w: Mapping[str, Any], delay_s: int, *, ignore_deadline: bool) -> int | None:
    release = int(o["release_s"])
    deadline = int(o["deadline_s"])
    start = int(w["start_s"])
    end = int(w["end_s"])
    t = max(release, start)
    if t >= end:
        return None
    if not ignore_deadline and t + delay_s > deadline:
        return None
    return t


def _assignment_problem(
    bundle: Mapping[str, Any],
    world: Mapping[str, Any],
    *,
    relax_deadline: bool = False,
    relax_capacity: bool = False,
    relax_satellite_budget: bool = False,
) -> tuple[list[list[AssignmentOption]], dict[str, int], int]:
    obligations = list(bundle["obligations"])
    caps: dict[str, int] = {}
    options: list[list[AssignmentOption]] = []
    for w in world["terrestrial_windows"]:
        caps[f"T::{w['window_id']}"] = (
            len(obligations) if relax_capacity else int(w["capacity_units"])
        )
    for w in bundle["public_environment"]["satellite_windows"]:
        caps[f"S::{w['window_id']}"] = (
            len(obligations) if relax_capacity else int(w["capacity_units"])
        )
    sat_budget = (
        len(obligations)
        if relax_satellite_budget
        else int(bundle["public_environment"]["satellite_budget_units"])
    )
    for o in obligations:
        row: list[AssignmentOption] = []
        for w in world["terrestrial_windows"]:
            t = _earliest_send(o, w, FINAL_ACK_DELAY_S, ignore_deadline=relax_deadline)
            if t is not None:
                row.append(AssignmentOption(f"T::{w['window_id']}", "TERRESTRIAL", t))
        for w in bundle["public_environment"]["satellite_windows"]:
            t = _earliest_send(o, w, SATELLITE_COMPLETION_DELAY_S, ignore_deadline=relax_deadline)
            if t is not None:
                row.append(AssignmentOption(f"S::{w['window_id']}", "SATELLITE", t))
        options.append(row)
    return options, caps, sat_budget


def count_physical_success_plans(
    bundle: Mapping[str, Any],
    world: Mapping[str, Any],
    *,
    cap: int = 10_000,
    relax_deadline: bool = False,
    relax_capacity: bool = False,
    relax_satellite_budget: bool = False,
) -> int:
    """Count resource assignments exactly up to ``cap`` for 2-4 obligations."""
    options, capacities, sat_budget = _assignment_problem(
        bundle,
        world,
        relax_deadline=relax_deadline,
        relax_capacity=relax_capacity,
        relax_satellite_budget=relax_satellite_budget,
    )
    if any(not row for row in options):
        return 0
    order = sorted(range(len(options)), key=lambda i: len(options[i]))
    used: dict[str, int] = {}
    total = 0

    def rec(depth: int, sat_used: int) -> None:
        nonlocal total
        if total >= cap:
            return
        if depth == len(order):
            total += 1
            return
        i = order[depth]
        for opt in options[i]:
            current = used.get(opt.resource_id, 0)
            if current >= capacities[opt.resource_id]:
                continue
            is_sat = opt.path == "SATELLITE"
            if is_sat and sat_used >= sat_budget:
                continue
            used[opt.resource_id] = current + 1
            rec(depth + 1, sat_used + int(is_sat))
            if current:
                used[opt.resource_id] = current
            else:
                used.pop(opt.resource_id, None)
            if total >= cap:
                return

    rec(0, 0)
    return total


def _blind_process(process: Mapping[str, Any]) -> dict[str, Any]:
    blind = deepcopy(dict(process))
    blind["direct_observation"] = False
    blind["query_capabilities"] = []
    blind["passive_observation_rules"] = []
    blind["normal_send_probe_rules"] = []
    blind["evidence_regime"] = "BLIND_OPEN_LOOP_REFERENCE"
    return blind


def _filter(fid: str, passed: bool | None, reason: str, **extra: Any) -> dict[str, Any]:
    return {"filter_id": fid, "passed": passed, "reason_code": reason, **extra}


def evaluate_v0_v7(
    bundle: Mapping[str, Any],
    *,
    max_memo_nodes: int = 50_000,
    plan_count_cap: int = 10_000,
) -> dict[str, Any]:
    process = attach_causal_evidence(bundle)
    physical = hindsight_bundle_reference(bundle)
    filters: list[dict[str, Any]] = []

    # V0: current task authority is DB44; partial adjacent profiles only supply
    # resolved primitives.  Recipe blockers are preserved for the filter that
    # owns them rather than misclassified as V0 task-source gaps.
    filters.append(_filter("V0_SOURCE_COMPLETE", True, "PASS_TASK_AUTHORITY_AND_SAMPLED_AXES_RESOLVED"))

    all_worlds = bool(physical["all_worlds_solvable"])
    filters.append(
        _filter(
            "V1_SOLVABLE",
            all_worlds,
            "PASS_ALL_ALIAS_WORLDS_PHYSICALLY_SOLVABLE" if all_worlds else "GENERATOR_INVALID_CONTROLLED_STRESS_WORLD_INFEASIBLE",
            world_solvability={r["world_id"]: bool(r["solvable"]) for r in physical["worlds"]},
        )
    )

    plan_counts: dict[str, int] = {}
    deadline_relaxed: dict[str, int] = {}
    capacity_relaxed: dict[str, int] = {}
    sat_relaxed: dict[str, int] = {}
    for world in bundle["worlds"]:
        wid = str(world["world_id"])
        plan_counts[wid] = count_physical_success_plans(bundle, world, cap=plan_count_cap)
        deadline_relaxed[wid] = count_physical_success_plans(
            bundle, world, cap=plan_count_cap, relax_deadline=True
        )
        capacity_relaxed[wid] = count_physical_success_plans(
            bundle, world, cap=plan_count_cap, relax_capacity=True
        )
        sat_relaxed[wid] = count_physical_success_plans(
            bundle, world, cap=plan_count_cap, relax_satellite_budget=True
        )

    multiple = any(n >= 2 for n in plan_counts.values())
    filters.append(
        _filter(
            "V2_MULTIPLE_LEGAL_OPTIONS",
            multiple,
            "PASS_MULTIPLE_PHYSICAL_SUCCESS_PLANS" if multiple else "UNIQUE_READY",
            success_plan_assignment_count_capped=plan_counts,
            count_cap=plan_count_cap,
        )
    )

    exact = solve_observation_matched(bundle, process, max_memo_nodes=max_memo_nodes)
    no_paid = solve_observation_matched(
        bundle, process, disable_paid_query=True, max_memo_nodes=max_memo_nodes
    )
    blind = solve_observation_matched(
        bundle, _blind_process(process), disable_paid_query=True, max_memo_nodes=max_memo_nodes
    )
    search_limited = any(x["status"] == "SEARCH_LIMIT" for x in (exact, no_paid, blind))

    if search_limited:
        filters.append(_filter("V3_COMMON_SAFE_ACTION", None, "ORACLE_SEARCH_LIMIT"))
        filters.append(_filter("V4_OBSERVATION_RELEVANCE", None, "ORACLE_SEARCH_LIMIT"))
    elif not exact["solvable"]:
        filters.append(
            _filter(
                "V3_COMMON_SAFE_ACTION",
                None,
                "NOT_REACHED_INFORMATION_INFEASIBLE",
                note="V3 is an admission test for solvable information structures, not a label for impossible bundles",
            )
        )
        filters.append(
            _filter(
                "V4_OBSERVATION_RELEVANCE",
                None,
                "NOT_REACHED_INFORMATION_INFEASIBLE",
                exact_solvable=False,
                no_paid_query_solvable=no_paid["solvable"],
                blind_open_loop_solvable=blind["solvable"],
            )
        )
    else:
        # Conservative V3 witness: if a blind open-loop policy already succeeds
        # over the whole alias support, the case cannot claim EvidenceNeed.
        # Passive ACK / normal send-as-probe are deliberately NOT counted as a
        # common-safe shortcut; cache06 requires them to remain in the no-paid
        # reference rather than be stripped from ordinary policies.
        common_safe = bool(blind["solvable"])
        filters.append(
            _filter(
                "V3_COMMON_SAFE_ACTION",
                not common_safe,
                "COMMON_SAFE_OPEN_LOOP_POLICY" if common_safe else "PASS_NO_COMMON_BLIND_POLICY",
                note="policy-level conservative witness; query/passive/probe actions are excluded from the blind reference",
            )
        )
        evidence_relevant = not bool(blind["solvable"])
        paid_required = bool(exact["solvable"]) and not bool(no_paid["solvable"])
        filters.append(
            _filter(
                "V4_OBSERVATION_RELEVANCE",
                evidence_relevant,
                "PASS_PAID_EVIDENCE_REQUIRED"
                if paid_required
                else "PASS_PASSIVE_OR_DIRECT_EVIDENCE_RELEVANT"
                if evidence_relevant
                else "EVIDENCE_IRRELEVANT_TO_ROBUST_SUCCESS",
                paid_evidence_required=paid_required,
                exact_solvable=exact["solvable"],
                no_paid_query_solvable=no_paid["solvable"],
                blind_open_loop_solvable=blind["solvable"],
            )
        )

    # V5 uses plan-set expansion, not only max-completed count.  The source
    # reporting deadline is a genuine source-backed constraint; capacity and
    # satellite-budget comparisons are reported separately as stress bindings.
    deadline_binding = any(deadline_relaxed[w] > plan_counts[w] for w in plan_counts)
    capacity_binding = any(capacity_relaxed[w] > plan_counts[w] for w in plan_counts)
    satellite_binding = any(sat_relaxed[w] > plan_counts[w] for w in plan_counts)
    filters.append(
        _filter(
            "V5_BINDING_CONSTRAINT",
            deadline_binding or capacity_binding or satellite_binding,
            "PASS_BINDING_CONSTRAINT" if (deadline_binding or capacity_binding or satellite_binding) else "NO_BINDING_CONSTRAINT",
            source_deadline_binding=deadline_binding,
            controlled_capacity_binding=capacity_binding,
            controlled_satellite_budget_binding=satellite_binding,
            relaxed_plan_counts={
                "deadline": deadline_relaxed,
                "capacity": capacity_relaxed,
                "satellite_budget": sat_relaxed,
            },
        )
    )

    # V6: if at least one robust policy succeeds while another legal open-loop
    # policy class cannot guarantee success, legal policy choice changes the
    # obligation-feasibility trajectory.  Multiple physical plan assignments
    # also establish distinct execution trajectories even when both terminate
    # successfully.
    if search_limited:
        filters.append(_filter("V6_OUTCOME_SEPARATION", None, "ORACLE_SEARCH_LIMIT"))
    else:
        separated = (bool(exact["solvable"]) and not bool(blind["solvable"])) or multiple
        filters.append(
            _filter(
                "V6_OUTCOME_SEPARATION",
                separated,
                "PASS_POLICY_OR_EXECUTION_TRAJECTORY_SEPARATION" if separated else "OUTCOME_EQUIVALENT",
            )
        )

    unresolved_priority = bundle.get("recovery", {}).get("unresolved_field") == "reconnect_backlog_priority"
    if all_worlds:
        filters.append(
            _filter(
                "V7_OBJECTIVE_DEFINED",
                True,
                "PASS_ALL_OBLIGATIONS_JOINTLY_FEASIBLE_PRIORITY_NOT_INVOKED"
                if unresolved_priority
                else "PASS_NO_UNDEFINED_SACRIFICE_ORDERING",
            )
        )
    else:
        filters.append(
            _filter(
                "V7_OBJECTIVE_DEFINED",
                False if unresolved_priority else None,
                "OBJECTIVE_AMBIGUOUS" if unresolved_priority else "NOT_REACHED_WORLD_INFEASIBLE",
            )
        )

    return {
        "schema_version": "0.1",
        "recipe_id": bundle["recipe_id"],
        "bundle_id": bundle["bundle_id"],
        "stage": "V0_V7_AUTOMATIC_VALIDITY",
        "filters": filters,
        "oracle_summary": {
            "hindsight_all_worlds_solvable": all_worlds,
            "exact_status": exact["status"],
            "exact_solvable": exact["solvable"],
            "no_paid_query_status": no_paid["status"],
            "no_paid_query_solvable": no_paid["solvable"],
            "blind_status": blind["status"],
            "blind_solvable": blind["solvable"],
            "max_memo_nodes": max(int(exact["memo_nodes"]), int(no_paid["memo_nodes"]), int(blind["memo_nodes"])),
        },
        "release_status": "NOT_BENCHMARK_ADMIT",
        "next_stage": "V8_STRONG_BASELINE_SHORTCUT_AUDIT",
    }
