"""Canonical layer ownership and execution modes for Agent attribution.

The benchmark deliberately separates runtime-owned upstream artifacts from
planner/model-owned decisions.  A gold replacement can only be interpreted as
"model failure attribution" when the replaced object is actually produced by
the model.  Upstream Task/EvidenceNeed/Percept/Context replacements are method /
runtime ablations unless a future model is explicitly assigned ownership of
those objects.
"""
from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from .trajectory_eval import GoldReplacementLayer
from .upstream_gold import upstream_layer_ownership


class AttributionOwner(StrEnum):
    RUNTIME = "runtime"
    PLANNER_MODEL = "planner_model"
    EVALUATOR = "evaluator"


class ReplacementExecutionMode(StrEnum):
    MODEL_RERUN = "model_rerun"
    POSTHOC_DECISION = "posthoc_decision"
    FULL_R3_RERUN = "full_r3_rerun"


class AttributionLayerSpec(BaseModel):
    order: int = Field(ge=0)
    layer: GoldReplacementLayer
    owner: AttributionOwner
    execution_mode: ReplacementExecutionMode
    replaces: str
    artifact_refs: list[str] = Field(default_factory=list)
    interpretation: str


def attribution_layers() -> list[AttributionLayerSpec]:
    upstream = upstream_layer_ownership()
    return [
        AttributionLayerSpec(
            order=1,
            layer=GoldReplacementLayer.TASK,
            owner=AttributionOwner.RUNTIME,
            execution_mode=ReplacementExecutionMode.MODEL_RERUN,
            replaces="Runtime TaskContract interpretation/materialization",
            artifact_refs=upstream[GoldReplacementLayer.TASK.value],
            interpretation="runtime/method ablation under the current architecture; not an LLM error by default",
        ),
        AttributionLayerSpec(
            order=2,
            layer=GoldReplacementLayer.EVIDENCE_NEED,
            owner=AttributionOwner.RUNTIME,
            execution_mode=ReplacementExecutionMode.MODEL_RERUN,
            replaces="open EvidenceNeed set and stop/reopen state",
            artifact_refs=upstream[GoldReplacementLayer.EVIDENCE_NEED.value],
            interpretation="runtime evidence-acquisition ablation; changed model input requires model rerun",
        ),
        AttributionLayerSpec(
            order=3,
            layer=GoldReplacementLayer.PERCEPT,
            owner=AttributionOwner.RUNTIME,
            execution_mode=ReplacementExecutionMode.MODEL_RERUN,
            replaces="CapabilityResult-to-Percept / recent outcome interpretation",
            artifact_refs=upstream[GoldReplacementLayer.PERCEPT.value],
            interpretation="runtime/tool-result interpretation ablation; changed model input requires model rerun",
        ),
        AttributionLayerSpec(
            order=4,
            layer=GoldReplacementLayer.CONTEXT,
            owner=AttributionOwner.RUNTIME,
            execution_mode=ReplacementExecutionMode.MODEL_RERUN,
            replaces="ContextManifest/materialized resource, state, evidence and capability fragments",
            artifact_refs=upstream[GoldReplacementLayer.CONTEXT.value],
            interpretation="context-construction ablation; model must be rerun on the replacement assembly",
        ),
        AttributionLayerSpec(
            order=5,
            layer=GoldReplacementLayer.CAPABILITY_SELECTION,
            owner=AttributionOwner.PLANNER_MODEL,
            execution_mode=ReplacementExecutionMode.POSTHOC_DECISION,
            replaces="capability identity multiset",
            artifact_refs=["PlannerDecision.invocations[].capability_id"],
            interpretation="planner/model diagnostic; candidate arguments are preserved when possible",
        ),
        AttributionLayerSpec(
            order=6,
            layer=GoldReplacementLayer.CAPABILITY_ORDER,
            owner=AttributionOwner.PLANNER_MODEL,
            execution_mode=ReplacementExecutionMode.POSTHOC_DECISION,
            replaces="capability invocation order",
            artifact_refs=["PlannerDecision.invocations[] order"],
            interpretation="planner/model sequencing diagnostic independent from argument grounding",
        ),
        AttributionLayerSpec(
            order=7,
            layer=GoldReplacementLayer.CAPABILITY_ARGUMENTS,
            owner=AttributionOwner.PLANNER_MODEL,
            execution_mode=ReplacementExecutionMode.POSTHOC_DECISION,
            replaces="resource and canonical capability arguments",
            artifact_refs=["PlannerDecision.invocations[].resource", "PlannerDecision.invocations[].canonical_arguments"],
            interpretation="planner/model parameter-grounding diagnostic",
        ),
        AttributionLayerSpec(
            order=8,
            layer=GoldReplacementLayer.POLICY,
            owner=AttributionOwner.PLANNER_MODEL,
            execution_mode=ReplacementExecutionMode.FULL_R3_RERUN,
            replaces="entire planner capability/action trajectory",
            artifact_refs=["PlannerDecision"],
            interpretation="replace planner decisions and rerun physics to measure downstream communication consequence",
        ),
        AttributionLayerSpec(
            order=9,
            layer=GoldReplacementLayer.PHYSICAL_ORACLE,
            owner=AttributionOwner.EVALUATOR,
            execution_mode=ReplacementExecutionMode.FULL_R3_RERUN,
            replaces="online policy with evaluator-side physical reference/upper bound",
            artifact_refs=["evaluator_oracles", "physical_signature"],
            interpretation="upper-bound decomposition only; never an online Agent arm",
        ),
    ]


def attribution_protocol() -> dict:
    rows = attribution_layers()
    return {
        "revision": "agentic-attribution-v1",
        "rule": (
            "runtime-owned upstream replacements are method/runtime ablations under the current architecture; "
            "planner-owned selection/order/argument/policy replacements may be attributed to the planner/model"
        ),
        "cumulative_order": [x.layer.value for x in rows],
        "layers": [x.model_dump(mode="json") for x in rows],
    }
