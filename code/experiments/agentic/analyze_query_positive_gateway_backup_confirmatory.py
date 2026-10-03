#!/usr/bin/env python3
"""Aggregate and audit the five-seed query-positive DeepSeek result."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "results" / "agentic" / "query-positive-gateway-backup-v1"
MODEL_ROOT = BASE / "deepseek-flash"
OUT = BASE / "confirmatory-aggregate.json"
AUDIT = BASE / "confirmatory-audit.json"
ANALYSIS = BASE / "confirmatory-analysis.md"
BASE_MANIFEST = BASE / "model-probe-source-manifest.json"
SAFE_MANIFEST = BASE / "confirmatory-safe-source-manifest.json"
DETERMINISTIC_GATE = BASE / "deterministic-gate.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _seed0() -> dict:
    data = json.loads((MODEL_ROOT / "seed-000" / "recovered-summary.json").read_text(encoding="utf-8"))
    behavior = data["model_behavior"]
    return {
        "seed": 0,
        "status": data["status"],
        "result_kind": "recovered_completed_episode",
        "planner_turns": behavior["planner_turns"],
        "successful_attempts": behavior["successful_attempts"],
        "failed_attempts": behavior["failed_attempts"],
        "effect_exact_turns": behavior["effect_scope_exact_turns"],
        "effect_inexact_turns": behavior["effect_scope_inexact_turns"],
        "query_requests": len(behavior["query_requests"]),
        "queried_capabilities": behavior["queried_capabilities"],
        "backup_effect_count": len(behavior["backup_effects"]),
        "direct_physical_signature_persisted": False,
        "direct_physical_equal_reference": None,
        "execution_equivalence_basis_pass": data["deterministic_execution_equivalence"]["basis_pass"],
        "replay_pass": data["streaming_audit"]["status"] == "PASS",
        "r2_exact": data["streaming_audit"]["r2"]["exact_assembly_matches"],
        "r2_total": data["streaming_audit"]["r2"]["contexts"],
        "communication_metrics": data["communication_metrics"],
        "no_acquisition_control_metrics": data["no_acquisition_control_metrics"],
        "delta_vs_no_acquisition": data["delta_vs_no_acquisition"],
        "usage": behavior["usage"],
        "source": str((MODEL_ROOT / "seed-000" / "recovered-summary.json").relative_to(ROOT)),
    }


def _direct(seed: int) -> dict:
    path = MODEL_ROOT / f"seed-{seed:03d}" / "summary.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    behavior = data["planner_behavior_audit"]
    query = data["query_behavior_audit"]
    return {
        "seed": seed,
        "status": data["status"],
        "result_kind": "direct_safe_runner",
        "planner_turns": behavior["planner_decision_turns"],
        "successful_attempts": behavior["successful_model_attempts"],
        "failed_attempts": behavior["failed_model_attempts"],
        "effect_exact_turns": behavior["effect_scope_exact_turns"],
        "effect_inexact_turns": behavior["effect_scope_inexact_turns"],
        "query_requests": sum(
            len(turn.get("actual_query_capabilities") or []) for turn in query["turns"]
        ),
        "queried_capabilities": query["queried_capabilities"],
        "backup_effect_count": query["backup_effect_count"],
        "direct_physical_signature_persisted": True,
        "direct_physical_equal_reference": data["physical_equal_deterministic_query_positive_reference"],
        "execution_equivalence_basis_pass": data["physical_equal_deterministic_query_positive_reference"],
        "replay_pass": data["replay_audit"]["passed"],
        "r2_exact": data["replay_audit"]["R2"]["exact_assembly_matches"],
        "r2_total": data["replay_audit"]["R2"]["contexts"],
        "communication_metrics": data["communication_metrics"],
        "no_acquisition_control_metrics": data["no_acquisition_control_metrics"],
        "delta_vs_no_acquisition": data["delta_vs_no_acquisition"],
        "usage": data["usage"],
        "source": str(path.relative_to(ROOT)),
    }


def main() -> int:
    rows = [_seed0(), *[_direct(seed) for seed in (1, 2, 3, 4)]]
    rows.sort(key=lambda row: row["seed"])

    aggregate = {
        "experiment": "query-positive-gateway-backup-v1-deepseek-confirmatory",
        "model": "deepseek-flash",
        "seeds": [0, 1, 2, 3, 4],
        "completed_rows": len(rows),
        "expected_rows": 5,
        "planner_turns": sum(row["planner_turns"] for row in rows),
        "successful_attempts": sum(row["successful_attempts"] for row in rows),
        "failed_attempts": sum(row["failed_attempts"] for row in rows),
        "effect_exact_turns": sum(row["effect_exact_turns"] for row in rows),
        "effect_inexact_turns": sum(row["effect_inexact_turns"] for row in rows),
        "query_requests": sum(row["query_requests"] for row in rows),
        "backup_effects": sum(row["backup_effect_count"] for row in rows),
        "execution_equivalent_episodes": sum(
            row["execution_equivalence_basis_pass"] is True for row in rows
        ),
        "direct_physical_exact_episodes": sum(
            row["direct_physical_equal_reference"] is True for row in rows
        ),
        "recovered_execution_equivalent_episodes": sum(
            row["result_kind"] == "recovered_completed_episode"
            and row["execution_equivalence_basis_pass"] is True
            for row in rows
        ),
        "all_replay_pass": all(row["replay_pass"] for row in rows),
        "all_tdr_improved": all(
            row["delta_vs_no_acquisition"]["timely_delivery_rate"] > 0 for row in rows
        ),
        "all_aoi_improved": all(
            row["delta_vs_no_acquisition"]["aoi_mean_s"] < 0 for row in rows
        ),
        "mean_tdr_delta": statistics.fmean(
            row["delta_vs_no_acquisition"]["timely_delivery_rate"] for row in rows
        ),
        "mean_aoi_delta_s": statistics.fmean(
            row["delta_vs_no_acquisition"]["aoi_mean_s"] for row in rows
        ),
        "total_tokens": sum(int(row["usage"].get("total_tokens") or 0) for row in rows),
        "rows": rows,
        "seed0_recovery_boundary": (
            "Seed0 task 018 completed its episode but was SIGKILLed during high-memory post-processing. "
            "Its direct physical_signature boolean was not persisted. Streaming recovery establishes "
            "source-exact R2, exact effect/query/backup traces and exact shared task-completion metrics "
            "against the deterministic reference. Seeds1..4 persist direct physical_signature equality."
        ),
    }
    OUT.write_text(json.dumps(aggregate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    failures = []
    if aggregate["completed_rows"] != aggregate["expected_rows"]:
        failures.append("incomplete_coordinate_set")
    if [row["seed"] for row in rows] != [0, 1, 2, 3, 4]:
        failures.append("coordinate_set_mismatch")
    if rows[0]["status"] != "RECOVERED_PASS":
        failures.append("seed0_not_recovered_pass")
    if any(row["status"] != "PASS" for row in rows[1:]):
        failures.append("direct_seed_nonpass")
    if aggregate["failed_attempts"] != 0:
        failures.append("failed_model_attempts")
    if aggregate["effect_inexact_turns"] != 0:
        failures.append("effect_scope_inexact")
    if aggregate["backup_effects"] != 5:
        failures.append("backup_effect_count")
    if aggregate["execution_equivalent_episodes"] != 5:
        failures.append("execution_equivalence")
    if aggregate["direct_physical_exact_episodes"] != 4:
        failures.append("direct_physical_exact_count")
    if not aggregate["all_replay_pass"]:
        failures.append("replay_failure")
    if not aggregate["all_tdr_improved"]:
        failures.append("tdr_not_improved_all_seeds")
    if not aggregate["all_aoi_improved"]:
        failures.append("aoi_not_improved_all_seeds")
    if any(row["queried_capabilities"] != ["communication.gateway.receipt_summary"] for row in rows):
        failures.append("unexpected_query_capability")

    base_manifest = json.loads(BASE_MANIFEST.read_text(encoding="utf-8"))
    source_mismatches = []
    for rel, expected in (base_manifest.get("files") or {}).items():
        path = ROOT / rel
        actual = _sha(path) if path.is_file() else None
        if actual != expected:
            source_mismatches.append({"path": rel, "expected": expected, "actual": actual})
    if source_mismatches:
        failures.append("base_source_hash_mismatch")

    safe_manifest = json.loads(SAFE_MANIFEST.read_text(encoding="utf-8"))
    if safe_manifest.get("base_task018_manifest_sha256") != _sha(BASE_MANIFEST):
        failures.append("safe_manifest_base_hash_mismatch")
    if safe_manifest.get("deterministic_gate_sha256") != _sha(DETERMINISTIC_GATE):
        failures.append("safe_manifest_gate_hash_mismatch")

    audit = {
        "experiment": "query-positive-gateway-backup-v1-deepseek-confirmatory-audit",
        "status": "PASS" if not failures else "FAIL",
        "source": str(OUT.relative_to(ROOT)),
        "complete_coordinate_set": len(rows) == 5 and [row["seed"] for row in rows] == [0, 1, 2, 3, 4],
        "no_posthoc_exclusion": len(rows) == 5,
        "base_source_manifest": str(BASE_MANIFEST.relative_to(ROOT)),
        "safe_source_manifest": str(SAFE_MANIFEST.relative_to(ROOT)),
        "source_mismatches": source_mismatches,
        "aggregate": {
            key: aggregate[key]
            for key in (
                "planner_turns",
                "successful_attempts",
                "failed_attempts",
                "effect_exact_turns",
                "effect_inexact_turns",
                "query_requests",
                "backup_effects",
                "execution_equivalent_episodes",
                "direct_physical_exact_episodes",
                "recovered_execution_equivalent_episodes",
                "all_replay_pass",
                "all_tdr_improved",
                "all_aoi_improved",
                "mean_tdr_delta",
                "mean_aoi_delta_s",
                "total_tokens",
            )
        },
        "failures": failures,
        "claim_boundary": (
            "DeepSeek Flash only; O3 gateway-placed query-positive coordinate with backup initially disabled "
            "and 3600s primary store-and-forward delay. Supports decision-conditioned acquisition -> "
            "plan-feasibility closure -> gateway-backup execution -> communication improvement across five "
            "simulator seeds. Seed0 is recovered from a completed episode after post-processing SIGKILL; "
            "seeds1..4 have direct persisted physical_signature equality. Does not establish cross-model "
            "query-positive generalization or optimal evidence-acquisition policy."
        ),
    }
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# Query-positive gateway backup — five-seed DeepSeek confirmatory",
        "",
        "| Seed | Status | Turns | Effect exact | Queries | Backup | Physical/reference | TDR Δ | AoI Δ (s) | Tokens |",
        "|---:|---|---:|---:|---:|---:|---|---:|---:|---:|",
    ]
    for row in rows:
        physical = (
            "direct exact"
            if row["direct_physical_equal_reference"] is True
            else "recovered execution-equivalent"
        )
        md.append(
            f"| {row['seed']} | {row['status']} | {row['planner_turns']} | "
            f"{row['effect_exact_turns']}/{row['planner_turns']} | {row['query_requests']} | "
            f"{row['backup_effect_count']} | {physical} | "
            f"{row['delta_vs_no_acquisition']['timely_delivery_rate']:.6f} | "
            f"{row['delta_vs_no_acquisition']['aoi_mean_s']:.1f} | "
            f"{int(row['usage'].get('total_tokens') or 0)} |"
        )
    md.extend(
        [
            "",
            f"Mean TDR delta: **{aggregate['mean_tdr_delta']:.6f}** (+{aggregate['mean_tdr_delta']*100:.3f} pp).",
            f"Mean AoI delta: **{aggregate['mean_aoi_delta_s']:.1f} s**.",
            f"Effect-scope exact: **{aggregate['effect_exact_turns']}/{aggregate['planner_turns']}**; failed attempts: **{aggregate['failed_attempts']}**.",
            f"Owner queries: **{aggregate['query_requests']}**; gateway-backup applied effects: **{aggregate['backup_effects']}**.",
            "",
            "Seed0 boundary: task 018's episode completed, but its original runner was SIGKILLed during high-memory post-processing before summary write. The recovered row is kept explicitly distinct from the four directly persisted physical-signature rows.",
        ]
    )
    ANALYSIS.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps(audit, ensure_ascii=False, indent=2))
    print(f"WROTE {OUT}")
    print(f"WROTE {AUDIT}")
    print(f"WROTE {ANALYSIS}")
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())

