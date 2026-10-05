#!/usr/bin/env python3
"""Certified next-action frontier at one causal continuation boundary."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping

from causal_evidence_process_v0_1 import attach_causal_evidence
from continuation_resource_domains_v0_1 import ContinuationPlanner, verify_witness
from exact_reference_oracle_v0_1 import LocalState, _normalize
from v8_policy_baselines_v0_1 import _legal_actions, _step


Action = tuple[str, str | None]
QUERY: Action = ("ISSUE_QUERY", "gateway_state_summary")


def _action_key(action: Action) -> str:
    return f"{action[0]}:{action[1] if action[1] is not None else '-'}"


def _action_json(action: Action) -> dict[str, Any]:
    return {"kind": action[0], "arg": action[1]}


def build_action_frontier(
    bundle: Mapping[str, Any],
    *,
    at_s: int,
    states: Mapping[str, LocalState],
    query_budget: int,
    max_expansions: int = 200_000,
) -> dict[str, Any]:
    if query_budget < 0:
        raise ValueError("negative query budget")
    process = attach_causal_evidence(bundle)
    normalized = _normalize(bundle, process, at_s, states)
    if len(normalized) != 1 or next(iter(normalized)) != "same":
        raise ValueError("frontier requires a decision boundary without immediate observation split")
    support = next(iter(normalized.values()))
    legal = _legal_actions(bundle, process, support, at_s)

    certified: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for action in legal:
        dq = int(action[0] == "ISSUE_QUERY")
        if dq > query_budget:
            rejected.append({"action": _action_json(action), "reason": "QUERY_BUDGET_EXHAUSTED"})
            continue
        stepped = _step(bundle, process, support, at_s, action)
        if stepped is None:
            rejected.append({"action": _action_json(action), "reason": "STEP_NOT_EXECUTABLE"})
            continue
        child, next_t = stepped
        result = ContinuationPlanner(bundle, mode="witness_domain").solve(
            next_t,
            deepcopy(child),
            query_budget=query_budget - dq,
            max_expansions=max_expansions,
        )
        if result["solvable"] is not True:
            rejected.append({
                "action": _action_json(action),
                "reason": result["status"] if result["solvable"] is None else "NO_CAUSAL_CONTINUATION",
                "continuation_status": result["status"],
                "metrics": result["metrics"],
            })
            continue
        full_policy = {
            "time_s": at_s,
            "action": action[0],
            "arg": action[1],
            "worlds": sorted(support),
            "subpolicy": result["policy"],
        }
        actual = verify_witness(bundle, at_s, deepcopy(support), full_policy, query_budget=query_budget)
        certified.append({
            "action": _action_json(action),
            "action_key": _action_key(action),
            "continuation_requirement_after_action": result["requirement"],
            "full_policy_requirement": actual,
            "policy_sha256": sha256(json.dumps(full_policy, sort_keys=True).encode()).hexdigest(),
            "continuation_metrics": result["metrics"],
        })

    no_query = ContinuationPlanner(bundle, mode="witness_domain").solve(
        at_s,
        deepcopy(support),
        query_budget=0,
        max_expansions=max_expansions,
    )
    if no_query["solvable"] is True:
        verify_witness(bundle, at_s, deepcopy(support), no_query["policy"], query_budget=0)

    legal_keys = [_action_key(a) for a in legal]
    certified_keys = [row["action_key"] for row in certified]
    query_key = _action_key(QUERY)
    non_query = [k for k in certified_keys if k != query_key]
    query_legal = query_key in legal_keys and query_budget > 0
    query_certified = query_key in certified_keys
    return {
        "schema_version": "0.1",
        "status": "CERTIFIED_ACTION_FRONTIER",
        "bundle_id": bundle["bundle_id"],
        "recipe_id": bundle["recipe_id"],
        "time_s": at_s,
        "query_budget": query_budget,
        "satellite_budget": sorted({st.satellite_budget for st in support.values()}),
        "compatible_world_ids": sorted(support),
        "legal_action_keys": legal_keys,
        "certified_action_keys": certified_keys,
        "certified_actions": certified,
        "rejected_actions": rejected,
        "context": {
            "query_free_completion": no_query["solvable"],
            "query_free_status": no_query["status"],
            "query_now_legal": query_legal,
            "query_now_certified": query_certified,
            "query_legal_but_not_certified": query_legal and not query_certified,
            "query_is_only_certified_next_action": query_certified and not non_query,
            "can_defer_query_now": bool(non_query),
            "certified_non_query_action_count": len(non_query),
            "certified_action_count": len(certified_keys),
        },
        "rules": [
            "legal = executable now; certified = exact causal continuation exists after taking the action",
            "a legal query can be uncertified when the read destroys a future feasible continuation",
            "can_defer_query_now is weaker than query_free_completion",
            "every certified action carries a replayed full causal witness",
        ],
    }

