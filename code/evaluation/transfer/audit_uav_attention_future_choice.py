#!/usr/bin/env python3
"""Find a native future-choice counterexample in uav-attention-routing.

External environment:
  mdehghani86/uav-attention-routing (2026), single UAV with customer
  deadlines, battery, charger and depot.

The released environment's ``get_action_mask`` checks only whether the *next*
node is reachable with current battery and remaining mission time.  This audit
keeps the external geometry/dynamics untouched and asks a stricter mission
question already implicit in the task: can all unserved customers still be
visited by their individual deadlines and can the UAV return to the depot?

For default N=5 instances, a small exact DFS is cheap enough to serve as an
evaluator-only continuation oracle.  We search for a seed where:

1. the initial state has at least one full hard-feasible completion route;
2. an action allowed by the released one-step mask is itself on-time;
3. after taking that action, no full hard-feasible continuation remains.

No new customer, deadline, energy model, action or reward is added.
"""
from __future__ import annotations

from functools import lru_cache
import json
import os
from pathlib import Path
import subprocess
import sys
import types


ROOT = Path(__file__).resolve().parents[3]
EXT = ROOT / "local_research/external/uav-attention-routing"


def _install_gymnasium_shim() -> None:
    """Only the space constructors / Env base are needed for environment import."""

    class Env:
        pass

    class _Space:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class Box(_Space):
        pass

    class Dict(_Space):
        pass

    class MultiBinary(_Space):
        pass

    class Discrete(_Space):
        pass

    spaces = types.SimpleNamespace(
        Box=Box, Dict=Dict, MultiBinary=MultiBinary, Discrete=Discrete
    )
    gym = types.ModuleType("gymnasium")
    gym.Env = Env
    gym.spaces = spaces
    sys.modules.setdefault("gymnasium", gym)
    sys.modules.setdefault("gymnasium.spaces", spaces)


def _git_head(path: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(path), "rev-parse", "HEAD"], text=True
        ).strip()
    except Exception:
        return None


def main() -> int:
    if not (EXT / "src/env.py").exists():
        raise SystemExit(f"missing local external checkout: {EXT}")

    # Avoid BLAS fan-out on the small WSL worker.
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

    def inspect_seed(seed: int):
        # Use the paper experiment's N=5 evaluation setting from
        # experiments/exp_common.py, not env.py's deliberately loose demo
        # defaults (mission_time=500, deadlines 80..250).
        cfg = SingleUAVConfig(
            num_customers=5,
            num_chargers=1,
            mission_time=15,
            deadline_min=3,
            deadline_max=12,
        )
        env = SingleUAVEnv(cfg)
        _obs, info = env.reset(seed=seed)

        n = cfg.num_customers
        all_mask = (1 << n) - 1
        charger_ids = tuple(sorted(env.charger_nodes))
        pos = env.node_positions.copy()
        deadlines = {nid: float(node.deadline) for nid, node in env.service_nodes.items()}

        def dist(a: int, b: int) -> float:
            import numpy as np
            return float(np.linalg.norm(pos[a] - pos[b]))

        def travel(a: int, b: int):
            d = dist(a, b)
            return d * cfg.battery_per_meter, d / cfg.drone_speed

        # Continuous battery values come from a finite set of deterministic path
        # sums / charger resets. Millijoule-ish precision is far below any decision
        # boundary in this toy environment while keeping memo keys stable.
        def q(x: float) -> float:
            return round(float(x), 7)

        @lru_cache(maxsize=None)
        def feasible(cur: int, visited: int, battery_q: float, elapsed_q: float):
            battery = float(battery_q)
            elapsed = float(elapsed_q)
            if visited == all_mask:
                e, t = travel(cur, 0)
                if e <= battery + 1e-9 and elapsed + t <= cfg.mission_time + 1e-9:
                    return (cur, 0)
                return None

            # Earliest-deadline ordering is only branch ordering, not pruning.
            customer_actions = [
                1 + i for i in range(n) if not (visited & (1 << i))
            ]
            customer_actions.sort(key=lambda nid: deadlines[nid])
            actions = customer_actions + [c for c in charger_ids if c != cur]
            for a in actions:
                e, t = travel(cur, a)
                if e > battery + 1e-9 or elapsed + t > cfg.mission_time + 1e-9:
                    continue
                nb = battery - e
                nt = elapsed + t
                nv = visited
                if 1 <= a <= n:
                    if nt > deadlines[a] + 1e-9:
                        continue
                    nv |= 1 << (a - 1)
                else:
                    nt += cfg.charger_time_cost
                    if nt > cfg.mission_time + 1e-9:
                        continue
                    nb = min(cfg.battery_capacity, nb + cfg.recharge_rate)
                sub = feasible(a, nv, q(nb), q(nt))
                if sub is not None:
                    return (cur,) + sub
            return None

        initial_route = feasible(0, 0, q(cfg.battery_capacity), q(0.0))
        if initial_route is None:
            return None

        native_mask = info["action_mask"]
        destructive = []
        for a in range(1, 1 + n):
            if not bool(native_mask[a]):
                continue
            e, t = travel(0, a)
            if t > deadlines[a] + 1e-9:
                continue
            cont = feasible(
                a,
                1 << (a - 1),
                q(cfg.battery_capacity - e),
                q(t),
            )
            if cont is None:
                destructive.append(
                    {
                        "action": a,
                        "customer_deadline": deadlines[a],
                        "travel_time": t,
                        "travel_energy": e,
                        "distance": dist(0, a),
                    }
                )
        if not destructive:
            return None

        destructive.sort(key=lambda row: (row["distance"], row["action"]))
        bad = destructive[0]
        destructive_actions = {int(row["action"]) for row in destructive}
        heuristic_actions = {}
        for cls in (
            NearestNeighbourHeuristic,
            NearestDeadlineFirstHeuristic,
            GreedyDeadlineBatteryHeuristic,
            BatteryAwareNearestNeighbour,
        ):
            policy = cls()
            action = int(policy.act(env, _obs, info))
            heuristic_actions[cls.__name__] = action
        heuristic_failures = sorted(
            name for name, action in heuristic_actions.items()
            if action in destructive_actions
        )
        return {
            "seed": seed,
            "initial_full_completion_route": list(initial_route),
            "native_action_mask_true": [
                int(i) for i, ok in enumerate(native_mask) if bool(ok)
            ],
            "official_heuristic_first_actions": heuristic_actions,
            "official_heuristics_selecting_destructive_action": heuristic_failures,
            "destructive_allowed_action": bad,
            "all_destructive_allowed_customer_actions": destructive,
            "customer_deadlines": {str(k): v for k, v in deadlines.items()},
            "node_positions": pos.tolist(),
            "battery_capacity": cfg.battery_capacity,
            "mission_time": cfg.mission_time,
        }

    witness = None
    first_mask_witness = None
    scanned = 0
    for seed in range(500):
        scanned += 1
        row = inspect_seed(seed)
        if row is None:
            continue
        if first_mask_witness is None:
            first_mask_witness = row
        if row["official_heuristics_selecting_destructive_action"]:
            witness = row
            break
    if witness is None:
        witness = first_mask_witness

    native_replay = None
    if witness is not None:
        replay_seed = int(witness["seed"])

        def rollout(policy=None, route=None):
            cfg = SingleUAVConfig(
                num_customers=5,
                num_chargers=1,
                mission_time=15,
                deadline_min=3,
                deadline_max=12,
                reward_mode="completion_ratio",
            )
            env = SingleUAVEnv(cfg)
            obs, info = env.reset(seed=replay_seed)
            actions = []
            total_reward = 0.0
            route_index = 0
            while True:
                if route is not None:
                    if route_index >= len(route):
                        break
                    action = int(route[route_index])
                    route_index += 1
                else:
                    action = int(policy.act(env, obs, info))
                actions.append(action)
                obs, reward, terminated, truncated, info = env.step(action)
                total_reward += float(reward)
                if terminated or truncated:
                    break
            return {
                "actions": actions,
                "completed": bool(info["completed"]),
                "returned_to_depot": bool(info["returned_to_depot"]),
                "customers_served": int(info["customers_served"]),
                "tardiness": float(info["ep_tardiness"]),
                "elapsed_time": float(info["elapsed_time"]),
                "energy": float(info["ep_energy"]),
                "infeasible_count": int(info["ep_infeasible"]),
                "native_return": float(total_reward),
            }

        heuristic_rollouts = {}
        for cls in (
            NearestNeighbourHeuristic,
            NearestDeadlineFirstHeuristic,
            GreedyDeadlineBatteryHeuristic,
            BatteryAwareNearestNeighbour,
        ):
            heuristic_rollouts[cls.__name__] = rollout(policy=cls())

        exact_actions = list(witness["initial_full_completion_route"])[1:]
        native_replay = {
            "seed": replay_seed,
            "reward_mode": "completion_ratio",
            "official_heuristics": heuristic_rollouts,
            "hard_feasible_route": rollout(route=exact_actions),
            "checks": {
                "hard_feasible_route_zero_tardiness": None,
                "hard_feasible_route_completed_and_returned": None,
                "at_least_one_official_heuristic_has_avoidable_tardiness_or_failure": None,
            },
        }
        hard = native_replay["hard_feasible_route"]
        native_replay["checks"]["hard_feasible_route_zero_tardiness"] = (
            abs(float(hard["tardiness"])) <= 1e-9
        )
        native_replay["checks"]["hard_feasible_route_completed_and_returned"] = (
            hard["completed"] and hard["returned_to_depot"]
        )
        native_replay["checks"][
            "at_least_one_official_heuristic_has_avoidable_tardiness_or_failure"
        ] = any(
            (float(row["tardiness"]) > 1e-9)
            or (not row["completed"])
            or (not row["returned_to_depot"])
            or (int(row["infeasible_count"]) > 0)
            for row in heuristic_rollouts.values()
        )

    payload = {
        "stage": "UAV_ATTENTION_NATIVE_FUTURE_CHOICE_AUDIT",
        "external_repo": "mdehghani86/uav-attention-routing",
        "external_commit": _git_head(EXT),
        "external_experiment_setting": {
            "num_customers": 5,
            "mission_time": 15,
            "deadline_min": 3,
            "deadline_max": 12,
            "source": "experiments/exp_common.py::N_SETTINGS[5]",
        },
        "seeds_scanned": scanned,
        "witness_found": witness is not None,
        "official_heuristic_failure_found": bool(
            witness and witness["official_heuristics_selecting_destructive_action"]
        ),
        "witness": witness,
        "native_replay": native_replay,
        "checks": {
            "native_task_has_deadlines": True,
            "native_task_has_persistent_battery": True,
            "native_mask_is_one_step_only": True,
            "full_feasible_state_with_destructive_native_allowed_action": witness is not None,
            "native_replay_confirms_avoidable_tardiness_or_failure": bool(
                native_replay
                and all(native_replay["checks"].values())
            ),
        },
        "claim_boundary": [
            "The exact DFS is evaluator-only and interprets the external environment's native per-customer deadlines as hard operational obligations; the released environment itself allows tardy service and reports tardiness as a KPI rather than making zero tardiness part of its native completed flag.",
            "No new mission obligation or external-environment transition is introduced.",
            "The audit tests the released one-step action mask and official heuristic baselines; it does not claim the released learned PPO policy selects the destructive action without separately evaluating that checkpoint/policy.",
            "Native rollout metrics are reported under the external environment's own completion_ratio reward and tardiness/infeasibility fields; the hard-feasible route is not assigned a custom reward.",
            "A witness establishes an external-domain continuation-awareness gap, not superiority of the current Layer-2 implementation."
        ],
    }
    assert payload["checks"]["full_feasible_state_with_destructive_native_allowed_action"], payload
    out = ROOT / "local_research/current/transfer/uav-attention-native-future-choice.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "out": str(out),
                "witness_found": payload["witness_found"],
                "seeds_scanned": scanned,
                "seed": None if witness is None else witness["seed"],
                "official_heuristic_failure_found": payload["official_heuristic_failure_found"],
                "heuristic_failures": None if witness is None else witness["official_heuristics_selecting_destructive_action"],
                "destructive_action": None if witness is None else witness["destructive_allowed_action"],
                "initial_route": None if witness is None else witness["initial_full_completion_route"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
