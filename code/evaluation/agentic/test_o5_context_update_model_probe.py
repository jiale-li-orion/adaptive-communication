#!/usr/bin/env python3
"""Regression checks for the O5 Task-revision Context ablation evaluator."""
from __future__ import annotations

import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
ROOT = CODE.parent
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from run_o5_context_update_model_probe import (  # noqa: E402
    authority_precedence_baseline,
    current_period,
    evaluate_decision,
    fresh_gold,
    task_targets,
)


TRANSITION = (
    ROOT
    / "results"
    / "agentic"
    / "o5-context-update-ablation-v1"
    / "backhaul_recovery_before_task_recovery__to__task_recovery_revision"
)


def load(name: str) -> dict:
    return json.loads((TRANSITION / f"{name}.json").read_text(encoding="utf-8"))


def main() -> int:
    fresh = load("fresh_rebuild")
    naive = load("naive_incremental_cache")
    gold = fresh_gold(fresh)

    assert current_period(naive) == 3600
    assert naive["candidate_action_context"]["required_period_s"] == 300
    assert task_targets(fresh) == sorted(fresh["candidate_action_context"]["action_scope"])
    assert "monitoring-network" not in task_targets(fresh)

    baseline = authority_precedence_baseline(naive)
    targets = {
        int((row.get("canonical_arguments") or {})["target_s"])
        for row in baseline["invocations"]
    }
    assert targets == {3600}, targets
    result = evaluate_decision(baseline, naive, gold)
    assert result["revision_authority_correct"] is True
    assert result["stale_config_targets"] == []
    assert result["config_recall_vs_fresh_gold"] == 1.0
    assert result["pred_config_invocations"] == 2 * len(task_targets(naive))

    print(
        "PASS O5 context update model probe: stale candidate cannot override current Task authority"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
