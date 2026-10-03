#!/usr/bin/env python3
"""Aggregate the frozen 5-seed confirmatory Agentic Communication main table."""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parents[3]
SOURCE = (
    ROOT
    / "results"
    / "agentic"
    / "main-table-v2-confirmatory"
    / "deepseek-flash"
    / "aggregate.json"
)
OUT_JSON = SOURCE.with_name("analysis.json")
OUT_MD = SOURCE.with_name("analysis.md")
METHOD = "action_conditioned_compact"
TASKS = ("localized-o2", "o5", "o6")
ARMS = (METHOD, "task_conditioned", "full_dump", "generic_react")
PHYSICAL_FIDELITY_METRICS = (
    "timely_delivery_rate",
    "collection_rate",
    "aoi_mean_s",
    "config_mismatch_node_s",
    "sampling_mismatch_node_s",
    "report_mismatch_node_s",
    "total_consumed_wh",
    "backup_bytes",
    "commands_sent",
)


def _mean(values):
    vals = [float(v) for v in values if v is not None]
    return None if not vals else statistics.fmean(vals)


def _median(values):
    vals = [float(v) for v in values if v is not None]
    return None if not vals else statistics.median(vals)


def _effect_rate(row: dict) -> float | None:
    exact = int(row.get("effect_scope_exact_turns") or 0)
    inexact = int(row.get("effect_scope_inexact_turns") or 0)
    total = exact + inexact
    return None if total == 0 else exact / total


def _summarize(rows: list[dict]) -> dict:
    exact = sum(int(r.get("effect_scope_exact_turns") or 0) for r in rows)
    inexact = sum(int(r.get("effect_scope_inexact_turns") or 0) for r in rows)
    total = exact + inexact
    obs = [
        int(r.get("local_observation_invocations") or 0)
        + int(r.get("remote_observation_invocations") or 0)
        for r in rows
    ]
    calls = [int(r.get("model_calls") or 0) for r in rows]
    tokens = [int((r.get("usage") or {}).get("total_tokens") or 0) for r in rows]
    latency = [float((r.get("usage") or {}).get("latency_ms") or 0.0) for r in rows]
    ctx = [r.get("mean_materialized_bytes") for r in rows]
    mean_abs_delta = {}
    for metric in PHYSICAL_FIDELITY_METRICS:
        values = []
        for row in rows:
            delta = (row.get("delta_vs_candidate_reference") or {}).get(metric)
            if isinstance(delta, (int, float)) and not isinstance(delta, bool):
                values.append(abs(float(delta)))
        mean_abs_delta[metric] = _mean(values)
    return {
        "n": len(rows),
        "seeds": sorted(int(r["seed"]) for r in rows),
        "effect_scope_exact_turns": exact,
        "effect_scope_inexact_turns": inexact,
        "effect_scope_exact_rate": None if total == 0 else exact / total,
        "episodes_with_any_inexact_effect": sum(
            int(r.get("effect_scope_inexact_turns") or 0) > 0 for r in rows
        ),
        "physical_equal_candidate_reference": sum(
            r.get("physical_equal_candidate_reference") is True for r in rows
        ),
        "failed_model_attempts": sum(int(r.get("failed_model_attempts") or 0) for r in rows),
        "observations_mean": _mean(obs),
        "observations_median": _median(obs),
        "model_calls_mean": _mean(calls),
        "model_calls_median": _median(calls),
        "total_tokens_mean": _mean(tokens),
        "total_tokens_median": _median(tokens),
        "api_latency_ms_mean": _mean(latency),
        "context_bytes_mean": _mean(ctx),
        "context_bytes_median": _median(ctx),
        "mean_abs_delta_to_candidate": mean_abs_delta,
    }


def _paired(method: dict, baseline: dict) -> dict:
    m_obs = int(method.get("local_observation_invocations") or 0) + int(
        method.get("remote_observation_invocations") or 0
    )
    b_obs = int(baseline.get("local_observation_invocations") or 0) + int(
        baseline.get("remote_observation_invocations") or 0
    )
    return {
        "task": method["task"],
        "seed": method["seed"],
        "baseline": baseline["context_mode"],
        "effect_scope_exact_rate_delta": (
            None
            if _effect_rate(method) is None or _effect_rate(baseline) is None
            else _effect_rate(method) - _effect_rate(baseline)
        ),
        "observations_delta": m_obs - b_obs,
        "model_calls_delta": int(method.get("model_calls") or 0)
        - int(baseline.get("model_calls") or 0),
        "tokens_delta": int((method.get("usage") or {}).get("total_tokens") or 0)
        - int((baseline.get("usage") or {}).get("total_tokens") or 0),
        "context_bytes_delta": (
            None
            if method.get("mean_materialized_bytes") is None
            or baseline.get("mean_materialized_bytes") is None
            else float(method["mean_materialized_bytes"])
            - float(baseline["mean_materialized_bytes"])
        ),
        "method_physical_equal": method.get("physical_equal_candidate_reference"),
        "baseline_physical_equal": baseline.get("physical_equal_candidate_reference"),
    }


def main() -> int:
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    rows = list(payload.get("rows") or [])
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    indexed: dict[tuple[str, int, str], dict] = {}
    for row in rows:
        key = (str(row["task"]), str(row["context_mode"]))
        groups[key].append(row)
        indexed[(str(row["task"]), int(row["seed"]), str(row["context_mode"]))] = row

    group_summary = {
        f"{task}/{arm}": _summarize(groups.get((task, arm), []))
        for task in TASKS
        for arm in ARMS
    }
    paired_rows = []
    for task in TASKS:
        for seed in range(5):
            method = indexed.get((task, seed, METHOD))
            if method is None:
                continue
            for arm in ARMS:
                if arm == METHOD:
                    continue
                baseline = indexed.get((task, seed, arm))
                if baseline is not None:
                    paired_rows.append(_paired(method, baseline))

    paired_summary = {}
    for task in TASKS:
        for arm in ARMS:
            if arm == METHOD:
                continue
            subset = [r for r in paired_rows if r["task"] == task and r["baseline"] == arm]
            paired_summary[f"{task}/{arm}"] = {
                "n": len(subset),
                "effect_scope_exact_rate_delta_mean": _mean(
                    [r["effect_scope_exact_rate_delta"] for r in subset]
                ),
                "observations_delta_mean": _mean([r["observations_delta"] for r in subset]),
                "model_calls_delta_mean": _mean([r["model_calls_delta"] for r in subset]),
                "tokens_delta_mean": _mean([r["tokens_delta"] for r in subset]),
                "context_bytes_delta_mean": _mean(
                    [r["context_bytes_delta"] for r in subset]
                ),
                "method_physical_equal_count": sum(r["method_physical_equal"] is True for r in subset),
                "baseline_physical_equal_count": sum(
                    r["baseline_physical_equal"] is True for r in subset
                ),
            }

    method_rows = [r for r in rows if r.get("context_mode") == METHOD]
    report = {
        "source": str(SOURCE),
        "completed_rows": payload.get("completed_rows"),
        "expected_rows": payload.get("expected_rows"),
        "complete": payload.get("completed_rows") == payload.get("expected_rows"),
        "group_summary": group_summary,
        "paired_summary": paired_summary,
        "method_gate": {
            "method_rows_present": len(method_rows),
            "expected_method_rows": 15,
            "observed_method_rows_all_effect_scope_exact": bool(method_rows)
            and all(int(r.get("effect_scope_inexact_turns") or 0) == 0 for r in method_rows),
            "observed_method_rows_all_physical_equal": bool(method_rows)
            and all(r.get("physical_equal_candidate_reference") is True for r in method_rows),
            "method_rows_with_observations": sum(
                int(r.get("local_observation_invocations") or 0)
                + int(r.get("remote_observation_invocations") or 0)
                > 0
                for r in method_rows
            ),
            "method_failed_model_attempts": sum(
                int(r.get("failed_model_attempts") or 0) for r in method_rows
            ),
            "confirmatory_method_gate_complete": len(method_rows) == 15,
            "confirmatory_method_gate_passed": len(method_rows) == 15
            and all(int(r.get("effect_scope_inexact_turns") or 0) == 0 for r in method_rows)
            and all(r.get("physical_equal_candidate_reference") is True for r in method_rows),
        },
    }
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# Agentic Communication confirmatory main table",
        "",
        f"Completed: **{report['completed_rows']}/{report['expected_rows']}**",
        "",
        "## Method gate",
        "",
    ]
    for key, value in report["method_gate"].items():
        md.append(f"- `{key}`: `{value}`")
    md.extend(["", "## Group summary", ""])
    for key, value in group_summary.items():
        md.append(
            f"- `{key}`: n={value['n']}, exact_rate={value['effect_scope_exact_rate']}, "
            f"physical_equal={value['physical_equal_candidate_reference']}, "
            f"obs_mean={value['observations_mean']}, tokens_mean={value['total_tokens_mean']}"
        )
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({
        "complete": report["complete"],
        "completed_rows": report["completed_rows"],
        "expected_rows": report["expected_rows"],
        "method_gate": report["method_gate"],
        "analysis_json": str(OUT_JSON),
        "analysis_md": str(OUT_MD),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

