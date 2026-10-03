#!/usr/bin/env python3
"""Read-only analysis for the protocol-v5 corrected seed0 main table."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "results" / "agentic" / "main-table-v5-corrected" / "deepseek-flash" / "seed0-main-table-summary.json"
METHOD = "action_conditioned_compact"
TASKS = ("localized-o2", "o5", "o6")
ARMS = (METHOD, "task_conditioned", "full_dump", "generic_react")
PHYSICAL_KEYS = (
    "timely_delivery_rate",
    "collection_rate",
    "aoi_mean_s",
    "config_mismatch_node_s",
    "sampling_mismatch_node_s",
    "report_mismatch_node_s",
    "commands_sent",
    "commands_delivered",
    "downlink_attempts",
    "downlink_airtime_h",
    "total_consumed_wh",
    "backup_bytes",
)


def taxonomy(summary_path: str) -> dict:
    d = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    counts = Counter(effect_omission=0, underscope=0, overscope=0, wrong_scope=0, spurious_effect=0)
    for turn in (d.get("planner_behavior_audit") or {}).get("turns") or []:
        if turn.get("effect_scope_exact"):
            continue
        expected = int(turn.get("expected_effect_invocations") or 0)
        actual = int(turn.get("actual_effect_invocations") or 0)
        missing = len(turn.get("missing_effect_invocations") or [])
        extra = len(turn.get("unexpected_effect_invocations") or [])
        if expected == 0 and actual > 0:
            counts["spurious_effect"] += 1
        elif expected > 0 and actual == 0:
            counts["effect_omission"] += 1
        elif missing > 0 and extra == 0:
            counts["underscope"] += 1
        elif extra > 0 and missing == 0:
            counts["overscope"] += 1
        else:
            counts["wrong_scope"] += 1
    return dict(counts)


def enrich(row: dict) -> dict:
    exact = int(row.get("effect_scope_exact_turns") or 0)
    inexact = int(row.get("effect_scope_inexact_turns") or 0)
    obs = int(row.get("local_observation_invocations") or 0) + int(row.get("remote_observation_invocations") or 0)
    usage = row.get("usage") or {}
    return {
        **row,
        "effect_scope_exact_rate": None if exact + inexact == 0 else exact / (exact + inexact),
        "observations": obs,
        "total_tokens": int(usage.get("total_tokens") or 0),
        "semantic_failure_taxonomy": taxonomy(row["summary"]),
        "physical_delta_vs_legacy": {
            key: (row.get("delta_vs_legacy") or {}).get(key)
            for key in PHYSICAL_KEYS
        },
    }


def main() -> int:
    raw = json.loads(SRC.read_text(encoding="utf-8"))
    rows = [enrich(row) for row in raw.get("rows") or []]
    by = {(row["task"], row["context_mode"]): row for row in rows}
    paired = []
    for task in TASKS:
        m = by.get((task, METHOD))
        if m is None:
            continue
        for arm in ARMS[1:]:
            b = by.get((task, arm))
            if b is None:
                continue
            paired.append({
                "task": task,
                "baseline": arm,
                "exact_rate_delta": m["effect_scope_exact_rate"] - b["effect_scope_exact_rate"],
                "observation_delta": m["observations"] - b["observations"],
                "model_call_delta": int(m.get("model_calls") or 0) - int(b.get("model_calls") or 0),
                "token_delta": m["total_tokens"] - b["total_tokens"],
                "token_reduction_pct": None if not b["total_tokens"] else 100.0 * (b["total_tokens"] - m["total_tokens"]) / b["total_tokens"],
                "context_reduction_pct": None if not b.get("mean_materialized_bytes") else 100.0 * (float(b["mean_materialized_bytes"]) - float(m.get("mean_materialized_bytes") or 0.0)) / float(b["mean_materialized_bytes"]),
                "method_candidate_exact": m.get("physical_equal_candidate_reference"),
                "method_legacy_exact": m.get("physical_equal_legacy"),
                "baseline_candidate_exact": b.get("physical_equal_candidate_reference"),
                "baseline_legacy_exact": b.get("physical_equal_legacy"),
            })
    method = [r for r in rows if r["context_mode"] == METHOD]
    baseline = [r for r in rows if r["context_mode"] != METHOD]
    report = {
        "protocol_revision": raw.get("protocol_revision"),
        "completed_rows": raw.get("completed_rows"),
        "expected_rows": raw.get("expected_rows"),
        "method_gate": {
            "rows": len(method),
            "all_effect_exact": len(method) == 3 and all(int(r.get("effect_scope_inexact_turns") or 0) == 0 for r in method),
            "all_zero_observation": len(method) == 3 and all(r["observations"] == 0 for r in method),
            "all_candidate_exact": len(method) == 3 and all(r.get("physical_equal_candidate_reference") is True for r in method),
            "all_legacy_exact": len(method) == 3 and all(r.get("physical_equal_legacy") is True for r in method),
        },
        "baseline_signals": {
            "rows": len(baseline),
            "rows_with_semantic_error": sum(int(r.get("effect_scope_inexact_turns") or 0) > 0 for r in baseline),
            "rows_with_candidate_divergence": sum(r.get("physical_equal_candidate_reference") is False for r in baseline),
            "rows_with_legacy_divergence": sum(r.get("physical_equal_legacy") is False for r in baseline),
            "rows_with_observation": sum(r["observations"] > 0 for r in baseline),
        },
        "rows": rows,
        "paired": paired,
    }
    out = SRC.with_name("seed0-analysis.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("completed_rows", "expected_rows", "method_gate", "baseline_signals", "paired")}, ensure_ascii=False, indent=2))
    print(f"WROTE {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
