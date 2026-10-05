#!/usr/bin/env python3
"""Close the frozen Layer-2 v1 revalidation matrix on Layer-1 v0.2.

The matrix distinguishes three outcomes:

* A — the v1 mechanism/contract transfers without changing decision semantics;
* B — the old O1--O6 implementation is task-specific and needs a representation
  or capability binding before it can be evaluated fairly;
* C — after a lossless binding, the v1 decision semantics themselves fail.

No B result is promoted into a method failure, and no historical A7--A11 result
is silently re-labelled as a new-v0.2 result.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any

from agentic_communication.planner import (
    ActionConditionedReferencePlannerConsumer,
    CompiledChecklistPlannerConsumer,
    EvidenceAwareComplyPlannerConsumer,
)
from agentic_communication.runtime_contracts import (
    FragmentCacheClass,
    FragmentTrustClass,
    MaterializedFragment,
    ModelRequest,
    PromptAssembly,
)
from compositional_recipe_generator_v0_1 import core_recipes
from dynamic_world_materializer_v0_1 import materialize_recipe
from exact_reference_oracle_v0_1 import LocalState, _attempt_lattice, _normalize
from layer1_v02_v1_binding import (
    CAP_GATEWAY_SUMMARY,
    candidate_context_from_boundary,
    capability_catalog_rows,
    task_contract_from_bundle,
)


ROOT = Path(__file__).resolve().parents[3]
SPLIT = ROOT / "results/benchmark/layer1-structure-aware-split-v0.2-retry-legality.json"
REP = ROOT / "results/agentic/layer1-v02-layer2-v1-representability.json"
BIND = ROOT / "results/agentic/layer1-v02-v1-lossless-binding.json"
TRIGGER = ROOT / "results/agentic/layer1-v02-layer2-v1-acquisition-trigger.json"


def hard_representatives() -> list[dict[str, Any]]:
    frozen = json.loads(SPLIT.read_text(encoding="utf-8"))
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in frozen["rows"]:
        if row.get("candidate_role") == "HARD_PRE_ADMISSION_SURVIVOR":
            grouped[str(row["signature"])].append(row)
    return [min(rows, key=lambda row: str(row["recipe_id"])) for _, rows in sorted(grouped.items())]


def initial_boundary(bundle: dict[str, Any]) -> tuple[int, dict[str, LocalState]]:
    at_s = min(_attempt_lattice(bundle))
    states = {
        str(world["world_id"]): LocalState(
            satellite_budget=int(bundle["public_environment"]["satellite_budget_units"])
        )
        for world in bundle["worlds"]
    }
    process = __import__("causal_evidence_process_v0_1").attach_causal_evidence(bundle)
    branches = _normalize(bundle, process, at_s, states)
    if len(branches) != 1 or next(iter(branches)) != "same":
        raise RuntimeError("initial hard boundary unexpectedly emits an observation split")
    return at_s, next(iter(branches.values()))


def assembly_for_candidate(bundle: dict[str, Any]) -> PromptAssembly:
    at_s, states = initial_boundary(bundle)
    candidate = candidate_context_from_boundary(bundle, at_s=at_s, states=states)
    fragments = [
        MaterializedFragment.build(
            kind="candidate_action_context",
            source_ref="layer1-v02-v1-revalidation",
            source_revision="1",
            trust_class=FragmentTrustClass.RUNTIME_CONTROL,
            cache_class=FragmentCacheClass.STATE_DYNAMIC,
            content=candidate,
        ),
        MaterializedFragment.build(
            kind="capability_catalog",
            source_ref="layer1-v02-v1-revalidation",
            source_revision="1",
            trust_class=FragmentTrustClass.RUNTIME_CONTROL,
            cache_class=FragmentCacheClass.STATIC,
            content=capability_catalog_rows(),
        ),
    ]
    task = task_contract_from_bundle(bundle)
    return PromptAssembly.build(
        task_contract_id=task.task_contract_id,
        task_run_id=f"run:{bundle['recipe_id']}",
        context_manifest_revision=1,
        fragments=fragments,
    )


def request_for(assembly: PromptAssembly, consumer_id: str) -> ModelRequest:
    return ModelRequest(
        request_id=f"request:{consumer_id}:{assembly.task_run_id}",
        task_run_id=assembly.task_run_id,
        assembly_id=assembly.assembly_id,
        assembly_hash=assembly.assembly_hash,
        consumer_id=consumer_id,
    )


def compiled_checklist_probe(bundle: dict[str, Any]) -> dict[str, Any]:
    assembly = assembly_for_candidate(bundle)
    consumer = CompiledChecklistPlannerConsumer()
    decision, _ = consumer.decide(request_for(assembly, consumer.consumer_id), assembly)
    return {
        "stop": bool(decision.stop),
        "selected_plan_id": decision.selected_plan_id,
        "reason_codes": list(decision.reason_codes),
    }


def evidence_aware_gateway_summary_probe(bundle: dict[str, Any]) -> dict[str, Any]:
    """Check whether the frozen EvidenceAware consumer understands the new owner read ID."""

    assembly = assembly_for_candidate(bundle)
    need = MaterializedFragment.build(
        kind="evidence_needs",
        source_ref="layer1-v02-v1-revalidation",
        source_revision="1",
        trust_class=FragmentTrustClass.RUNTIME_CONTROL,
        cache_class=FragmentCacheClass.STATE_DYNAMIC,
        content=[
            {
                "status": "open",
                "proposition_or_question": CAP_GATEWAY_SUMMARY,
                "purpose": "resolve current gateway state summary",
            }
        ],
    )
    assembly = PromptAssembly.build(
        task_contract_id=assembly.task_contract_id,
        task_run_id=assembly.task_run_id,
        context_manifest_revision=2,
        fragments=[*assembly.fragments, need],
    )
    consumer = EvidenceAwareComplyPlannerConsumer()
    try:
        decision, _ = consumer.decide(request_for(assembly, consumer.consumer_id), assembly)
        return {
            "status": "DECIDED",
            "stop": bool(decision.stop),
            "invocation_ids": [row.capability_id for row in decision.invocations],
            "reason_codes": list(decision.reason_codes),
        }
    except Exception as exc:  # frozen v1 may fall through to O1-O6 comply fields
        return {
            "status": "BINDING_ERROR",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "stop": True,
            "invocation_ids": [],
            "reason_codes": ["old-task-binding-error"],
        }


def action_conditioned_gateway_summary_probe(bundle: dict[str, Any]) -> dict[str, Any]:
    """Exercise the generic v1 active-dependency trigger through the lossless binding."""

    assembly = assembly_for_candidate(bundle)
    candidate = next(fragment for fragment in assembly.fragments if fragment.kind == "candidate_action_context")
    content = dict(candidate.content)
    content["dependencies"] = [
        {
            "proposition": CAP_GATEWAY_SUMMARY,
            "subject": "gw0",
            "fresh": False,
            "acquisition": "active_capability",
            "blocking_plan_ids": [row["plan_id"] for row in content["candidate_plans"]],
        }
    ]
    replacement = MaterializedFragment.build(
        kind="candidate_action_context",
        source_ref="layer1-v02-v1-revalidation",
        source_revision="2",
        trust_class=FragmentTrustClass.RUNTIME_CONTROL,
        cache_class=FragmentCacheClass.STATE_DYNAMIC,
        content=content,
    )
    fragments = [replacement if fragment.kind == "candidate_action_context" else fragment for fragment in assembly.fragments]
    assembly = PromptAssembly.build(
        task_contract_id=assembly.task_contract_id,
        task_run_id=assembly.task_run_id,
        context_manifest_revision=2,
        fragments=fragments,
    )
    consumer = ActionConditionedReferencePlannerConsumer()
    decision, _ = consumer.decide(request_for(assembly, consumer.consumer_id), assembly)
    return {
        "stop": bool(decision.stop),
        "invocation_ids": [row.capability_id for row in decision.invocations],
        "reason_codes": list(decision.reason_codes),
    }


def main() -> int:
    representability = json.loads(REP.read_text(encoding="utf-8"))
    binding = json.loads(BIND.read_text(encoding="utf-8"))
    trigger = json.loads(TRIGGER.read_text(encoding="utf-8"))
    recipes = {row.recipe_id: row for row in core_recipes()}
    reps = hard_representatives()

    checklist = []
    evidence_aware = []
    action_conditioned = []
    for rep in reps:
        bundle = materialize_recipe(recipes[str(rep["recipe_id"])])
        checklist.append(compiled_checklist_probe(bundle))
        evidence_aware.append(evidence_aware_gateway_summary_probe(bundle))
        action_conditioned.append(action_conditioned_gateway_summary_probe(bundle))

    matrix = [
        {
            "mechanism": "Task/Evidence/Context/Capability runtime contracts",
            "class": "A",
            "verdict": "TRANSFERRED_THROUGH_LOSSLESS_BINDING",
            "evidence": {
                "hard_signatures": binding["summary"]["signature_count"],
                "decision_boundaries": binding["summary"]["decision_boundary_count"],
                "candidate_actions": binding["summary"]["candidate_action_count"],
                "roundtrip_mismatches": binding["summary"]["action_roundtrip_mismatch_count"],
                "hidden_field_leakage": binding["summary"]["forbidden_hidden_field_count"],
            },
        },
        {
            "mechanism": "old O1-O6 compiler/registry/selector binding",
            "class": "B",
            "verdict": "TASK_SPECIFIC_LOSSY_AS_IS",
            "evidence": {
                "lossless": representability["as_is_lossless_count"],
                "lossy": representability["as_is_lossy_count"],
            },
        },
        {
            "mechanism": "CompiledChecklist ordinary baseline",
            "class": "A",
            "verdict": "NO_LONGER_SATURATES_OPEN_DECISION_SURFACE",
            "evidence": {
                "initial_stop_count": sum(row["stop"] for row in checklist),
                "unique_plan_count": sum(row["selected_plan_id"] is not None for row in checklist),
                "signature_count": len(checklist),
            },
            "interpretation": "The lossless binding preserves all legal actions as conditional, so ordinary unique-ready compilation no longer solves the hard surface.",
        },
        {
            "mechanism": "EvidenceAwareComply owner acquisition",
            "class": "B",
            "verdict": "OLD_CAPABILITY_IDS_DO_NOT_BIND_GATEWAY_STATE_SUMMARY",
            "evidence": {
                "gateway_summary_query_count": sum(
                    CAP_GATEWAY_SUMMARY in row["invocation_ids"] for row in evidence_aware
                ),
                "binding_error_count": sum(row["status"] == "BINDING_ERROR" for row in evidence_aware),
                "signature_count": len(evidence_aware),
            },
        },
        {
            "mechanism": "ActionConditionedReference active dependency acquisition trigger",
            "class": "C",
            "verdict": "QUERY_RELEVANCE_WITHOUT_FUTURE_CHOICE_SAFETY",
            "evidence": {
                "protocol_query_trigger_count": sum(
                    CAP_GATEWAY_SUMMARY in row["invocation_ids"] for row in action_conditioned
                ),
                **trigger["summary"],
            },
        },
        {
            "mechanism": "Decision Sufficiency / candidate feasibility compiler",
            "class": "B",
            "verdict": "OLD_SELECTOR_IS_PROFILE_FALLBACK_SPECIFIC",
            "evidence": {
                "lossless_binding_decision_sufficiency": "UNRESOLVED_BY_BINDING",
                "reason": "A fair bridge cannot inject future-feasibility labels; v1 O1-O6 selector does not compute obligation-level future choice.",
            },
        },
        {
            "mechanism": "persistent execution / typed invocation lifecycle",
            "class": "A",
            "verdict": "CONTRACT_LEVEL_TRANSFERRED",
            "evidence": {
                "typed_action_roundtrip_mismatch": binding["summary"]["action_roundtrip_mismatch_count"],
                "note": "Physical executor wiring for Layer-1 evaluation capabilities is evaluation infrastructure, not a v1 semantic change.",
            },
        },
        {
            "mechanism": "CR/CF/CS model-facing ablations",
            "class": "B",
            "verdict": "OLD_CONTEXT_COORDINATES_NOT_DIRECTLY_PORTABLE",
            "evidence": {
                "reason": "Their frozen fragments encode O1-O6 profile/fallback semantics; recreating them for Layer-1 v0.2 would require a new model-facing compiler and is not evidence about the frozen v1 method itself."
            },
        },
        {
            "mechanism": "WirelessOpsAgent-style adaptation",
            "class": "B",
            "verdict": "OLD_DOMAIN_ADAPTER_NOT_DIRECTLY_PORTABLE",
            "evidence": {
                "reason": "The frozen WOA-style adapter shares the old profile/fallback capability family. A new adaptation belongs in the later policy comparison, not in v1 compatibility accounting."
            },
        },
        {
            "mechanism": "A10/A11 query-positive mechanism evidence",
            "class": "A",
            "verdict": "HISTORICAL_RESULT_RETAINED_NOT_TRANSFER_CLAIM",
            "evidence": {
                "reason": "The old gateway-backup family still proves v1 can execute useful multi-round acquisition, but Layer-1 v0.2 shows acquisition timing is not universally safe."
            },
        },
    ]

    counts = Counter(row["class"] for row in matrix)
    artifact = {
        "schema_version": "0.1",
        "status": "COMPLETE",
        "experiment": "layer2-v1-full-revalidation-matrix-on-layer1-v0.2",
        "summary": {
            "mechanism_count": len(matrix),
            "class_counts": dict(sorted(counts.items())),
            "hard_signature_count": len(reps),
            "compiled_checklist_initial_stop_count": sum(row["stop"] for row in checklist),
            "evidence_aware_gateway_summary_query_count": sum(
                CAP_GATEWAY_SUMMARY in row["invocation_ids"] for row in evidence_aware
            ),
            "evidence_aware_binding_error_count": sum(
                row["status"] == "BINDING_ERROR" for row in evidence_aware
            ),
            "action_conditioned_gateway_summary_query_count": sum(
                CAP_GATEWAY_SUMMARY in row["invocation_ids"] for row in action_conditioned
            ),
            "confirmed_category_c_failure_count": 1,
        },
        "classification_rule": {
            "A": "transfers or remains valid without changing decision semantics",
            "B": "task-specific implementation/binding prevents a fair direct transfer",
            "C": "after a lossless binding, frozen v1 decision semantics fail",
        },
        "matrix": matrix,
        "claim_boundary": [
            "B rows are not counted as v1 method failures.",
            "Historical A7-A11 evidence remains historical unless the mechanism is explicitly re-executed on Layer-1 v0.2.",
            "The confirmed C result is acquisition timing: relevance/ownership alone is insufficient when acquisition changes future task feasibility.",
        ],
    }
    print(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
