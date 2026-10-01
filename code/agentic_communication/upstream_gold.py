"""Frozen-artifact gold replacement for upstream Agent runtime layers.

Planner-level replacement lives in :mod:`gold_replacement`.  This module owns
the model-input side: Runtime TaskContract, EvidenceNeed, recent Percept/tool
outcomes, and Context materialization.  Layers are intentionally disjoint so a
later replacement cannot silently repair an earlier failure class.
"""
from __future__ import annotations

from dataclasses import dataclass

from .runtime_contracts import MaterializedFragment, PromptAssembly
from .trajectory_eval import GoldReplacementLayer


_LAYER_KINDS: dict[GoldReplacementLayer, tuple[str, ...]] = {
    GoldReplacementLayer.TASK: ("runtime_task_contract",),
    GoldReplacementLayer.EVIDENCE_NEED: ("evidence_needs",),
    GoldReplacementLayer.PERCEPT: ("recent_capability_outcomes",),
    GoldReplacementLayer.CONTEXT: (
        "resource_inventory",
        "investigation_state",
        "evidence_slice",
        "capability_catalog",
    ),
}


@dataclass(frozen=True)
class UpstreamGoldReplacementOutcome:
    assembly: PromptAssembly
    replaced_layers: tuple[GoldReplacementLayer, ...]
    replaced_fragment_kinds: tuple[str, ...]


def _by_kind(assembly: PromptAssembly) -> dict[str, MaterializedFragment]:
    return {fragment.kind: fragment for fragment in assembly.fragments}


def apply_upstream_gold_replacement(
    candidate: PromptAssembly,
    gold: PromptAssembly,
    layers: list[GoldReplacementLayer] | tuple[GoldReplacementLayer, ...],
) -> UpstreamGoldReplacementOutcome:
    """Replace selected upstream artifacts while preserving other candidate layers."""
    selected = tuple(layers)
    unsupported = set(selected) - set(_LAYER_KINDS)
    if unsupported:
        raise ValueError(
            "upstream replacement does not own planner/physical layers: "
            + ",".join(sorted(x.value for x in unsupported))
        )

    candidate_by_kind = _by_kind(candidate)
    gold_by_kind = _by_kind(gold)
    replace_kinds: set[str] = set()
    for layer in selected:
        replace_kinds.update(_LAYER_KINDS[layer])

    # Use gold fragment order for known shared kinds so full upstream replacement
    # can become byte/hash identical to the gold assembly. Candidate-only extra
    # fragments are appended and remain candidate-owned.
    ordered_kinds: list[str] = []
    for fragment in gold.fragments:
        if fragment.kind in candidate_by_kind or fragment.kind in replace_kinds:
            if fragment.kind not in ordered_kinds:
                ordered_kinds.append(fragment.kind)
    for fragment in candidate.fragments:
        if fragment.kind not in ordered_kinds:
            ordered_kinds.append(fragment.kind)

    fragments: list[MaterializedFragment] = []
    for kind in ordered_kinds:
        if kind in replace_kinds:
            if kind not in gold_by_kind:
                raise ValueError(f"gold assembly missing fragment kind {kind!r}")
            fragments.append(
                MaterializedFragment.model_validate(
                    gold_by_kind[kind].model_dump(mode="json")
                )
            )
        elif kind in candidate_by_kind:
            fragments.append(
                MaterializedFragment.model_validate(
                    candidate_by_kind[kind].model_dump(mode="json")
                )
            )

    task_contract_id = (
        gold.task_contract_id
        if GoldReplacementLayer.TASK in selected
        else candidate.task_contract_id
    )
    context_revision = (
        gold.context_manifest_revision
        if GoldReplacementLayer.CONTEXT in selected
        else candidate.context_manifest_revision
    )
    percept_refs = (
        list(gold.percept_refs)
        if GoldReplacementLayer.PERCEPT in selected
        else list(candidate.percept_refs)
    )
    rebuilt = PromptAssembly.build(
        task_contract_id=task_contract_id,
        task_run_id=candidate.task_run_id,
        context_manifest_revision=context_revision,
        fragments=fragments,
        percept_refs=percept_refs,
    )
    return UpstreamGoldReplacementOutcome(
        assembly=rebuilt,
        replaced_layers=selected,
        replaced_fragment_kinds=tuple(sorted(replace_kinds)),
    )


def upstream_layer_ownership() -> dict[str, list[str]]:
    return {layer.value: list(kinds) for layer, kinds in _LAYER_KINDS.items()}
