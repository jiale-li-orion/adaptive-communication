#!/usr/bin/env python3
"""Full-cohort parity audit for the generic FutureChoiceEngine on C/N=10.

Historical C result generation used a domain-local orchestration loop.  This
audit keeps the frozen environment, cohort, heuristic ranking, set-MST U bound,
constructive-search limit and independent exact authority unchanged, but routes
all method decisions through the generic ``FutureChoiceEngine`` plus the formal
``UAVFutureChoiceAdapter``.

Passing this audit closes the code-path reuse gate without rewriting the
historical result artifacts that already support F5/F6.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
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
from uav_future_choice_adapter import UAVFutureChoiceAdapter  # noqa: E402


COHORT = ROOT / "results/transfer/uav-attention-n10-constructive-cohort.json"
FROZEN = ROOT / "results/transfer/uav-attention-set-mst-attribution.json"
OUT = ROOT / "results/transfer/uav-attention-generic-engine-n10-parity.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit-seeds", type=int, default=None)
    ap.add_argument(
        "--seed-list",
        default=None,
        help="Comma-separated explicit layout seeds. Overrides the frozen legacy cohort file.",
    )
    ap.add_argument(
        "--allow-infeasible-starts",
        action="store_true",
        help=(
            "Allow mixed panels containing layouts with no exact zero-tardiness full continuation. "
            "FutureChoice is not applied on those starts; native heuristic rollout is recorded instead."
        ),
    )
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
    _install_gymnasium_shim()
    ext = ROOT / "local_research/external/uav-attention-routing"
    sys.path.insert(0, str(ext))
    from src.env import SingleUAVConfig, SingleUAVEnv  # type: ignore
    from src.heuristic import (  # type: ignore
        BatteryAwareNearestNeighbour,
        GreedyDeadlineBatteryHeuristic,
        NearestDeadlineFirstHeuristic,
        NearestNeighbourHeuristic,
    )

    cohort_doc = _load(COHORT)
    frozen = _load(FROZEN)
    if args.seed_list:
        seeds = [int(x) for x in args.seed_list.split(",") if x.strip()]
    else:
        seeds = list(cohort_doc["cohort"])
    if args.limit_seeds is not None:
        seeds = seeds[: args.limit_seeds]

    policies = {
        "nearest_neighbour": NearestNeighbourHeuristic,
        "nearest_deadline": NearestDeadlineFirstHeuristic,
        "greedy_deadline_battery": GreedyDeadlineBatteryHeuristic,
        "battery_aware_nn": BatteryAwareNearestNeighbour,
    }
    mission_time, deadline_min, deadline_max = N_SETTINGS[10]

    def cfg():
        return SingleUAVConfig(
            num_customers=10,
            num_chargers=1,
            mission_time=mission_time,
            deadline_min=deadline_min,
            deadline_max=deadline_max,
            reward_mode="completion_ratio",
        )

    rows: list[dict[str, Any]] = []
    total_frontier_checks = 0
    total_mismatches = 0
    for seed in seeds:
        # Independent hard-feasible start check uses the older/basic exact
        # authority, not the set-MST method bound.
        probe = SingleUAVEnv(cfg())
        probe.reset(seed=seed)
        start_ref = FutureChoiceRouteFrontier(
            probe, lower_search_limit=0, upper_mode="basic"
        )
        start_route, _ = start_ref.exact_with_delta(start_ref.state(probe))
        hard_start = start_route is not None
        if not hard_start and not args.allow_infeasible_starts:
            raise AssertionError(f"frozen constructive cohort seed {seed} is not exact hard-feasible")

        for policy_name, policy_cls in policies.items():
            env = SingleUAVEnv(cfg())
            obs, info = env.reset(seed=seed)
            policy = policy_cls()
            method_front = FutureChoiceRouteFrontier(
                env, lower_search_limit=96, upper_mode="deadline_set_mst"
            )
            adapter = UAVFutureChoiceAdapter(method_front)
            engine = FutureChoiceEngine(adapter)
            exact_front = FutureChoiceRouteFrontier(
                env, lower_search_limit=0, upper_mode="basic"
            )
            frontier_checks = 0
            interventions = 0
            source_counts: Counter[str] = Counter()
            total_return = 0.0

            while True:
                native = env.get_action_mask()
                native_action = int(policy.act(env, obs, info))
                classifications = {}
                import numpy as np
                method_mask = np.zeros_like(native, dtype=bool)
                exact_mask = np.zeros_like(native, dtype=bool)
                if hard_start:
                    exact_state = exact_front.state(env)
                    for action, ok in enumerate(native):
                        if not bool(ok):
                            continue
                        cls = engine.classify(env, int(action))
                        classifications[int(action)] = cls
                        method_mask[action] = bool(cls.safe)
                        source_counts[cls.source] += 1

                        child = exact_front.post(exact_state, int(action))
                        exact_mask[action] = bool(
                            child is not None and exact_front.exact(child) is not None
                        )

                    frontier_checks += 1
                    total_frontier_checks += 1
                    if list(map(bool, method_mask)) != list(map(bool, exact_mask)):
                        total_mismatches += 1
                        raise AssertionError(
                            {
                                "seed": seed,
                                "policy": policy_name,
                                "method": list(map(bool, method_mask)),
                                "exact": list(map(bool, exact_mask)),
                            }
                        )

                    if method_mask.any():
                        use_info = dict(info)
                        use_info["action_mask"] = method_mask
                        action = int(policy.act(env, obs, use_info))
                        interventions += int(action != native_action)
                    else:
                        action = native_action

                    if action in classifications:
                        engine.commit(env, classifications[action])
                    else:
                        engine.clear()
                else:
                    action = native_action

                obs, reward, terminated, truncated, info = env.step(action)
                total_return += float(reward)
                if terminated or truncated:
                    break

            rows.append(
                {
                    "seed": seed,
                    "policy": policy_name,
                    "hard_feasible_start": int(hard_start),
                    "method_applied": bool(hard_start),
                    "zero_tardiness": int(float(info["ep_tardiness"]) <= 1e-9),
                    "completed": int(bool(info["completed"])),
                    "returned_to_depot": int(bool(info["returned_to_depot"])),
                    "infeasible": int(info["ep_infeasible"]),
                    "tardiness": float(info["ep_tardiness"]),
                    "energy": float(info["ep_energy"]),
                    "native_return": total_return,
                    "frontier_checks": frontier_checks,
                    "interventions": interventions,
                    "classification_sources": dict(sorted(source_counts.items())),
                    "engine_metrics": dict(engine.metrics),
                    "adapter_metrics": dict(adapter.metrics),
                }
            )

    by_policy = {}
    for policy_name in policies:
        subset = [r for r in rows if r["policy"] == policy_name]
        hard_subset = [r for r in subset if r["hard_feasible_start"]]
        by_policy[policy_name] = {
            "episodes": len(subset),
            "hard_feasible_seed_count": len(hard_subset),
            "zero_tardiness": sum(r["zero_tardiness"] for r in subset),
            "completed": sum(r["completed"] for r in subset),
            "infeasible": sum(r["infeasible"] > 0 for r in subset),
            "hard_zero_tardiness": sum(r["zero_tardiness"] for r in hard_subset),
            "hard_completed": sum(r["completed"] for r in hard_subset),
            "hard_infeasible": sum(r["infeasible"] > 0 for r in hard_subset),
            "frontier_checks": sum(r["frontier_checks"] for r in subset),
            "engine_metrics": {
                key: sum(int(r["engine_metrics"][key]) for r in subset)
                for key in next(iter(subset))["engine_metrics"]
            },
            "adapter_exact_new_states": sum(
                int(r["adapter_metrics"]["exact_new_states"]) for r in subset
            ),
        }

    full = args.limit_seeds is None and not args.seed_list and not args.allow_infeasible_starts
    checks = {
        "all_frontiers_match_independent_exact": total_mismatches == 0,
        "all_hard_feasible_episodes_zero_tardiness_complete": all(
            r["zero_tardiness"] == 1
            and r["completed"] == 1
            and r["returned_to_depot"] == 1
            and r["infeasible"] == 0
            for r in rows
            if r["hard_feasible_start"]
        ),
        "generic_engine_used_carried_certificates": (
            sum(int(r["engine_metrics"]["carried_hits"]) for r in rows) > 0
            if any(r["hard_feasible_start"] for r in rows)
            else True
        ),
    }
    if full:
        checks.update(
            {
                "full_21_seed_cohort": seeds == list(cohort_doc["cohort"]),
                "full_924_frontier_checks": total_frontier_checks == 924,
                "matches_frozen_set_mst_quality": all(
                    by_policy[p]["zero_tardiness"]
                    == int(frozen["n10"]["rows"][p]["n10_quality"]["set_mst_lu_zero_tardiness"])
                    and by_policy[p]["completed"]
                    == int(frozen["n10"]["rows"][p]["n10_quality"]["set_mst_lu_completed"])
                    and by_policy[p]["infeasible"]
                    == int(frozen["n10"]["rows"][p]["n10_quality"]["set_mst_lu_infeasible"])
                    for p in policies
                ),
            }
        )
    if not all(checks.values()):
        raise AssertionError(checks)

    payload = {
        "stage": "UAV_GENERIC_FUTURE_CHOICE_ENGINE_N10_PARITY",
        "cohort": seeds,
        "full_frozen_cohort": full,
        "method": {
            "engine": "FutureChoiceEngine",
            "adapter": "UAVFutureChoiceAdapter",
            "upper_mode": "deadline_set_mst",
            "lower_search_limit": 96,
            "exact_authority_upper_mode": "basic",
        },
        "allow_infeasible_starts": bool(args.allow_infeasible_starts),
        "frontier_checks": total_frontier_checks,
        "frontier_mismatches": total_mismatches,
        "by_policy": by_policy,
        "checks": checks,
        "rows": rows,
        "claim_boundary": [
            "This audit closes code-path parity: historical F5/F6 result artifacts remain unchanged and retain their original source lineage.",
            "The generic engine owns orchestration only; routing transitions, set-MST U bounds and replayable routes remain domain-specific adapter semantics.",
            "Search-work metrics are not wall-time claims."
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "out": str(args.out),
                "frontier_checks": total_frontier_checks,
                "by_policy": by_policy,
                **checks,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
