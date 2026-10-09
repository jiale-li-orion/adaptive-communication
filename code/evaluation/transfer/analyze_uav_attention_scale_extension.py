#!/usr/bin/env python3
"""Statistical analysis for frozen C4/C5 N=10 scale extensions."""
from __future__ import annotations

from collections import defaultdict
import json
import math
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
COMMON = ROOT / "code/evaluation/common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from paper_stats import bootstrap_mean_ci_linear, wilson_interval  # noqa: E402


PAPER50 = ROOT / "results/transfer/uav-attention-n10-scale-paper50"
CONSTRUCTIVE100 = ROOT / "results/transfer/uav-attention-n10-scale-constructive100"
COHORTS = ROOT / "results/transfer/uav-attention-n10-scale-extension-cohorts.json"
LEGACY_COHORT = ROOT / "results/transfer/uav-attention-n10-constructive-cohort.json"
OUT = ROOT / "results/transfer/uav-attention-n10-scale-statistics.json"
MD = ROOT / "results/transfer/UAV-N10-SCALE-RESULTS.md"


POLICIES = (
    "nearest_neighbour",
    "nearest_deadline",
    "greedy_deadline_battery",
    "battery_aware_nn",
)
METHODS = ("native", "depth4", "future_choice")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def rows(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def exact_mcnemar(b: int, c: int) -> dict[str, float | int]:
    """Two-sided exact McNemar via Binomial(n=b+c, p=.5)."""
    n = int(b + c)
    if n == 0:
        return {"future_better": b, "future_worse": c, "discordant": 0, "p_two_sided": 1.0}
    k = min(int(b), int(c))
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return {
        "future_better": b,
        "future_worse": c,
        "discordant": n,
        "p_two_sided": min(1.0, 2.0 * tail),
    }


def paired_by_seed(items: list[dict]) -> dict[tuple[str, str], dict[int, dict]]:
    out: dict[tuple[str, str], dict[int, dict]] = defaultdict(dict)
    for r in items:
        if r["status"] != "OK":
            continue
        out[(r["policy"], r["method"])][int(r["seed"])] = r
    return out


def binary_stats(items: list[dict], key: str) -> dict:
    vals = [int(r[key]) for r in items]
    success = sum(vals)
    return wilson_interval(success, len(vals))


def paired_compare(
    future: dict[int, dict],
    baseline: dict[int, dict],
    *,
    seed: int,
) -> dict:
    shared = sorted(set(future) & set(baseline))
    f = [future[s] for s in shared]
    b = [baseline[s] for s in shared]

    def diff(key: str, transform=lambda x: float(x)):
        return [transform(x[key]) - transform(y[key]) for x, y in zip(f, b)]

    zdiff = diff("zero_tardiness", int)
    cdiff = diff("completed", int)
    # Positive means FutureChoice reduces infeasible episodes.
    idiff = [int(y["infeasible"] > 0) - int(x["infeasible"] > 0) for x, y in zip(f, b)]
    # Positive means FutureChoice reduces tardiness.
    tdiff = [float(y["tardiness"]) - float(x["tardiness"]) for x, y in zip(f, b)]
    # Positive means FutureChoice consumes more energy.
    ediff = [float(x["energy"]) - float(y["energy"]) for x, y in zip(f, b)]
    bbetter = sum(int(x["zero_tardiness"] == 1 and y["zero_tardiness"] == 0) for x, y in zip(f, b))
    bworse = sum(int(x["zero_tardiness"] == 0 and y["zero_tardiness"] == 1) for x, y in zip(f, b))
    return {
        "n": len(shared),
        "zero_tardiness_rate_diff": bootstrap_mean_ci_linear(zdiff, seed=seed, resamples=10000),
        "completion_rate_diff": bootstrap_mean_ci_linear(cdiff, seed=seed + 1, resamples=10000),
        "infeasible_episode_reduction": bootstrap_mean_ci_linear(idiff, seed=seed + 2, resamples=10000),
        "tardiness_reduction": bootstrap_mean_ci_linear(tdiff, seed=seed + 3, resamples=10000),
        "energy_delta_future_minus_baseline": bootstrap_mean_ci_linear(ediff, seed=seed + 4, resamples=10000),
        "zero_tardiness_mcnemar": exact_mcnemar(bbetter, bworse),
        "future_zero_better": bbetter,
        "future_zero_equal": len(shared) - bbetter - bworse,
        "future_zero_worse": bworse,
    }


def search_stats(items: list[dict], policy: str) -> dict:
    depth = [r for r in items if r["policy"] == policy and r["method"] == "depth4" and r["status"] == "OK"]
    fc = [r for r in items if r["policy"] == policy and r["method"] == "future_choice" and r["status"] == "OK"]
    return {
        "depth4_partial_states_expanded": sum(int((r.get("search") or {}).get("partial_states_expanded", 0)) for r in depth),
        "future_choice_lower_search_expanded": sum(int(r.get("lower_search_expanded") or 0) for r in fc),
        "future_choice_exact_new_states": sum(int((r.get("adapter_metrics") or {}).get("exact_new_states", 0)) for r in fc),
        "future_choice_exact_calls": sum(int((r.get("adapter_metrics") or {}).get("exact_calls", 0)) for r in fc),
        "future_choice_carried_hits": sum(int((r.get("engine_metrics") or {}).get("carried_hits", 0)) for r in fc),
        "future_choice_upper_impossible": sum(int((r.get("engine_metrics") or {}).get("upper_impossible", 0)) for r in fc),
        "future_choice_total_search_proxy": sum(
            int(r.get("lower_search_expanded") or 0)
            + int((r.get("adapter_metrics") or {}).get("exact_new_states", 0))
            for r in fc
        ),
        "boundary": "depth4 partial expansions and FutureChoice lower/exact state counts are different operation units; do not translate their ratio into wall time",
    }


def analyze_constructive100(items: list[dict]) -> dict:
    by = paired_by_seed(items)
    result = {}
    for idx, policy in enumerate(POLICIES):
        methods = {}
        for method in METHODS:
            subset = list(by[(policy, method)].values())
            if len(subset) != 100:
                raise AssertionError((policy, method, len(subset)))
            methods[method] = {
                "zero_tardiness": binary_stats(subset, "zero_tardiness"),
                "completion": binary_stats(subset, "completed"),
                "infeasible_free": wilson_interval(sum(int(r["infeasible"] == 0) for r in subset), len(subset)),
                "mean_tardiness": sum(float(r["tardiness"]) for r in subset) / len(subset),
                "mean_energy": sum(float(r["energy"]) for r in subset) / len(subset),
            }
        result[policy] = {
            "methods": methods,
            "future_vs_depth4": paired_compare(by[(policy, "future_choice")], by[(policy, "depth4")], seed=20261009 + idx * 20),
            "future_vs_native": paired_compare(by[(policy, "future_choice")], by[(policy, "native")], seed=20261109 + idx * 20),
            "search": search_stats(items, policy),
        }
    return result


def analyze_paper50(items: list[dict], constructive: set[int]) -> dict:
    by = paired_by_seed(items)
    result = {}
    for policy in POLICIES:
        methods = {}
        for method in ("native", "depth4"):
            subset = list(by[(policy, method)].values())
            if len(subset) != 50:
                raise AssertionError((policy, method, len(subset)))
            methods[method] = {
                "zero_tardiness": binary_stats(subset, "zero_tardiness"),
                "completion": binary_stats(subset, "completed"),
                "infeasible_free": wilson_interval(sum(int(r["infeasible"] == 0) for r in subset), 50),
                "mean_tardiness": sum(float(r["tardiness"]) for r in subset) / 50,
            }
        fc = by[(policy, "future_choice")]
        if set(fc) != constructive:
            raise AssertionError((policy, sorted(fc), sorted(constructive)))
        methods["future_choice_constructive_subset"] = {
            "n": len(fc),
            "zero_tardiness": binary_stats(list(fc.values()), "zero_tardiness"),
            "completion": binary_stats(list(fc.values()), "completed"),
        }
        result[policy] = {
            "methods": methods,
            "constructive_subset_future_vs_depth4_descriptive": paired_compare(fc, by[(policy, "depth4")], seed=20262009),
            "note": "n=6 constructive subset: descriptive only; no broad significance claim",
        }
    return result


def main() -> int:
    c100agg = load(CONSTRUCTIVE100 / "aggregate.json")
    p50agg = load(PAPER50 / "aggregate.json")
    if not c100agg["complete"] or not p50agg["complete"]:
        raise AssertionError("scale panels incomplete")
    c100 = rows(CONSTRUCTIVE100 / "rows.jsonl")
    p50 = rows(PAPER50 / "rows.jsonl")
    cohorts = load(COHORTS)
    old = load(LEGACY_COHORT)["cohort"]
    new = cohorts["constructive_100"]["seeds"]
    constructive_paper = {int(x) for x in cohorts["paper_matched_50"]["constructive_seeds"]}

    payload = {
        "stage": "UAV_ATTENTION_N10_SCALE_STATISTICS",
        "checks": {
            "constructive100_complete_1200_rows": len(c100) == 1200,
            "paper50_complete_600_rows": len(p50) == 600,
            "legacy_21_exact_audited_cohort_is_constructive100_prefix": old == new[: len(old)],
            "paper50_exact_external_protocol_size": len(cohorts["paper_matched_50"]["layout_seeds"]) == 50,
            "paper50_constructive_lower_bound_count_6": len(constructive_paper) == 6,
        },
        "constructive100": analyze_constructive100(c100),
        "paper50": {
            "layout_count": 50,
            "constructive_hard_feasible_lower_bound_count": len(constructive_paper),
            "constructive_hard_feasible_lower_bound_rate": len(constructive_paper) / 50,
            "by_policy": analyze_paper50(p50, constructive_paper),
        },
        "claim_boundary": [
            "Constructive100 is a conservative hard-feasible cohort because every seed has an ordinary official-heuristic zero-tardiness witness before FutureChoice evaluation.",
            "The first 21 constructive100 seeds are exactly the frozen C2 cohort with 924/924 independent exact-frontier audits; the remaining 79 extend statistical scale without repeating pure-exact auditing.",
            "Paper50 exactly matches the external repository's 50-episode layout-seed protocol. Its six constructive seeds are only a lower bound on hard-feasible layouts; unlabelled layouts are not declared infeasible.",
            "FutureChoice on paper50 is reported only on the six constructive-witness layouts."
        ],
    }
    if not all(payload["checks"].values()):
        raise AssertionError(payload["checks"])
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# UAV N=10 Scale Extension",
        "",
        "## Constructive hard-feasible 100",
        "",
        "All 100 seeds were selected before FutureChoice evaluation by an official-heuristic zero-tardiness witness. The first 21 are exactly the previously frozen exact-audited cohort.",
        "",
        "| Policy | Native zero | Depth4 zero | FutureChoice zero | Native complete | Depth4 complete | Future complete | Depth4 infeasible | Future infeasible |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for policy in POLICIES:
        x = payload["constructive100"][policy]["methods"]
        lines.append(
            f"| {policy} | {x['native']['zero_tardiness']['success']}/100 | {x['depth4']['zero_tardiness']['success']}/100 | {x['future_choice']['zero_tardiness']['success']}/100 | "
            f"{x['native']['completion']['success']}/100 | {x['depth4']['completion']['success']}/100 | {x['future_choice']['completion']['success']}/100 | "
            f"{100-int(x['depth4']['infeasible_free']['success'])} | {100-int(x['future_choice']['infeasible_free']['success'])} |"
        )
    lines += [
        "",
        "## External-paper-matched 50",
        "",
        "The 50 layout seeds exactly follow the external repository's evaluate_policy RNG protocol (episodes=50, seed=999). Six layouts have an ordinary constructive zero-tardiness witness; FutureChoice is only evaluated on those six.",
        "",
        "Full Wilson intervals, paired bootstrap CIs, exact McNemar discordance, energy/tardiness deltas and search-work summaries are in `uav-attention-n10-scale-statistics.json`.",
    ]
    MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(OUT), "summary": str(MD), "checks": payload["checks"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
