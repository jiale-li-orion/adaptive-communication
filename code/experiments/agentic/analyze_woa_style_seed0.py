#!/usr/bin/env python3
"""Analyze seed-0 WOA-style adaptation against the frozen v6 Method rows."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WOA_ROOT = ROOT / "results" / "agentic" / "woa-style-baseline-v1" / "deepseek-flash"
METHOD_ROOT = ROOT / "results" / "agentic" / "main-table-v6-confirmatory" / "deepseek-flash"
TASKS = ("localized-o2", "o5", "o6")
OUT = WOA_ROOT / "seed0-analysis.json"


def _method_row(task: str) -> dict:
    p = METHOD_ROOT / task / "seed-000" / "action_conditioned_compact" / "summary.json"
    return json.loads(p.read_text(encoding="utf-8"))


def _woa_row(task: str) -> dict:
    p = WOA_ROOT / task / "seed-000" / "summary.json"
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    aggregate_path = WOA_ROOT / "seed0-aggregate.json"
    aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
    if int(aggregate.get("completed_rows") or 0) != 3:
        raise RuntimeError("WOA-style seed0 table incomplete")

    rows = []
    for task in TASKS:
        method = _method_row(task)
        woa = _woa_row(task)
        ma = method.get("planner_behavior_audit") or {}
        wa = woa.get("planner_behavior_audit") or {}
        assurance = woa.get("assurance_audit") or {}
        mu = {}
        for line in Path(method["trace"]).read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            if event.get("event_type") != "model_usage":
                continue
            p = event.get("payload") or {}
            for key in ("input_tokens", "output_tokens", "total_tokens"):
                mu[key] = int(mu.get(key, 0)) + int(p.get(key) or 0)
            mu["latency_ms"] = float(mu.get("latency_ms", 0.0)) + float(p.get("latency_ms") or 0.0)
        wu = woa.get("usage") or {}
        rows.append(
            {
                "task": task,
                "method": {
                    "model_calls": method.get("model_calls_consumed"),
                    "effect_exact": ma.get("effect_scope_exact_turns"),
                    "effect_inexact": ma.get("effect_scope_inexact_turns"),
                    "observations": int(ma.get("local_observation_invocations") or 0)
                    + int(ma.get("remote_observation_invocations") or 0),
                    "physical_candidate": method.get("physical_equal_candidate_reference"),
                    "physical_legacy": method.get("physical_equal_legacy"),
                    "usage": mu,
                },
                "woa_style": {
                    "model_calls": woa.get("model_calls_consumed"),
                    "effect_exact": wa.get("effect_scope_exact_turns"),
                    "effect_inexact": wa.get("effect_scope_inexact_turns"),
                    "observations": int(wa.get("local_observation_invocations") or 0)
                    + int(wa.get("remote_observation_invocations") or 0),
                    "physical_candidate": woa.get("physical_equal_candidate_reference"),
                    "physical_legacy": woa.get("physical_equal_legacy"),
                    "usage": wu,
                    "raw_selected_plan_exact_turns": assurance.get("raw_selected_plan_exact_turns"),
                    "raw_query_turns": assurance.get("raw_query_turns"),
                    "repaired_turns": assurance.get("repaired_turns"),
                    "governor_counts": assurance.get("governor_counts") or {},
                    "repair_type_counts": assurance.get("repair_type_counts") or {},
                },
                "paired_delta_woa_minus_method": {
                    "model_calls": int(woa.get("model_calls_consumed") or 0)
                    - int(method.get("model_calls_consumed") or 0),
                    "observations": (
                        int(wa.get("local_observation_invocations") or 0)
                        + int(wa.get("remote_observation_invocations") or 0)
                        - int(ma.get("local_observation_invocations") or 0)
                        - int(ma.get("remote_observation_invocations") or 0)
                    ),
                    "total_tokens": int(wu.get("total_tokens") or 0) - int(mu.get("total_tokens") or 0),
                    "latency_ms": float(wu.get("latency_ms") or 0.0)
                    - float(mu.get("latency_ms") or 0.0),
                },
            }
        )

    payload = {
        "experiment": "woa-style-baseline-v1-seed0-analysis",
        "source": str(aggregate_path.relative_to(ROOT)),
        "rows": rows,
        "interpretation_boundary": (
            "WOA-style is a strong method adaptation over the same repository interface, not an "
            "official source-code reproduction. Raw-proposal and post-assurance metrics must be "
            "reported separately so repair work is not hidden by final physical equality."
        ),
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for row in rows:
        print(json.dumps(row, ensure_ascii=False))
    print(f"WROTE {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

