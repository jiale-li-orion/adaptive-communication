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

  journal            it recovers the operation, its identity and its epoch from durable storage.

The middle arm decides how the paper's claim may be stated. If a coordinator can rebuild the
identity, durable storage is not a correctness requirement — it is one implementation of identity
continuity. So both command kinds are run, because they differ exactly there:

  scheduled   the command at slot r is fully determined by the mission. Its identity is
              reconstructible from the schedule alone.
  adhoc       the payload carries a decision made at the moment of acting — which hazard to
              re-measure, which alarm to acknowledge. That choice is gone when the process dies,
              and no recomputation brings it back.

Durable journaling is therefore not the only way to keep identity; it is the only way to keep an
identity that cannot be recomputed. That is the honest form of the claim, and it is also where
the word "agent" starts to earn its place: a fixed schedule is recomputable, an action an LLM
improvised from what it happened to observe is not.

Every protocol message crosses Link.exchange(); nothing reads the far side directly, and the
channel is sampled exactly once per message.

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
from method_comparison import Link, FarSide, make_nodes                           # noqa: E402

OUT = os.path.join(ROOT, "results", "restart_experiment.json")

ARMS = ("fresh_id", "reconstructed_id", "journal")
KINDS = ("scheduled", "adhoc")


def run_arm(arm: str, kind: str, nodes, hours: int, cmd_period: int, crash_period: int,
            seed: int, use_energy: bool) -> dict:
    rng = np.random.default_rng(seed)
    sinks = {n["nid"]: FarSide(n["nid"], receipts=True, fencing=True) for n in nodes}
    link = Link(rng)

    journal = Journal() if arm == "journal" else None
    reg = OperationRegistry(journal, incarnation="i0-")
    inc = 0
    applied: dict[str, int] = {}      # identity -> executions at the far side
    attempted: set[str] = set()       # every identity the coordinator ever sent
    intended: dict[str, str] = {}     # mission slot -> the identity the mission actually wanted
    spurious = 0                      # applications of an identity the mission never asked for
    done_keys: set[str] = set()       # identities the coordinator believes are satisfied
    crashes = 0
    # The window of commands the mission still cares about. A coordinator that loses its state
    # cannot tell which of these already landed, so it re-asserts them; that re-assertion is
    # what a restart actually costs.
    recent: list[tuple[int, dict]] = []
    REASSERT_WINDOW = 4

    for t in range(hours):
        doy = t // 24
        for n in nodes:
            if n["energy"] is not None:
                n["energy"].step(doy)
                n["alive"] = n["energy"].alive
            if not n["permanent"]:
                if n["good"]:
                    if rng.random() < 0.071211:
                        n["good"] = False
                elif rng.random() < 0.156721:
                    n["good"] = True

        # ------------------------------------------------ the coordinator dies and restarts
        if crash_period and t > 0 and t % crash_period == 0:
            crashes += 1
            inc += 1
            to_reassert: list = []
            if arm == "journal":
                reg = recover(journal)
                done_keys = {o.logical_intent for o in reg.ops.values()
                             if o.outcome is Outcome.APPLIED}
                for op in list(reg.ops.values()):
                    if not op.unresolved:
                        continue
                    node = next(x for x in nodes if x["nid"] == op.entity_id)
                    arrived, replied = link.exchange(node, "reconcile_read")
                    if not (arrived and replied):
                        continue          # the receipt may exist and still be unreachable
                    if sinks[op.entity_id].read_receipt(op.operation_id) is Outcome.APPLIED:
                        done_keys.add(op.logical_intent)
                to_reassert = [it for it in recent
                               if it[0] not in {k for k in done_keys}]
            else:
                # no storage. What survives is whatever the mission can recompute.
                reg = OperationRegistry(None, incarnation=f"i{inc}-")
                done_keys = set()
                to_reassert = list(recent)
            # re-assert the outstanding window. The identity used here is what decides whether
            # the far side recognises the repeat.
            for r_, nd in to_reassert:
                if not nd["alive"]:
                    continue
                ident, payload, draw = _identity_for(arm, kind, nd, r_, journal_draws, rng, inc)
                attempted.add(ident)
                op = reg.register(nd["nid"], payload["op"], payload, ident, t, True)
                sent_id = op.operation_id if arm == "fresh_id" else ident
                reg.dispatched(op, t)
                arrived, replied = link.exchange(nd, "data_write")
                if not arrived:
                    continue
                _o, did = sinks[nd["nid"]].apply(sent_id, t + 1, payload, t)
                if did:
                    applied[ident] = applied.get(ident, 0) + 1
                if replied:
                    reg.settle(op, Outcome.APPLIED, t, "reasserted")
                    done_keys.add(ident)

        if t % cmd_period != 0:
            continue
        r = t // cmd_period
        for n in nodes:
            if not n["alive"]:
                continue

            ident, payload, _d = _identity_for(arm, kind, n, r, journal_draws, rng, inc)
            attempted.add(ident)
            intended.setdefault(f"{n['nid']}:{r}", ident)
            recent.append((r, n))
            if len(recent) > REASSERT_WINDOW * max(len(nodes), 1):
                del recent[:len(nodes)]

            if ident in done_keys:
                continue

            op = reg.register(n["nid"], payload["op"], payload, ident, t, True)
            # the identity sent to the far side IS the logical identity for the arms that can
            # reconstruct it; only fresh_id is forced to invent a new one
            sent_id = (op.operation_id if arm == "fresh_id" else ident)
            reg.dispatched(op, t)
            arrived, replied = link.exchange(n, "data_write")
            if not arrived:
                reg.observe(op, Observation.UNKNOWN)
                continue
            # The epoch must be monotone ACROSS restarts, as a clock-derived or durably
            # persisted counter is. A per-process counter that restarts at 1 would let the far
            # side's fencing reject every re-assert by accident, which would hide the very
            # failure this experiment exists to measure.
            _outcome, did = sinks[n["nid"]].apply(sent_id, t + 1, payload, t)
            if did:
                applied[ident] = applied.get(ident, 0) + 1
            if replied:
                reg.settle(op, Outcome.APPLIED, t, "replied")
                done_keys.add(ident)

    # score the identities the MISSION asked for; an unrequested re-issue is counted separately
    # The mission delivers an operation only if the identity it chose is the one that lands.
    # A re-assert under a fresh draw is a different, unrequested action, so its applications are
    # counted as spurious side effects rather than as deliveries (or as duplicates) of the intent.
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


def _identity_for(arm, kind, n, r, draws, rng, inc):
    """The identity this coordinator would use for slot r, and the payload that goes with it."""
    if kind == "scheduled":
        # fully determined by the mission, so any incarnation recomputes the same one
        return f"{n['nid']}:measure:{r}", {"op": "trigger_measurement", "slot": r}, None
    # an ad-hoc decision: which alarm to acknowledge was chosen when the coordinator acted.
    # Only durable storage can reproduce that choice; without it the coordinator makes a new
    # one, and a new choice is genuinely a new operation.
    if arm == "journal" and r in draws:
        draw = draws[r]
    else:
        draw = int(rng.integers(1 << 30))
        if arm == "journal":
            draws[r] = draw
    return (f"{n['nid']}:adhoc:{r}:{draw}",
            {"op": "ack_alarm", "slot": r, "alarm": f"a{draw}"}, draw)


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

    rows = []
    for kind in KINDS:
        print(f"===== 命令类型: {kind} =====")
        hdr = (f"{'arm':18s} {'操作数':>7s} {'恰好一次':>9s} {'零次':>6s} {'多次':>6s} "
               f"{'多余应用':>9s} {'非请求':>7s} {'写入':>8s} {'调和读':>7s} {'日志条目':>9s}")
        print(hdr); print("-" * len(hdr))
        for arm in ARMS:
            acc = []
            for s in range(args.seeds):
                rng = np.random.default_rng(1000 + s)
                nodes = make_nodes(args.reach, args.blocked, rng, use_energy)
                global journal_draws
                journal_draws = {}
                acc.append(run_arm(arm, kind, nodes, hours, args.cmd_period,
                                   args.crash_period, 2000 + s, use_energy))
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


journal_draws: dict[int, int] = {}


if __name__ == "__main__":
    main()
