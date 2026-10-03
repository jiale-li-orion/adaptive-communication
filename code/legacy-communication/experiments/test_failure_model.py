#!/usr/bin/env python3
"""
test_failure_model.py — deterministic verification of README §9's eleven failure classes.

The stochastic episode run produces most of these by chance, but "by chance" is not a
specification. Each class gets a targeted test here so the benchmark's coverage claim is
verifiable rather than hopeful.

Run:  python3 test_failure_model.py
Exit: 0 if all eleven are producible on demand.
"""
from __future__ import annotations

# --- module resolution -------------------------------------------------------
# Scripts live in code/{physics,runtime,experiments,analysis}; any of them may import from
# another group, so the code root and every group directory go on the path.
import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, *(_os.path.join(_CODE, d) for d in ("physics", "runtime",
                                                     "experiments", "analysis"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)
# -----------------------------------------------------------------------------


import os
import sys
from disruption_env import DisruptionEnv  # noqa: E402
RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))


def env(**kw) -> DisruptionEnv:
    base = dict(n_nodes=8, ticks=5000, channel="ge", energy_model="real",
                heated_fraction=0.5, ack_loss_p=0.9)
    base.update(kw)
    e = DisruptionEnv(**base)
    e.tick()
    return e


def reachable(e: DisruptionEnv):
    return [n for n in e.nodes if n.reachable][0]


# --------------------------------------------------------------------- F01
def f01() -> None:
    """Dispatch, then kill the node before the reply arrives. Deterministic."""
    e = env(seed=1)
    n = reachable(e)
    op = e.dispatch(n, "alert.send", latency=5)
    e.tick()
    n.energy = None                      # stop the energy model from reviving it
    n.alive = False                      # the node dies mid-flight
    state, _ = e.poll(op)
    ok = state == "outcome_unknown" and \
        e.registry.counts.get("F01_node_lost_after_dispatch", 0) > 0
    check("F01 node lost after dispatch", ok, f"state={state}")


# --------------------------------------------------------------------- F02
def f02() -> None:
    e = env(seed=2)
    n = reachable(e)
    for _ in range(400):
        e.tick()
        e.call(n, "alert.send", intent=None)
        if e.registry.counts.get("F02_ack_lost_after_execution", 0) > 0:
            break
    check("F02 ACK lost after execution",
          e.registry.counts.get("F02_ack_lost_after_execution", 0) > 0)


# --------------------------------------------------------------------- F03
def f03() -> None:
    """One logical intent, retried with a FRESH identity each time -> sink applies twice."""
    e = env(seed=3, ack_loss_p=1.0)      # force the unknown branch
    n = reachable(e)
    applied_before = len(e.truth.applied)
    for _ in range(400):
        e.tick()
        for _k in range(5):
            e.call(n, "alert.send", intent=None)   # naive: new identity every retry
        if len(e.truth.applied) > applied_before + 1:
            break
    dups = e.duplicate_side_effects()
    check("F03 duplicate side effect", dups > 0, f"duplicates={dups}")


# --------------------------------------------------------------------- F04
def f04() -> None:
    """Dispatch to a node that then goes away and is never revisited: abandoned pending."""
    e = env(seed=4)
    n = reachable(e)
    e.dispatch(n, "alert.send", latency=5)    # in flight
    n.energy = None                            # keep the model from reviving it
    n.alive = False                            # capability gone
    for _ in range(60):                        # nobody ever polls it
        e.tick()
    check("F04 pending invocation forgotten",
          e.registry.counts.get("F04_pending_forgotten", 0) > 0,
          f"count={e.registry.counts.get('F04_pending_forgotten', 0)}")


# --------------------------------------------------------------------- F05
def f05() -> None:
    e = env(seed=5)
    n = reachable(e)
    for _ in range(200):
        e.tick()
        if e.stale_read(n, "sensor.read")[0] == "stale_result":
            break
    check("F05 stale used as current",
          e.registry.counts.get("F05_stale_used_as_current", 0) > 0)


# --------------------------------------------------------------------- F06
def f06() -> None:
    """Force the replay path directly: a node buffers several results, then returns."""
    e = env(seed=6)
    n = reachable(e)
    n.buffered = [(e.t, "alert.send", f"n{i}") for i in range(5)]
    for _ in range(50):                      # _replay has a 50% reversal chance
        e._replay(n)
        if e.registry.counts.get("F06_wrong_replay_order", 0) > 0:
            break
    check("F06 wrong replay order after recovery",
          e.registry.counts.get("F06_wrong_replay_order", 0) > 0)


# --------------------------------------------------------------------- F07
def f07() -> None:
    """Retry until the budget runs out.

    A terrain-blocked node is used on purpose. The earlier version relied on ack_loss_p=1.0,
    but a call can still succeed and settle, and re-dispatching a SETTLED effect is now refused
    (correctly: that would be a second logical write, not a retry). An unreachable node never
    settles, so the budget is what ends the attempts.
    """
    e = env(seed=7)
    n = next(x for x in e.nodes if not x.reachable)
    for _ in range(50):
        e.tick()
    for _ in range(10):                      # same intent, more attempts than the budget
        e.call(n, "alert.send", intent="key:budget-probe")
    check("F07 retry budget exhausted",
          e.registry.counts.get("F07_retry_budget_exhausted", 0) > 0)


# --------------------------------------------------------------------- F08
def f08() -> None:
    """An old unresolved operation blocks later ones (head-of-line)."""
    e = env(seed=8)
    n = reachable(e)
    old = e.registry.register(n.nid, "alert.send", {}, "key:stuck", e.t, True)
    old.budget = 99
    e.registry.dispatched(old, e.t)
    for _ in range(60):
        e.tick()
        later = e.registry.register(n.nid, "sensor.read", {}, f"later-{_}", e.t, False)
        later.budget = 99
        e.registry.dispatched(later, e.t)
        e.sweep_pending()
        if e.registry.counts.get("F08_starvation_head_of_line", 0) > 0:
            break
    check("F08 starvation / head-of-line", 
          e.registry.counts.get("F08_starvation_head_of_line", 0) > 0)


# --------------------------------------------------------------------- F09
def f09() -> None:
    e = env(seed=9, enable_flapping=True)
    for _ in range(2000):
        e.tick()
        if e.registry.counts.get("F09_gateway_flapping", 0) > 0:
            break
    check("F09 gateway / relay flapping",
          e.registry.counts.get("F09_gateway_flapping", 0) > 0)


# --------------------------------------------------------------------- F10
def f10() -> None:
    e = env(seed=10, enable_partition=True)
    for _ in range(3000):
        e.tick()
        if e.registry.counts.get("F10_partition_state_divergence", 0) > 0:
            check("F10 partition state divergence", True)
            return
    check("F10 partition state divergence", False)


# --------------------------------------------------------------------- F11
def f11() -> None:
    e = env(seed=11, coordinator_restart_p=0.5)
    for _ in range(5):
        e.tick()
    check("F11 coordinator restart",
          e.registry.counts.get("F11_coordinator_restart", 0) > 0)


TESTS = [f01, f02, f03, f04, f05, f06, f07, f08, f09, f10, f11]


def main() -> int:
    print("=" * 74)
    print("README §9 — eleven failure classes, deterministic verification")
    print("=" * 74)
    for t in TESTS:
        try:
            t()
        except Exception as exc:                       # noqa: BLE001
            check(t.__name__.upper(), False, f"raised {type(exc).__name__}: {exc}")

    ok = 0
    for name, passed, detail in RESULTS:
        print(f"  {'PASS' if passed else 'FAIL'}  {name:<44}{detail}")
        ok += bool(passed)
    print("-" * 74)
    print(f"  {ok}/{len(RESULTS)} failure classes producible on demand")
    return 0 if ok == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
