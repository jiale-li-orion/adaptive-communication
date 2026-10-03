#!/usr/bin/env python3
"""Mechanical aggregation for the seed-0 Agentic Communication main table.

This script makes no research decision.  It separates semantic fidelity, model
cost/observations and communication consequences, and writes a compact JSON +
Markdown report that can be interpreted once all 12 runs are present.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT = (
    ROOT
    / "results"
    / "agentic"
    / "main-table-v1"
    / "deepseek-flash"
    / "seed0-main-table-summary.json"
)
METHOD_ARM = "action_conditioned_compact"
TASK_ORDER = ("localized-o2", "o5", "o6")
ARM_ORDER = ("generic_react", "full_dump", "task_conditioned", METHOD_ARM)
KEY_COMM_METRICS = (
    "timely_delivery_rate",
    "collection_rate",
    "aoi_mean_s",
    "config_mismatch_node_s",
    "sampling_mismatch_node_s",
    "report_mismatch_node_s",
    "total_consumed_wh",
    "backup_bytes",
    "commands_sent",
    "commands_delivered",
    "commands_refused",
)


def _exact_rate(row: dict) -> float | None:
    exact = int(row.get("effect_scope_exact_turns") or 0)
    inexact = int(row.get("effect_scope_inexact_turns") or 0)
    denom = exact + inexact
    return None if denom == 0 else exact / denom


def _compact_row(row: dict) -> dict:
    usage = dict(row.get("usage") or {})
    delta = dict(row.get("delta_vs_candidate_reference") or {})
    agent_metrics: dict = {}
    audit_turns: list[dict] = []
    summary_path = row.get("summary")
    if summary_path:
        path = Path(str(summary_path))
        if path.exists():
            try:
                summary_payload = json.loads(path.read_text(encoding="utf-8"))
                agent_metrics = dict(summary_payload.get("agent_metrics") or {})
                audit_turns = list(
                    (summary_payload.get("planner_behavior_audit") or {}).get("turns") or []
                )
            except (OSError, json.JSONDecodeError):
                agent_metrics = {}
                audit_turns = []
    taxonomy = {
        "effect_omission": 0,
        "underscope": 0,
        "overscope": 0,
        "wrong_scope": 0,
        "spurious_effect": 0,
    }
    for turn in audit_turns:
        if turn.get("effect_scope_exact"):
            continue
        expected = int(turn.get("expected_effect_invocations") or 0)
        actual = int(turn.get("actual_effect_invocations") or 0)
        missing = len(turn.get("missing_effect_invocations") or [])
        extra = len(turn.get("unexpected_effect_invocations") or [])
        if expected == 0 and actual > 0:
            taxonomy["spurious_effect"] += 1
        elif expected > 0 and actual == 0:
            taxonomy["effect_omission"] += 1
        elif missing > 0 and extra == 0:
            taxonomy["underscope"] += 1
        elif extra > 0 and missing == 0:
            taxonomy["overscope"] += 1
        else:
            taxonomy["wrong_scope"] += 1
    return {
        "task": row.get("task"),
        "context_mode": row.get("context_mode"),
        "model_calls": row.get("model_calls"),
        "successful_model_attempts": row.get("successful_model_attempts"),
        "failed_model_attempts": row.get("failed_model_attempts"),
        "effect_scope_exact_turns": row.get("effect_scope_exact_turns"),
        "effect_scope_inexact_turns": row.get("effect_scope_inexact_turns"),
        "effect_scope_exact_rate": _exact_rate(row),
        "local_observation_invocations": row.get("local_observation_invocations"),
        "remote_observation_invocations": row.get("remote_observation_invocations"),
        "total_observation_invocations": int(row.get("local_observation_invocations") or 0)
        + int(row.get("remote_observation_invocations") or 0),
        "physical_equal_candidate_reference": row.get("physical_equal_candidate_reference"),
        "physical_equal_legacy": row.get("physical_equal_legacy"),
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "latency_ms": usage.get("latency_ms"),
        "mean_materialized_bytes": agent_metrics.get("mean_materialized_bytes"),
        "capability_requests": agent_metrics.get("capability_requests"),
        "capability_results": agent_metrics.get("capability_results"),
        "physical_action_confirmation_rate": agent_metrics.get(
            "physical_action_confirmation_rate"
        ),
        "semantic_failure_taxonomy": taxonomy,
        "nonzero_communication_delta": {
            key: value
            for key, value in delta.items()
            if value not in (None, False, 0, 0.0)
        },
        "key_communication_delta": {key: delta.get(key, 0) for key in KEY_COMM_METRICS},
        "summary": row.get("summary"),
    }


def _compare(baseline: dict, method: dict) -> dict:
    b_tokens = int(baseline.get("total_tokens") or 0)
    m_tokens = int(method.get("total_tokens") or 0)
    b_latency = float(baseline.get("latency_ms") or 0.0)
    m_latency = float(method.get("latency_ms") or 0.0)
    b_rate = baseline.get("effect_scope_exact_rate")
    m_rate = method.get("effect_scope_exact_rate")
    return {
        "baseline_arm": baseline["context_mode"],
        "method_arm": method["context_mode"],
        "effect_scope_exact_rate_delta_method_minus_baseline": (
            None if b_rate is None or m_rate is None else m_rate - b_rate
        ),
        "model_calls_delta_method_minus_baseline": int(method.get("model_calls") or 0)
        - int(baseline.get("model_calls") or 0),
        "observation_invocations_delta_method_minus_baseline": int(
            method.get("total_observation_invocations") or 0
        )
        - int(baseline.get("total_observation_invocations") or 0),
        "token_delta_method_minus_baseline": m_tokens - b_tokens,
        "token_ratio_method_over_baseline": None if b_tokens == 0 else m_tokens / b_tokens,
        "context_bytes_ratio_method_over_baseline": (
            None
            if not baseline.get("mean_materialized_bytes")
            else float(method.get("mean_materialized_bytes") or 0.0)
            / float(baseline["mean_materialized_bytes"])
        ),
        "capability_requests_delta_method_minus_baseline": int(
            method.get("capability_requests") or 0
        )
        - int(baseline.get("capability_requests") or 0),
        "latency_delta_ms_method_minus_baseline": m_latency - b_latency,
        "latency_ratio_method_over_baseline": None if b_latency == 0 else m_latency / b_latency,
        "baseline_physical_equal_candidate_reference": baseline.get(
            "physical_equal_candidate_reference"
        ),
        "method_physical_equal_candidate_reference": method.get(
            "physical_equal_candidate_reference"
        ),
    }


def _fmt(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _markdown(report: dict) -> str:
    lines = [
        "# Agentic Communication seed-0 main table",
        "",
        f"Completed: **{report['completed_rows']}/{report['expected_rows']}**",
        "",
        "This report is mechanical aggregation only; it does not choose a research winner.",
        "",
    ]
    by_key = {
        (row["task"], row["context_mode"]): row for row in report.get("rows", [])
    }
    for task in TASK_ORDER:
        lines.extend(
            [
                f"## {task}",
                "",
                "| Context | Calls | Exact scope | Obs | Context B | Tokens | API latency s | Physical = candidate |",
                "|---|---:|---:|---:|---:|---:|---:|---|",
            ]
        )
        for arm in ARM_ORDER:
            row = by_key.get((task, arm))
            if row is None:
                lines.append(f"| {arm} | — | — | — | — | — | missing |")
                continue
            latency_s = None if row["latency_ms"] is None else float(row["latency_ms"]) / 1000.0
            lines.append(
                "| "
                + " | ".join(
                    [
                        arm,
                        _fmt(row["model_calls"]),
                        _fmt(row["effect_scope_exact_rate"]),
                        _fmt(row["total_observation_invocations"]),
                        _fmt(row["mean_materialized_bytes"]),
                        _fmt(row["total_tokens"]),
                        _fmt(latency_s),
                        _fmt(row["physical_equal_candidate_reference"]),
                    ]
                )
                + " |"
            )
        lines.append("")

    lines.extend(["## Mechanical signals", ""])
    for key, value in report.get("mechanical_signals", {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(DEFAULT_INPUT))
    args = ap.parse_args()
    source = Path(args.input)
    payload = json.loads(source.read_text(encoding="utf-8"))
    rows = [_compact_row(row) for row in payload.get("rows", [])]
    by_task: dict[str, list[dict]] = {}
    for row in rows:
        by_task.setdefault(str(row["task"]), []).append(row)

    comparisons: dict[str, list[dict]] = {}
    for task, task_rows in by_task.items():
        method = next((row for row in task_rows if row["context_mode"] == METHOD_ARM), None)
        if method is None:
            continue
        comparisons[task] = [
            _compare(row, method)
            for row in task_rows
            if row["context_mode"] != METHOD_ARM
        ]

    method_rows = [row for row in rows if row["context_mode"] == METHOD_ARM]
    baseline_rows = [row for row in rows if row["context_mode"] != METHOD_ARM]
    report = {
        "source": str(source),
        "expected_rows": payload.get("expected_rows"),
        "completed_rows": payload.get("completed_rows"),
        "complete": payload.get("completed_rows") == payload.get("expected_rows"),
        "rows": rows,
        "method_vs_baseline": comparisons,
        "mechanical_signals": {
            "method_rows_present": len(method_rows),
            "method_all_effect_scope_exact": bool(method_rows)
            and all(int(row.get("effect_scope_inexact_turns") or 0) == 0 for row in method_rows),
            "method_all_physical_equal_candidate_reference": bool(method_rows)
            and all(row.get("physical_equal_candidate_reference") is True for row in method_rows),
            "baseline_rows_with_effect_scope_error": sum(
                int(row.get("effect_scope_inexact_turns") or 0) > 0 for row in baseline_rows
            ),
            "baseline_rows_with_physical_divergence": sum(
                row.get("physical_equal_candidate_reference") is False for row in baseline_rows
            ),
            "baseline_rows_with_observations": sum(
                int(row.get("total_observation_invocations") or 0) > 0 for row in baseline_rows
            ),
        },
    }
    out_json = source.with_name("seed0-analysis.json")
    out_md = source.with_name("seed0-analysis.md")
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "complete": report["complete"],
                "completed_rows": report["completed_rows"],
                "expected_rows": report["expected_rows"],
                "mechanical_signals": report["mechanical_signals"],
                "analysis_json": str(out_json),
                "analysis_md": str(out_md),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

