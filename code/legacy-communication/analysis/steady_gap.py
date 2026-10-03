"""Where do the 5.3 points of no-fault steady-state coverage come from?

Runs the `none` trajectory (no injected fault, 72 h) over a set of arms that differ from the
monolithic runtime `policies.RuntimePolicy` in exactly one knob at a time, and from the composed
runtime `compose.ContractRuntime` by construction. Every arm sees the same deployment, the same
exogenous demand, the same energy model and the same opportunity budget as
`code/experiments/monitoring_trajectories.py --paths backhaul:0.62`; only the policy differs.

Nothing under `code/monitoring/`, `code/runtime/` or `code/experiments/` is touched. Three of the
arms below are ablations that no constructor parameter can express (switching W1 off, moving the
profile writes ahead of the measurement requests in one tick's output, and dropping the in-flight
veto); they are implemented here by subclassing, so they are visible and reproducible rather than
hidden in a monkeypatch.

Run:  export PYTHONPATH="$PWD/libs/pylibs"
      python3 code/analysis/steady_gap.py --seeds 20 --tag q3
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
# -----------------------------------------------------------------------------

import argparse
import dataclasses
import json
import os

import numpy as np

from compose import ComposedPolicy, ContractRuntime, RulePlanner
from policies import RuntimePolicy, build_composed_arm
from runner import build_deployment, run_episode
from scorer import score
from supply import SupplyFleet
from task_generator import RISK_WINDOWS_H

OUT = os.path.join(_CODE, "..", "results", "steady_gap")

# The scenario's own knobs, copied from `code/experiments/monitoring_trajectories.py` so an arm run
# here is the same run as a row of the published business-layer table.
PATHS = (("backhaul", 0.62),)
RUNTIME_PATHS = (0,)


# ------------------------------------------------------------------ ablation arms
class NoW1(RuntimePolicy):
    """`ours` with the W1 measurement request never issued.

    The interface stays (nothing in `code/monitoring` is edited); only the decision to ask is
    switched off. This separates "the request is expensive" from "the request is ordered wrong".
    """

    name = "ours_no_w1"

    def _w1_needs_fresh_measurement(self, view, node_id: str, want: str) -> bool:
        return False


class W3BeforeW1(RuntimePolicy):
    """`ours` with the profile writes put ahead of the measurement requests in one tick's output.

    `RuntimePolicy.plan` returns W2, then W1, then W3. The control plane delivers only the head of
    a node's queue inside one uplink opportunity (`opportunity.ControlPlane._deliver`, one message
    per `downlink_per_uplink`), so the order of a single tick's list decides which of the two
    operations gets that opportunity. Nothing else changes here: same decisions, same counters.
    """

    name = "ours_w3_first"

    def plan(self, view):
        out = super().plan(view)
        writes = [item for item in out if item[1].get("op") == "set_monitoring_profile"]
        rest = [item for item in out if item[1].get("op") != "set_monitoring_profile"]
        return writes + rest


class NoInFlightVeto(RuntimePolicy):
    """`ours` with the `skip/in_flight` veto removed.

    `RuntimePolicy.plan` refuses to write a node that has any operation outstanding, so a W1
    measurement request that is still in the gateway queue also blocks the profile write the node
    needs. The composed runtime has no such veto. Removing it here isolates that rule from the
    ordering rule above.
    """

    name = "ours_no_inflight_veto"

    def plan(self, view):
        return super().plan(dataclasses.replace(view, in_flight=frozenset()))


class NoW1Planner(RulePlanner):
    """`RulePlanner` with W1 switched off, to see whether the cost of a measurement request is a
    property of the monolithic runtime's placement or of the request itself."""

    def _w1_intents(self, view):
        return []


# ------------------------------------------------------------------ arm registry
# Each entry: label -> (factory, note). The factory takes no argument; parameters that the policy
# exposes are set here so the label and the code cannot drift apart.
def _runtime(**attrs):
    """`RuntimePolicy` with the knobs it does not take in its constructor set afterwards.

    Only `dwell_s`, `ttl_s` and `retry_budget` are constructor arguments; `status_max_age_s`,
    `measure_window_mult` and `enable_backfill` are plain attributes. Setting them here rather than
    reaching into the class keeps every arm a constructible object.
    """
    pol = RuntimePolicy(**{k: attrs.pop(k) for k in ("dwell_s", "ttl_s", "retry_budget")
                           if k in attrs})
    for key, value in attrs.items():
        if not hasattr(pol, key):
            raise AttributeError(f"RuntimePolicy has no knob {key!r}")
        setattr(pol, key, value)
    return pol


def _arms() -> dict:
    reg: dict = {}

    def add(label, factory, note):
        reg[label] = (factory, note)

    add("ours", RuntimePolicy,
        "monolithic runtime, every default")
    add("rule__contract", lambda: build_composed_arm("rule__contract", paths=RUNTIME_PATHS),
        "composed runtime: RulePlanner + ContractRuntime")

    # -- candidate 1: the retry budget and the dwell, relaxed one at a time ---------------------
    add("ours retry_budget=99", lambda: RuntimePolicy(retry_budget=99),
        "retry cap 3 -> 99")
    add("ours dwell_s=0", lambda: RuntimePolicy(dwell_s=0),
        "mismatch dwell 300s -> 0s")
    add("ours ttl_s=1", lambda: RuntimePolicy(ttl_s=1),
        "the 'no evidence since write' wait ends at once instead of at issued_at+6h")

    # -- candidate 2: the remaining exposed knobs ------------------------------------------------
    add("ours status_max_age_s=86400", lambda: _runtime(status_max_age_s=86400),
        "status freshness bound 1h -> 24h (only read by the W2 path)")
    add("ours measure_window_mult=1", lambda: _runtime(measure_window_mult=1),
        "W1 request deadline 2h -> 1h")
    add("ours measure_window_mult=8", lambda: _runtime(measure_window_mult=8),
        "W1 request deadline 2h -> 8h")
    add("ours enable_backfill=True", lambda: _runtime(enable_backfill=True),
        "W2 backfill orders on (off by default)")

    def all_relaxed():
        return _runtime(retry_budget=99, dwell_s=0, ttl_s=1, status_max_age_s=86400,
                        measure_window_mult=1, enable_backfill=True)

    add("ours all knobs relaxed", all_relaxed,
        "every exposed knob at once, both W2 on")

    # -- mechanism isolation: ablations that no constructor parameter can express ----------------
    add("ours W1 off", NoW1, "ablation: never ask for a fresh measurement")
    add("ours W3 before W1", W3BeforeW1, "ablation: profile writes queued ahead of W1 requests")
    add("ours no in_flight veto", NoInFlightVeto, "ablation: in-flight veto removed")
    add("rule__contract W1 off",
        lambda: ComposedPolicy(planner=NoW1Planner(), runtime=ContractRuntime(paths=RUNTIME_PATHS),
                               name="rule__contract_no_w1"),
        "ablation: the composed cell with W1 switched off")

    return reg


MEASURES = ("coverage", "observation_gap", "downlink_attempts", "risk_coverage",
            "risk_open_wrong", "switch_on_delay_min", "config_mismatch_min")


def _profile_at(timeline, node_id: str, at_s: int) -> str | None:
    """What the node was really running at `at_s`, from the run's own timeline."""
    best_at, best = None, None
    for nid, when, profile in timeline:
        if nid != node_id or when > at_s:
            continue
        if best_at is None or when >= best_at:
            best_at, best = when, profile
    return best


def _risk_diagnostics(record) -> dict:
    """Two readings that say *why* a risk demand was missed, not just that it was.

    `risk_open_wrong` is the share of risk demands where *no* node of the demand's node set was
    running the risk profile when the demand's sample window opened -- the group had not been
    switched on in time. A risk demand is served by a sample from any node of the set, so "none of
    them was in the dense profile yet" is the part of the miss the runtime is answerable for.
    `switch_on_delay_min` is the mean delay between a risk window opening and each node actually
    running `risk`, counted from the node's own applied-profile timeline and capped at the window
    length.
    """
    risk = [d for d in record.demands if d.priority == 1]

    def switched_on(demand) -> bool:
        return any(_profile_at(record.profile_timeline, nid, demand.release_time) == "risk"
                   for nid in demand.node_set)

    wrong = sum(1 for d in risk if not switched_on(d))
    delays = []
    for start_h, end_h in RISK_WINDOWS_H:
        start, end = int(start_h * 3600), int(end_h * 3600)
        for node_id in record.node_ids:
            hit = None
            for nid, when, profile in record.profile_timeline:
                if nid == node_id and start <= when < end and profile == "risk":
                    hit = when
                    break
            delays.append(((hit - start) if hit is not None else (end - start)) / 60.0)
    return {"risk_open_wrong": (100.0 * wrong / len(risk)) if risk else float("nan"),
            "switch_on_delay_min": float(np.mean(delays)) if delays else float("nan")}


def one_run(factory, hours: int, seed: int, downlink_per_uplink: int = 1) -> dict:
    deployment = build_deployment(seed)
    supply = SupplyFleet(deployment.nodes, seed)
    policy = factory()
    record, _state, plane = run_episode(policy, hours=hours, seed=seed, fault=None,
                                        supply=supply, paths=PATHS,
                                        downlink_per_uplink=downlink_per_uplink)
    plane.check_opportunity_bound()
    result = score(record)
    row = {
        "coverage": 100.0 * result.coverage,
        "observation_gap": 100.0 * result.aux["observation_gap_ratio"],
        "downlink_attempts": float(plane.downlink_attempts),
        "risk_coverage": 100.0 * result.by_class["risk"]["coverage"],
        "config_mismatch_min": result.aux["config_mismatch_s"] / 60.0,
        "demands": result.demands,
        "covered": result.covered,
    }
    row.update(_risk_diagnostics(record))
    return row


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seeds", type=int, default=20, help="seeds 0..N-1 from the dev split")
    ap.add_argument("--hours", type=int, default=72, help="3 days by default")
    # Defaulted to the tag whose output is registered in `results/README.md`, so that running this
    # script with no arguments reproduces a file the index already knows about rather than creating
    # an unregistered orphan that `code/experiments/audit_consistency.py` would fail on.
    ap.add_argument("--tag", default="q3_attrib", help="results/steady_gap_<tag>.json")
    ap.add_argument("--arms", default="", help="comma-separated subset of arm labels")
    ap.add_argument("--json-out", default="", help="override the output path")
    # Not a scenario sweep: the frozen scenario is Class A, `downlink_per_uplink=1`. The knob is
    # exposed only as a mechanism probe -- if the blocking story in the report is right, giving each
    # uplink a second delivery slot should remove most of the gap without touching either runtime.
    ap.add_argument("--downlink-per-uplink", type=int, default=1,
                    help="delivery slots per uplink opportunity (frozen scenario: 1)")
    args = ap.parse_args()

    registry = _arms()
    labels = [a for a in (args.arms.split(",") if args.arms else registry) if a]
    unknown = [a for a in labels if a not in registry]
    if unknown:
        raise SystemExit(f"unknown arms {unknown}; have {sorted(registry)}")

    print(f"稳态差距归因：trajectory=none, {args.hours}h, seeds 0..{args.seeds - 1}, "
          f"paths={PATHS}, energy=on, downlink_per_uplink={args.downlink_per_uplink}", flush=True)
    rows = []
    for label in labels:
        factory, note = registry[label]
        per_seed = []
        for seed in range(args.seeds):
            per_seed.append(one_run(factory, args.hours, seed, args.downlink_per_uplink))
        mean = {k: float(np.mean([r[k] for r in per_seed])) for k in MEASURES}
        rows.append({"arm": label, "note": note, "per_seed": per_seed, **mean})
        print(f"  {label:26s} done", flush=True)

    hdr = (f"{'arm':28s}" + "".join(f"{n:>14s}" for n in MEASURES))
    print("")
    print(hdr)
    print("-" * len(hdr))
    for row in rows:
        print(f"{row['arm']:28s}" + "".join(f"{row[n]:14.2f}" for n in MEASURES))
    print("")
    print("coverage/risk_coverage/risk_open_wrong in %, observation_gap % of demanded samples,")
    print("downlink_attempts per 72h run, switch_on_delay_min/config_mismatch_min in minutes.")

    path = args.json_out or f"{OUT}_{args.tag}.json"
    with open(path, "w") as f:
        json.dump({"config": vars(args), "measures": list(MEASURES), "scenario": {
            "trajectory": "none", "paths": PATHS, "runtime_paths": RUNTIME_PATHS,
            "energy": True, "downlink_per_uplink": args.downlink_per_uplink},
            "results": rows}, f, indent=2, ensure_ascii=False)
    print(f"\nwrote {os.path.abspath(path)}")


if __name__ == "__main__":
    main()
