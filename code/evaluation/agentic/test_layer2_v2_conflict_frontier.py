#!/usr/bin/env python3
"""Small structural tests for the Layer-2 v2 max-flow/min-cut conflict witness."""
from __future__ import annotations

from layer2_v2_conflict_frontier import _hall_deficit


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
