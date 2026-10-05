#!/usr/bin/env python3
"""Bound-only future-choice controller for evidence acquisition decisions.

This module never calls the exact continuation solver.  It exposes only sound
L/U conclusions: replayable lower certificates (L=1) and structural
impossibility upper bounds (U=0).  Unresolved actions remain UNKNOWN.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from action_feasibility_bounds_v0_1 import (
    causal_upper,
    choice_depth_lower_certificate,
    choice_depth_upper,
)
from causal_evidence_process_v0_1 import attach_causal_evidence
from continuation_resource_domains_v0_1 import verify_witness
from exact_reference_oracle_v0_1 import LocalState, _normalize
from v8_policy_baselines_v0_1 import _legal_actions, _step


Action = tuple[str, str | None]
QUERY: Action = ("ISSUE_QUERY", "gateway_state_summary")


def action_key(action: Action) -> str:
    return f"{action[0]}:{action[1] if action[1] is not None else '-'}"


def bound_action(
    bundle: Mapping[str, Any],
    process: Mapping[str, Any],
    *,
    at_s: int,
    states: Mapping[str, LocalState],
    query_budget: int,
    action: Action,
    upper_depth: int,
    choice_upper_depth: int | None,
    choice_lower_depth: int,
) -> dict[str, Any]:
    dq = int(action[0] == "ISSUE_QUERY")
    if dq > query_budget:
        return {"lower": 0, "upper": 0, "status": "IMPOSSIBLE", "source": "QUERY_BUDGET_EXHAUSTED"}
    stepped = _step(bundle, process, states, at_s, action)
    if stepped is None:
        return {"lower": 0, "upper": 0, "status": "IMPOSSIBLE", "source": "STEP_NOT_EXECUTABLE"}
    child, next_t = stepped
    qleft = query_budget - dq

    upper_metrics: dict[str, int] = {}
    if choice_upper_depth is None:
        upper_ok = causal_upper(
            bundle, process, next_t, deepcopy(child), qleft, upper_depth,
            metrics=upper_metrics,
        )
        upper_nodes = upper_metrics.get("upper_nodes", 0)
        upper_source = f"UPPER_D{upper_depth}"
    else:
        upper_ok = choice_depth_upper(
            bundle, process, next_t, deepcopy(child), qleft, choice_upper_depth,
            metrics=upper_metrics,
        )
        upper_nodes = upper_metrics.get("choice_upper_nodes", 0)
        upper_source = f"CHOICE_UPPER_D{choice_upper_depth}"
    if not upper_ok:
        return {
            "lower": 0, "upper": 0, "status": "IMPOSSIBLE",
            "source": upper_source,
            "upper_nodes": upper_nodes,
            "lower_nodes": 0,
        }

    lower_metrics: dict[str, int] = {}
    policy = choice_depth_lower_certificate(
        bundle, process, next_t, deepcopy(child), qleft, choice_lower_depth,
        metrics=lower_metrics,
    )
    if policy is not None:
        verify_witness(bundle, next_t, deepcopy(child), policy, query_budget=qleft)
        return {
            "lower": 1, "upper": 1, "status": "CERTIFIED",
            "source": f"CHOICE_LOWER_D{choice_lower_depth}",
            "upper_nodes": upper_nodes,
            "lower_nodes": lower_metrics.get("choice_lower_nodes", 0),
        }

    return {
        "lower": 0, "upper": 1, "status": "UNKNOWN",
        "source": "UNRESOLVED",
        "upper_nodes": upper_nodes,
        "lower_nodes": lower_metrics.get("choice_lower_nodes", 0),
    }


def bound_future_choice_context(
    bundle: Mapping[str, Any],
    *,
    at_s: int,
    states: Mapping[str, LocalState],
    query_budget: int,
    upper_depth: int = 0,
    choice_upper_depth: int | None = None,
    choice_lower_depth: int = 2,
) -> dict[str, Any]:
    process = attach_causal_evidence(bundle)
    normalized = _normalize(bundle, process, at_s, states)
    if len(normalized) != 1 or next(iter(normalized)) != "same":
        raise ValueError("controller requires a decision boundary without immediate observation split")
    support = next(iter(normalized.values()))
    actions = _legal_actions(bundle, process, support, at_s)
    rows = []
    for action in actions:
        rows.append({
            "action_key": action_key(action),
            **bound_action(
                bundle,
                process,
                at_s=at_s,
                states=support,
                query_budget=query_budget,
                action=action,
                upper_depth=upper_depth,
                choice_upper_depth=choice_upper_depth,
                choice_lower_depth=choice_lower_depth,
            ),
        })

    by_key = {row["action_key"]: row for row in rows}
    qkey = action_key(QUERY)
    query = by_key.get(qkey)
    non_query = [row for row in rows if row["action_key"] != qkey]

    # Stronger stop condition: a replayable continuation exists with zero future
    # paid queries from the current boundary itself.
    stop_metrics: dict[str, int] = {}
    stop_policy = choice_depth_lower_certificate(
        bundle,
        process,
        at_s,
        deepcopy(support),
        0,
        choice_lower_depth,
        metrics=stop_metrics,
    )
    stop_certified = stop_policy is not None
    if stop_policy is not None:
        verify_witness(bundle, at_s, deepcopy(support), stop_policy, query_budget=0)

    labels: list[str] = []
    if stop_certified:
        labels.append("STOP_ACQUISITION_CERTIFIED")
    if query is not None and query["status"] == "IMPOSSIBLE":
        labels.append("QUERY_HARMFUL_NOW")
    if any(row["status"] == "CERTIFIED" for row in non_query):
        labels.append("CAN_DEFER_QUERY")
    if (
        query is not None
        and query["status"] == "CERTIFIED"
        and non_query
        and all(row["status"] == "IMPOSSIBLE" for row in non_query)
    ):
        labels.append("QUERY_REQUIRED_NOW")
    if not labels:
        labels.append("UNRESOLVED")

    return {
        "schema_version": "0.1",
        "time_s": at_s,
        "query_budget": query_budget,
        "upper_depth": upper_depth,
        "choice_upper_depth": choice_upper_depth,
        "choice_lower_depth": choice_lower_depth,
        "labels": labels,
        "actions": rows,
        "stop_acquisition_certified": stop_certified,
        "stop_lower_nodes": stop_metrics.get("choice_lower_nodes", 0),
        "bound_cost": {
            "upper_nodes": sum(int(row.get("upper_nodes", 0)) for row in rows),
            "lower_nodes": sum(int(row.get("lower_nodes", 0)) for row in rows)
            + int(stop_metrics.get("choice_lower_nodes", 0)),
        },
    }
