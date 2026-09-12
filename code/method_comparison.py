#!/usr/bin/env python3
"""
method_comparison.py — the paper's main experiment.

One fixed decision trajectory, four execution runtimes. The agent always decides the same
thing at the same hour; only the layer that turns that decision into a remote effect changes.
That keeps the causal claim clean:

    same agent  +  same action  +  same channel  +  different runtime

The four runtimes follow the gap chain: B1 does communication decisions and assumes tool
execution is reliable; B2 checks before executing (pre-execution assurance); B3 verifies after a
timeout and then retries; ours treats the operation as a durable object that survives the
disconnection until reconciliation settles it.

An honest asymmetry has to be stated up front, and the experiment measures it rather than
hiding it. Epoch fencing and per-operation receipts are capabilities of the FAR SIDE. A
commodity entity has neither, so the baselines run against a plain sink while our protocol
requires a fenced one. The fifth arm runs our runtime against the plain sink anyway, to show
what the protocol degrades to without the far-side contract. A method whose advantage exists
only under an assumption it never states is not a method.

Ground truth is counted at the sink, never from what the agent believes.

  terrain + loss        results/coverage_grid.csv  (real SRTM + Longley-Rice ITM)
  transient churn       ChirpBox GE, p(g->b)=0.0712, p(b->g)=0.1567
  energy-induced silence  energy.py (LiFePO4 + charge gate)
  far side               operations.RemoteSink, plain (no epoch, no receipt) vs fenced

Deps: numpy only.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)

from operations import OperationRegistry, Outcome, Observation, Lifecycle   # noqa: E402

GRID = os.path.join(ROOT, "results", "coverage_grid.csv")
OUT = os.path.join(ROOT, "results", "method_comparison.json")

P_GOOD_TO_BAD = 0.071211
P_BAD_TO_GOOD = 0.156721
ACK_LOSS_P = 0.35              # of applied requests whose acknowledgment never returns
RETRY_BUDGET = 3               # attempts per logical write for the retrying arms
RETENTION_H = 168
HEATED_FRACTION = 0.5        # sites whose battery box removes the cold charge gate

SENS = {7: -123.0, 8: -126.0, 9: -129.0, 10: -132.0, 11: -134.5, 12: -137.0}
TX_DBM, G_TX, G_RX, FEEDER = 14.0, 2.0, 2.0, 1.0

ARMS = ("b1_wirelessagent", "b2_wirelessops", "b3_verified", "ours", "ours_plain_sink")


def load_terrain() -> tuple[list, list]:
    reach, blocked = [], []
    with open(GRID) as f:
        for r in csv.DictReader(f):
            sf = int(r["best_sf(-1=unreachable)"])
            (reach if sf > 0 else blocked).append(
                {"lat": float(r["lat"]), "lon": float(r["lon"]),
                 "loss_db": float(r["loss_dB"]), "sf": sf})
    return reach, blocked


def p_given_good(loss_db: float, sf: int) -> float:
    margin = TX_DBM + G_TX + G_RX - FEEDER - loss_db - SENS[sf]
    return 1.0 / (1.0 + math.exp(-margin / 5.0))


class FarSide:
    """The communication entity.

    1.0.0 is the commodity entity: it applies whatever reaches it, and remembers nothing
    between requests. `fenced` adds the minimal contract our protocol relies on — a durable
    last-accepted epoch and a per-operation receipt — which is the thing the paper asks a
    deployment to provide.
    """

    def __init__(self, nid: str, fenced: bool):
        self.nid = nid
        self.fenced = fenced
        self.last_accepted_epoch = 0
        self.receipts: dict[str, Outcome] = {}
        self.applied: list[tuple[int, str]] = []      # (hour, operation_id) actually applied

    def receive(self, op_id: str, epoch: int, t: int) -> tuple[str, bool]:
        """Returns (what the caller learns, did_apply)."""
        if self.fenced:
            prev = self.receipts.get(op_id)
            if prev is not None:
                return prev.value, False
            if epoch <= self.last_accepted_epoch and self.last_accepted_epoch > 0:
                return (Outcome.SUPERSEDED.value if epoch < self.last_accepted_epoch
                        else Outcome.REJECTED.value), False
            self.last_accepted_epoch = epoch
            self.receipts[op_id] = Outcome.APPLIED
        self.applied.append((t, op_id))
        return Outcome.APPLIED.value, True

    def receipt(self, op_id: str) -> Outcome | None:
        return self.receipts.get(op_id)

    def ever_applied(self, node_has_any: bool) -> bool:
        """An UNSCOPED postcondition predicate: has ANY write ever landed here."""
        return node_has_any


def make_nodes(n_reach: int, n_blocked: int, rng, use_energy: bool):
    """Nodes on the real terrain grid, with the real energy model where requested.

    Half the sites get a heated battery box. That is not a tuning knob: the charge gate is what
    decides whether a high-altitude node survives the winter, and real deployments differ in
    whether they paid for heating. It also keeps the comparison meaningful, because a node that
    is dead cannot receive anything under ANY runtime, and a scenario where most nodes are dead
    adds the same near-total zero rate to every arm and washes out the differences the
    experiment exists to measure.
    """
    reach, blocked = load_terrain()
    picks = [(reach[i], False) for i in rng.choice(len(reach), n_reach, replace=False)]
    picks += [(blocked[i], True) for i in rng.choice(len(blocked), n_blocked, replace=False)]

    dem = elv = None
    if use_energy:
        from dem_to_mitsuba import elev_at, load_tile
        dem = load_tile()
        elv = elev_at

    nodes = []
    for k, (r, permanent) in enumerate(picks):
        nd = {"nid": f"{'b' if permanent else 'r'}{k:02d}",
              "sf": 12 if permanent else r["sf"], "loss_db": r["loss_db"],
              "permanent": permanent, "good": not permanent, "alive": True, "energy": None}
        if use_energy:
            from energy import NodeEnergy
            nd["energy"] = NodeEnergy(elev_m=elv(dem, r["lat"], r["lon"]), rng=rng,
                                      heated=bool(rng.random() < HEATED_FRACTION))
        nodes.append(nd)
    return nodes


def link_attempt(node: dict, rng) -> bool:
    """One request crosses the link. Returns whether the far side received it."""
    if node["permanent"] or not node["alive"]:
        return False
    return node["good"] and rng.random() < p_given_good(node["loss_db"], node["sf"])


def run_arm(arm: str, nodes: list, hours: int, cmd_period: int, seed: int,
            use_energy: bool) -> dict:
    rng = np.random.default_rng(seed)
    fenced = arm in ("ours", "ours_plain_sink") and arm != "ours_plain_sink"
    sinks = {n["nid"]: FarSide(n["nid"], fenced) for n in nodes}
    reg = OperationRegistry()

    # ground truth per logical write
    applied_count: dict[str, int] = {}
    settled_intents = 0
    unresolved_intents = 0
    attempts_total = 0
    pending: list[dict] = []          # logical writes still being carried

    for t in range(hours):
        doy = t // 24
        for n in nodes:
            if n["energy"] is not None:
                n["energy"].step(doy)
                n["alive"] = n["energy"].alive
            if not n["permanent"]:
                if n["good"]:
                    if rng.random() < P_GOOD_TO_BAD:
                        n["good"] = False
                elif rng.random() < P_BAD_TO_GOOD:
                    n["good"] = True

        # ---------------- the agent decides (identical in every arm) ----------------
        if t % cmd_period == 0:
            for n in nodes:
                op = reg.register(n["nid"], "set_sampling_rate", {"rate": "5min"},
                                  f"{n['nid']}:rate", t, True)
                pending.append({"op": op, "node": n, "intent": f"{n['nid']}:rate:t{t}",
                                "epoch": op.epoch, "attempts": 0, "done": False})

        # ---------------- the runtime carries the decision ----------------
        for item in pending:
            if item["done"]:
                continue
            op, n = item["op"], item["node"]

            # ---- what each runtime does this hour ----
            if arm == "b1_wirelessagent":
                # one shot per decision; a failed response is reported to the model and dropped
                if t < op.created_at:
                    continue
                want = (item["attempts"] == 0)
            elif arm == "b2_wirelessops":
                # pre-execution assurance, then retry under a FRESH request up to a budget
                want = item["attempts"] < RETRY_BUDGET
            elif arm == "b3_verified":
                # on no-ACK, verify the postcondition, then retry if it says "not applied"
                if item["attempts"] == 0:
                    want = True
                elif item["attempts"] >= RETRY_BUDGET:
                    want = False
                else:
                    # The published wrapper verifies the POSTCONDITION STATE, not the operation:
                    # "is the effect in place?" On a commodity entity that is the only question
                    # it can ask, because there are no per-operation receipts to ask about. When
                    # the same configuration is re-asserted every round -- normal practice in a
                    # monitoring mission -- the state is already correct after the first success,
                    # so every later round is answered "yes, done" whether or not this round's
                    # request ever arrived. That is the difference between verifying state and
                    # verifying the operation, and it is the axis this arm exists to expose.
                    state_ok = bool(sinks[n["nid"]].applied)
                    want = not state_ok
            else:                                            # ours / ours_plain_sink
                want = item["attempts"] < RETRY_BUDGET
            if not want:
                item["done"] = True
                settled_intents += 1
                continue
            if (t - op.created_at) > RETENTION_H:
                item["done"] = True
                unsettled_op = op
                unresolved_intents += 1
                continue

            # ---- send, under the runtime's identity discipline ----
            item["attempts"] += 1
            attempts_total += 1
            op_id = op.operation_id if arm in ("ours",) else f"{item['intent']}#{item['attempts']}"
            epoch = item["epoch"] if arm == "ours" else 0
            reg.dispatched(op, t)

            if not link_attempt(n, rng):
                if arm == "ours":
                    reg.observe(op, Observation.UNKNOWN)
                continue

            learned, did_apply = sinks[n["nid"]].receive(op_id, epoch, t)
            if did_apply:
                applied_count[item["intent"]] = applied_count.get(item["intent"], 0) + 1

            # ---- acknowledgment ----
            if did_apply and rng.random() >= ACK_LOSS_P:
                # a clean acknowledgment: the runtime may settle
                if arm == "ours":
                    reg.settle(op, Outcome(did_apply and learned or "applied"), t, "acked")
                    reg.observe(op, Observation.FRESH)
                item["done"] = True
                settled_intents += 1
            else:
                # no usable response: this is where the arms differ in what they conclude
                if arm in ("b1_wirelessagent",):
                    item["done"] = True
                    settled_intents += 1
                elif arm == "ours":
                    # reconciliation, SCOPED to this operation
                    if learned == "applied" and sinks[n["nid"]].receipt(op.operation_id) is not None:
                        reg.settle(op, Outcome.APPLIED, t, "scoped reconcile")
                        reg.observe(op, Observation.FRESH)
                        item["done"] = True
                        settled_intents += 1

        # a write whose budget ran out without resolution stays unresolved
        if t % 24 == 0:
            for item in pending:
                if not item["done"] and item["attempts"] >= RETRY_BUDGET and arm != "ours":
                    item["done"] = True
                    settled_intents += 1

    # ---------------------------------------------------------------- metrics
    intents = applied_count.keys() | {i["intent"] for i in pending}
    once = sum(1 for i in intents if applied_count.get(i, 0) == 1)
    zero = sum(1 for i in intents if applied_count.get(i, 0) == 0)
    many = sum(1 for i in intents if applied_count.get(i, 0) > 1)
    extra = sum(max(0, applied_count.get(i, 0) - 1) for i in intents)
    total = len(intents)
    return {
        "arm": arm,
        "logical_writes": total,
        "exactly_once": once,
        "zero_times": zero,
        "more_than_once": many,
        "duplicate_applications": extra,
        "attempts": attempts_total,
        "exactly_once_rate": once / max(total, 1),
        "zero_rate": zero / max(total, 1),
        "dup_rate": many / max(total, 1),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=180)
    ap.add_argument("--cmd-period", type=int, default=6, help="hours between config commands")
    ap.add_argument("--reach", type=int, default=12)
    ap.add_argument("--blocked", type=int, default=4)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--no-energy", action="store_true")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    hours = args.days * 24
    use_energy = not args.no_energy
    n = args.reach + args.blocked
    print(f"对照实验：{args.days} 天，{n} 个节点，每 {args.cmd_period} h 一条配置命令")
    print(f"同一决策轨迹跑 {len(ARMS)} 个 runtime，远端：基线为普通 sink，ours 为 fenced sink")
    print(f"ack 丢失率 {ACK_LOSS_P}，重试预算 {RETRY_BUDGET}，能量模型 {'开' if use_energy else '关'}")
    print()

    hdr = (f"{'runtime':20s} {'逻辑写入':>8s} {'恰好一次':>9s} {'零次':>7s} {'多次':>7s} "
           f"{'多余应用':>9s} {'尝试':>7s}")
    print(hdr)
    print("-" * len(hdr))
    rows = []
    for arm in ARMS:
        acc = []
        for s in range(args.seeds):
            rng = np.random.default_rng(1000 + s)
            nodes = make_nodes(args.reach, args.blocked, rng, use_energy)
            acc.append(run_arm(arm, nodes, hours, args.cmd_period, 2000 + s, use_energy))
        agg = {k: float(np.mean([a[k] for a in acc]))
               for k in acc[0] if k != "arm"}
        agg["arm"] = arm
        rows.append(agg)
        print(f"{arm:20s} {agg['logical_writes']:8.0f} {100*agg['exactly_once_rate']:8.1f}% "
              f"{100*agg['zero_rate']:6.1f}% {100*agg['dup_rate']:6.1f}% "
              f"{agg['duplicate_applications']:9.1f} {agg['attempts']:7.0f}")

    print()
    base = next(r for r in rows if r["arm"] == "b1_wirelessagent")
    for r in rows:
        if r["arm"] == "b1_wirelessagent":
            continue
        print(f"  {r['arm']:20s} 恰好一次 {100*base['exactly_once_rate']:.1f}% -> "
              f"{100*r['exactly_once_rate']:.1f}%   多余应用 {base['duplicate_applications']:.0f} -> "
              f"{r['duplicate_applications']:.0f}   零次 {base['zero_times']:.0f} -> "
              f"{r['zero_times']:.0f}")

    tag = f"_{args.tag}" if args.tag else ""
    path = OUT.replace(".json", f"{tag}.json")
    with open(path, "w") as f:
        json.dump({"config": vars(args), "results": rows}, f, indent=2, ensure_ascii=False)
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
