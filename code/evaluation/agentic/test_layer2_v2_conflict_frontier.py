#!/usr/bin/env python3
"""Small structural tests for the Layer-2 v2 max-flow/min-cut conflict witness."""
from __future__ import annotations

from itertools import product

from layer2_v2_conflict_frontier import (
    _combined_matching_feasible,
    _combined_matching_feasible_dfs_reference,
    _hall_deficit,
)


def test_hall_deficit_zero_for_perfect_matching() -> None:
    candidate_map = {
        "A": (("T", "w0", 0),),
        "B": (("T", "w1", 0),),
    }
    deficit, witnesses = _hall_deficit(("A", "B"), candidate_map)
    assert deficit == 0
    assert witnesses == ()


def test_hall_deficit_one_from_residual_min_cut() -> None:
    shared = ("T", "w0", 0)
    candidate_map = {
        "A": (shared,),
        "B": (shared,),
    }
    deficit, witnesses = _hall_deficit(("A", "B"), candidate_map)
    assert deficit == 1
    assert len(witnesses) == 1
    witness = witnesses[0]
    assert set(witness) == {"A", "B"}
    neighbours = {
        slot
        for oid in witness
        for slot in candidate_map[oid]
    }
    assert len(witness) - len(neighbours) == deficit


def test_hall_deficit_two_when_no_terrestrial_opportunity_exists() -> None:
    candidate_map = {"A": (), "B": ()}
    deficit, witnesses = _hall_deficit(("A", "B"), candidate_map)
    assert deficit == 2
    assert witnesses == (("A", "B"),)


def test_combined_matching_maxflow_matches_dfs_exhaustive_small_graphs() -> None:
    """Production max-flow must exactly preserve the historical DFS semantics."""

    obligations = ("A", "B", "C")
    slots = (
        ("T", "t0", 0),
        ("T", "t1", 0),
        ("S", "s0", 0),
        ("S", "s1", 0),
    )
    subsets = [
        tuple(slot for bit, slot in enumerate(slots) if mask & (1 << bit))
        for mask in range(1 << len(slots))
    ]
    for choices in product(subsets, repeat=len(obligations)):
        terr = {
            oid: tuple(slot for slot in row if slot[0] == "T")
            for oid, row in zip(obligations, choices)
        }
        sat = {
            oid: tuple(slot for slot in row if slot[0] == "S")
            for oid, row in zip(obligations, choices)
        }
        for budget in range(4):
            assert _combined_matching_feasible(
                obligations, terr, sat, budget
            ) == _combined_matching_feasible_dfs_reference(
                obligations, terr, sat, budget
            )
