#!/usr/bin/env python3
"""Revalidate frozen Layer-2 v1 acquisition triggering on Layer-1 v0.2.

The frozen v1 action-conditioned planner resolves every unresolved dependency
that has an active visible owner capability before executing a supported action.
This audit asks whether that trigger remains safe when acquisition itself is a
physical communication action that consumes time/opportunity.

For each of the 41 V8 hard signatures we follow the exact minimal-resource
policy prefix up to its first paid query.  At every prefix where the same
gateway query is legal, we force the query and run an exact continuation with
the remaining query budget.  A legal query is "harmful now" when no causal
continuation remains after taking it.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
import json
from pathlib import Path

from agentic_communication.planner import ActionConditionedReferencePlannerConsumer
from agentic_communication.runtime_contracts import (
    FragmentCacheClass,
    FragmentTrustClass,
    MaterializedFragment,
    ModelRequest,
    PromptAssembly,
)
from causal_evidence_process_v0_1 import attach_causal_evidence
from compositional_recipe_generator_v0_1 import core_recipes
from dynamic_world_materializer_v0_1 import materialize_recipe
from exact_reference_oracle_v0_1 import LocalState, _attempt_lattice
from layer1_v02_exact_continuation import ExactContinuationReference, replay_continuation_policy
from v8_policy_baselines_v0_1 import _legal_actions, _normalize_one, _step


ROOT = Path(__file__).resolve().parents[3]
SPLIT = ROOT / "results/benchmark/layer1-structure-aware-split-v0.2-retry-legality.json"
QUERY = ("ISSUE_QUERY", "gateway_state_summary")
QUERY_CAPABILITY_ID = "communication.gateway.state_summary"


def _initial(bundle: dict, budget: int) -> dict[str, LocalState]:
    return {
        str(w["world_id"]): LocalState(satellite_budget=budget)
        for w in bundle["worlds"]
    }


def _hard_representatives() -> list[dict]:
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in split["rows"]:
        if row.get("candidate_role") == "HARD_PRE_ADMISSION_SURVIVOR":
            grouped[str(row["signature"])].append(row)
    return [min(rows, key=lambda x: str(x["recipe_id"])) for _, rows in sorted(grouped.items())]


def _minimal_resource_policy(bundle: dict) -> tuple[int, int, dict]:
    start = min(_attempt_lattice(bundle))
    for query_budget in range(len(bundle["obligations"]) + 1):
        for sat_budget in range(int(bundle["public_environment"]["satellite_budget_units"]) + 1):
            solver = ExactContinuationReference(bundle)
            result = solver.solve(
                start,
                _initial(bundle, sat_budget),
                query_budget=query_budget,
            )
            if result["solvable"] is True:
                replay_continuation_policy(
                    bundle,
                    at_s=start,
                    states=_initial(bundle, sat_budget),
                    policy=result["policy"],
                    query_budget=query_budget,
                )
                return query_budget, sat_budget, result
    raise RuntimeError(f"no bounded exact policy for {bundle['recipe_id']}")


def _verify_v1_trigger() -> dict:
    """Exercise the frozen v1 consumer on one synthetic unresolved owner dependency."""

    candidate = MaterializedFragment.build(
        kind="candidate_action_context",
        source_ref="layer1-v02-revalidation:synthetic-binding",
        source_revision="1",
        trust_class=FragmentTrustClass.RUNTIME_CONTROL,
        cache_class=FragmentCacheClass.STATE_DYNAMIC,
        content={
            "candidate_plans": [],
            "dependencies": [
                {
                    "proposition": QUERY_CAPABILITY_ID,
                    "subject": "gw0",
                    "fresh": False,
                    "acquisition": "active_capability",
                    "scope_reason": "layer1_v02_gateway_state_summary",
                    "blocking_plan_ids": ["layer1_v02_open_decision_surface"],
                }
            ],
        },
    )
    catalog = MaterializedFragment.build(
        kind="capability_catalog",
        source_ref="layer1-v02-revalidation:synthetic-binding",
        source_revision="1",
        trust_class=FragmentTrustClass.RUNTIME_CONTROL,
        cache_class=FragmentCacheClass.STATIC,
        content=[{"capability_id": QUERY_CAPABILITY_ID}],
    )
    assembly = PromptAssembly.build(
        task_contract_id="task:layer1-v02-revalidation",
        task_run_id="run:layer1-v02-revalidation",
        context_manifest_revision=1,
        fragments=[candidate, catalog],
    )
    request = ModelRequest(
        request_id="request:layer1-v02-revalidation",
        task_run_id=assembly.task_run_id,
        assembly_id=assembly.assembly_id,
        assembly_hash=assembly.assembly_hash,
        consumer_id="action-conditioned-reference-v1",
    )
    decision, _ = ActionConditionedReferencePlannerConsumer().decide(request, assembly)
    emitted = [x.model_dump(mode="json") for x in decision.invocations]
    passed = (
        not decision.stop
        and len(emitted) == 1
        and emitted[0]["capability_id"] == QUERY_CAPABILITY_ID
        and emitted[0]["resource"] == "gw0"
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "planner_consumer": "action-conditioned-reference-v1",
        "trigger_condition": "unresolved dependency + active visible owner capability",
        "decision": decision.model_dump(mode="json"),
    }


def _run_case(bundle: dict) -> dict:
    query_budget, sat_budget, solved = _minimal_resource_policy(bundle)
    process = attach_causal_evidence(bundle)
    states = _initial(bundle, sat_budget)
    at_s = min(_attempt_lattice(bundle))
    node = solved["policy"]
    checks = []
    steps = 0

    while node and not node.get("terminal") and steps < 512:
        branches = _normalize_one(bundle, process, at_s, states)
        if len(branches) != 1 or next(iter(branches)) != "same":
            break
        states = next(iter(branches.values()))

        if QUERY in _legal_actions(bundle, process, states, at_s):
            stepped = _step(bundle, process, states, at_s, QUERY)
            assert stepped is not None
            child, next_t = stepped
            continuation = ExactContinuationReference(bundle).solve(
                next_t,
                deepcopy(child),
                query_budget=max(0, query_budget - 1),
            )
            if continuation["solvable"] is True:
                replay_continuation_policy(
                    bundle,
                    at_s=next_t,
                    states=child,
                    policy=continuation["policy"],
                    query_budget=max(0, query_budget - 1),
                )
            checks.append(
                {
                    "time_s": at_s,
                    "query_legal": True,
                    "query_preserves_causal_success": continuation["solvable"] is True,
                    "continuation_status": continuation["status"],
                    "continuation_expanded": continuation["expanded"],
                }
            )

        if node.get("action") == "ISSUE_QUERY":
            exact_query_time = at_s
            break
        stepped = _step(bundle, process, states, at_s, (node["action"], node.get("arg")))
        if stepped is None:
            raise AssertionError("exact policy contains a non-executable action")
        states, at_s = stepped
        node = node["subpolicy"]
        steps += 1
    else:
        exact_query_time = None

    legal = [row for row in checks if row["query_legal"]]
    certified = [row for row in legal if row["query_preserves_causal_success"]]
    harmful = [row for row in legal if not row["query_preserves_causal_success"]]
    first_legal = legal[0]["time_s"] if legal else None
    first_certified = certified[0]["time_s"] if certified else None
    return {
        "minimal_query_budget": query_budget,
        "minimal_satellite_budget": sat_budget,
        "exact_first_query_time_s": exact_query_time,
        "first_query_legal_time_s": first_legal,
        "first_query_certified_time_s": first_certified,
        "legal_query_boundary_count": len(legal),
        "certified_query_boundary_count": len(certified),
        "harmful_query_boundary_count": len(harmful),
        "first_legal_query_is_harmful": bool(legal and not legal[0]["query_preserves_causal_success"]),
        "exact_query_later_than_first_legal": bool(
            exact_query_time is not None and first_legal is not None and exact_query_time > first_legal
        ),
        "checks": checks,
    }


def main() -> int:
    trigger = _verify_v1_trigger()
    if trigger["status"] != "PASS":
        raise AssertionError("frozen v1 acquisition trigger behavior changed")

    recipes = {r.recipe_id: r for r in core_recipes()}
    rows = []
    for rep in _hard_representatives():
        bundle = materialize_recipe(recipes[str(rep["recipe_id"])])
        result = _run_case(bundle)
        rows.append(
            {
                "signature": rep["signature"],
                "split": rep["split"],
                "recipe_id": rep["recipe_id"],
                "result": result,
            }
        )

    summary = {
        "signature_count": len(rows),
        "split_counts": dict(sorted(Counter(row["split"] for row in rows).items())),
        "all_minimal_query_budget_one": all(row["result"]["minimal_query_budget"] == 1 for row in rows),
        "signatures_with_harmful_query_boundary": sum(
            row["result"]["harmful_query_boundary_count"] > 0 for row in rows
        ),
        "signatures_with_first_legal_query_harmful": sum(
            row["result"]["first_legal_query_is_harmful"] for row in rows
        ),
        "exact_query_later_than_first_legal": sum(
            row["result"]["exact_query_later_than_first_legal"] for row in rows
        ),
        "total_legal_query_boundaries": sum(
            row["result"]["legal_query_boundary_count"] for row in rows
        ),
        "total_certified_query_boundaries": sum(
            row["result"]["certified_query_boundary_count"] for row in rows
        ),
        "total_harmful_query_boundaries": sum(
            row["result"]["harmful_query_boundary_count"] for row in rows
        ),
    }
    passed = (
        len(rows) == 41
        and summary["signatures_with_harmful_query_boundary"] == 41
        and summary["signatures_with_first_legal_query_harmful"] == 41
        and summary["exact_query_later_than_first_legal"] == 41
    )
    artifact = {
        "schema_version": "0.1",
        "status": "PASS" if passed else "FAIL",
        "classification": "C_LAYER2_V1_ACQUISITION_TRIGGER_FAILURE",
        "v1_trigger_protocol_check": trigger,
        "summary": summary,
        "interpretation": [
            "Frozen Layer-2 v1 opens active owner acquisition when a required dependency is unresolved and the capability is visible.",
            "Layer-1 v0.2 makes acquisition a physical action: a query may be legal and relevant yet consume the opportunity needed for later obligation completion.",
            "A harmful-now boundary is a legal query boundary whose forced query leaves no exact causal continuation at the minimal resource point.",
            "The result isolates a decision-semantic v1 failure after assuming a lossless Layer-1-to-v1 binding; it does not claim that the old O1-O6 binding itself was lossless.",
        ],
        "claim_boundary": [
            "The audit follows exact minimal-resource policy prefixes only up to the first paid query.",
            "It diagnoses the acquisition trigger; it does not yet evaluate a Layer-2 v2 algorithm.",
            "The correct next method question is when evidence acquisition preserves future feasible choices, matching the retained future-choice/L-U line in cache06.md.",
        ],
        "rows": rows,
    }
    print(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
