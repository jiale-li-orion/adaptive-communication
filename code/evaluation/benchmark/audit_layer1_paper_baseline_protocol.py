#!/usr/bin/env python3
"""Audit the frozen Layer-1 paper baseline protocol before unlocking test."""
from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from agentic_communication.baselines import baseline_registry, validate_implementation_refs  # noqa: E402


PROTOCOL = ROOT / "research/benchmark/PAPER-BASELINE-PROTOCOL.json"
SPLIT = ROOT / "results/benchmark/layer1-paper-split.json"


def main() -> int:
    p = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    registry = baseline_registry()

    referenced = set(p["full_test"]["universal"])
    for rows in p["full_test"]["by_template"].values():
        referenced.update(rows)
    referenced.update(p["full_test"]["evaluator_only_oracles"]["all"])
    referenced.update(p["full_test"]["evaluator_only_oracles"]["O4_O6"])

    # Two strong ordinary controls are implemented but were not historically
    # registered as standalone IDs; protocol pins their implementation directly.
    direct_ids = {
        "comm.ea_aoi",
        "comm.mission_sustain",
        "oracle.delivery.primary_only_decomposition",
    }
    registry_ids = referenced - direct_ids
    missing_registry = sorted(registry_ids - set(registry))
    missing_impl = validate_implementation_refs(ROOT)

    llm = p["llm_subset"]
    test_rows = split["coordinates"]["test"]
    llm_ids = {
        row["coordinate_id"]
        for row in test_rows
        if row["task_template"] in llm["task_templates"]
        and row["window_id"] in llm["windows"]
        and int(row["seed"]) in llm["seeds"]
    }
    expected_llm_ids = 5 * 3 * 2

    checks = {
        "protocol_frozen_before_test": p["status"] == "FROZEN_BEFORE_TEST_EXECUTION",
        "split_test_still_locked": bool(split["access_policy"]["test_outcomes_locked"]),
        "full_test_count_matches_split": p["full_test"]["coordinate_count"] == len(test_rows) == 150,
        "all_registered_baseline_ids_resolve": not missing_registry,
        "all_registry_implementation_refs_exist": not missing_impl,
        "direct_ea_aoi_implementation_exists": (ROOT / "code/substrate/instance/center.py").is_file(),
        "direct_mission_sustain_implementation_exists": (ROOT / "code/substrate/joint/mission_policy.py").is_file(),
        "oracle_ids_are_not_online": all(
            not registry[x].online_legal
            for x in ("oracle.dynamic_energy",)
        ),
        "delivery_oracle_is_primary_only_diagnostic": (
            p["oracle_semantics"]["oracle.delivery.primary_only_decomposition"]["coordinate_override"]
            == {"enable_backup": False}
            and p["oracle_semantics"]["oracle.delivery.primary_only_decomposition"]["ranking_role"]
            == "diagnostic_only"
        ),
        "llm_subset_is_exactly_30_frozen_test_coordinates": len(llm_ids) == expected_llm_ids == 30,
        "llm_subset_does_not_use_historical_w1": all(":w1:" not in x for x in llm_ids),
        "test_tuning_forbidden": bool(p["test_tuning_forbidden"]),
    }
    assert all(checks.values()), {
        "checks": checks,
        "missing_registry": missing_registry,
        "missing_impl": missing_impl,
    }
    print(json.dumps({
        "stage": "LAYER1_PAPER_BASELINE_PROTOCOL_AUDIT",
        "checks": checks,
        "referenced_baseline_ids": sorted(referenced),
        "llm_coordinate_ids": sorted(llm_ids),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
