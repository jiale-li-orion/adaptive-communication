#!/usr/bin/env python3
"""Analyze five-seed WOA-style adaptation against frozen protocol-v6 Method."""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parents[3]
WOA_ROOT = ROOT / "results" / "agentic" / "woa-style-baseline-v1" / "deepseek-flash"
METHOD_ROOT = ROOT / "results" / "agentic" / "main-table-v6-confirmatory" / "deepseek-flash"
SRC = WOA_ROOT / "confirmatory-aggregate.json"
OUT = WOA_ROOT / "confirmatory-analysis.json"
OUT_MD = WOA_ROOT / "confirmatory-analysis.md"
TASKS = ("localized-o2", "o5", "o6")


def _mean(values):
    vals = [float(v) for v in values]
    return statistics.fmean(vals) if vals else None


def _method_summary(task: str, seed: int) -> dict:
    path = METHOD_ROOT / task / f"seed-{seed:03d}" / "action_conditioned_compact" / "summary.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _method_usage(summary: dict) -> dict:
    total = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "latency_ms": 0.0}
    for line in Path(summary["trace"]).read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event.get("event_type") != "model_usage":
            continue
        row = event.get("payload") or {}
        for key in ("input_tokens", "output_tokens", "total_tokens"):
            total[key] += int(row.get(key) or 0)
        total["latency_ms"] += float(row.get("latency_ms") or 0.0)
    return total


def main() -> int:
    data = json.loads(SRC.read_text(encoding="utf-8"))
    if int(data.get("completed_rows") or 0) != 15:
        raise RuntimeError("WOA-style confirmatory is incomplete")
    rows = list(data.get("rows") or [])
    if len(rows) != 15:
        raise RuntimeError(f"expected 15 WOA rows, got {len(rows)}")

    paired = []
    grouped = defaultdict(list)
    for woa in rows:
        cfg = woa.get("config") or {}
        task = str(cfg["task"])
        seed = int(cfg["seed"])
        method = _method_summary(task, seed)
        method_usage = _method_usage(method)
        wa = woa.get("planner_behavior_audit") or {}
        ma = method.get("planner_behavior_audit") or {}
        assurance = woa.get("assurance_audit") or {}
        wu = woa.get("usage") or {}
        row = {
            "task": task,
            "seed": seed,
            "woa": {
                "turns": int(assurance.get("turns") or 0),
                "effect_exact": int(wa.get("effect_scope_exact_turns") or 0),
                "effect_inexact": int(wa.get("effect_scope_inexact_turns") or 0),
                "observations": int(wa.get("local_observation_invocations") or 0)
                + int(wa.get("remote_observation_invocations") or 0),
                "physical_candidate": woa.get("physical_equal_candidate_reference"),
                "physical_legacy": woa.get("physical_equal_legacy"),
                "raw_plan_exact": int(assurance.get("raw_selected_plan_exact_turns") or 0),
                "raw_effect_exact": int(assurance.get("raw_effect_scope_exact_turns") or 0),
                "raw_stop_exact": int(assurance.get("raw_stop_exact_turns") or 0),
                "raw_query_turns": int(assurance.get("raw_query_turns") or 0),
                "repaired_turns": int(assurance.get("repaired_turns") or 0),
                "governor_counts": assurance.get("governor_counts") or {},
                "repair_type_counts": assurance.get("repair_type_counts") or {},
                "usage": wu,
            },
            "method": {
                "effect_exact": int(ma.get("effect_scope_exact_turns") or 0),
                "effect_inexact": int(ma.get("effect_scope_inexact_turns") or 0),
                "observations": int(ma.get("local_observation_invocations") or 0)
                + int(ma.get("remote_observation_invocations") or 0),
                "physical_candidate": method.get("physical_equal_candidate_reference"),
                "physical_legacy": method.get("physical_equal_legacy"),
                "usage": method_usage,
            },
            "woa_minus_method": {
                "total_tokens": int(wu.get("total_tokens") or 0)
                - int(method_usage.get("total_tokens") or 0),
                "latency_ms": float(wu.get("latency_ms") or 0.0)
                - float(method_usage.get("latency_ms") or 0.0),
            },
        }
        paired.append(row)
        grouped[task].append(row)

    summary = {}
    for task in TASKS:
        subset = grouped[task]
        total_turns = sum(row["woa"]["turns"] for row in subset)
        summary[task] = {
            "episodes": len(subset),
            "post_assurance_effect_inexact_turns": sum(
                row["woa"]["effect_inexact"] for row in subset
            ),
            "post_assurance_physical_legacy_exact_episodes": sum(
                row["woa"]["physical_legacy"] is True for row in subset
            ),
            "post_assurance_observation_turns": sum(row["woa"]["observations"] for row in subset),
            "raw_total_turns": total_turns,
            "raw_plan_exact_turns": sum(row["woa"]["raw_plan_exact"] for row in subset),
            "raw_effect_exact_turns": sum(row["woa"]["raw_effect_exact"] for row in subset),
            "raw_stop_exact_turns": sum(row["woa"]["raw_stop_exact"] for row in subset),
            "raw_query_turns": sum(row["woa"]["raw_query_turns"] for row in subset),
            "repaired_turns": sum(row["woa"]["repaired_turns"] for row in subset),
            "woa_tokens_mean": _mean(row["woa"]["usage"].get("total_tokens", 0) for row in subset),
            "method_tokens_mean": _mean(
                row["method"]["usage"].get("total_tokens", 0) for row in subset
            ),
            "paired_token_delta_mean": _mean(
                row["woa_minus_method"]["total_tokens"] for row in subset
            ),
            "paired_latency_delta_ms_mean": _mean(
                row["woa_minus_method"]["latency_ms"] for row in subset
            ),
        }

    payload = {
        "experiment": "woa-style-baseline-v1-confirmatory-analysis",
        "source": str(SRC.relative_to(ROOT)),
        "summary": summary,
        "paired_rows": paired,
        "interpretation_boundary": (
            "WirelessOpsAgent-style is a strong same-interface method adaptation, not an official "
            "source-code reproduction. Post-assurance reliability, raw proposal quality and repair "
            "activity are reported separately."
        ),
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# WirelessOpsAgent-style five-seed confirmatory",
        "",
        "| Task | Episodes | Post-assurance errors | Physical=legacy | Raw plan exact | Raw effect exact | Raw stop exact | Raw queries | Repaired turns | WOA tokens | Method tokens | Δ tokens |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for task in TASKS:
        s = summary[task]
        md.append(
            f"| {task} | {s['episodes']} | {s['post_assurance_effect_inexact_turns']} | "
            f"{s['post_assurance_physical_legacy_exact_episodes']}/{s['episodes']} | "
            f"{s['raw_plan_exact_turns']}/{s['raw_total_turns']} | "
            f"{s['raw_effect_exact_turns']}/{s['raw_total_turns']} | "
            f"{s['raw_stop_exact_turns']}/{s['raw_total_turns']} | "
            f"{s['raw_query_turns']} | {s['repaired_turns']} | "
            f"{s['woa_tokens_mean']:.0f} | {s['method_tokens_mean']:.0f} | "
            f"{s['paired_token_delta_mean']:.0f} |"
        )
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"WROTE {OUT}")
    print(f"WROTE {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

