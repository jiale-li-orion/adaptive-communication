#!/usr/bin/env python3
"""Audit acquisition-mode competition on frozen Layer-1 v0.2 hard dev.

This closes cache06.md mechanism gate 8 without adding any new Layer-1 tool.
The compared modes are already present in the frozen causal process:

* dedicated paid owner query: ``ISSUE_QUERY gateway_state_summary``;
* normal business transmission: ``SEND_TERR`` which later yields receipt/ACK;
* passive/deferred observation: ``WAIT`` while execution feedback is pending;
* direct fallback execution: ``SEND_SAT``.

Exact action-feasibility labels are reused from the frozen reachable-prefix
L/U soundness artifact.  We replay the same v2 exact policy only to recover the
execution-state metadata needed to distinguish passive-feedback WAIT from a
plain defer.  No test split and no hidden future field are read.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any, Mapping

from causal_evidence_process_v0_1 import attach_causal_evidence
from compositional_recipe_generator_v0_1 import core_recipes
from dynamic_world_materializer_v0_1 import materialize_recipe
from exact_reference_oracle_v0_1 import LocalState, _attempt_lattice, _normalize
from layer2_v2_future_choice import solve_minimal_resource_v2
from v8_policy_baselines_v0_1 import _step


ROOT = Path(__file__).resolve().parents[3]
SPLIT = ROOT / "results/benchmark/layer1-structure-aware-split-v0.2-retry-legality.json"
BOUND = ROOT / "results/agentic/layer2-v2-bound-soundness-dev.json"
QUERY_KEY = "ISSUE_QUERY:gateway_state_summary"


def _representatives() -> dict[str, dict[str, Any]]:
    frozen = json.loads(SPLIT.read_text(encoding="utf-8"))
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in frozen["rows"]:
        if (
            row.get("candidate_role") == "HARD_PRE_ADMISSION_SURVIVOR"
            and row.get("split") == "dev"
        ):
            grouped[str(row["signature"])].append(row)
    return {
        signature: min(rows, key=lambda row: str(row["recipe_id"]))
        for signature, rows in grouped.items()
    }


def _initial(bundle: Mapping[str, Any], sat_budget: int) -> dict[str, LocalState]:
    return {
        str(world["world_id"]): LocalState(satellite_budget=sat_budget)
        for world in bundle["worlds"]
    }


def _walk_state_rows(
    bundle: Mapping[str, Any],
    *,
    at_s: int,
    states: Mapping[str, LocalState],
    query_budget: int,
    policy: Mapping[str, Any],
    rows: list[dict[str, Any]],
) -> None:
    process = attach_causal_evidence(bundle)
    branches = _normalize(bundle, process, at_s, states)
    if len(branches) != 1 or next(iter(branches)) != "same":
        if policy.get("event") != "OBSERVATION":
            raise AssertionError("policy misses required observation branch")
        children = {str(row["observation"]): row for row in policy["children"]}
        if set(children) != set(branches):
            raise AssertionError("policy observation support mismatch")
        for observation, child in sorted(branches.items()):
            _walk_state_rows(
                bundle,
                at_s=at_s,
                states=child,
                query_budget=query_budget,
                policy=children[observation]["subpolicy"],
                rows=rows,
            )
        return

    support = next(iter(branches.values()))
    pending_counts = [len(state.pending_deliveries) for state in support.values()]
    pending_query = any(state.pending_query is not None for state in support.values())
    rows.append(
        {
            "time_s": int(at_s),
            "query_budget": int(query_budget),
            "world_count": len(support),
            "pending_delivery_any": any(pending_counts),
            "pending_delivery_max": max(pending_counts, default=0),
            "pending_query_any": pending_query,
            "policy_action": (
                None
                if policy.get("terminal")
                else f"{policy['action']}:{policy.get('arg') if policy.get('arg') is not None else '-'}"
            ),
        }
    )
    if policy.get("terminal"):
        return
    action = (str(policy["action"]), policy.get("arg"))
    dq = int(action[0] == "ISSUE_QUERY")
    stepped = _step(bundle, process, support, at_s, action)
    if stepped is None:
        raise AssertionError("exact policy contains non-executable action")
    child, next_t = stepped
    _walk_state_rows(
        bundle,
        at_s=next_t,
        states=child,
        query_budget=query_budget - dq,
        policy=policy["subpolicy"],
        rows=rows,
    )


def _safe_modes(action_rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    modes: dict[str, list[str]] = defaultdict(list)
    for row in action_rows:
        if not bool(row["exact_solvable"]):
            continue
        key = str(row["action_key"])
        kind = key.split(":", 1)[0]
        modes[kind].append(key)
    return dict(modes)


def _case(
    bundle: Mapping[str, Any],
    *,
    bound_case: Mapping[str, Any],
) -> dict[str, Any]:
    solved = solve_minimal_resource_v2(bundle, upper_mode="all_recursive")
    if solved["solvable"] is not True:
        raise AssertionError("hard-dev case unexpectedly unsolved by v2")
    q, sat = map(int, solved["minimal_resource_point"])
    state_rows: list[dict[str, Any]] = []
    _walk_state_rows(
        bundle,
        at_s=min(_attempt_lattice(bundle)),
        states=_initial(bundle, sat),
        query_budget=q,
        policy=solved["policy"],
        rows=state_rows,
    )
    bound_rows = list(bound_case["result"]["rows"])
    if len(state_rows) != len(bound_rows):
        raise AssertionError("state replay and bound artifact prefix count diverged")

    rows = []
    for state_row, bound_row in zip(state_rows, bound_rows):
        if (
            state_row["time_s"] != int(bound_row["time_s"])
            or state_row["query_budget"] != int(bound_row["query_budget"])
        ):
            raise AssertionError("state replay and bound artifact ordering diverged")
        if state_row["query_budget"] <= 0:
            continue
        by_key = {
            str(row["action_key"]): bool(row["exact_solvable"])
            for row in bound_row["actions"]
        }
        if QUERY_KEY not in by_key:
            continue
        modes = _safe_modes(bound_row["actions"])
        query_safe = bool(by_key[QUERY_KEY])
        non_query_modes = {
            kind: keys
            for kind, keys in modes.items()
            if kind != "ISSUE_QUERY"
        }
        wait_safe = bool(non_query_modes.get("WAIT"))
        send_terr_safe = bool(non_query_modes.get("SEND_TERR"))
        send_sat_safe = bool(non_query_modes.get("SEND_SAT"))
        passive_feedback_safe = wait_safe and bool(state_row["pending_delivery_any"])

        labels = []
        if query_safe and not non_query_modes:
            labels.append("DEDICATED_QUERY_REQUIRED_FOR_FEASIBILITY")
        if query_safe and send_terr_safe:
            labels.append("QUERY_COMPETES_WITH_NORMAL_SEND_AS_PROBE")
        if query_safe and wait_safe:
            labels.append("QUERY_CAN_BE_DEFERRED")
        if not query_safe:
            labels.append("DEDICATED_QUERY_HARMFUL_NOW")
        if not query_safe and send_terr_safe:
            labels.append("NORMAL_SEND_AS_PROBE_DOMINATES_HARMFUL_QUERY_FOR_FEASIBILITY")
        if not query_safe and passive_feedback_safe:
            labels.append("PASSIVE_EXECUTION_FEEDBACK_DOMINATES_HARMFUL_QUERY_FOR_FEASIBILITY")
        if not query_safe and wait_safe and not passive_feedback_safe:
            labels.append("PLAIN_DEFER_DOMINATES_HARMFUL_QUERY_FOR_FEASIBILITY")
        if not query_safe and send_sat_safe:
            labels.append("DIRECT_FALLBACK_DOMINATES_HARMFUL_QUERY_FOR_FEASIBILITY")

        rows.append(
            {
                **state_row,
                "query_safe": query_safe,
                "safe_modes": non_query_modes,
                "passive_feedback_safe": passive_feedback_safe,
                "labels": labels,
            }
        )

    counter = Counter(label for row in rows for label in row["labels"])
    return {
        "minimal_resource_point": [q, sat],
        "query_budget_positive_query_boundary_count": len(rows),
        "query_safe_count": sum(row["query_safe"] for row in rows),
        "query_harmful_count": sum(not row["query_safe"] for row in rows),
        "label_counts": dict(sorted(counter.items())),
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    bound = json.loads(BOUND.read_text(encoding="utf-8"))
    if bound.get("status") != "PASS" or bound.get("split") != "dev":
        raise SystemExit("bound-soundness dev artifact is not frozen PASS")
    by_signature = {str(row["signature"]): row for row in bound["cases"]}
    reps = _representatives()
    recipes = {row.recipe_id: row for row in core_recipes()}
    cases = []
    for index, signature in enumerate(sorted(by_signature), 1):
        rep = reps[signature]
        result = _case(
            materialize_recipe(recipes[str(rep["recipe_id"])]),
            bound_case=by_signature[signature],
        )
        cases.append(
            {
                "signature": signature,
                "recipe_id": rep["recipe_id"],
                "result": result,
            }
        )
        print(
            index,
            signature[:12],
            "q-boundaries",
            result["query_budget_positive_query_boundary_count"],
            "required",
            result["label_counts"].get("DEDICATED_QUERY_REQUIRED_FOR_FEASIBILITY", 0),
            "send-probe",
            result["label_counts"].get("QUERY_COMPETES_WITH_NORMAL_SEND_AS_PROBE", 0),
            "passive",
            result["label_counts"].get(
                "PASSIVE_EXECUTION_FEEDBACK_DOMINATES_HARMFUL_QUERY_FOR_FEASIBILITY", 0
            ),
            flush=True,
        )

    labels = Counter(
        label
        for case in cases
        for label, count in case["result"]["label_counts"].items()
        for _ in range(int(count))
    )
    summary = {
        "signature_count": len(cases),
        "query_budget_positive_query_boundary_count": sum(
            case["result"]["query_budget_positive_query_boundary_count"] for case in cases
        ),
        "query_safe_count": sum(case["result"]["query_safe_count"] for case in cases),
        "query_harmful_count": sum(case["result"]["query_harmful_count"] for case in cases),
        "label_counts": dict(sorted(labels.items())),
    }
    required = labels["DEDICATED_QUERY_REQUIRED_FOR_FEASIBILITY"]
    send_competition = (
        labels["QUERY_COMPETES_WITH_NORMAL_SEND_AS_PROBE"]
        + labels["NORMAL_SEND_AS_PROBE_DOMINATES_HARMFUL_QUERY_FOR_FEASIBILITY"]
    )
    passive_competition = labels[
        "PASSIVE_EXECUTION_FEEDBACK_DOMINATES_HARMFUL_QUERY_FOR_FEASIBILITY"
    ]
    passed = bool(cases) and required > 0 and send_competition > 0 and passive_competition > 0
    artifact = {
        "schema_version": "0.1",
        "status": "PASS" if passed else "FAIL",
        "experiment": "layer2-v2-acquisition-mode-competition-dev",
        "scope": "exact-policy reachable dev prefixes with remaining paid-query budget",
        "summary": summary,
        "rules": [
            "Dedicated query, normal SEND_TERR, WAIT and SEND_SAT use the frozen Layer-1 causal transition semantics.",
            "SEND_TERR is counted as normal-send-as-probe only because the frozen process generates its real receipt/ACK or timeout feedback; no synthetic probe reward is added.",
            "WAIT is called passive-feedback competition only when an actual pending delivery/ACK exists; plain defer is reported separately.",
            "Safe non-query alternatives establish feasibility competition, not scalar cost dominance; bytes/airtime/energy remain uncalibrated.",
            "The audit reuses exact action labels from the frozen L/U soundness artifact and does not read test.",
        ],
        "cases": cases,
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps({"status": artifact["status"], "summary": summary}, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
