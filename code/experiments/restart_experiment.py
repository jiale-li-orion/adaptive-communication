#!/usr/bin/env python3
"""
restart_experiment.py — does durable lifecycle survive the coordinator's own death?

The protocol's first rule is register-before-dispatch. That rule is only worth something if the
registration outlives the process that made it. When a coordinator restarts:

  without a journal  it has no record of what was in flight. It can only re-derive intent from
                     the mission goal ("this node should be configured"), so it sends a NEW
                     operation under a NEW epoch. The far side sees a new write, its fencing has
                     nothing to fence, and the retry lands as a second effect.

  with a journal     it recovers the unresolved operations, reconciles each against the far side,
                     and only issues a new operation when the reconcile says the old one never
                     landed.

Both arms run against the SAME fenced far side and the same channel. The only difference is
whether the runtime remembers. Epoch fencing is not a substitute for memory: fencing rejects a
stale REPLAY of an old epoch, but a coordinator that forgot cannot replay what it cannot name.

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
import csv
import json
import math
import os
import sys

import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
from operations import (OperationRegistry, Journal, recover,   # noqa: E402
                        Outcome, Observation)
from method_comparison import Link, FarSide, make_nodes, load_terrain   # noqa: E402

GRID = os.path.join(ROOT, "results", "coverage_grid.csv")
OUT = os.path.join(ROOT, "results", "restart_experiment.json")

P_GOOD_TO_BAD = 0.071211
P_BAD_TO_GOOD = 0.156721
ACK_LOSS_P = 0.35
SENS = {7: -123.0, 8: -126.0, 9: -129.0, 10: -132.0, 11: -134.5, 12: -137.0}
TX_DBM, G_TX, G_RX, FEEDER = 14.0, 2.0, 2.0, 1.0

ARMS = ("no_journal", "journal")


def load_terrain():
    reach, blocked = [], []
    with open(GRID) as f:
        for r in csv.DictReader(f):
            sf = int(r["best_sf(-1=unreachable)"])
            (reach if sf > 0 else blocked).append(
                {"sf": sf, "loss_db": float(r["loss_dB"])})
    return reach, blocked


def p_given_good(loss_db, sf):
    margin = TX_DBM + G_TX + G_RX - FEEDER - loss_db - SENS[sf]
    return 1.0 / (1.0 + math.exp(-margin / 5.0))


def run_arm(arm: str, nodes, hours: int, cmd_period: int, crash_period: int,
            seed: int) -> dict:
    rng = np.random.default_rng(seed)
    # The far side is reached only through the link. Reconciliation is a communication
    # operation like any other: it can arrive, it can lose its reply, and it costs airtime.
    sinks = {n["nid"]: FarSide(n["nid"], receipts=True, fencing=True) for n in nodes}
    link = Link(rng)
    journal = Journal() if arm == "journal" else None
    inc = 0
    reg = OperationRegistry(journal, incarnation=f"i{inc}-")

    applied: dict[str, int] = {}
    achieved: set[str] = set()        # logical intents the coordinator believes are done
    outstanding: dict[str, object] = {}   # intent -> the operation still being carried
    crashes = 0

    for t in range(hours):
        for n in nodes:
            if not n["permanent"]:
                if n["good"]:
                    if rng.random() < P_GOOD_TO_BAD:
                        n["good"] = False
                elif rng.random() < P_BAD_TO_GOOD:
                    n["good"] = True

        # ------------------------------------------------ the coordinator dies and restarts
        if crash_period and t > 0 and t % crash_period == 0:
            crashes += 1
            # the incarnation advances on every restart, so operation ids never collide with
            # ids the far side has already seen, whether or not the runtime remembers anything
            inc += 1
            if arm == "journal":
                reg = recover(journal)
                # what it had achieved, and what it still owes, both come back
                achieved = {o.logical_intent for o in reg.ops.values()
                            if o.outcome is Outcome.APPLIED}
                outstanding = {o.logical_intent: o for o in reg.ops.values() if o.unresolved}
                for intent, op in list(outstanding.items()):
                    if op.first_dispatch_at is None:
                        continue
                    node = next(x for x in nodes if x["nid"] == op.entity_id)
                    arrived, replied = link.exchange(node, "reconcile_read")
                    if not (arrived and replied):
                        # the receipt may exist remotely and still be unreachable right now.
                        # Leaving the operation unresolved is the honest outcome; inventing a
                        # verdict here is what a free read would let us do.
                        continue
                    if sinks[op.entity_id].read_receipt(op.operation_id) is Outcome.APPLIED:
                        achieved.add(intent)
                        outstanding.pop(intent, None)
            else:
                # a restart with no memory: it keeps the mission goal, which is external, but
                # has no idea what it already sent or already achieved
                reg = OperationRegistry(None, incarnation=f"i{inc}-")
                achieved = set()
                outstanding = {}

        # ------------------------------------------------ the mission still requires the config
        if t % cmd_period == 0:
            for n in nodes:
                intent = f"{n['nid']}:rate"
                if intent in achieved:
                    continue
                op = outstanding.get(intent)
                if op is None:
                    # the epoch is derived from the hour, which a restarted coordinator still
                    # knows: it advances across crashes, so a re-issued write outranks the one
                    # the far side may already hold
                    op = reg.register(n["nid"], "set_sampling_rate", {"rate": "5min"},
                                      intent, t, True, epoch=t + 1)
                    outstanding[intent] = op
                # a retry reuses the SAME operation and epoch. That is the entire point: it is
                # what lets the far side recognise the repeat instead of accepting a new write.
                reg.dispatched(op, t)
                if n["permanent"] or not n["good"]:
                    reg.observe(op, Observation.UNAVAILABLE)
                    continue
                if rng.random() >= p_given_good(n["loss_db"], n["sf"]):
                    reg.observe(op, Observation.UNKNOWN)
                    continue
                arrived, replied = link.exchange(n, "data_write")
                if not arrived:
                    reg.observe(op, Observation.UNKNOWN)
                    continue
                outcome, did = sinks[n["nid"]].apply(op.operation_id, op.epoch,
                                                     {"rate": "5min"}, t)
                if did:
                    applied[intent] = applied.get(intent, 0) + 1
                if outcome is Outcome.APPLIED and rng.random() >= ACK_LOSS_P:
                    reg.settle(op, Outcome.APPLIED, t, "acked")
                    achieved.add(intent)
                    outstanding.pop(intent, None)
                elif outcome in (Outcome.SUPERSEDED, Outcome.REJECTED):
                    # the far side already holds this write; the goal is satisfied
                    reg.settle(op, outcome, t, "fenced by the sink")
                    achieved.add(intent)
                    outstanding.pop(intent, None)
                else:
                    reg.observe(op, Observation.UNKNOWN)

    intents = set(applied) | achieved
    for op in reg.ops.values():
        intents.add(op.logical_intent)
    once = sum(1 for i in intents if applied.get(i, 0) == 1)
    zero = sum(1 for i in intents if applied.get(i, 0) == 0)
    many = sum(1 for i in intents if applied.get(i, 0) > 1)
    extra = sum(max(0, applied.get(i, 0) - 1) for i in intents)
    return {"arm": arm, "intents": len(intents), "once": once, "zero": zero, "many": many,
            "duplicates": extra, "crashes": crashes,
            "once_rate": once / max(len(intents), 1),
            "dup_rate": many / max(len(intents), 1),
            "journal_entries": (len(journal) if journal is not None else 0)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=180)
    ap.add_argument("--cmd-period", type=int, default=12)
    ap.add_argument("--crash-period", type=int, default=72, help="hours between restarts")
    ap.add_argument("--reach", type=int, default=12)
    ap.add_argument("--blocked", type=int, default=4)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    hours = args.days * 24
    print(f"协调者重启实验：{args.days} 天，每 {args.crash_period} h 重启一次"
          f"（共约 {hours//args.crash_period} 次）")
    print(f"节点 {args.reach} 可达 + {args.blocked} 永久遮挡，每 {args.cmd_period} h 一条配置命令")
    print("两组跑在同一个 fenced sink 与同一信道上，唯一差别是 runtime 是否记得")
    print()

    hdr = f"{'arm':12s} {'逻辑意图':>8s} {'恰好一次':>9s} {'零次':>7s} {'多次':>7s} {'多余应用':>9s} {'日志条目':>9s}"
    print(hdr)
    print("-" * len(hdr))
    rows = []
    for arm in ARMS:
        acc = []
        for s in range(args.seeds):
            rng = np.random.default_rng(1000 + s)
            nodes = make_nodes(args.reach, args.blocked, rng, use_energy=True)
            acc.append(run_arm(arm, nodes, hours, args.cmd_period, args.crash_period,
                               2000 + s))
        agg = {k: float(np.mean([a[k] for a in acc])) for k in acc[0] if k != "arm"}
        agg["arm"] = arm
        rows.append(agg)
        print(f"{arm:12s} {agg['intents']:8.0f} {100*agg['once_rate']:8.1f}% "
              f"{agg['zero']:7.0f} {agg['many']:7.0f} {agg['duplicates']:9.1f} "
              f"{agg['journal_entries']:9.0f}")

    a = next(r for r in rows if r["arm"] == "no_journal")
    b = next(r for r in rows if r["arm"] == "journal")
    print()
    print(f"  无日志：多余应用 {a['duplicates']:.1f}，{a['many']:.0f} 条意图被应用了不止一次")
    print(f"  有日志：多余应用 {b['duplicates']:.1f}，{b['many']:.0f} 条意图被应用了不止一次")
    print(f"  差别：{a['duplicates'] - b['duplicates']:.1f} 次重复效果被持久化挡住")

    tag = f"_{args.tag}" if args.tag else ""
    path = OUT.replace(".json", f"{tag}.json")
    with open(path, "w") as f:
        json.dump({"config": vars(args), "results": rows}, f, indent=2, ensure_ascii=False)
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
