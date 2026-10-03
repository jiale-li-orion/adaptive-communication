"""Supporting counters for `steady_gap.py`: which decision, not which reading.

`steady_gap.py` says how far each configuration gets. This says *what the monolithic runtime was
doing* while it got there: how many node-ticks the profile write was refused because something was
already outstanding, and how many of those refusals happened while a W1 measurement request was the
thing outstanding. That distinction is the difference between the two candidates the ablation arms
separate, and it is not visible in any scored metric.

Read-only with respect to `code/monitoring/`, `code/runtime/` and `code/experiments/`: the tally is
taken from `RuntimePolicy.last_decision`, which the runtime already fills in for its own audit, and
from `RuntimePolicy.measure_outstanding`, which the W1 path already maintains.

Run:  export PYTHONPATH="$PWD/libs/pylibs"
      python3 code/analysis/steady_gap_counters.py --seeds 20 --tag q3_attrib
"""

from __future__ import annotations

import os as _os
import sys as _sys

_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, *(_os.path.join(_CODE, d) for d in ("physics", "runtime", "experiments",
                                                      "analysis", "monitoring"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

import argparse
import collections
import json
import os

import numpy as np

from policies import RuntimePolicy
from runner import build_deployment, run_episode
from scorer import score
from supply import SupplyFleet

OUT = os.path.join(_CODE, "..", "results", "steady_gap_counters")


class Counting(RuntimePolicy):
    """`RuntimePolicy`, unmodified, with its own audit record read back out."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.c = collections.Counter()

    def plan(self, view):
        out = super().plan(view)
        for node_id, want in view.demanded_profile.items():
            record = self.last_decision.get(node_id) or {}
            action, reason = record.get("action"), record.get("reason")
            key = {"settle": reason, "wait": reason, "write": "assert"}.get(action, action)
            self.c[f"decision/{key}"] += 1
            if action == "write":
                self.c[f"write_for/{want}"] += 1
            if reason == "in_flight":
                # The veto is about the node, and what it is really about is which operation holds
                # the node. `measure_outstanding` names the W1 requests the runtime still considers
                # unanswered, so the two cases can be told apart.
                self.c["veto/in_flight_with_W1_open" if node_id in self.measure_outstanding
                       else "veto/in_flight_without_W1"] += 1
                self.c[f"veto/demand_{want}"] += 1
        for _node, payload in out:
            self.c[f"dispatch/{payload.get('op')}"] += 1
        return out


def one(seed: int, hours: int) -> tuple[dict, float]:
    deployment = build_deployment(seed)
    supply = SupplyFleet(deployment.nodes, seed)
    policy = Counting()
    record, _state, plane = run_episode(policy, hours=hours, seed=seed, fault=None,
                                        supply=supply, paths=(("backhaul", 0.62),))
    plane.check_opportunity_bound()
    return dict(policy.c), 100.0 * score(record).coverage


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--hours", type=int, default=72)
    ap.add_argument("--tag", default="q3_attrib")
    args = ap.parse_args()

    keys = set()
    runs = []
    for seed in range(args.seeds):
        tally, coverage = one(seed, args.hours)
        runs.append({"seed": seed, "coverage": coverage, "counters": tally})
        keys |= set(tally)

    order = [k for k in sorted(keys)]
    mean = {k: float(np.mean([r["counters"].get(k, 0) for r in runs])) for k in order}
    print(f"RuntimePolicy 决策计数：trajectory=none, {args.hours}h, seeds 0..{args.seeds - 1}")
    print(f"{'counter':36s}{'per run':>14s}")
    print("-" * 50)
    for key in order:
        print(f"{key:36s}{mean[key]:14.1f}")
    print(f"{'coverage':36s}{float(np.mean([r['coverage'] for r in runs])):14.2f}")

    path = f"{OUT}_{args.tag}.json"
    with open(path, "w") as f:
        json.dump({"config": vars(args), "mean": mean, "runs": runs}, f, indent=2,
                  ensure_ascii=False)
    print(f"\nwrote {os.path.abspath(path)}")


if __name__ == "__main__":
    main()
