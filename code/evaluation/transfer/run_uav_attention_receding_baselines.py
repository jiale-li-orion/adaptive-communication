#!/usr/bin/env python3
"""Strong finite-horizon receding baselines for the external UAV mission.

Each official heuristic is evaluated with an optimistic depth-k action mask.
An action survives when there exists a legal/on-time partial continuation for
``k`` actions and the terminal partial state still passes the same sound
optimistic necessary conditions used by the L/U future-choice method.

This baseline deliberately does *not* prove a full completion continuation and
does not use exact fallback.  It therefore tests whether the gain from the
future-choice shield is reducible to ordinary short-horizon lookahead.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import statistics
import sys


ROOT = Path(__file__).resolve().parents[3]
TRANSFER = ROOT / "code/evaluation/transfer"
if str(TRANSFER) not in sys.path:
    sys.path.insert(0, str(TRANSFER))

from run_uav_attention_future_choice_lu import (  # noqa: E402
    FutureChoiceRouteFrontier,
    N_SETTINGS,
    _git_head,
    _install_gymnasium_shim,
)


EXT = ROOT / "local_research/external/uav-attention-routing"


class RecedingMask:
    def __init__(self, env, depth: int):
        self.front = FutureChoiceRouteFrontier(env, lower_search_limit=0)
        self.depth = int(depth)
        self.metrics = {
            "mask_calls": 0,
            "actions_checked": 0,
            "partial_states_expanded": 0,
            "actions_pruned": 0,
        }

    def _terminal_or_optimistic(self, state) -> bool:
        if state.visited == self.front.all_mask:
            if state.current == 0:
                return True
            return self.front.post(state, 0) is not None
        return self.front.upper_possible(state)

    def _exists(self, state, remaining_depth: int) -> bool:
        if not self._terminal_or_optimistic(state):
            return False
        if remaining_depth <= 0:
            return True
        if state.visited == self.front.all_mask:
            return True
        self.metrics["partial_states_expanded"] += 1
        for action in self.front._candidate_actions(state):
            child = self.front.post(state, action)
            if child is None:
                continue
            if self._exists(child, remaining_depth - 1):
                return True
        return False

    def mask(self, env, native_mask):
        import numpy as np
        self.metrics["mask_calls"] += 1
        state = self.front.state(env)
        out = np.zeros_like(native_mask, dtype=bool)
        for action, ok in enumerate(native_mask):
            if not bool(ok):
                continue
            self.metrics["actions_checked"] += 1
            child = self.front.post(state, int(action))
            keep = child is not None and self._exists(child, self.depth - 1)
            if keep:
                out[action] = True
            else:
                self.metrics["actions_pruned"] += 1
        return out


def mean(rows, key):
    return float(statistics.fmean(float(row[key]) for row in rows))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=1000)
    ap.add_argument("--customers", type=int, default=5, choices=sorted(N_SETTINGS))
    ap.add_argument("--depths", default="1,2,3")
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT / "results/transfer/uav-attention-receding-baselines-n5.json",
    )
    args = ap.parse_args()
    depths = [int(x) for x in args.depths.split(",") if x.strip()]

    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    _install_gymnasium_shim()
    sys.path.insert(0, str(EXT))

    from src.env import SingleUAVConfig, SingleUAVEnv  # type: ignore
    from src.heuristic import (  # type: ignore
        BatteryAwareNearestNeighbour,
        GreedyDeadlineBatteryHeuristic,
        NearestDeadlineFirstHeuristic,
        NearestNeighbourHeuristic,
    )

    heuristics = {
        "nearest_neighbour": NearestNeighbourHeuristic,
        "nearest_deadline": NearestDeadlineFirstHeuristic,
        "greedy_deadline_battery": GreedyDeadlineBatteryHeuristic,
        "battery_aware_nn": BatteryAwareNearestNeighbour,
    }

    mission_time,deadline_min,deadline_max=N_SETTINGS[args.customers]
    def cfg():
        return SingleUAVConfig(
            num_customers=args.customers,
            num_chargers=1,
            mission_time=mission_time,
            deadline_min=deadline_min,
            deadline_max=deadline_max,
            reward_mode="completion_ratio",
        )

    rows = []
    for seed in range(args.seeds):
        probe = SingleUAVEnv(cfg())
        probe.reset(seed=seed)
        oracle = FutureChoiceRouteFrontier(probe, lower_search_limit=0)
        start_route, _ = oracle.exact_with_delta(oracle.state(probe))
        hard_start = start_route is not None

        for pname, pcls in heuristics.items():
            for depth in depths:
                env = SingleUAVEnv(cfg())
                obs, info = env.reset(seed=seed)
                policy = pcls()
                receding = RecedingMask(env, depth)
                interventions = 0
                total_return = 0.0
                while True:
                    native = env.get_action_mask()
                    native_action = int(policy.act(env, obs, info))
                    if hard_start:
                        mask = receding.mask(env, native)
                        if mask.any():
                            use = dict(info)
                            use["action_mask"] = mask
                            action = int(policy.act(env, obs, use))
                            interventions += int(action != native_action)
                        else:
                            action = native_action
                    else:
                        action = native_action
                    obs, reward, terminated, truncated, info = env.step(action)
                    total_return += float(reward)
                    if terminated or truncated:
                        break

                rows.append(
                    {
                        "seed": seed,
                        "policy": pname,
                        "depth": depth,
                        "hard_feasible_start": int(hard_start),
                        "zero_tardiness": int(float(info["ep_tardiness"]) <= 1e-9),
                        "completed": int(bool(info["completed"])),
                        "returned_to_depot": int(bool(info["returned_to_depot"])),
                        "customers_served": int(info["customers_served"]),
                        "infeasible": int(info["ep_infeasible"]),
                        "tardiness": float(info["ep_tardiness"]),
                        "energy": float(info["ep_energy"]),
                        "native_return": total_return,
                        "interventions": interventions,
                        **receding.metrics,
                    }
                )

    summary = {}
    for pname in heuristics:
        for depth in depths:
            subset = [
                row for row in rows
                if row["policy"] == pname and row["depth"] == depth and row["hard_feasible_start"]
            ]
            key = f"{pname}:depth{depth}"
            summary[key] = {
                "hard_feasible_seed_count": len(subset),
                "zero_tardiness": sum(row["zero_tardiness"] for row in subset),
                "completed": sum(row["completed"] for row in subset),
                "infeasible": sum(row["infeasible"] > 0 for row in subset),
                "mean_tardiness": mean(subset, "tardiness") if subset else None,
                "mean_energy": mean(subset, "energy") if subset else None,
                "interventions": sum(row["interventions"] for row in subset),
                "partial_states_expanded": sum(row["partial_states_expanded"] for row in subset),
                "actions_pruned": sum(row["actions_pruned"] for row in subset),
            }

    payload = {
        "stage": "UAV_ATTENTION_RECEDING_MASK_BASELINES",
        "external_repo": "mdehghani86/uav-attention-routing",
        "external_commit": _git_head(EXT),
        "setting": {
            "num_customers": args.customers,
            "mission_time": mission_time,
            "deadline_min": deadline_min,
            "deadline_max": deadline_max,
            "seed_range": [0, args.seeds - 1],
            "depths": depths,
        },
        "summary": summary,
        "rows": rows,
        "claim_boundary": [
            "The receding mask is optimistic: it only requires a legal/on-time k-step partial continuation plus terminal necessary conditions, not a full mission completion certificate.",
            "This is an ordinary finite-horizon control baseline, not a future-choice exact fallback method.",
            "Paired comparison must be restricted to initial hard-feasible episodes, exactly as in the exact/L-U shield experiments.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(args.out), "summary": summary}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
