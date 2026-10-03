#!/usr/bin/env python3
"""Read-only aggregation for protocol-v5 5-seed confirmatory main table."""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "results" / "agentic" / "main-table-v5-confirmatory" / "deepseek-flash" / "aggregate.json"
METHOD = "action_conditioned_compact"
TASKS = ("localized-o2", "o5", "o6")
ARMS = (METHOD, "task_conditioned", "full_dump", "generic_react")


def mean(values):
    xs = [float(v) for v in values if v is not None]
    return None if not xs else statistics.fmean(xs)


def rate(row):
    exact = int(row.get("effect_scope_exact_turns") or 0)
    bad = int(row.get("effect_scope_inexact_turns") or 0)
    return None if exact + bad == 0 else exact / (exact + bad)


def obs(row):
    return int(row.get("local_observation_invocations") or 0) + int(row.get("remote_observation_invocations") or 0)


def group(rows):
    return {
        "n": len(rows),
        "seeds": sorted(int(r["seed"]) for r in rows),
        "effect_exact_rate_mean": mean(rate(r) for r in rows),
        "episodes_with_any_inexact": sum(int(r.get("effect_scope_inexact_turns") or 0) > 0 for r in rows),
        "physical_candidate_exact_count": sum(r.get("physical_equal_candidate_reference") is True for r in rows),
        "physical_legacy_exact_count": sum(r.get("physical_equal_legacy") is True for r in rows),
        "observation_mean": mean(obs(r) for r in rows),
        "model_calls_mean": mean(r.get("model_calls") for r in rows),
        "tokens_mean": mean((r.get("usage") or {}).get("total_tokens") for r in rows),
        "context_bytes_mean": mean(r.get("mean_materialized_bytes") for r in rows),
        "failed_model_attempts": sum(int(r.get("failed_model_attempts") or 0) for r in rows),
    }


def main() -> int:
    d = json.loads(SRC.read_text(encoding="utf-8"))
    rows = list(d.get("rows") or [])
    groups = defaultdict(list)
    by = {}
    for r in rows:
        groups[(r["task"], r["context_mode"])].append(r)
        by[(r["task"], int(r["seed"]), r["context_mode"])] = r

    summary = {f"{task}/{arm}": group(groups[(task, arm)]) for task in TASKS for arm in ARMS}
    paired = []
    for task in TASKS:
        for seed in range(5):
            m = by.get((task, seed, METHOD))
            if not m:
                continue
            for arm in ARMS[1:]:
                b = by.get((task, seed, arm))
                if not b:
                    continue
                mt = int((m.get("usage") or {}).get("total_tokens") or 0)
                bt = int((b.get("usage") or {}).get("total_tokens") or 0)
                paired.append({
                    "task": task,
                    "seed": seed,
                    "baseline": arm,
                    "exact_rate_delta": rate(m) - rate(b),
                    "observation_delta": obs(m) - obs(b),
                    "model_call_delta": int(m.get("model_calls") or 0) - int(b.get("model_calls") or 0),
                    "token_delta": mt - bt,
                    "token_reduction_pct": None if bt == 0 else 100.0 * (bt - mt) / bt,
                    "method_candidate_exact": m.get("physical_equal_candidate_reference"),
                    "method_legacy_exact": m.get("physical_equal_legacy"),
                    "baseline_candidate_exact": b.get("physical_equal_candidate_reference"),
                    "baseline_legacy_exact": b.get("physical_equal_legacy"),
                })

    method_rows = [r for r in rows if r["context_mode"] == METHOD]
    baseline_rows = [r for r in rows if r["context_mode"] != METHOD]
    report = {
        "completed_rows": d.get("completed_rows"),
        "expected_rows": d.get("expected_rows"),
        "reused_seed0_rows": d.get("reused_seed0_rows"),
        "method_gate": {
            "rows": len(method_rows),
            "expected_rows": 15,
            "all_effect_exact": len(method_rows) == 15 and all(int(r.get("effect_scope_inexact_turns") or 0) == 0 for r in method_rows),
            "all_zero_observation": len(method_rows) == 15 and all(obs(r) == 0 for r in method_rows),
            "all_candidate_exact": len(method_rows) == 15 and all(r.get("physical_equal_candidate_reference") is True for r in method_rows),
            "all_legacy_exact": len(method_rows) == 15 and all(r.get("physical_equal_legacy") is True for r in method_rows),
        },
        "baseline_signals": {
            "rows": len(baseline_rows),
            "rows_with_semantic_error": sum(int(r.get("effect_scope_inexact_turns") or 0) > 0 for r in baseline_rows),
            "rows_with_candidate_divergence": sum(r.get("physical_equal_candidate_reference") is False for r in baseline_rows),
            "rows_with_legacy_divergence": sum(r.get("physical_equal_legacy") is False for r in baseline_rows),
            "rows_with_observation": sum(obs(r) > 0 for r in baseline_rows),
        },
        "group_summary": summary,
        "paired": paired,
    }
    out = SRC.with_name("analysis.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("completed_rows", "expected_rows", "method_gate", "baseline_signals", "group_summary")}, ensure_ascii=False, indent=2))
    print(f"WROTE {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
