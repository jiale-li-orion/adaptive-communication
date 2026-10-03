#!/usr/bin/env python3
"""Freeze a machine-checkable candidate claim from the v6 confirmatory table.

This script is intentionally read-only with respect to experiment results.  It
only emits a candidate claim artifact after the full 60-row table is complete
and the pre-registered Method gate has passed 15/15 rows.
"""
from __future__ import annotations

import json
from pathlib import Path
import statistics
import hashlib


ROOT = Path(__file__).resolve().parents[3]
SRC = (
    ROOT
    / "results"
    / "agentic"
    / "main-table-v6-confirmatory"
    / "deepseek-flash"
    / "aggregate.json"
)
OUT = SRC.with_name("claim-candidate.json")
AUDIT = SRC.with_name("audit.json")
METHOD = "action_conditioned_compact"
TASKS = ("localized-o2", "o5", "o6")
BASELINES = ("task_conditioned", "full_dump", "generic_react")


def _obs(row: dict) -> int:
    return int(row.get("local_observation_invocations") or 0) + int(
        row.get("remote_observation_invocations") or 0
    )


def _rate(row: dict) -> float:
    exact = int(row.get("effect_scope_exact_turns") or 0)
    bad = int(row.get("effect_scope_inexact_turns") or 0)
    return exact / (exact + bad) if exact + bad else 1.0


def _mean(xs):
    vals = [float(x) for x in xs]
    return statistics.fmean(vals) if vals else None


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    assert AUDIT.is_file(), "formal confirmatory audit is missing"
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    assert audit.get("status") == "PASS", audit.get("status")
    assert audit.get("complete_expected_coordinate_set") is True
    assert audit.get("no_posthoc_exclusion") is True
    assert audit.get("source_manifest_current_hashes_match_frozen") is True
    assert audit.get("all_per_run_configs_match_contract") is True
    assert audit.get("all_r0_r1_r2_replay_audits_pass") is True
    assert (audit.get("candidate_reference_equals_legacy_comply") or {}).get("all_equal") is True

    data = json.loads(SRC.read_text(encoding="utf-8"))
    rows = list(data.get("rows") or [])
    assert data.get("protocol_revision") == "communication-planner-json-v6-no-action-sufficiency"
    assert int(data.get("completed_rows") or 0) == 60, "confirmatory table is incomplete"
    assert int(data.get("expected_rows") or 0) == 60

    method = [r for r in rows if r.get("context_mode") == METHOD]
    baseline = [r for r in rows if r.get("context_mode") in BASELINES]
    assert len(method) == 15, len(method)
    assert len(baseline) == 45, len(baseline)
    assert all(int(r.get("effect_scope_inexact_turns") or 0) == 0 for r in method)
    assert all(_obs(r) == 0 for r in method)
    assert all(r.get("physical_equal_candidate_reference") is True for r in method)
    assert all(r.get("physical_equal_legacy") is True for r in method)

    by_task: dict[str, dict] = {}
    for task in TASKS:
        m = [r for r in method if r["task"] == task]
        b = [r for r in baseline if r["task"] == task]
        assert len(m) == 5, (task, len(m))
        assert len(b) == 15, (task, len(b))
        by_task[task] = {
            "method_effect_exact_turns": sum(int(r.get("effect_scope_exact_turns") or 0) for r in m),
            "method_effect_inexact_turns": 0,
            "method_zero_observation_rows": sum(_obs(r) == 0 for r in m),
            "method_candidate_physical_exact_rows": sum(
                r.get("physical_equal_candidate_reference") is True for r in m
            ),
            "method_legacy_physical_exact_rows": sum(r.get("physical_equal_legacy") is True for r in m),
            "baseline_rows_with_semantic_error": sum(
                int(r.get("effect_scope_inexact_turns") or 0) > 0 for r in b
            ),
            "baseline_rows_with_candidate_physical_divergence": sum(
                r.get("physical_equal_candidate_reference") is False for r in b
            ),
            "baseline_rows_with_legacy_physical_divergence": sum(
                r.get("physical_equal_legacy") is False for r in b
            ),
            "baseline_rows_with_observation": sum(_obs(r) > 0 for r in b),
            "method_effect_exact_rate_mean": _mean(_rate(r) for r in m),
            "baseline_effect_exact_rate_mean": _mean(_rate(r) for r in b),
            "method_tokens_mean": _mean((r.get("usage") or {}).get("total_tokens", 0) for r in m),
            "baseline_tokens_mean": _mean((r.get("usage") or {}).get("total_tokens", 0) for r in b),
        }

    artifact = {
        "status": "candidate_only_not_yet_claim_authority",
        "source": str(SRC.relative_to(ROOT)),
        "formal_audit": str(AUDIT.relative_to(ROOT)),
        "formal_audit_sha256": _sha256(AUDIT),
        "protocol_revision": data["protocol_revision"],
        "model": data.get("model"),
        "seeds": data.get("seeds"),
        "tasks": list(TASKS),
        "method": METHOD,
        "baseline_arms": list(BASELINES),
        "pre_registered_method_gate": {
            "rows": 15,
            "all_effect_scope_exact": True,
            "all_zero_observation": True,
            "all_candidate_physical_exact": True,
            "all_legacy_physical_exact": True,
        },
        "by_task": by_task,
        "claim_ceiling": (
            "DeepSeek Flash, three development tasks, five simulator seeds: the frozen action-conditioned "
            "control surface reproduced the deterministic candidate/legacy comply effect scope and physical "
            "trajectory without extra observation calls. Baseline comparisons are descriptive for these "
            "tasks/seeds only; this artifact does not establish cross-model or workload-wide generalization."
        ),
    }
    OUT.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

