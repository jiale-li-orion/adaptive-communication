#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from scenario_generator_v0_1 import BENCH, generate


def main() -> int:
    config = json.loads((BENCH / "GENERATOR-CONFIG.v0.1.json").read_text())
    rows = list(generate(config))
    assert rows
    ids = [r["candidate_id"] for r in rows]
    assert len(ids) == len(set(ids))

    hard = [r for r in rows if r["disposition"] == "HARD_CANDIDATE"]
    assert hard, "generator must expose at least one oracle-validated hard candidate"

    for row in hard[:200]:
        oracle = row["oracle"]
        assert oracle["base"]["solvable"]
        assert oracle["multiple_legal_first_actions"]
        assert oracle["resource_binding"]
        assert oracle["forced_send_wait_outcome_separation"]
        assert oracle["forced_wait"]["solvable"]
        assert not oracle["forced_send"]["solvable"]
        assert not oracle["greedy_baseline_success"]
        assert row["provenance"]["satellite_tx_budget_count"] == "CONTROLLED_STRESS"

    # Same structural world at different phases must share group id.
    by_group: dict[str, list[dict]] = {}
    for row in rows:
        by_group.setdefault(row["structural_group_id"], []).append(row)
    assert any(len(v) > 1 for v in by_group.values())

    # Determinism: first 100 ids are stable under a second generation pass.
    ids2 = [r["candidate_id"] for _, r in zip(range(100), generate(config))]
    assert ids[:100] == ids2

    dispositions = {}
    for row in rows:
        dispositions[row["disposition"]] = dispositions.get(row["disposition"], 0) + 1
    print(
        "PASS scenario generator v0.1:",
        len(rows),
        "candidates;",
        len(hard),
        "hard;",
        json.dumps(dispositions, sort_keys=True),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
