#!/usr/bin/env python3
"""Evaluate continuation-aware shielding on the public UAV deadline environment.

The external policy is never modified.  At each decision boundary we intersect
the released one-step action mask with an evaluator-side exact mask containing
only actions that still admit a zero-tardiness completion of every unvisited
customer followed by depot return under the environment's native battery,
charger and mission-time dynamics.

This is a transfer experiment, not a claim that the external paper defines
deadlines as hard completion semantics.  Native environment KPIs -- tardiness,
served customers, infeasible actions, energy and depot return -- are reported
for both the original and shielded versions of the same official heuristics.
"""
from __future__ import annotations

from functools import lru_cache
import argparse
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import types
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
EXT = ROOT / "local_research/external/uav-attention-routing"


def _install_gymnasium_shim() -> None:
    class Env:
        pass

    class _Space:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class Box(_Space): pass
    class Dict(_Space): pass
    class MultiBinary(_Space): pass
    class Discrete(_Space):
        def __init__(self, n, *args, **kwargs):
            super().__init__(n, *args, **kwargs)
            self.n = n

    spaces = types.SimpleNamespace(Box=Box, Dict=Dict, MultiBinary=MultiBinary, Discrete=Discrete)
    gym = types.ModuleType("gymnasium")
    gym.Env = Env
    gym.spaces = spaces
    sys.modules.setdefault("gymnasium", gym)
    sys.modules.setdefault("gymnasium.spaces", spaces)


def _git_head(path: Path) -> str | None:
    try:
        return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return None


class ContinuationOracle:
    def __init__(self, env):
        self.cfg = env.config
        self.pos = env.node_positions.copy()
        self.deadlines = {nid: float(node.deadline) for nid, node in env.service_nodes.items()}
        self.chargers = tuple(sorted(env.charger_nodes))
        self.n = int(self.cfg.num_customers)
        self.all_mask = (1 << self.n) - 1
        self.safe_mask_calls = 0
        self.actions_checked = 0
        self.actions_pruned = 0

    @staticmethod
    def q(x: float) -> float:
        return round(float(x), 7)

    def dist(self, a: int, b: int) -> float:
        import numpy as np
        return float(np.linalg.norm(self.pos[a] - self.pos[b]))

    def travel(self, a: int, b: int) -> tuple[float, float]:
        d = self.dist(a, b)
        return d * self.cfg.battery_per_meter, d / self.cfg.drone_speed

    @lru_cache(maxsize=None)
    def continuation(self, cur: int, visited: int, battery_q: float, elapsed_q: float):
        battery = float(battery_q)
        elapsed = float(elapsed_q)
        if visited == self.all_mask:
            e, t = self.travel(cur, 0)
            if e <= battery + 1e-9 and elapsed + t <= self.cfg.mission_time + 1e-9:
                return (cur, 0)
            return None

        customer_actions = [1 + i for i in range(self.n) if not (visited & (1 << i))]
        customer_actions.sort(key=lambda nid: (self.deadlines[nid], nid))
        actions = customer_actions + [c for c in self.chargers if c != cur]
        for action in actions:
            e, t = self.travel(cur, action)
            if e > battery + 1e-9 or elapsed + t > self.cfg.mission_time + 1e-9:
                continue
            nb = battery - e
            nt = elapsed + t
            nv = visited
            if 1 <= action <= self.n:
                if nt > self.deadlines[action] + 1e-9:
                    continue
                nv |= 1 << (action - 1)
            else:
                nt += self.cfg.charger_time_cost
                if nt > self.cfg.mission_time + 1e-9:
                    continue
                nb = min(self.cfg.battery_capacity, nb + self.cfg.recharge_rate)
            sub = self.continuation(action, nv, self.q(nb), self.q(nt))
            if sub is not None:
                return (cur,) + sub
        return None

    def visited_bits(self, env) -> int:
        out = 0
        for i, value in enumerate(env.visited_mask):
            if int(value):
                out |= 1 << i
        return out

    def action_preserves(self, env, action: int) -> bool:
        cur = int(env.current_node)
        visited = self.visited_bits(env)
        battery = float(env.battery)
        elapsed = float(env.elapsed_time)
        if action == cur:
            return False
        e, t = self.travel(cur, action)
        if e > battery + 1e-9 or elapsed + t > self.cfg.mission_time + 1e-9 or t <= 0:
            return False
        nb = battery - e
        nt = elapsed + t
        nv = visited
        if 1 <= action <= self.n:
            if visited & (1 << (action - 1)):
                return False
            if nt > self.deadlines[action] + 1e-9:
                return False
            nv |= 1 << (action - 1)
        elif action in self.chargers:
            nt += self.cfg.charger_time_cost
            if nt > self.cfg.mission_time + 1e-9:
                return False
            nb = min(self.cfg.battery_capacity, nb + self.cfg.recharge_rate)
        elif action == 0:
            # Direct depot is only useful once all customers are served. Under
            # Euclidean travel it cannot improve a pre-completion continuation.
            if visited != self.all_mask:
                return False
            return True
        else:
            return False
        return self.continuation(action, nv, self.q(nb), self.q(nt)) is not None

    def safe_mask(self, env, native_mask):
        import numpy as np
        self.safe_mask_calls += 1
        out = np.zeros_like(native_mask, dtype=bool)
        for action, native_ok in enumerate(native_mask):
            if not bool(native_ok):
                continue
            self.actions_checked += 1
            if self.action_preserves(env, int(action)):
                out[action] = True
            else:
                self.actions_pruned += 1
        return out


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def mean(key: str) -> float:
        return float(statistics.fmean(float(row[key]) for row in rows))
    return {
        "episodes": len(rows),
        "hard_feasible_start_rate": mean("hard_feasible_start"),
        "zero_tardiness_rate": mean("zero_tardiness"),
        "completed_rate": mean("completed"),
        "returned_rate": mean("returned_to_depot"),
        "mean_customers_served": mean("customers_served"),
        "mean_tardiness": mean("tardiness"),
        "mean_infeasible": mean("infeasible"),
        "mean_energy": mean("energy"),
        "mean_native_return": mean("native_return"),
        "mean_shield_interventions": mean("shield_interventions"),
        "mean_actions_pruned": mean("actions_pruned"),
        "mean_oracle_cache_states": mean("oracle_cache_states"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=200, help="evaluate seeds 0..N-1")
    ap.add_argument("--out", type=Path, default=ROOT / "results/transfer/uav-attention-continuation-shield-n5.json")
    args = ap.parse_args()

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

    def cfg():
        return SingleUAVConfig(
            num_customers=5,
            num_chargers=1,
            mission_time=15,
            deadline_min=3,
            deadline_max=12,
            reward_mode="completion_ratio",
        )

    rows = []
    for seed in range(args.seeds):
        probe = SingleUAVEnv(cfg())
        _obs, _info = probe.reset(seed=seed)
        oracle = ContinuationOracle(probe)
        start_route = oracle.continuation(
            int(probe.current_node),
            oracle.visited_bits(probe),
            oracle.q(probe.battery),
            oracle.q(probe.elapsed_time),
        )
        hard_start = start_route is not None

        for policy_name, policy_cls in heuristics.items():
            for shielded in (False, True):
                env = SingleUAVEnv(cfg())
                obs, info = env.reset(seed=seed)
                policy = policy_cls()
                interventions = 0
                decisions = 0
                before_pruned = oracle.actions_pruned
                total_return = 0.0
                while True:
                    native_mask = env.get_action_mask()
                    use_info = dict(info)
                    if shielded and hard_start:
                        safe = oracle.safe_mask(env, native_mask)
                        if safe.any():
                            native_action = int(policy.act(env, obs, info))
                            use_info["action_mask"] = safe
                            action = int(policy.act(env, obs, use_info))
                            interventions += int(action != native_action)
                        else:
                            action = int(policy.act(env, obs, info))
                    else:
                        action = int(policy.act(env, obs, info))
                    obs, reward, terminated, truncated, info = env.step(action)
                    total_return += float(reward)
                    decisions += 1
                    if terminated or truncated:
                        break
                    if decisions > 64:
                        raise RuntimeError(f"seed {seed} {policy_name} runaway episode")

                rows.append({
                    "seed": seed,
                    "policy": policy_name,
                    "shielded": shielded,
                    "hard_feasible_start": int(hard_start),
                    "completed": int(bool(info["completed"])),
                    "returned_to_depot": int(bool(info["returned_to_depot"])),
                    "customers_served": int(info["customers_served"]),
                    "tardiness": float(info["ep_tardiness"]),
                    "zero_tardiness": int(float(info["ep_tardiness"]) <= 1e-9),
                    "infeasible": int(info["ep_infeasible"]),
                    "energy": float(info["ep_energy"]),
                    "native_return": total_return,
                    "decisions": decisions,
                    "shield_interventions": interventions,
                    "actions_pruned": oracle.actions_pruned - before_pruned if shielded else 0,
                    "oracle_cache_states": oracle.continuation.cache_info().currsize,
                })

    summaries = {}
    paired = {}
    for policy_name in heuristics:
        for shielded in (False, True):
            key = f"{policy_name}:{'shielded' if shielded else 'native'}"
            subset = [r for r in rows if r["policy"] == policy_name and r["shielded"] == shielded]
            summaries[key] = summarize(subset)
        native = {r["seed"]: r for r in rows if r["policy"] == policy_name and not r["shielded"]}
        shield = {r["seed"]: r for r in rows if r["policy"] == policy_name and r["shielded"]}
        hard_seeds = [s for s in native if native[s]["hard_feasible_start"]]
        paired[policy_name] = {
            "hard_feasible_seed_count": len(hard_seeds),
            "zero_tardiness_native": sum(native[s]["zero_tardiness"] for s in hard_seeds),
            "zero_tardiness_shielded": sum(shield[s]["zero_tardiness"] for s in hard_seeds),
            "completed_native": sum(native[s]["completed"] for s in hard_seeds),
            "completed_shielded": sum(shield[s]["completed"] for s in hard_seeds),
            "infeasible_native": sum(native[s]["infeasible"] > 0 for s in hard_seeds),
            "infeasible_shielded": sum(shield[s]["infeasible"] > 0 for s in hard_seeds),
            "mean_tardiness_delta_shield_minus_native": (
                statistics.fmean(shield[s]["tardiness"] - native[s]["tardiness"] for s in hard_seeds)
                if hard_seeds else None
            ),
            "mean_energy_delta_shield_minus_native": (
                statistics.fmean(shield[s]["energy"] - native[s]["energy"] for s in hard_seeds)
                if hard_seeds else None
            ),
            "seeds_improved_zero_tardiness": [
                s for s in hard_seeds if not native[s]["zero_tardiness"] and shield[s]["zero_tardiness"]
            ],
            "seeds_harmed_zero_tardiness": [
                s for s in hard_seeds if native[s]["zero_tardiness"] and not shield[s]["zero_tardiness"]
            ],
        }

    payload = {
        "stage": "UAV_ATTENTION_CONTINUATION_SHIELD_N5",
        "external_repo": "mdehghani86/uav-attention-routing",
        "external_commit": _git_head(EXT),
        "setting": {
            "num_customers": 5,
            "num_chargers": 1,
            "mission_time": 15,
            "deadline_min": 3,
            "deadline_max": 12,
            "reward_mode": "completion_ratio",
            "seed_range": [0, args.seeds - 1],
        },
        "shield": {
            "semantics": "mask an action iff no zero-tardiness full-customer + depot-return continuation remains after that action",
            "policy_ranking_modified": False,
            "environment_transition_modified": False,
            "evaluator_only_exact_continuation": True,
        },
        "summaries": summaries,
        "paired_hard_feasible": paired,
        "rows": rows,
        "claim_boundary": [
            "Hard deadlines are a transfer interpretation of the environment's native deadline/tardiness fields; the released environment's completed flag itself permits tardy service.",
            "The exact continuation oracle is evaluator-side and not a deployable efficient method; this experiment measures attainable benefit from continuation-aware masking.",
            "The same official heuristic ranking is used before and after shielding; only the feasible action mask changes.",
            "Results do not evaluate the external PPO checkpoint unless that policy is run separately."
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(args.out), "paired_hard_feasible": paired}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
