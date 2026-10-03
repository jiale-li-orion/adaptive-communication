#!/usr/bin/env python3
"""Recover the scientific result of task 018 from its completed trace."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "results" / "agentic" / "query-positive-gateway-backup-v1"
TRACE = BASE / "deepseek-flash" / "seed-000" / "runtime_trace.jsonl"
STREAM_AUDIT = TRACE.parent / "recovered-streaming-audit.json"
MANIFEST = BASE / "model-probe-source-manifest.json"
GATE = BASE / "deterministic-gate.json"
OUT = TRACE.parent / "recovered-summary.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _invocation_key(row: dict) -> tuple[str, str, str]:
    args = dict(row.get("canonical_arguments") or {})
    cid = str(row.get("capability_id") or "")
    resource = str(row.get("resource") or "")
    if cid.startswith("communication.config.") and args.get("node_id") == resource:
        args.pop("node_id", None)
    return cid, resource, json.dumps(args, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    streaming = json.loads(STREAM_AUDIT.read_text(encoding="utf-8"))
    deterministic = json.loads(GATE.read_text(encoding="utf-8"))
    deterministic_row = next(row for row in deterministic["rows"] if int(row["seed"]) == 0)

    source_mismatches = []
    for rel, expected in (manifest.get("files") or {}).items():
        path = ROOT / rel
        actual = _sha(path) if path.is_file() else None
        if actual != expected:
            source_mismatches.append({"path": rel, "expected": expected, "actual": actual})

    semantic_reference: dict = {}
    latest_prompt: dict = {}
    attempts = Counter()
    usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "latency_ms": 0.0}
    turns = []
    query_requests = []
    query_results = []
    backup_effects = []
    completion = None
    nonempty_state_patches = 0

    with TRACE.open(encoding="utf-8") as fh:
        for line in fh:
            event = json.loads(line)
            typ = event.get("event_type")
            t_s = int(event.get("t_s") or 0)
            payload = event.get("payload") or {}
            if typ == "prompt_assembly":
                fragments = {
                    str(row.get("kind") or ""): row.get("content")
                    for row in payload.get("fragments", [])
                    if isinstance(row, dict)
                }
                candidate = fragments.get("candidate_action_context") or {}
                qp = candidate.get("query_positive_gateway_backup") or {}
                latest_prompt = {
                    "guard_result": qp.get("guard_result"),
                    "needs": [
                        row
                        for row in (fragments.get("evidence_needs") or [])
                        if isinstance(row, dict)
                    ],
                }
            elif typ == "planner_semantic_reference":
                semantic_reference = dict(payload)
            elif typ == "model_attempt":
                attempts[str(payload.get("status"))] += 1
            elif typ == "model_usage":
                for key in ("input_tokens", "output_tokens", "total_tokens"):
                    usage[key] += int(payload.get(key) or 0)
                usage["latency_ms"] += float(payload.get("latency_ms") or 0.0)
            elif typ == "planner_decision":
                actual = list(payload.get("invocations") or [])
                actual_effect = [
                    row
                    for row in actual
                    if str(row.get("capability_id") or "").startswith(
                        ("communication.config.", "communication.fallback.")
                    )
                ]
                observations = [
                    row
                    for row in actual
                    if str(row.get("capability_id") or "").startswith(
                        ("communication.center.", "communication.gateway.")
                    )
                ]
                expected = list(semantic_reference.get("expected_effect_invocations") or [])
                expected_set = {_invocation_key(row) for row in expected}
                actual_set = {_invocation_key(row) for row in actual_effect}
                state_patch = dict(payload.get("state_patch") or {})
                nonempty_state_patches += bool(state_patch)
                expected_open = set()
                for need in latest_prompt.get("needs") or []:
                    if "consider_gateway_backup" not in set(need.get("blocking_plan_ids") or []):
                        continue
                    question = str(need.get("proposition_or_question") or "")
                    for capability_id in (
                        "communication.gateway.primary_health",
                        "communication.gateway.receipt_summary",
                    ):
                        if capability_id in question:
                            expected_open.add(capability_id)
                turns.append(
                    {
                        "t_s": t_s,
                        "guard_result": latest_prompt.get("guard_result"),
                        "primary_plan_id": semantic_reference.get("primary_plan_id"),
                        "selected_plan_id": payload.get("selected_plan_id"),
                        "effect_scope_exact": expected_set == actual_set,
                        "expected_effect_count": len(expected_set),
                        "actual_effect_count": len(actual_set),
                        "expected_open_query_capabilities": sorted(expected_open),
                        "actual_observation_capabilities": sorted(
                            str(row.get("capability_id")) for row in observations
                        ),
                        "stop": bool(payload.get("stop")),
                    }
                )
            elif typ == "capability_request":
                capability_id = str(payload.get("capability_id") or "")
                if capability_id in {
                    "communication.gateway.primary_health",
                    "communication.gateway.receipt_summary",
                }:
                    query_requests.append(
                        {
                            "t_s": t_s,
                            "capability_id": capability_id,
                            "request_id": payload.get("request_id"),
                        }
                    )
            elif typ == "capability_result":
                request_id = str(payload.get("request_id") or "")
                if request_id.startswith("evidence:"):
                    query_results.append(
                        {
                            "t_s": t_s,
                            "request_id": request_id,
                            "status": payload.get("status"),
                        }
                    )
            elif (
                typ == "physical_effect"
                and payload.get("capability_id") == "communication.fallback.gateway_backup"
                and payload.get("lifecycle_stage") == "applied"
            ):
                backup_effects.append({"t_s": t_s, **payload})
            elif typ == "task_completion":
                completion = dict(payload)

    reference_queries = [
        {
            "t_s": int(row["t_s"]),
            "capability_id": str(row["capability_id"]),
            "request_id": row.get("request_id"),
        }
        for row in deterministic_row["query_audit"]["query_requests"]
    ]
    reference_backup_effects = [
        {"t_s": int(row.get("applied_at_s") or 0), **row}
        for row in deterministic_row["query_audit"]["backup_effects"]
    ]
    query_trace_exact = query_requests == reference_queries
    backup_trace_exact = [
        (row["t_s"], row.get("capability_id"), row.get("resource"), row.get("enabled"))
        for row in backup_effects
    ] == [
        (row["t_s"], row.get("capability_id"), row.get("resource"), row.get("enabled"))
        for row in reference_backup_effects
    ]

    dynamic = deterministic_row["dynamic"]
    completion_checks = {
        "routine_obligations": completion["routine"]["n"] == dynamic["routine_obligations"],
        "routine_delivered": completion["routine"]["delivered"] == dynamic["routine_delivered"],
        "missing_collection": completion["routine"]["missing_collection"] == dynamic["missing_collection"],
        "missing_delivery": completion["routine"]["missing_delivery"] == dynamic["missing_delivery"],
        "censored": completion["routine"]["censored"] == dynamic["censored"],
        "aoi_mean_s": completion["routine"]["aoi_mean_s"] == dynamic["aoi_mean_s"],
        "aoi_p50_s": completion["routine"]["aoi_p50_s"] == dynamic["aoi_p50_s"],
        "aoi_p90_s": completion["routine"]["aoi_p90_s"] == dynamic["aoi_p90_s"],
        "aoi_p95_s": completion["routine"]["aoi_p95_s"] == dynamic["aoi_p95_s"],
        "latency_mean_s": completion["routine"]["latency_mean_s"] == dynamic["delivery_latency_mean_s"],
        "commands_sent": completion["command_counters"]["commands_sent"] == dynamic["commands_sent"],
        "commands_delivered": completion["command_counters"]["commands_delivered"] == dynamic["commands_delivered"],
        "commands_refused": completion["command_counters"]["commands_refused"] == dynamic["commands_refused"],
        "alive_nodes": completion["survival"]["alive"] == dynamic["alive_nodes"],
        "mean_final_soc": completion["survival"]["mean_final_soc"] == dynamic["mean_final_soc"],
    }
    all_completion_checks = all(completion_checks.values())
    expected_open = {
        capability_id
        for turn in turns
        for capability_id in turn["expected_open_query_capabilities"]
    }
    actual_queries = {row["capability_id"] for row in query_requests}
    recovered_behavior_pass = bool(
        attempts.get("failed", 0) == 0
        and attempts.get("succeeded", 0) == 15
        and len(turns) == 15
        and all(turn["effect_scope_exact"] for turn in turns)
        and expected_open
        and expected_open <= actual_queries
        and len(backup_effects) == 1
    )
    execution_equivalence_basis = bool(
        recovered_behavior_pass
        and query_trace_exact
        and backup_trace_exact
        and all_completion_checks
        and streaming.get("status") == "PASS"
        and not source_mismatches
    )
    control = deterministic_row["no_acquisition_control"]
    communication_gain = {
        "timely_delivery_rate": dynamic["timely_delivery_rate"] - control["timely_delivery_rate"],
        "aoi_mean_s": dynamic["aoi_mean_s"] - control["aoi_mean_s"],
    }

    recovered_pass = bool(
        execution_equivalence_basis
        and communication_gain["timely_delivery_rate"] > 0
        and communication_gain["aoi_mean_s"] < 0
    )
    payload = {
        "experiment": "task-018-query-positive-result-recovery",
        "status": "RECOVERED_PASS" if recovered_pass else "RECOVERY_INCOMPLETE",
        "original_worker_exit_code": 137,
        "original_summary_persisted": False,
        "direct_physical_signature_boolean_persisted": False,
        "source_manifest_current_match": not source_mismatches,
        "source_mismatches": source_mismatches,
        "streaming_audit": {
            "status": streaming.get("status"),
            "r0": streaming.get("streaming_r0"),
            "r2": streaming.get("streaming_r2"),
        },
        "model_behavior": {
            "successful_attempts": attempts.get("succeeded", 0),
            "failed_attempts": attempts.get("failed", 0),
            "planner_turns": len(turns),
            "effect_scope_exact_turns": sum(turn["effect_scope_exact"] for turn in turns),
            "effect_scope_inexact_turns": sum(not turn["effect_scope_exact"] for turn in turns),
            "expected_open_query_capabilities": sorted(expected_open),
            "queried_capabilities": sorted(actual_queries),
            "query_requests": query_requests,
            "query_results": query_results,
            "backup_effects": backup_effects,
            "nonempty_state_patch_turns": nonempty_state_patches,
            "turns": turns,
            "usage": usage,
        },
        "deterministic_execution_equivalence": {
            "query_request_trace_exact": query_trace_exact,
            "backup_effect_trace_exact": backup_trace_exact,
            "task_completion_shared_metrics_exact": all_completion_checks,
            "task_completion_checks": completion_checks,
            "basis_pass": execution_equivalence_basis,
            "interpretation": (
                "The original run did not persist the direct physical_signature equality boolean. "
                "Recovery instead proves identical decision effect scopes, identical owner-query "
                "schedule, identical gateway-backup applied effect, exact "
                "R2 reconstruction, and exact shared task-completion metrics under the same frozen "
                "seed/simulator/source. Planner state patches are allowed because the original task-018 "
                "gate did not forbid them and they do not execute physical capabilities."
            ),
        },
        "communication_metrics": dynamic,
        "no_acquisition_control_metrics": control,
        "delta_vs_no_acquisition": communication_gain,
        "failure_diagnosis": {
            "episode_completed": completion is not None and completion.get("status") == "completed",
            "trace_bytes": TRACE.stat().st_size,
            "trace_records": streaming["streaming_r0"]["events"],
            "post_episode_runner_pattern": (
                "original runner retained the in-memory policy trace, then load_trace() parsed the "
                "entire 194 MB trace, and _audit_query_positive_r2() called load_trace() again before "
                "summary write; this is consistent with severe WSL memory pressure after episode completion"
            ),
            "causal_certainty": (
                "high-confidence infrastructure diagnosis, not kernel-level proof of the SIGKILL source"
            ),
        },
        "recovery_boundary": (
            "RECOVERED_PASS means the completed seed0 model episode satisfies the scientific behavior, "
            "query, execution-equivalence, and communication-gain gates from persisted artifacts. "
            "It does not pretend that the original runner persisted its direct physical_signature boolean."
        ),
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "attempts": payload["model_behavior"]["successful_attempts"],
                "effect_exact": payload["model_behavior"]["effect_scope_exact_turns"],
                "queries": len(query_requests),
                "query_trace_exact": query_trace_exact,
                "backup_effects": len(backup_effects),
                "backup_trace_exact": backup_trace_exact,
                "r2_exact": streaming["streaming_r2"]["exact_assembly_matches"],
                "r2_total": streaming["streaming_r2"]["contexts"],
                "completion_metrics_exact": all_completion_checks,
                "tdr_delta": communication_gain["timely_delivery_rate"],
                "aoi_delta_s": communication_gain["aoi_mean_s"],
                "source_match": not source_mismatches,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print(f"WROTE {OUT}")
    return 0 if recovered_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())

