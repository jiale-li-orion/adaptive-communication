#!/usr/bin/env python3
"""Incremental future-choice context compiler with persistent L/U proof memos."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from action_feasibility_bounds_v0_1 import choice_depth_lower_certificate, choice_depth_upper
from causal_evidence_process_v0_1 import attach_causal_evidence
from continuation_resource_domains_v0_1 import verify_witness
from exact_reference_oracle_v0_1 import LocalState, _normalize
from v8_policy_baselines_v0_1 import _legal_actions, _step


Action = tuple[str, str | None]
QUERY: Action = ("ISSUE_QUERY", "gateway_state_summary")


def _akey(action: Action) -> str:
    return f"{action[0]}:{action[1] if action[1] is not None else '-'}"


class FutureChoiceContextCompiler:
    """Maintain structural future-choice proofs across successive boundaries."""

    def __init__(self, bundle: Mapping[str, Any], *, choice_upper_depth: int, choice_lower_depth: int):
        self.bundle = deepcopy(bundle)
        self.process = attach_causal_evidence(self.bundle)
        self.choice_upper_depth = choice_upper_depth
        self.choice_lower_depth = choice_lower_depth
        self.upper_memo: dict[Any, bool] = {}
        self.lower_memo: dict[Any, dict[str, Any] | None] = {}
        self.totals = {
            "upper_nodes": 0,
            "lower_nodes": 0,
            "contexts": 0,
            "actions": 0,
        }

    def _bound_action(
        self,
        *,
        at_s: int,
        states: Mapping[str, LocalState],
        query_budget: int,
        action: Action,
    ) -> dict[str, Any]:
        self.totals["actions"] += 1
        dq = int(action[0] == "ISSUE_QUERY")
        if dq > query_budget:
            return {"status": "IMPOSSIBLE", "source": "QUERY_BUDGET_EXHAUSTED", "upper_nodes": 0, "lower_nodes": 0}
        stepped = _step(self.bundle, self.process, states, at_s, action)
        if stepped is None:
            return {"status": "IMPOSSIBLE", "source": "STEP_NOT_EXECUTABLE", "upper_nodes": 0, "lower_nodes": 0}
        child, next_t = stepped
        qleft = query_budget - dq

        um: dict[str, int] = {}
        upper_ok = choice_depth_upper(
            self.bundle,
            self.process,
            next_t,
            deepcopy(child),
            qleft,
            self.choice_upper_depth,
            metrics=um,
            memo=self.upper_memo,
        )
        unodes = int(um.get("choice_upper_nodes", 0))
        self.totals["upper_nodes"] += unodes
        if not upper_ok:
            return {
                "status": "IMPOSSIBLE",
                "source": f"CHOICE_UPPER_D{self.choice_upper_depth}",
                "upper_nodes": unodes,
                "lower_nodes": 0,
            }

        lm: dict[str, int] = {}
        policy = choice_depth_lower_certificate(
            self.bundle,
            self.process,
            next_t,
            deepcopy(child),
            qleft,
            self.choice_lower_depth,
            metrics=lm,
            memo=self.lower_memo,
        )
        lnodes = int(lm.get("choice_lower_nodes", 0))
        self.totals["lower_nodes"] += lnodes
        if policy is not None:
            verify_witness(self.bundle, next_t, deepcopy(child), policy, query_budget=qleft)
            return {
                "status": "CERTIFIED",
                "source": f"CHOICE_LOWER_D{self.choice_lower_depth}",
                "upper_nodes": unodes,
                "lower_nodes": lnodes,
            }
        return {
            "status": "UNKNOWN",
            "source": "UNRESOLVED",
            "upper_nodes": unodes,
            "lower_nodes": lnodes,
        }

    def context(
        self,
        *,
        at_s: int,
        states: Mapping[str, LocalState],
        query_budget: int,
    ) -> dict[str, Any]:
        self.totals["contexts"] += 1
        normalized = _normalize(self.bundle, self.process, at_s, states)
        if len(normalized) != 1 or next(iter(normalized)) != "same":
            raise ValueError("compiler requires a decision boundary without immediate observation split")
        support = next(iter(normalized.values()))
        actions = _legal_actions(self.bundle, self.process, support, at_s)
        rows = []
        for action in actions:
            rows.append({
                "action_key": _akey(action),
                **self._bound_action(
                    at_s=at_s,
                    states=support,
                    query_budget=query_budget,
                    action=action,
                ),
            })

        qkey = _akey(QUERY)
        by_key = {row["action_key"]: row for row in rows}
        query = by_key.get(qkey)
        non_query = [row for row in rows if row["action_key"] != qkey]

        stop_metrics: dict[str, int] = {}
        stop_policy = choice_depth_lower_certificate(
            self.bundle,
            self.process,
            at_s,
            deepcopy(support),
            0,
            self.choice_lower_depth,
            metrics=stop_metrics,
            memo=self.lower_memo,
        )
        stop_nodes = int(stop_metrics.get("choice_lower_nodes", 0))
        self.totals["lower_nodes"] += stop_nodes
        stop = stop_policy is not None
        if stop_policy is not None:
            verify_witness(self.bundle, at_s, deepcopy(support), stop_policy, query_budget=0)

        labels = []
        if stop:
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
            "time_s": at_s,
            "labels": labels,
            "actions": rows,
            "stop_acquisition_certified": stop,
            "new_nodes": {
                "upper": sum(int(r["upper_nodes"]) for r in rows),
                "lower": sum(int(r["lower_nodes"]) for r in rows) + stop_nodes,
            },
            "memo_size": {
                "upper": len(self.upper_memo),
                "lower": len(self.lower_memo),
            },
        }
