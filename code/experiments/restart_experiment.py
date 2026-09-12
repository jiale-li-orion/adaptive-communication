#!/usr/bin/env python3
"""
restart_experiment.py — does operation identity survive the coordinator's own death?

The protocol's first rule is register-before-dispatch, and that rule is only worth anything if
the registration outlives the process that made it. When a coordinator restarts, three things can
happen, and they are NOT the same method:

  fresh_id           no record and no way to rebuild one, so it invents a new operation identity.
                     The far side sees a new write; its dedup and fencing have nothing to match;
                     the effect lands a second time.

  reconstructed_id   no journal, but the operation's identity is a deterministic function of the
                     schedule, so it recomputes the SAME identity and the far side recognises the
                     repeat. No durable storage was needed for this.

  journal            it recovers the operation, its identity and its epoch from durable storage,
                     and settles a recovered operation once its receipt is confirmed, so the same
                     operation is not reconciled again at every later restart.

The middle arm decides how the paper's claim may be stated. If a coordinator can rebuild the
identity, durable storage is not a correctness requirement — it is one implementation of identity
continuity. So both command kinds are run, because they differ exactly there:

  scheduled   the command at slot r is fully determined by the mission. Its identity is
              reconstructible from the schedule alone.
  adhoc       the payload carries a decision made at the moment of acting — which hazard to
              re-measure, which alarm to acknowledge. That choice is gone when the process dies,
              and no recomputation brings it back.

What the three arms show is narrower than "journalling is necessary". It is: among these three
mechanisms, journalling is the one that covers both command kinds. The general statement is that
an action whose identity cannot be recomputed needs SOME durable source for its identity and its
decision context; a durable queue, an upstream event log or a persisted task id would do the same
job. The journal is this paper's implementation of that continuity, not the only possible one.

Every protocol message crosses Link.request()/reply(); nothing reads the far side directly. The
uplink and the downlink are drawn separately, so a request that never arrived or that the network
is still holding draws no reply. The environment (per-node channel state and power) is a fixed
trace shared by all three arms, so an arm that sends more queries does not change the weather that
the next arm meets.

Deps: numpy only.
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

import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)

from operations import OperationRegistry, Journal, recover, Outcome, Observation  # noqa: E402
from method_comparison import (Link, FarSide, make_nodes, EnvironmentTrace,   # noqa: E402
                               _u)

OUT = os.path.join(ROOT, "results", "restart_experiment.json")

ARMS = ("fresh_id", "reconstructed_id", "journal")
KINDS = ("scheduled", "adhoc")


def run_arm(arm: str, kind: str, nodes, hours: int, cmd_period: int, crash_period: int,
            seed: int, use_energy: bool, trace=None) -> dict:
    if trace is None:
        trace = EnvironmentTrace(nodes, hours, seed)
    sinks = {n["nid"]: FarSide(n["nid"], receipts=True, fencing=True) for n in nodes}
    link = Link(seed)

    journal = Journal() if arm == "journal" else None
    reg = OperationRegistry(journal, incarnation="i0-")
    inc = 0
    applied: dict[str, int] = {}          # identity -> executions at the far side
    intended: dict[tuple[str, int], str] = {}   # (node, slot) -> the identity the mission wanted
    done: set[str] = set()                # logical intents the coordinator is finished with
    crashes = 0
    # What this incarnation remembers of the ad-hoc choices it made. For the journal arm it is
    # backed by durable storage and survives the restart; for the others it dies with the process,
    # which is the whole point of the experiment.
    live_draws: dict[tuple[str, int], int] = {}
    durable_draws: dict[tuple[str, int], int] = {}
    # The missions's outstanding window. A coordinator that loses its state cannot tell which of
    # these already landed, so it re-asserts them; that re-assertion is what a restart costs.
    recent: list[tuple[int, dict]] = []
    REASSERT_WINDOW = 4

    for t in range(hours):
        trace.apply(nodes, t)
        epoch_seq = 0

        def next_epoch():
            """A logical clock, not a process counter. Monotone across restarts because it is
            derived from the hour, which is why fencing cannot reject a legitimate re-assert by
            accident and hide the failure this experiment exists to measure."""
            nonlocal epoch_seq
            epoch_seq += 1
            return t * 100 + epoch_seq

        # ------------------------------------------------ the coordinator dies and restarts
        if crash_period and t > 0 and t % crash_period == 0:
            crashes += 1
            inc += 1
            if arm == "journal":
                reg = recover(journal)
                done = {o.logical_intent for o in reg.ops.values()
                        if o.outcome is Outcome.APPLIED}
                window = {(nd["nid"], r) for (r, nd) in recent}
                for op in list(reg.ops.values()):
                    if not op.unresolved:
                        continue
                    # Retention applies here too: an operation outside the mission's outstanding
                    # window is abandoned rather than reconciled forever. Without this the journal
                    # arm pays a per-restart reconciliation for every command ever sent to a node
                    # that is permanently screened, which is a cost that grows with the run length
                    # and belongs to no real deployment.
                    if (op.entity_id, _slot_of(op.logical_intent)) not in window:
                        continue
                    node = next(x for x in nodes if x["nid"] == op.entity_id)
                    arrived, replied = link.exchange(node, t, "reconcile_read", op.epoch)
                    if not (arrived and replied):
                        continue          # the receipt may exist and still be unreachable
                    if sinks[op.entity_id].read_receipt(op.operation_id) is Outcome.APPLIED:
                        # Settle it back into the recovered registry. Without this the operation
                        # stays unresolved and is reconciled again at every later restart, which
                        # inflates the cost of the journal arm without bound.
                        reg.settle(op, Outcome.APPLIED, t, "reconciled")
                        done.add(op.logical_intent)
            else:
                # no storage. What survives is whatever the mission can recompute.
                reg = OperationRegistry(None, incarnation=f"i{inc}-")
                done = set()
                live_draws = {}          # the choices this process made are gone
            # Re-assert the outstanding window, keyed on the identity the mission wanted. Comparing
            # the slot index against a set of identity strings would match nothing and silently
            # re-assert the entire window on every arm.
            to_reassert = [(r, nd) for (r, nd) in recent
                           if intended.get((nd["nid"], r)) not in done]
            for r, nd in to_reassert:
                ident, payload = _identity_for(arm, kind, nd, r,
                                               durable_draws if arm == "journal" else live_draws,
                                               seed, inc)
                op = reg.register(nd["nid"], payload["op"], payload, ident, t, True)
                sent_id = op.operation_id if arm == "fresh_id" else ident
                reg.dispatched(op, t)
                arrived, replied = link.exchange(nd, t, "data_write", r)
                if not arrived:
                    continue
                ep = next_epoch()
                _o, did = sinks[nd["nid"]].apply(sent_id, ep, payload, t, true_epoch=ep)
                if did:
                    applied[ident] = applied.get(ident, 0) + 1
                if replied:
                    reg.settle(op, Outcome.APPLIED, t, "reasserted")
                    done.add(ident)

        if t % cmd_period != 0:
            continue
        r = t // cmd_period
        for n in nodes:
            # The mission issues its command whether or not the node is reachable. There is no
            # out-of-band health signal here: liveness is discovered by trying, and an oracle that
            # skips dead nodes would understate both the pending work and the restart burden.
            ident, payload = _identity_for(arm, kind, n, r,
                                           durable_draws if arm == "journal" else live_draws,
                                           seed, inc)
            intended.setdefault((n["nid"], r), ident)
            recent.append((r, n))
            if len(recent) > REASSERT_WINDOW * max(len(nodes), 1):
                del recent[:len(nodes)]

            if ident in done:
                continue

            op = reg.register(n["nid"], payload["op"], payload, ident, t, True)
            sent_id = (op.operation_id if arm == "fresh_id" else ident)
            reg.dispatched(op, t)
            arrived, replied = link.exchange(n, t, "data_write", r)
            if not arrived:
                reg.observe(op, Observation.UNKNOWN)
                continue
            ep = next_epoch()
            _outcome, did = sinks[n["nid"]].apply(sent_id, ep, payload, t, true_epoch=ep)
            if did:
                applied[ident] = applied.get(ident, 0) + 1
            if replied:
                reg.settle(op, Outcome.APPLIED, t, "replied")
                done.add(ident)

    # ---------------------------------------------------------------- scoring
    # The mission delivers an operation only if the identity IT chose is the one that lands. A
    # re-assert under a fresh draw is a different, unrequested action, so its applications are
    # counted as spurious side effects rather than as deliveries or duplicates of the intent.
    keys = set(intended.values())
    spurious = sum(c for k, c in applied.items() if k not in keys)
    once = sum(1 for k in keys if applied.get(k, 0) == 1)
    zero = sum(1 for k in keys if applied.get(k, 0) == 0)
    many = sum(1 for k in keys if applied.get(k, 0) > 1)
    extra = sum(max(0, applied.get(k, 0) - 1) for k in keys)
    total = max(len(keys), 1)
    return {"arm": arm, "kind": kind, "keys": total, "once": once, "zero": zero, "many": many,
            "duplicates": extra, "spurious": spurious,
            "once_rate": once / total, "crashes": crashes,
            "data_writes": link.msg["data_write"], "reconcile_reads": link.msg["reconcile_read"],
            "airtime_s": link.airtime_ms_total / 1000.0,
            "journal_entries": len(journal) if journal is not None else 0}


def _slot_of(logical_intent: str):
    """The slot a logical intent belongs to. The intent encodes it: `<nid>:<kind>:<slot>[:draw]`."""
    parts = logical_intent.split(":")
    try:
        return int(parts[2])
    except (IndexError, ValueError):
        return None


def _identity_for(arm, kind, n, r, memory, seed, inc):
    """The identity this coordinator would use for slot r, and the payload that goes with it.

    `memory` is what the current incarnation can still recall of its ad-hoc choices. The journal
    arm is handed storage that outlives the process; the others are handed a dict that is emptied
    at every restart.
    """
    if kind == "scheduled":
        # fully determined by the mission, so any incarnation recomputes the same one
        return f"{n['nid']}:measure:{r}", {"op": "trigger_measurement", "slot": r}
    key = (n["nid"], r)
    if key in memory:
        draw = memory[key]
    else:
        # An ad-hoc decision: which alarm to acknowledge was chosen when the coordinator acted.
        # `inc` enters the draw so that a coordinator which has forgotten still makes a NEW choice,
        # rather than recomputing the old one by accident and looking better than it is.
        draw = int(_u(seed, "adhoc_draw", n["nid"], r, inc) * (1 << 30))
        memory[key] = draw
    return (f"{n['nid']}:adhoc:{r}:{draw}",
            {"op": "ack_alarm", "slot": r, "alarm": f"a{draw}"})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=180)
    ap.add_argument("--cmd-period", type=int, default=12)
    ap.add_argument("--crash-period", type=int, default=72)
    ap.add_argument("--reach", type=int, default=12)
    ap.add_argument("--blocked", type=int, default=4)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--no-energy", action="store_true")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    hours = args.days * 24
    use_energy = not args.no_energy
    print(f"协调者重启实验：{args.days} 天，每 {args.crash_period} h 重启一次"
          f"（约 {hours // args.crash_period} 次），每 {args.cmd_period} h 一条命令")
    print(f"节点 {args.reach} 可达 + {args.blocked} 永久遮挡，"
          f"能量模型 {'开' if use_energy else '关'}，所有消息走同一条链路")
    print("far side 支持 operation 回执与 epoch fencing，即 C1 + C2 都在")
    print()

    # One node set and one environment trace per seed, built before any arm runs, so that every
    # arm meets the same weather and no arm can shift it by sending a different number of messages.
    env = []
    for s in range(args.seeds):
        rng = np.random.default_rng(1000 + s)
        nodes = make_nodes(args.reach, args.blocked, rng, use_energy)
        env.append((nodes, EnvironmentTrace(nodes, hours, 2000 + s)))

    rows = []
    for kind in KINDS:
        print(f"===== 命令类型: {kind} =====")
        hdr = (f"{'arm':18s} {'操作数':>7s} {'恰好一次':>9s} {'零次':>6s} {'多次':>6s} "
               f"{'多余应用':>9s} {'非请求':>7s} {'写入':>8s} {'调和读':>7s} {'日志条目':>9s}")
        print(hdr); print("-" * len(hdr))
        for arm in ARMS:
            acc = []
            for s in range(args.seeds):
                nodes, trace = env[s]
                acc.append(run_arm(arm, kind, nodes, hours, args.cmd_period,
                                   args.crash_period, 2000 + s, use_energy, trace=trace))
            agg = {k: float(np.mean([a[k] for a in acc])) for k in acc[0]
                   if isinstance(acc[0][k], (int, float))}
            agg["arm"] = arm; agg["kind"] = kind
            rows.append(agg)
            print(f"{arm:18s} {agg['keys']:7.0f} {100*agg['once_rate']:8.1f}% "
                  f"{agg['zero']:6.0f} {agg['many']:6.0f} {agg['duplicates']:9.1f} "
                  f"{agg['spurious']:7.0f} "
                  f"{agg['data_writes']:8.0f} {agg['reconcile_reads']:7.0f} "
                  f"{agg['journal_entries']:9.0f}")
        print()

    tag = f"_{args.tag}" if args.tag else ""
    path = OUT.replace(".json", f"{tag}.json")
    with open(path, "w") as f:
        json.dump({"config": vars(args), "results": rows}, f, indent=2, ensure_ascii=False)
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
