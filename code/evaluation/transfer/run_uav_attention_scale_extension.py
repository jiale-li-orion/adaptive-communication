#!/usr/bin/env python3
"""Resource-safe scale runner for C4/C5 in the frozen experiment matrix.

Panels
------
``paper50``
    Exact 50 layout seeds used by the external repository's published
    ``evaluate_policy(..., episodes=50, seed=999)`` protocol. Native heuristics
    and depth-4 receding run on all 50. FutureChoice runs only on the
    method-independent constructive-feasibility lower-bound subset; other rows
    are explicitly marked skipped rather than forcing an exact search on an
    unknown/possibly impossible start.

``constructive100``
    First 100 method-independent constructive hard-feasible seeds frozen from
    the 0..999 scan. Native, depth4 and generic set-MST FutureChoice all run on
    every seed.

Correctness is not re-proved at every frontier here. The frozen C2 21-seed
cohort already provides 924/924 independent exact-mask parity. This runner is
for scale/statistical stability and uses the formal FutureChoiceEngine +
UAVFutureChoiceAdapter core path.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gc
from hashlib import sha256
import json
import os
from pathlib import Path
import statistics
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
AGENTIC = ROOT / "code/evaluation/agentic"
TRANSFER = ROOT / "code/evaluation/transfer"
for _p in (AGENTIC, TRANSFER):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from future_choice_engine import FutureChoiceEngine  # noqa: E402
from run_uav_attention_future_choice_lu import (  # noqa: E402
    FutureChoiceRouteFrontier,
    N_SETTINGS,
    _install_gymnasium_shim,
)
from run_uav_attention_receding_baselines import RecedingMask  # noqa: E402
from uav_future_choice_adapter import UAVFutureChoiceAdapter  # noqa: E402


COHORTS = ROOT / "results/transfer/uav-attention-n10-scale-extension-cohorts.json"
EXT = ROOT / "local_research/external/uav-attention-routing"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _panel(panel: str, doc: dict) -> tuple[list[int], set[int]]:
    if panel == "paper50":
        seeds = [int(x) for x in doc["paper_matched_50"]["layout_seeds"]]
        constructive = {
            int(x) for x in doc["paper_matched_50"]["constructive_seeds"]
        }
        return seeds, constructive
    if panel == "constructive100":
        seeds = [int(x) for x in doc["constructive_100"]["seeds"]]
        return seeds, set(seeds)
    raise ValueError(panel)


def _read_rows(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    out = {}
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        rid = str(row["row_id"])
        if rid in out:
            raise RuntimeError(f"duplicate row_id {rid} at line {lineno}")
        out[rid] = row
    return out


def _append(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        fh.flush()


def _native_rollout(env, obs, info, policy) -> dict[str, Any]:
    total_return = 0.0
    while True:
        action = int(policy.act(env, obs, info))
        obs, reward, terminated, truncated, info = env.step(action)
        total_return += float(reward)
        if terminated or truncated:
            break
    return {"info": info, "native_return": total_return}


def _depth4_rollout(env, obs, info, policy) -> dict[str, Any]:
    mask = RecedingMask(env, 4)
    total_return = 0.0
    interventions = 0
    while True:
        native = env.get_action_mask()
        native_action = int(policy.act(env, obs, info))
        allowed = mask.mask(env, native)
        if allowed.any():
            use = dict(info)
            use["action_mask"] = allowed
            action = int(policy.act(env, obs, use))
            interventions += int(action != native_action)
        else:
            action = native_action
        obs, reward, terminated, truncated, info = env.step(action)
        total_return += float(reward)
        if terminated or truncated:
            break
    return {
        "info": info,
        "native_return": total_return,
        "interventions": interventions,
        "search": dict(mask.metrics),
    }


def _future_choice_rollout(env, obs, info, policy) -> dict[str, Any]:
    front = FutureChoiceRouteFrontier(
        env, lower_search_limit=96, upper_mode="deadline_set_mst"
    )
    adapter = UAVFutureChoiceAdapter(front)
    engine = FutureChoiceEngine(adapter)
    total_return = 0.0
    interventions = 0
    sources: Counter[str] = Counter()
    while True:
        native = env.get_action_mask()
        native_action = int(policy.act(env, obs, info))
        classifications = {}
        import numpy as np
        allowed = np.zeros_like(native, dtype=bool)
        for action, ok in enumerate(native):
            if not bool(ok):
                continue
            cls = engine.classify(env, int(action))
            classifications[int(action)] = cls
            allowed[action] = bool(cls.safe)
            sources[cls.source] += 1
        if allowed.any():
            use = dict(info)
            use["action_mask"] = allowed
            action = int(policy.act(env, obs, use))
            interventions += int(action != native_action)
        else:
            action = native_action
        if action in classifications:
            engine.commit(env, classifications[action])
        else:
            engine.clear()
        obs, reward, terminated, truncated, info = env.step(action)
        total_return += float(reward)
        if terminated or truncated:
            break
    result = {
        "info": info,
        "native_return": total_return,
        "interventions": interventions,
        "classification_sources": dict(sorted(sources.items())),
        "engine_metrics": dict(engine.metrics),
        "adapter_metrics": dict(adapter.metrics),
        "lower_search_expanded": int(front.metrics["lower_search_expanded"]),
    }
    # Bound cache lifetime to one episode.  Scale runs should not accumulate
    # exact-search states across unrelated layouts.
    front.exact.cache_clear()
    del engine, adapter, front
    gc.collect()
    return result


def _row(
    *, panel: str, seed: int, policy_name: str, method: str,
    constructive: bool, outcome: dict[str, Any] | None,
    status: str = "OK",
) -> dict[str, Any]:
    base = {
        "row_id": f"{panel}:seed-{seed}:{policy_name}:{method}",
        "panel": panel,
        "seed": seed,
        "policy": policy_name,
        "method": method,
        "constructive_hard_feasible_lower_bound": bool(constructive),
        "status": status,
    }
    if outcome is None:
        return base
    info = outcome["info"]
    base.update(
        {
            "zero_tardiness": int(float(info["ep_tardiness"]) <= 1e-9),
            "completed": int(bool(info["completed"])),
            "returned_to_depot": int(bool(info["returned_to_depot"])),
            "customers_served": int(info["customers_served"]),
            "infeasible": int(info["ep_infeasible"]),
            "tardiness": float(info["ep_tardiness"]),
            "energy": float(info["ep_energy"]),
            "native_return": float(outcome["native_return"]),
        }
    )
    for key in (
        "interventions", "search", "classification_sources", "engine_metrics",
        "adapter_metrics", "lower_search_expanded",
    ):
        if key in outcome:
            base[key] = outcome[key]
    return base


def _aggregate(panel: str, seeds: list[int], constructive: set[int], rows: dict[str, dict]):
    grouped = defaultdict(list)
    for row in rows.values():
        grouped[(row["policy"], row["method"])].append(row)
    summary = {}
    for (policy, method), items in sorted(grouped.items()):
        ok = [r for r in items if r["status"] == "OK"]
        hard = [r for r in ok if r["constructive_hard_feasible_lower_bound"]]
        summary[f"{policy}:{method}"] = {
            "rows": len(items),
            "ok": len(ok),
            "skipped": sum(r["status"].startswith("SKIPPED") for r in items),
            "hard_rows": len(hard),
            "zero_tardiness_all": sum(r.get("zero_tardiness", 0) for r in ok),
            "completed_all": sum(r.get("completed", 0) for r in ok),
            "infeasible_all": sum(r.get("infeasible", 0) > 0 for r in ok),
            "zero_tardiness_hard": sum(r.get("zero_tardiness", 0) for r in hard),
            "completed_hard": sum(r.get("completed", 0) for r in hard),
            "infeasible_hard": sum(r.get("infeasible", 0) > 0 for r in hard),
            "mean_tardiness_hard": (
                statistics.fmean(r["tardiness"] for r in hard) if hard else None
            ),
            "mean_energy_hard": (
                statistics.fmean(r["energy"] for r in hard) if hard else None
            ),
        }
    expected_per_seed = 4 * 3
    expected_rows = len(seeds) * expected_per_seed
    return {
        "stage": "UAV_ATTENTION_N10_SCALE_EXTENSION",
        "panel": panel,
        "seed_count": len(seeds),
        "constructive_hard_feasible_lower_bound_count": len(constructive),
        "expected_rows": expected_rows,
        "actual_rows": len(rows),
        "complete": len(rows) == expected_rows,
        "summary": summary,
        "claim_boundary": [
            "Scale runs do not repeat independent pure-exact frontier auditing; C2's frozen 924/924 exact parity is the correctness authority.",
            "For paper50, FutureChoice rows without a method-independent constructive feasibility witness are explicitly skipped, not counted as failures.",
            "Constructive feasibility is a lower-bound label: an unlabelled paper50 layout may still be hard-feasible."
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", choices=("paper50", "constructive100"), required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--max-new-seeds", type=int, default=None)
    args = ap.parse_args()

    for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ.setdefault(name, "1")
    _install_gymnasium_shim()
    sys.path.insert(0, str(EXT))
    from src.env import SingleUAVConfig, SingleUAVEnv  # type: ignore
    from src.heuristic import (  # type: ignore
        BatteryAwareNearestNeighbour,
        GreedyDeadlineBatteryHeuristic,
        NearestDeadlineFirstHeuristic,
        NearestNeighbourHeuristic,
    )

    doc = _load(COHORTS)
    seeds, constructive = _panel(args.panel, doc)
    policies = {
        "nearest_neighbour": NearestNeighbourHeuristic,
        "nearest_deadline": NearestDeadlineFirstHeuristic,
        "greedy_deadline_battery": GreedyDeadlineBatteryHeuristic,
        "battery_aware_nn": BatteryAwareNearestNeighbour,
    }
    mission_time, dmin, dmax = N_SETTINGS[10]

    def cfg():
        from src.env import SingleUAVConfig
        return SingleUAVConfig(
            num_customers=10, num_chargers=1, mission_time=mission_time,
            deadline_min=dmin, deadline_max=dmax, reward_mode="completion_ratio",
        )

    out_dir = args.out.resolve()
    rows_path = out_dir / "rows.jsonl"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "source-manifest.json"
    manifest = {
        "panel": args.panel,
        "cohorts_sha256": _sha(COHORTS),
        "runner_sha256": _sha(Path(__file__)),
        "generic_engine_sha256": _sha(ROOT / "code/evaluation/agentic/future_choice_engine.py"),
        "uav_adapter_sha256": _sha(ROOT / "code/evaluation/transfer/uav_future_choice_adapter.py"),
        "receding_sha256": _sha(ROOT / "code/evaluation/transfer/run_uav_attention_receding_baselines.py"),
    }
    if manifest_path.exists():
        if _load(manifest_path) != manifest:
            raise RuntimeError("scale-run source/cohort drift on resume")
    else:
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    existing = _read_rows(rows_path)
    completed_seeds = {
        seed for seed in seeds
        if all(
            f"{args.panel}:seed-{seed}:{policy}:{method}" in existing
            for policy in policies
            for method in ("native", "depth4", "future_choice")
        )
    }
    todo = [seed for seed in seeds if seed not in completed_seeds]
    if args.max_new_seeds is not None:
        todo = todo[: args.max_new_seeds]

    for seed in todo:
        is_constructive = seed in constructive
        for policy_name, policy_cls in policies.items():
            for method in ("native", "depth4", "future_choice"):
                rid = f"{args.panel}:seed-{seed}:{policy_name}:{method}"
                if rid in existing:
                    continue
                if method == "future_choice" and not is_constructive:
                    row = _row(
                        panel=args.panel, seed=seed, policy_name=policy_name,
                        method=method, constructive=False, outcome=None,
                        status="SKIPPED_NO_CONSTRUCTIVE_FEASIBILITY_WITNESS",
                    )
                else:
                    env = SingleUAVEnv(cfg())
                    obs, info = env.reset(seed=seed)
                    policy = policy_cls()
                    if method == "native":
                        outcome = _native_rollout(env, obs, info, policy)
                    elif method == "depth4":
                        outcome = _depth4_rollout(env, obs, info, policy)
                    else:
                        outcome = _future_choice_rollout(env, obs, info, policy)
                    row = _row(
                        panel=args.panel, seed=seed, policy_name=policy_name,
                        method=method, constructive=is_constructive, outcome=outcome,
                    )
                _append(rows_path, row)
                existing[rid] = row
        print(json.dumps({"panel": args.panel, "seed_done": seed}, sort_keys=True), flush=True)

    aggregate = _aggregate(args.panel, seeds, constructive, existing)
    (out_dir / "aggregate.json").write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"out": str(out_dir), **aggregate}, sort_keys=True))
    return 0 if aggregate["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
