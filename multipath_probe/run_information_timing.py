"""代表条件的信息获取/返回时序对照；保存逐种子指标。"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from env import generate_trace  # noqa: E402
from information_timing import run_arm  # noqa: E402


ARMS = ("history_only", "data_ack", "paid_probe", "current_truth")
METRICS = (
    "event_rate", "routine_rate", "attempts", "probe_attempts", "energy",
    "money", "sat_quota_used", "wasted_bad_path", "same_epoch_reroutes",
)
T975 = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447,
    7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179,
    13: 2.160, 14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110,
    18: 2.101, 19: 2.093, 20: 2.086,
}


def t975(df: int) -> float:
    for key in sorted(T975):
        if df <= key:
            return T975[key]
    return 1.96


def paired(rows_a: list[dict], rows_b: list[dict], metric: str) -> dict:
    """b-a；交付率换算为百分点。"""
    assert [row["seed"] for row in rows_a] == [row["seed"] for row in rows_b]
    scale = 100.0 if metric.endswith("_rate") else 1.0
    differences = [(b[metric] - a[metric]) * scale for a, b in zip(rows_a, rows_b)]
    mean = sum(differences) / len(differences)
    variance = sum((value - mean) ** 2 for value in differences) / (len(differences) - 1)
    half = t975(len(differences) - 1) * math.sqrt(variance / len(differences))
    return {
        "direction": "second_minus_first",
        "mean": mean,
        "lo": mean - half,
        "hi": mean + half,
        "win": sum(value > 1e-12 for value in differences),
        "tie": sum(abs(value) <= 1e-12 for value in differences),
        "loss": sum(value < -1e-12 for value in differences),
        "differences": differences,
    }


def summarize_ledger(result: dict) -> dict:
    actions = result["action_ledger"]
    reroutes = 0
    probe_informed = 0
    for previous, current in zip(actions, actions[1:]):
        if previous["t"] == current["t"] and not previous["success"] and previous["path"] != current["path"]:
            if previous["kind"] == "data" and current["kind"] == "data":
                reroutes += 1
            if previous["kind"] == "probe" and current["kind"] == "data":
                probe_informed += 1
    result["same_epoch_reroutes"] = reroutes
    result["probe_informed_reroutes"] = probe_informed
    result["epochs_with_actions"] = len({item["t"] for item in actions})
    result.pop("action_ledger")
    result.pop("evidence_ledger")
    return result


def run_condition(seeds: int, budget: float | None, event_multiplier: float = 3.0) -> dict:
    per_seed = {arm: [] for arm in ARMS}
    for seed in range(seeds):
        trace = generate_trace(seed=seed, K=3, burst="chirpbox", T=336)
        for arm in ARMS:
            result = summarize_ledger(run_arm(
                trace, arm, budget, probe_cost_multiplier=1.0,
                event_energy_multiplier=event_multiplier,
            ))
            result["seed"] = seed
            per_seed[arm].append(result)
    comparisons = {}
    for label, first, second in (
        ("data_ack_minus_history_only", "history_only", "data_ack"),
        ("paid_probe_minus_data_ack", "data_ack", "paid_probe"),
        ("current_truth_minus_data_ack", "data_ack", "current_truth"),
    ):
        comparisons[label] = {
            metric: paired(per_seed[first], per_seed[second], metric) for metric in METRICS
        }
    means = {
        arm: {metric: sum(row[metric] for row in rows) / len(rows) for metric in METRICS}
        for arm, rows in per_seed.items()
    }
    return {"means": means, "comparisons": comparisons, "per_seed": per_seed}


def run_aggressiveness_grid(seeds: int, budget: float, alphas=(2.0, 3.0, 4.0, 6.0)) -> dict:
    """首轮出现服务/成本取舍后使用的有限诊断网格，不作为预注册主比较。"""
    grid = {}
    for alpha in alphas:
        key = f"alpha{alpha:g}"
        grid[key] = {}
        for arm in ("history_only", "data_ack"):
            rows = []
            for seed in range(seeds):
                trace = generate_trace(seed=seed, K=3, burst="chirpbox", T=336)
                result = summarize_ledger(run_arm(
                    trace, arm, budget, event_energy_multiplier=alpha,
                ))
                result["seed"] = seed
                rows.append(result)
            grid[key][arm] = {
                "means": {metric: sum(row[metric] for row in rows) / len(rows) for metric in METRICS},
                "per_seed": rows,
            }
    return grid


def run_feedback_batch_grid(seeds: int, budget: float, sizes=(1, 2, 3, 6)) -> dict:
    """ACK 噪声下的普通聚合基线；用于解释逐包更新的事件损失。"""
    grid = {}
    for size in sizes:
        rows = []
        for seed in range(seeds):
            trace = generate_trace(seed=seed, K=3, burst="chirpbox", T=336)
            result = summarize_ledger(run_arm(
                trace, "data_ack", budget, feedback_batch_size=size,
            ))
            result["seed"] = seed
            rows.append(result)
        grid[f"batch{size}"] = {
            "means": {metric: sum(row[metric] for row in rows) / len(rows) for metric in METRICS},
            "per_seed": rows,
        }
    return grid


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--out", default=os.path.join(HERE, "results", "information_timing.json"))
    args = parser.parse_args()
    output = {
        "schema": "information-timing-v1",
        "created": "2026-09-14",
        "scope": {"K": 3, "burst": "chirpbox", "T": 336, "seeds": args.seeds},
        "timing": [
            "arrive_and_expire", "optional_probe", "probe_result", "data_attempt",
            "data_ack", "next_same_epoch_choice", "advance_one_hour",
        ],
        "interface_assumption": "probe and data ACK return before the next same-epoch choice (A-level)",
        "probe_cost": "one path transmission: same cap, energy, money, and satellite quota as data",
        "conditions": {
            "budget1950": run_condition(args.seeds, 1950.0),
            "loose": run_condition(args.seeds, None),
        },
        "posthoc_aggressiveness_grid": {
            "reason": "the fixed-alpha comparison exposed an event-service versus cost tradeoff",
            "status": "diagnostic, not preregistered",
            "budget1950": run_aggressiveness_grid(args.seeds, 1950.0),
        },
        "posthoc_feedback_batch_grid": {
            "reason": "one noisy ACK caused immediate Bayesian reallocation and reduced event reliability",
            "status": "ordinary-rule diagnostic, not a proposed method",
            "budget1950": run_feedback_batch_grid(args.seeds, 1950.0),
        },
    }
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    for condition, block in output["conditions"].items():
        print(f"[{condition}]")
        for arm in ARMS:
            means = block["means"][arm]
            print(f"  {arm:14s} event={means['event_rate']*100:6.2f}% "
                  f"routine={means['routine_rate']*100:6.2f}% attempts={means['attempts']:7.1f} "
                  f"probe={means['probe_attempts']:5.1f} energy={means['energy']:8.2f}")
        for label, comparison in block["comparisons"].items():
            event = comparison["event_rate"]
            print(f"  {label}: event {event['mean']:+.2f}pp "
                  f"[{event['lo']:+.2f},{event['hi']:+.2f}] "
                  f"W/T/L={event['win']}/{event['tie']}/{event['loss']}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
