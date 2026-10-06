#!/usr/bin/env python3
"""Audit the v0.7 generation-axis correction against frozen v0.6 axes.

Only process-support semantics and the explicit >=3-stage declaration may
change. All source/model/resource/evidence/timing/fallback axes must remain
identical to v0.1 so v0.7 cannot hide a hardness-targeting parameter change.
"""
from __future__ import annotations

from copy import deepcopy
from itertools import product
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OLD = ROOT / "research/benchmark/GENERATION-AXES.v0.1.json"
NEW = ROOT / "research/benchmark/GENERATION-AXES.v0.2.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _runs(bits: tuple[bool, ...], value: bool) -> int:
    runs = 0
    inside = False
    for bit in bits:
        if bit == value and not inside:
            runs += 1
            inside = True
        elif bit != value:
            inside = False
    return runs


def _has_recovery(bits: tuple[bool, ...]) -> bool:
    return any((not bits[i]) and bits[i + 1] for i in range(len(bits) - 1))


def _support(stage_count: int, family: str) -> tuple[tuple[bool, ...], ...]:
    rows: list[tuple[bool, ...]] = []
    for bits in product((False, True), repeat=stage_count):
        down_runs = _runs(bits, False)
        if family == "STEADY_AVAILABLE_CONTROL":
            keep = all(bits)
        elif family == "SINGLE_RECOVERY":
            keep = down_runs == 1 and any(not b for b in bits) and _has_recovery(bits)
        elif family == "REINTERRUPTIBLE":
            keep = down_runs in (1, 2) and _has_recovery(bits)
        elif family == "FULL_BINARY_SUPPORT":
            keep = True
        else:
            raise ValueError(family)
        if keep:
            rows.append(tuple(bits))
    return tuple(sorted(rows))


def _normalize_for_invariance(doc: dict) -> dict:
    x = deepcopy(doc)
    # Version/lineage metadata is expected to differ.
    x["schema_version"] = "<VERSION>"
    x["status"] = "<STATUS>"
    auth = x["authority"]
    auth.pop("parent_generation_axes", None)
    auth.pop("lineage_reason", None)
    x.pop("v07_change_scope", None)
    # The sole scientific-axis change is process support. Remove it before the
    # equality check; every other controlled-stress field must remain exact.
    x["controlled_stress"]["terrestrial_service_process"] = "<PROCESS_SUPPORT>"
    comp = x["controlled_stress"]["obligation_composition"]
    comp.pop("minimum_dynamic_release_stages", None)
    comp.pop("minimum_dynamic_release_stages_rule", None)
    return x


def main() -> int:
    old = _load(OLD)
    new = _load(NEW)
    assert new["schema_version"] == "0.2"
    assert new["status"] == "FROZEN_FOR_LAYER1_V07_REBUILD"
    assert new["authority"]["parent_generation_axes"] == "research/benchmark/GENERATION-AXES.v0.1.json"
    assert _normalize_for_invariance(old) == _normalize_for_invariance(new), (
        "v0.2 changed an axis outside the declared process-support/stage-contract scope"
    )

    cs = new["controlled_stress"]
    assert cs["obligation_composition"]["minimum_dynamic_release_stages"] == 3
    families = {row["id"]: row for row in cs["terrestrial_service_process"]["support_families"]}
    assert set(families) == {
        "STEADY_AVAILABLE_CONTROL",
        "SINGLE_RECOVERY",
        "REINTERRUPTIBLE",
        "FULL_BINARY_SUPPORT",
    }
    assert families["STEADY_AVAILABLE_CONTROL"]["role"] == "CONTROL"
    assert families["SINGLE_RECOVERY"]["role"] == "CANDIDATE"
    assert families["REINTERRUPTIBLE"]["role"] == "CANDIDATE"
    assert families["FULL_BINARY_SUPPORT"]["role"] == "DIAGNOSTIC_CONTROL"

    for stages in range(3, 7):
        steady = _support(stages, "STEADY_AVAILABLE_CONTROL")
        single = _support(stages, "SINGLE_RECOVERY")
        reint = _support(stages, "REINTERRUPTIBLE")
        full = _support(stages, "FULL_BINARY_SUPPORT")
        all_down = tuple(False for _ in range(stages))
        all_up = tuple(True for _ in range(stages))

        assert steady == (all_up,)
        assert all_down not in single and all_up not in single
        assert all_down not in reint and all_up not in reint
        assert all_down in full and all_up in full
        assert all(_runs(bits, False) == 1 and _has_recovery(bits) for bits in single)
        assert all(_runs(bits, False) in (1, 2) and _has_recovery(bits) for bits in reint)
        if stages >= 3:
            assert any(_runs(bits, False) == 2 for bits in reint), (
                f"stage_count={stages} reinterruptible support lacks a second-down trajectory"
            )

    change = new["v07_change_scope"]
    assert change["fallback_budget_derivation_changed"] is False
    assert change["satellite_geometry_changed"] is False
    assert change["feedback_or_query_timing_changed"] is False
    assert change["source_task_contract_changed"] is False

    print(
        "PASS generation axes v0.2: only process-support/stage semantics changed; "
        "candidate recovery families exclude ALL_DOWN and preserve v0.6 resource/evidence axes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
