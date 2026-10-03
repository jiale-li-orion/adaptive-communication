#!/usr/bin/env python3
"""Post-hoc audit/freeze for the protocol-v6 confirmatory main table.

This script does not run or modify any model experiment. It validates the frozen
60-row result set, source hashes, per-run replay audits and Method-first gate,
then emits the formal result-contract artifacts required by P7.
"""
from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RESULT_ROOT = ROOT / "results" / "agentic" / "main-table-v6-confirmatory" / "deepseek-flash"
AGGREGATE = RESULT_ROOT / "aggregate.json"
SOURCE_MANIFEST = RESULT_ROOT / "source-manifest.json"
PROTOCOL = "communication-planner-json-v6-no-action-sufficiency"
MODEL = "deepseek-flash"
METHOD = "action_conditioned_compact"
SEEDS = tuple(range(5))
TASKS = ("localized-o2", "o5", "o6")
ARMS = (METHOD, "task_conditioned", "full_dump", "generic_react")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _expected_episode(task: str) -> str | None:
    return {"localized-o2": None, "o5": "O5", "o6": "O6"}[task]


def _expected_variant(task: str) -> str:
    return "localized" if task == "localized-o2" else "global"


def _obs(row: dict) -> int:
    return int(row.get("local_observation_invocations") or 0) + int(
        row.get("remote_observation_invocations") or 0
    )


def _deterministic_reference_identity() -> dict:
    """Re-check candidate reference vs ordinary legacy comply without model calls."""
    if str(ROOT / "code") not in sys.path:
        sys.path.insert(0, str(ROOT / "code"))
    from agentic_communication.episodes import (  # type: ignore
        benchmark_episode_catalog,
        o2_localized_risk_escalation_task,
    )
    from agentic_communication.metrics import physical_signature  # type: ignore
    from agentic_communication.planner import ActionConditionedReferencePlannerConsumer  # type: ignore
    from agentic_communication.run import run_agentic_episode, run_reference_comply  # type: ignore

    episode_catalog = benchmark_episode_catalog()
    specs = {
        "localized-o2": (o2_localized_risk_escalation_task(), {}),
        "o5": (episode_catalog["O5"].task, episode_catalog["O5"].simulator_overrides),
        "o6": (episode_catalog["O6"].task, episode_catalog["O6"].simulator_overrides),
    }
    rows = []
    for task in TASKS:
        operational_task, simulator_kwargs = specs[task]
        for seed in SEEDS:
            legacy, _, _ = run_reference_comply(
                seed=seed,
                operational_task=operational_task,
                simulator_kwargs=simulator_kwargs,
            )
            candidate, _, _, _ = run_agentic_episode(
                seed=seed,
                operational_task=operational_task,
                context_mode=METHOD,
                planner_consumer=ActionConditionedReferencePlannerConsumer(),
                planner_replan_mode="decision_state",
                simulator_kwargs=simulator_kwargs,
            )
            rows.append(
                {
                    "task": task,
                    "seed": seed,
                    "physical_equal": physical_signature(candidate) == physical_signature(legacy),
                }
            )
    return {
        "rows": rows,
        "all_equal": all(row["physical_equal"] for row in rows),
        "equal_count": sum(row["physical_equal"] for row in rows),
        "expected_count": len(rows),
    }


def main() -> int:
    if not AGGREGATE.is_file() or not SOURCE_MANIFEST.is_file():
        raise FileNotFoundError("confirmatory aggregate/source manifest missing")

    aggregate = _load(AGGREGATE)
    source = _load(SOURCE_MANIFEST)
    assert aggregate.get("experiment") == "agentic-main-table-v6-confirmatory"
    assert aggregate.get("protocol_revision") == PROTOCOL
    assert aggregate.get("model") == MODEL
    assert int(aggregate.get("completed_rows") or 0) == 60, "refusing to freeze incomplete table"
    assert int(aggregate.get("expected_rows") or 0) == 60
    assert source.get("protocol_revision") == PROTOCOL
    assert source.get("model") == MODEL
    assert source.get("seeds") == list(SEEDS)
    assert source.get("tasks") == list(TASKS)
    assert source.get("arms") == list(ARMS)

    source_checks = []
    for rel, frozen_hash in (source.get("files") or {}).items():
        path = ROOT / rel
        exists = path.is_file()
        current_hash = _sha256(path) if exists else None
        source_checks.append(
            {
                "path": rel,
                "exists": exists,
                "frozen_sha256": frozen_hash,
                "current_sha256": current_hash,
                "match": exists and current_hash == frozen_hash,
            }
        )
    assert source_checks and all(row["match"] for row in source_checks), (
        "frozen source hash mismatch",
        [row for row in source_checks if not row["match"]],
    )

    rows = list(aggregate.get("rows") or [])
    by_key = {
        (str(row["task"]), int(row["seed"]), str(row["context_mode"])): row
        for row in rows
    }
    expected_keys = {
        (task, seed, arm)
        for arm in ARMS
        for task in TASKS
        for seed in SEEDS
    }
    assert set(by_key) == expected_keys, {
        "missing": sorted(expected_keys - set(by_key)),
        "unexpected": sorted(set(by_key) - expected_keys),
    }

    frozen_rows = []
    config_failures = []
    replay_failures = []
    for task, seed, arm in sorted(expected_keys):
        row = by_key[(task, seed, arm)]
        summary_path = Path(str(row["summary"]))
        assert summary_path.is_file(), summary_path
        summary = _load(summary_path)
        config = summary.get("config") or {}
        checks = {
            "model": config.get("model") == MODEL,
            "protocol": config.get("protocol_revision") == PROTOCOL,
            "seed": int(config.get("seed", -1)) == seed,
            "context_mode": config.get("context_mode") == arm,
            "planner_replan_mode": config.get("planner_replan_mode") == "decision_state",
            "episode": config.get("episode") == _expected_episode(task),
            "variant": config.get("variant") == _expected_variant(task),
            "temperature": float(config.get("temperature", 1.0)) == 0.0,
            "reasoning_effort": config.get("reasoning_effort") == "low",
            "max_tokens": int(config.get("max_tokens") or 0) == 8192,
            "json_object": config.get("json_object") is True,
            "credential_profile": config.get("credential_profile") == "deepseek_official",
        }
        if not all(checks.values()):
            config_failures.append({"task": task, "seed": seed, "arm": arm, "checks": checks})

        replay = summary.get("replay_audit") or {}
        if not replay.get("passed"):
            replay_failures.append({"task": task, "seed": seed, "arm": arm, "replay": replay})

        trace_path = Path(str(summary.get("trace") or ""))
        assert trace_path.is_file(), trace_path
        frozen_rows.append(
            {
                "task": task,
                "seed": seed,
                "context_mode": arm,
                "summary": str(summary_path.relative_to(ROOT)),
                "summary_sha256": _sha256(summary_path),
                "trace": str(trace_path.relative_to(ROOT)),
                "trace_sha256": _sha256(trace_path),
                "model_calls": row.get("model_calls"),
                "successful_model_attempts": row.get("successful_model_attempts"),
                "failed_model_attempts": row.get("failed_model_attempts"),
                "effect_scope_exact_turns": row.get("effect_scope_exact_turns"),
                "effect_scope_inexact_turns": row.get("effect_scope_inexact_turns"),
                "local_observation_invocations": row.get("local_observation_invocations"),
                "remote_observation_invocations": row.get("remote_observation_invocations"),
                "physical_equal_candidate_reference": row.get("physical_equal_candidate_reference"),
                "physical_equal_legacy": row.get("physical_equal_legacy"),
            }
        )

    assert not config_failures, config_failures
    assert not replay_failures, replay_failures

    method_rows = [row for row in rows if row.get("context_mode") == METHOD]
    baseline_rows = [row for row in rows if row.get("context_mode") != METHOD]
    method_gate = {
        "rows": len(method_rows),
        "all_effect_scope_exact": len(method_rows) == 15
        and all(int(row.get("effect_scope_inexact_turns") or 0) == 0 for row in method_rows),
        "all_zero_observation": len(method_rows) == 15 and all(_obs(row) == 0 for row in method_rows),
        "all_candidate_physical_exact": len(method_rows) == 15
        and all(row.get("physical_equal_candidate_reference") is True for row in method_rows),
        "all_legacy_physical_exact": len(method_rows) == 15
        and all(row.get("physical_equal_legacy") is True for row in method_rows),
        "failed_model_attempts": sum(int(row.get("failed_model_attempts") or 0) for row in method_rows),
    }
    assert all(
        (
            method_gate["rows"] == 15,
            method_gate["all_effect_scope_exact"],
            method_gate["all_zero_observation"],
            method_gate["all_candidate_physical_exact"],
            method_gate["all_legacy_physical_exact"],
            method_gate["failed_model_attempts"] == 0,
        )
    ), method_gate

    reference_identity = _deterministic_reference_identity()
    assert reference_identity["all_equal"], reference_identity

    experiment_contract = {
        "experiment": "agentic-main-table-v6-confirmatory",
        "protocol_revision": PROTOCOL,
        "model": MODEL,
        "seeds": list(SEEDS),
        "tasks": list(TASKS),
        "arms": list(ARMS),
        "planner_replan_mode": "decision_state",
        "model_parameters": {
            "temperature": 0,
            "reasoning_effort": "low",
            "max_tokens": 8192,
            "json_object": True,
            "credential_profile": "deepseek_official",
        },
        "method_first_gate": {
            "effect_scope_inexact_turns": 0,
            "observations": 0,
            "physical_equal_candidate_reference": True,
            "physical_equal_legacy": True,
        },
        "claim_boundary": (
            "Confirmatory evidence is limited to DeepSeek Flash, three development tasks and five "
            "simulator seeds. Candidate/legacy physical equality is fidelity to the declared comply "
            "reference, not proof of global communication-policy optimality."
        ),
    }
    contract_path = RESULT_ROOT / "experiment_contract.json"
    contract_path.write_text(json.dumps(experiment_contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rows_path = RESULT_ROOT / "per_episode_results.jsonl"
    rows_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in frozen_rows),
        encoding="utf-8",
    )

    run_manifest = {
        "experiment": "agentic-main-table-v6-confirmatory",
        "frozen_at": source.get("frozen_at"),
        "audited_at": _now(),
        "completed_rows": len(rows),
        "expected_rows": 60,
        "aggregate": str(AGGREGATE.relative_to(ROOT)),
        "aggregate_sha256": _sha256(AGGREGATE),
        "source_manifest": str(SOURCE_MANIFEST.relative_to(ROOT)),
        "source_manifest_sha256": _sha256(SOURCE_MANIFEST),
        "experiment_contract": str(contract_path.relative_to(ROOT)),
        "experiment_contract_sha256": _sha256(contract_path),
        "per_episode_results": str(rows_path.relative_to(ROOT)),
        "per_episode_results_sha256": _sha256(rows_path),
    }
    run_manifest_path = RESULT_ROOT / "run_manifest.json"
    run_manifest_path.write_text(json.dumps(run_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    audit = {
        "status": "PASS",
        "audited_at": _now(),
        "experiment": "agentic-main-table-v6-confirmatory",
        "protocol_revision": PROTOCOL,
        "complete_expected_coordinate_set": True,
        "no_posthoc_exclusion": True,
        "source_manifest_current_hashes_match_frozen": True,
        "all_per_run_configs_match_contract": True,
        "all_r0_r1_r2_replay_audits_pass": True,
        "method_gate": method_gate,
        "candidate_reference_equals_legacy_comply": reference_identity,
        "baseline_rows": len(baseline_rows),
        "baseline_rows_with_failed_model_attempt": sum(
            int(row.get("failed_model_attempts") or 0) > 0 for row in baseline_rows
        ),
        "artifact_sha256": {
            "aggregate.json": _sha256(AGGREGATE),
            "source-manifest.json": _sha256(SOURCE_MANIFEST),
            "experiment_contract.json": _sha256(contract_path),
            "run_manifest.json": _sha256(run_manifest_path),
            "per_episode_results.jsonl": _sha256(rows_path),
        },
    }
    audit_path = RESULT_ROOT / "audit.json"
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "status": audit["status"],
                "rows": len(rows),
                "method_gate": method_gate,
                "reference_identity": {
                    "equal_count": reference_identity["equal_count"],
                    "expected_count": reference_identity["expected_count"],
                },
                "audit": str(audit_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

