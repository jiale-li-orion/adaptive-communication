#!/usr/bin/env python3
"""Read-only aggregation for protocol-v6 5-seed confirmatory main table."""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "results" / "agentic" / "main-table-v6-confirmatory" / "deepseek-flash" / "aggregate.json"
OUT_MD = SRC.with_name("analysis.md")
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


def failure_taxonomy(rows):
    counts = {
        "effect_omission": 0,
        "underscope": 0,
        "overscope": 0,
        "wrong_scope": 0,
        "spurious_effect": 0,
    }
    for row in rows:
        path = Path(str(row.get("summary") or ""))
        if not path.is_file():
            continue
        summary = json.loads(path.read_text(encoding="utf-8"))
        for turn in (summary.get("planner_behavior_audit") or {}).get("turns", []):
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
    return counts


def group(rows):
    exact_turns = sum(int(r.get("effect_scope_exact_turns") or 0) for r in rows)
    inexact_turns = sum(int(r.get("effect_scope_inexact_turns") or 0) for r in rows)
    return {
        "n": len(rows),
        "seeds": sorted(int(r["seed"]) for r in rows),
        "effect_exact_turns": exact_turns,
        "effect_inexact_turns": inexact_turns,
        "effect_exact_rate_pooled": (
            None if exact_turns + inexact_turns == 0 else exact_turns / (exact_turns + inexact_turns)
        ),
        "effect_exact_rate_mean": mean(rate(r) for r in rows),
        "episodes_with_any_inexact": sum(int(r.get("effect_scope_inexact_turns") or 0) > 0 for r in rows),
        "physical_candidate_exact_count": sum(r.get("physical_equal_candidate_reference") is True for r in rows),
        "physical_legacy_exact_count": sum(r.get("physical_equal_legacy") is True for r in rows),
        "observation_mean": mean(obs(r) for r in rows),
        "model_calls_mean": mean(r.get("model_calls") for r in rows),
        "tokens_mean": mean((r.get("usage") or {}).get("total_tokens") for r in rows),
        "context_bytes_mean": mean(r.get("mean_materialized_bytes") for r in rows),
        "failed_model_attempts": sum(int(r.get("failed_model_attempts") or 0) for r in rows),
        "semantic_failure_taxonomy": failure_taxonomy(rows),
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

    paired_summary = {}
    for task in TASKS:
        for arm in ARMS[1:]:
            subset = [r for r in paired if r["task"] == task and r["baseline"] == arm]
            paired_summary[f"{task}/{arm}"] = {
                "n": len(subset),
                "exact_rate_delta_mean": mean(r["exact_rate_delta"] for r in subset),
                "observation_delta_mean": mean(r["observation_delta"] for r in subset),
                "model_call_delta_mean": mean(r["model_call_delta"] for r in subset),
                "token_delta_mean": mean(r["token_delta"] for r in subset),
                "token_reduction_pct_mean": mean(r["token_reduction_pct"] for r in subset),
            }

    method_rows = [r for r in rows if r["context_mode"] == METHOD]
    baseline_rows = [r for r in rows if r["context_mode"] != METHOD]
    report = {
        "completed_rows": d.get("completed_rows"),
        "expected_rows": d.get("expected_rows"),
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
        "paired_summary": paired_summary,
        "paired": paired,
    }
    out = SRC.with_name("analysis.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# Protocol-v6 confirmatory main table",
        "",
        f"Rows: **{report['completed_rows']}/{report['expected_rows']}**",
        "",
        "## Method gate",
        "",
    ]
    for key, value in report["method_gate"].items():
        md.append(f"- `{key}`: `{value}`")
    md.extend(
        [
            "",
            "## Group summary",
            "",
            "| Task | Context | Seeds | Pooled effect exact | Episodes with error | Physical=legacy | Obs mean | Calls mean | Tokens mean | Context bytes mean |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for task in TASKS:
        for arm in ARMS:
            row = summary[f"{task}/{arm}"]
            pooled = row["effect_exact_rate_pooled"]
            md.append(
                "| {task} | {arm} | {n} | {pooled} | {bad} | {physical} | {obs_mean} | {calls} | {tokens} | {ctx} |".format(
                    task=task,
                    arm=arm,
                    n=row["n"],
                    pooled="-" if pooled is None else f"{100.0 * pooled:.1f}%",
                    bad=row["episodes_with_any_inexact"],
                    physical=f"{row['physical_legacy_exact_count']}/{row['n']}",
                    obs_mean="-" if row["observation_mean"] is None else f"{row['observation_mean']:.2f}",
                    calls="-" if row["model_calls_mean"] is None else f"{row['model_calls_mean']:.2f}",
                    tokens="-" if row["tokens_mean"] is None else f"{row['tokens_mean']:.0f}",
                    ctx="-" if row["context_bytes_mean"] is None else f"{row['context_bytes_mean']:.0f}",
                )
            )
    md.extend(
        [
            "",
            "## Semantic failure taxonomy",
            "",
        ]
    )
    for task in TASKS:
        for arm in ARMS:
            row = summary[f"{task}/{arm}"]
            taxonomy = row["semantic_failure_taxonomy"]
            if not any(taxonomy.values()):
                continue
            md.append(
                f"- `{task}/{arm}`: "
                + ", ".join(f"{key}={value}" for key, value in taxonomy.items() if value)
            )
    md.extend(
        [
            "",
            "## Paired Method vs baseline",
            "",
            "Positive exact-rate delta favors Method; negative observation/call/token delta means Method uses less.",
            "",
            "| Task | Baseline | Pairs | Exact-rate Δ | Obs Δ | Calls Δ | Token Δ | Token reduction |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for task in TASKS:
        for arm in ARMS[1:]:
            row = paired_summary[f"{task}/{arm}"]
            md.append(
                "| {task} | {arm} | {n} | {exact} | {obs_delta} | {calls} | {tokens} | {reduction} |".format(
                    task=task,
                    arm=arm,
                    n=row["n"],
                    exact="-" if row["exact_rate_delta_mean"] is None else f"{100.0 * row['exact_rate_delta_mean']:.1f} pp",
                    obs_delta="-" if row["observation_delta_mean"] is None else f"{row['observation_delta_mean']:.2f}",
                    calls="-" if row["model_call_delta_mean"] is None else f"{row['model_call_delta_mean']:.2f}",
                    tokens="-" if row["token_delta_mean"] is None else f"{row['token_delta_mean']:.0f}",
                    reduction="-" if row["token_reduction_pct_mean"] is None else f"{row['token_reduction_pct_mean']:.1f}%",
                )
            )
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("completed_rows", "expected_rows", "method_gate", "baseline_signals", "group_summary")}, ensure_ascii=False, indent=2))
    print(f"WROTE {out}")
    print(f"WROTE {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
