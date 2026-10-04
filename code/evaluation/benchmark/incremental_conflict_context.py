#!/usr/bin/env python3
"""Incremental decision-context maintenance over cached feasibility witnesses."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from delivery_constraint_graph import (
    AliasConflictWitness,
    WorldFeasibilityWitness,
    aggregate_world_witnesses,
    alias_conflict_witness,
)
from multi_evidence_scenario_tree import Bundle, World


@dataclass(frozen=True)
class ContextDelta:
    event_type: str
    event_key: str
    event_value: str
    removed_world_ids: tuple[str, ...]
    remaining_world_ids: tuple[str, ...]
    previous_conflict_obligations: tuple[str, ...]
    current_conflict_obligations: tuple[str, ...]
    structural_flow_solves_added: int


@dataclass(frozen=True)
class ContextSnapshot:
    bundle_id: str
    active_world_ids: tuple[str, ...]
    conflict: AliasConflictWitness
    accumulated_structural_flow_solves: int
    observations: tuple[tuple[str, str], ...]


class IncrementalConflictContext:
    def __init__(self, bundle: Bundle) -> None:
        self.bundle = bundle
        initial = alias_conflict_witness(bundle)
        self._witness_cache: dict[str, WorldFeasibilityWitness] = {
            row.world_id: row for row in initial.world_witnesses
        }
        self._worlds: dict[str, World] = {w.world_id: w for w in bundle.worlds}
        self._active: set[str] = set(self._worlds)
        self._flow_solves = initial.flow_solve_count
        self._observations: list[tuple[str, str]] = []
        self._conflict = initial

    def snapshot(self) -> ContextSnapshot:
        return ContextSnapshot(
            bundle_id=self.bundle.bundle_id,
            active_world_ids=tuple(sorted(self._active)),
            conflict=self._conflict,
            accumulated_structural_flow_solves=self._flow_solves,
            observations=tuple(self._observations),
        )

    def _reaggregate(self) -> None:
        witnesses = tuple(
            self._witness_cache[wid] for wid in sorted(self._active)
        )
        # No new max-flow analysis: only aggregate cached world witnesses.
        self._conflict = aggregate_world_witnesses(
            witnesses,
            satellite_budget=int(self.bundle.satellite_budget),
            inherited_flow_solve_count=self._flow_solves,
        )

    def _apply_filter(
        self,
        *,
        event_type: str,
        event_key: str,
        event_value: str,
        keep: set[str],
    ) -> ContextDelta:
        before = set(self._active)
        prev_conflict = self._conflict.differing_obligations
        self._active &= keep
        if not self._active:
            raise ValueError("observation is incompatible with all active alias worlds")
        self._observations.append((f"{event_type}:{event_key}", event_value))
        self._reaggregate()
        return ContextDelta(
            event_type=event_type,
            event_key=event_key,
            event_value=event_value,
            removed_world_ids=tuple(sorted(before - self._active)),
            remaining_world_ids=tuple(sorted(self._active)),
            previous_conflict_obligations=prev_conflict,
            current_conflict_obligations=self._conflict.differing_obligations,
            structural_flow_solves_added=0,
        )

    def apply_query_result(self, *, query_id: str, value: str) -> ContextDelta:
        keep = {
            wid for wid in self._active
            if dict(self._worlds[wid].evidence_values).get(query_id) == value
        }
        return self._apply_filter(
            event_type="query_result",
            event_key=query_id,
            event_value=value,
            keep=keep,
        )

    def apply_terrestrial_ack(self, *, time_s: int, success: bool) -> ContextDelta:
        keep = {
            wid for wid in self._active
            if ((time_s in self._worlds[wid].terrestrial_slots) == bool(success))
        }
        return self._apply_filter(
            event_type="terrestrial_ack",
            event_key=str(time_s),
            event_value="success" if success else "failure",
            keep=keep,
        )

    def materialized_context(self) -> dict[str, Any]:
        s = self.snapshot()
        return {
            "bundle_id": s.bundle_id,
            "alias_count": len(s.active_world_ids),
            "shared_satellite_budget": s.conflict.shared_satellite_budget,
            "resource_conflict_present": s.conflict.resource_conflict_present,
            "conflict_obligations": list(s.conflict.differing_obligations),
            "mandatory_satellite_intersection": list(
                s.conflict.mandatory_satellite_intersection
            ),
            "observation_count": len(s.observations),
            "accumulated_structural_flow_solves": s.accumulated_structural_flow_solves,
        }
