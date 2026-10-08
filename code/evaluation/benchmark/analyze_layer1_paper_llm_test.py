#!/usr/bin/env python3
"""Analyze the frozen 60-row Layer-1 paper LLM subset.

This script refuses partial or protocol-drifted runs. It produces model-spectrum
evidence for the benchmark paper, not a Future-Choice method claim.
"""
from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import random
import statistics


ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "results/benchmark/layer1-paper-llm-test"
ROWS = RUN / "rows.jsonl"
AGG = RUN / "aggregate.json"
MANIFEST = RUN / "run-manifest.json"
PROTOCOL = ROOT / "research/benchmark/PAPER-BASELINE-PROTOCOL.json"
SPLIT = ROOT / "results/benchmark/layer1-paper-split.json"
OUT = RUN / "statistical-analysis.json"
SUMMARY = RUN / "RESULTS-SUMMARY.md"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _rows() -> list[dict]:
    return [json.loads(line) for line in ROWS.read_text(encoding="utf-8").splitlines() if line.strip()]


def _mean(xs):
    return float(statistics.fmean(xs)) if xs else None


def _median(xs):
    return float(statistics.median(xs)) if xs else None


def _std(xs):
    return float(statistics.stdev(xs)) if len(xs) > 1 else 0.0 if xs else None


def _bootstrap_mean_ci(values: list[float], *, seed: int, n: int):
    if not values:
        return None
    rng = random.Random(seed)
    samples = []
    for _ in range(n):
        draw = [values[rng.randrange(len(values))] for _ in values]
        samples.append(statistics.fmean(draw))
    samples.sort()
    return {
        "mean": float(statistics.fmean(values)),
        "lo": float(samples[int(0.025 * (n - 1))]),
        "hi": float(samples[int(0.975 * (n - 1))]),
    }


def _metric(row: dict, key: str):
    return (row.get("communication_metrics") or {}).get(key)


def _usage(row: dict, key: str):
    return (row.get("model_usage") or {}).get(key)


def _expected_ids(protocol: dict, split: dict) -> set[str]:
    llm = protocol["llm_subset"]
    coords = [
        row
        for row in split["coordinates"]["test"]
        if row["task_template"] in llm["task_templates"]
        and row["window_id"] in llm["windows"]
        and int(row["seed"]) in llm["seeds"]
    ]
    return {f"{coord['coordinate_id']}::{mode}" for coord in coords for mode in llm["context_modes"]}


def main() -> int:
    protocol = _load(PROTOCOL)
    split = _load(SPLIT)
    aggregate = _load(AGG)
    manifest = _load(MANIFEST)
    rows = _rows()
    expected = _expected_ids(protocol, split)
    ids = [str(row["row_id"]) for row in rows]
    model_cfg = protocol["llm_subset"]["model"]

    checks = {
        "exactly_60_rows": len(rows) == 60,
        "row_ids_unique": len(ids) == len(set(ids)) == 60,
        "exact_frozen_row_id_set": set(ids) == expected,
        "aggregate_complete": aggregate.get("complete") is True and aggregate.get("actual_rows") == 60,
        "run_manifest_complete": manifest.get("complete") is True,
        "rows_digest_matches_manifest": manifest.get("rows_sha256") == _sha(ROWS),
        "protocol_digest_matches_manifest": manifest.get("protocol_sha256") == _sha(PROTOCOL),
        "split_digest_matches_manifest": manifest.get("split_sha256") == _sha(SPLIT),
        "all_rows_frozen_model_config": all(row.get("model") == model_cfg for row in rows),
        "all_replay_audits_pass": all(
            row.get("status") != "OK" or bool((row.get("replay_audit") or {}).get("passed"))
            for row in rows
        ),
        "only_declared_statuses": all(row.get("status") in {"OK", "RUNTIME_FAILURE"} for row in rows),
    }
    if not all(checks.values()):
        raise AssertionError(checks)

    groups = defaultdict(list)
    for row in rows:
        groups[(row["task_template"], row["context_mode"])].append(row)

    group_stats = {}
    for (task, mode), items in sorted(groups.items()):
        ok = [r for r in items if r["status"] == "OK"]
        def vals(fn):
            return [float(v) for r in ok if (v := fn(r)) is not None]
        group_stats[f"{task}/{mode}"] = {
            "rows": len(items),
            "ok": len(ok),
            "runtime_failure": len(items) - len(ok),
            "timely_delivery_rate": {
                "mean": _mean(vals(lambda r: _metric(r, "timely_delivery_rate"))),
                "median": _median(vals(lambda r: _metric(r, "timely_delivery_rate"))),
                "std": _std(vals(lambda r: _metric(r, "timely_delivery_rate"))),
            },
            "collection_rate_mean": _mean(vals(lambda r: _metric(r, "collection_rate"))),
            "node_survival_rate_mean": _mean(vals(lambda r: _metric(r, "node_survival_rate"))),
            "energy_mean_wh": _mean(vals(lambda r: _metric(r, "total_consumed_wh"))),
            "model_calls_mean": _mean([float(r.get("model_calls_consumed") or 0) for r in items]),
            "input_tokens_mean": _mean(vals(lambda r: _usage(r, "input_tokens"))),
            "output_tokens_mean": _mean(vals(lambda r: _usage(r, "output_tokens"))),
            "latency_ms_mean": _mean(vals(lambda r: _usage(r, "latency_ms"))),
            "failed_model_attempts": sum(
                int((r.get("planner_behavior_audit") or {}).get("failed_model_attempts") or 0)
                for r in items
            ),
        }

    by_coord = defaultdict(dict)
    for row in rows:
        by_coord[row["coordinate_id"]][row["context_mode"]] = row
    paired = []
    for cid, pair in sorted(by_coord.items()):
        if set(pair) != {"generic_react", "task_conditioned"}:
            raise AssertionError((cid, sorted(pair)))
        g = pair["generic_react"]
        t = pair["task_conditioned"]
        row = {
            "coordinate_id": cid,
            "task_template": g["task_template"],
            "generic_status": g["status"],
            "task_conditioned_status": t["status"],
        }
        if g["status"] == t["status"] == "OK":
            row.update({
                "tdr_delta_task_minus_generic": float(_metric(t, "timely_delivery_rate")) - float(_metric(g, "timely_delivery_rate")),
                "energy_delta_task_minus_generic": float(_metric(t, "total_consumed_wh")) - float(_metric(g, "total_consumed_wh")),
                "model_calls_delta_task_minus_generic": int(t.get("model_calls_consumed") or 0) - int(g.get("model_calls_consumed") or 0),
                "input_tokens_delta_task_minus_generic": int(_usage(t, "input_tokens") or 0) - int(_usage(g, "input_tokens") or 0),
                "output_tokens_delta_task_minus_generic": int(_usage(t, "output_tokens") or 0) - int(_usage(g, "output_tokens") or 0),
                "latency_ms_delta_task_minus_generic": float(_usage(t, "latency_ms") or 0.0) - float(_usage(g, "latency_ms") or 0.0),
            })
        paired.append(row)

    paired_ok = [r for r in paired if "tdr_delta_task_minus_generic" in r]
    tdr_deltas = [r["tdr_delta_task_minus_generic"] for r in paired_ok]
    stats_cfg = protocol["statistics"]
    pair_stats = {
        "coordinate_count": len(paired),
        "both_ok_count": len(paired_ok),
        "tdr_delta_task_minus_generic": _bootstrap_mean_ci(
            tdr_deltas,
            seed=int(stats_cfg["paired_bootstrap_seed"]),
            n=int(stats_cfg["paired_bootstrap_resamples"]),
        ),
        "tdr_task_better": sum(x > 1e-12 for x in tdr_deltas),
        "tdr_equal": sum(abs(x) <= 1e-12 for x in tdr_deltas),
        "tdr_task_worse": sum(x < -1e-12 for x in tdr_deltas),
        "mean_model_calls_delta": _mean([float(r["model_calls_delta_task_minus_generic"]) for r in paired_ok]),
        "mean_input_tokens_delta": _mean([float(r["input_tokens_delta_task_minus_generic"]) for r in paired_ok]),
        "mean_output_tokens_delta": _mean([float(r["output_tokens_delta_task_minus_generic"]) for r in paired_ok]),
        "mean_latency_ms_delta": _mean([float(r["latency_ms_delta_task_minus_generic"]) for r in paired_ok]),
    }
    status_counts = {
        "OK": sum(r["status"] == "OK" for r in rows),
        "RUNTIME_FAILURE": sum(r["status"] == "RUNTIME_FAILURE" for r in rows),
    }
    payload = {
        "stage": "LAYER1_PAPER_LLM_STATISTICAL_ANALYSIS",
        "checks": checks,
        "status_counts": status_counts,
        "groups": group_stats,
        "paired_task_conditioned_vs_generic": pair_stats,
        "paired_rows": paired,
        "claim_boundary": [
            "This 30-coordinate × 2-mode subset is a frozen LLM model-spectrum diagnostic and is not the Future-Choice method experiment.",
            "Task-conditioned vs generic-ReAct is a context/runtime comparison under one frozen DeepSeek model; it is not cross-model generalization.",
            "Runtime failures remain counted and are never replaced by another provider/model.",
            "The 30-coordinate LLM subset is not extrapolated to all 150 deterministic test coordinates."
        ],
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md = [
        "# Layer-1 Paper LLM Test — Frozen 30×2 Subset",
        "",
        f"- Rows: **60**; OK: **{status_counts['OK']}**; runtime failures: **{status_counts['RUNTIME_FAILURE']}**.",
        "- Role: benchmark model-spectrum diagnostic only; Future-Choice method claims come from F1–F7 artifacts.",
        "",
    ]
    delta = pair_stats["tdr_delta_task_minus_generic"]
    if delta:
        md.append(
            f"Paired mean TDR delta (task-conditioned − generic): **{delta['mean']:.6f}** "
            f"(bootstrap 95% CI [{delta['lo']:.6f}, {delta['hi']:.6f}]); "
            f"better/equal/worse = {pair_stats['tdr_task_better']}/{pair_stats['tdr_equal']}/{pair_stats['tdr_task_worse']}."
        )
    md += [
        "",
        "Full per-task metrics, calls, tokens, latency and failures are in `statistical-analysis.json`.",
        "",
        "Boundaries: no cross-model claim; no extrapolation to the full 150-coordinate deterministic test; no Future-Choice claim inferred from this table.",
    ]
    SUMMARY.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(OUT), "status_counts": status_counts, "pair_stats": pair_stats}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
