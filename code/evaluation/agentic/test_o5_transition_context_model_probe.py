#!/usr/bin/env python3
"""Regression checks for the frozen O5 event/context model matrix."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DEVSET = ROOT / "results" / "agentic" / "o5-context-transition-devset-v1"
VALIDATE = ROOT / "results" / "agentic" / "o5-transition-context-model-probe-v1" / "validate.json"


def main() -> int:
    manifest = json.loads((DEVSET / "manifest.json").read_text(encoding="utf-8"))
    validate = json.loads(VALIDATE.read_text(encoding="utf-8"))
    assert len(manifest["events"]) == 3
    assert len(validate["rows"]) == 12
    assert set(validate["contexts"]) == {
        "task_conditioned",
        "full_dump",
        "generic_react",
        "action_conditioned_compact",
    }

    expected = {
        "backhaul_recovery_before_task_recovery": 300,
        "task_recovery_revision": 3600,
        "post_revision_reconciliation": 3600,
    }
    by_event = {event["event_id"]: event for event in manifest["events"]}
    for event_id, period in expected.items():
        event = by_event[event_id]
        ref = event.get("physical_consequence_ref") or {}
        assert ref.get("result") == "results/agentic/o5-task-revision-consequence-v1/aggregate.json"
        assert ref.get("arm")
        rows = [row for row in validate["rows"] if row["event_id"] == event_id]
        assert len(rows) == 4
        assert {int(row["current_required_period_s"]) for row in rows} == {period}
        assert all(int(row["gold_supported_config_invocations"]) > 0 for row in rows)

    print("PASS O5 transition context model probe: 3 events x 4 contexts, frozen Task authority + consequence refs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
