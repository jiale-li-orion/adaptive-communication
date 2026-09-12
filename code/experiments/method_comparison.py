#!/usr/bin/env python3
"""
method_comparison.py — the paper's main experiment.

One fixed decision trajectory, several execution runtimes. The agent decides the same thing at
the same hour; only the layer that turns that decision into a remote effect changes. That keeps
the causal claim clean:

    same agent  +  same action  +  same channel  +  different runtime

THE CHANNEL CARRIES EVERYTHING. The runtime's only view of the far side is through the same
lossy link it uses to act. There is no out-of-band health channel, and this file enforces that:
every verification and every reconciliation is a communication operation, subject to the same
link state, the same reply loss and the same airtime cost as a write. A runtime that could read
the far side for free would be solving an easier problem than the one this paper states — the
hard part is precisely that the receipt exists remotely but may not be reachable right now.

Two workloads are run, because they score different things and favour different methods:

  operation       every command is independently meaningful (versioned threshold update, alarm
                  acknowledgement, triggered measurement, watchdog refresh). Its logical
                  identity is the deliverable, so "was THIS command executed exactly once" is
                  not an artificial requirement.

  state_setting   the desired configuration cycles (1h -> 10min -> 5min -> 1h) and a round
                  succeeds when the desired state is in force. A configuration already in force
                  does not need re-execution, so a method that verifies state is doing something
                  legitimate here.

Reporting only the second would flatter the operation-scoped protocol; reporting only the first
would flatter state verification. Both are reported.

Every protocol message is counted and converted to airtime: data writes, verification reads,
reconciliation reads, and the reply leg of each.

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
sys.path.insert(0, HERE)

from operations import OperationRegistry, Outcome, Observation   # noqa: E402

GRID = os.path.join(ROOT, "results", "coverage_grid.csv")
OUT = os.path.join(ROOT, "results", "method_comparison.json")

P_GOOD_TO_BAD = 0.071211
P_BAD_TO_GOOD = 0.156721
ACK_LOSS_P = 0.35
RETRY_BUDGET = 3
RETENTION_H = 168
HEATED_FRACTION = 0.5
RELAY_DELIVERY = 0.85
RELAY_AVAILABILITY = 1.0

SENS = {7: -123.0, 8: -126.0, 9: -129.0, 10: -132.0, 11: -134.5, 12: -137.0}
TX_DBM, G_TX, G_RX, FEEDER = 14.0, 2.0, 2.0, 1.0

ARMS = ("one_shot", "retry_uncertainty", "verified_tool_calls", "ours", "ours_plain_sink",
        "ablate_identity", "ablate_fencing", "ablate_receipts", "ablate_scope")
RELAY_ARMS = ("relay_retry_uncertainty", "relay_ours")

# far side: (keeps per-operation receipts, enforces monotonic epoch) ; stable write identity
ARM_SPEC = {
    "one_shot":              ((False, False), False),
    "retry_uncertainty":     ((False, False), False),
    # the published wrapper passes one deterministic idempotency key with every attempt
    "verified_tool_calls":   ((False, False), True),
    "ours":                  ((True,  True),  True),
    "ours_plain_sink":       ((False, False), True),
    # Ablations. They remove one ingredient at a time so the protocol does not read as a
    # monolith.
    "ablate_identity":       ((True,  True),  False),   # stable write identity removed
    "ablate_fencing":        ((True,  False), True),    # C2 removed, C1 kept
    "ablate_receipts":       ((False, True),  True),    # C1 removed, C2 kept
    "ablate_scope":          ((True,  True),  True),    # reconciliation predicate not scoped
}

STATE_SCHEDULE = ("1h", "10min", "5min", "1h")
OP_KINDS = ("threshold_update", "alarm_ack", "trigger_measurement", "watchdog_refresh")


def airtime_ms(sf: int, payload_b: int = 38, bw_khz: float = 125.0) -> float:
    bitrate = {7: 5469, 8: 3125, 9: 1758, 10: 977, 11: 537, 12: 293}[sf]
    return 8 * payload_b / (bitrate * bw_khz / 125.0) * 1000.0


def load_terrain():
    reach, blocked = [], []
    with open(GRID) as f:
        for r in csv.DictReader(f):
            sf = int(r["best_sf(-1=unreachable)"])
            (reach if sf > 0 else blocked).append(
                {"lat": float(r["lat"]), "lon": float(r["lon"]),
                 "loss_db": float(r["loss_dB"]), "sf": sf})
    return reach, blocked


def p_given_good(loss_db, sf):
    margin = TX_DBM + G_TX + G_RX - FEEDER - loss_db - SENS[sf]
    return 1.0 / (1.0 + math.exp(-margin / 5.0))


def make_nodes(n_reach, n_blocked, rng, use_energy, heated_fraction=HEATED_FRACTION):
    reach, blocked = load_terrain()
    picks = [(reach[i], False) for i in rng.choice(len(reach), n_reach, replace=False)]
    picks += [(blocked[i], True) for i in rng.choice(len(blocked), n_blocked, replace=False)]
    dem = elv = None
    if use_energy:
        from dem_to_mitsuba import elev_at, load_tile
        dem = load_tile(); elv = elev_at
    nodes = []
    for k, (r, permanent) in enumerate(picks):
        nd = {"nid": f"{'b' if permanent else 'r'}{k:02d}",
              "sf": 12 if permanent else r["sf"], "loss_db": r["loss_db"],
              "permanent": permanent, "good": not permanent, "alive": True, "energy": None,
              "servable": bool(rng.random() < 0.244)}
        if use_energy:
            from energy import NodeEnergy
            nd["energy"] = NodeEnergy(elev_m=elv(dem, r["lat"], r["lon"]), rng=rng,
                                      heated=bool(rng.random() < heated_fraction))
        nodes.append(nd)
    return nodes


class FarSide:
    """The entity at the far end. Nothing here is reachable without crossing the link."""

    def __init__(self, nid, receipts: bool, fencing: bool):
        self.nid = nid
        self.keeps_receipts = receipts
        self.fenced = fencing
        self.last_accepted_epoch = 0
        self.receipts: dict[str, Outcome] = {}
        self.applied_writes: list[tuple[int, str]] = []
        self.state = {"rate": "1h", "version": 0, "alarms": set(), "last_watchdog": None}
        # when the rate changed, so a round boundary can ask what was in force at that time
        self.rate_timeline: list[tuple[int, str]] = [(0, "1h")]

    def apply(self, op_id, epoch, payload, t):
        """Returns (outcome, did_apply). A deduplicated repeat is APPLIED but did NOT apply."""
        if self.keeps_receipts and op_id in self.receipts:
            return Outcome.APPLIED, False
        if self.fenced and epoch <= self.last_accepted_epoch and self.last_accepted_epoch > 0:
            return Outcome.SUPERSEDED, False
        if self.fenced:
            self.last_accepted_epoch = epoch
        if self.keeps_receipts:
            self.receipts[op_id] = Outcome.APPLIED
        self.applied_writes.append((t, op_id))
        if "rate" in payload:
            self.state["rate"] = payload["rate"]
            self.rate_timeline.append((t, payload["rate"]))
        if "version" in payload:
            self.state["version"] = max(self.state["version"], payload["version"])
        if "alarm" in payload:
            self.state["alarms"].add(payload["alarm"])
        if payload.get("watchdog"):
            self.state["last_watchdog"] = t
        return Outcome.APPLIED, True

    def read_state(self):
        return dict(self.state) | {"alarms": sorted(self.state["alarms"])}

    def read_receipt(self, op_id):
        return self.receipts.get(op_id)


class Link:
    """Every message crosses this. Charges both legs and reports what survived."""

    def __init__(self, rng):
        self.rng = rng
        self.msg = {"data_write": 0, "verify_read": 0, "reconcile_read": 0,
                    "replies": 0, "reply_lost": 0}
        self.airtime_ms_total = 0.0

    def exchange(self, node, kind):
        """Returns (arrived, replied). Airtime is charged whether or not either leg survives."""
        self.msg[kind] = self.msg.get(kind, 0) + 1
        self.airtime_ms_total += 2 * airtime_ms(node["sf"])      # uplink + downlink
        if node["permanent"] or not node["alive"]:
            self.msg["reply_lost"] += 1
            return False, False
        if not (node["good"] and self.rng.random() < p_given_good(node["loss_db"], node["sf"])):
            self.msg["reply_lost"] += 1
            return False, False
        if self.rng.random() < ACK_LOSS_P:
            self.msg["reply_lost"] += 1
            return True, False
        self.msg["replies"] += 1
        return True, True


def postcondition_holds(state, target, workload) -> bool:
    """The postcondition STATE predicate: is the intended effect in place right now?

    Operation-scoped or not is a property of the predicate, not of a choice here. In the
    operation workload the target carries a version and an alarm id, so the predicate is
    genuinely specific to that command. In the state-setting workload the target is a rate, and
    the predicate is satisfied by any earlier round that produced the same rate.
    """
    if "rate" in target:
        return state.get("rate") == target["rate"]
    if "alarm" in target:
        return target["alarm"] in state.get("alarms", ())
    if target.get("watchdog"):
        return state.get("last_watchdog") is not None
    if "version" in target:
        return state.get("version", 0) >= target["version"]
    return False


def run_arm(arm, nodes, hours, cmd_period, seed, use_energy, workload,
            retry_budget=RETRY_BUDGET, relay=False, relay_availability=RELAY_AVAILABILITY):
    rng = np.random.default_rng(seed)
    base_arm = arm[6:] if arm.startswith("relay_") else arm
    (receipts, fencing), stable_id = ARM_SPEC[base_arm]
    if arm.startswith("relay_"):
        stable_id = (arm == "relay_ours")
        receipts, fencing = ((True, True) if arm == "relay_ours" else (False, False))

    sinks = {n["nid"]: FarSide(n["nid"], receipts, fencing) for n in nodes}
    link = Link(rng)
    reg = OperationRegistry()

    outcomes: dict[str, int] = {}
    pending: list[dict] = []
    relay_buf: dict[str, list] = {n["nid"]: [] for n in nodes}
    rounds_created = 0

    def channel_read(n, kind):
        """A read behind the channel. Returns (state_or_None, 'reply' | 'unknown')."""
        arrived, replied = link.exchange(n, kind)
        if not (arrived and replied):
            return None, "unknown"
        return sinks[n["nid"]].read_state(), "reply"

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
            r = t // cmd_period
            for n in nodes:
                if workload == "state_setting":
                    target = STATE_SCHEDULE[r % len(STATE_SCHEDULE)]
                    payload = {"rate": target}
                    intent = f"{n['nid']}:rate:{r}"
                else:
                    kind = OP_KINDS[r % len(OP_KINDS)]
                    payload = {"version": r + 1, "op": kind, "alarm": f"a{r}",
                               "watchdog": kind == "watchdog_refresh"}
                    intent = f"{n['nid']}:{kind}:{r}"
                rounds_created += 1
                op = reg.register(n["nid"], "command", payload, intent, t, True)
                pending.append({"op": op, "node": n, "intent": intent, "payload": payload,
                                "attempts": 0, "done": False})

        # ---------------- the runtime carries the decision ----------------
        for item in pending:
            if item["done"]:
                continue
            op, n = item["op"], item["node"]

            # ---- does this runtime attempt anything this hour? ----
            if arm == "one_shot":
                want = (item["attempts"] == 0)
            elif arm == "retry_uncertainty":
                want = item["attempts"] < retry_budget
            elif arm == "verified_tool_calls":
                want = None
                if item["attempts"] == 0:
                    want = True
                elif item["attempts"] >= retry_budget:
                    want = False
                else:
                    # the published algorithm's loop is `for i = 1 to N`, and its UNKNOWN branch
                    # does `continue`. The loop counter therefore advances on an inconclusive
                    # read just as it does on a definitive one, so a verification round consumes
                    # a retry slot. Without that, an unreadable state would be re-queried every
                    # hour until retention expires.
                    item["verify_rounds"] = item.get("verify_rounds", 0) + 1
                    if item["attempts"] + item["verify_rounds"] >= retry_budget:
                        want = False
                    else:
                        state, verdict = channel_read(n, "verify_read")
                        if verdict != "reply":
                            want = "wait"      # UNKNOWN: inconclusive, back off, do not resend
                        elif postcondition_holds(state, item["payload"], workload):
                            want = False       # True: the effect is in place, stop
                        else:
                            want = True        # False: not in place, re-execute
                if want is None:
                    raise AssertionError("verified_tool_calls left `want` unset")
            else:
                want = item["attempts"] < retry_budget

            if want == "wait":
                continue
            if not want:
                item["done"] = True
                continue
            if (t - op.created_at) > RETENTION_H:
                item["done"] = True
                continue

            # ---- send ----
            item["attempts"] += 1
            reg.dispatched(op, t)
            op_id = op.operation_id if stable_id else f"{item['intent']}#{item['attempts']}"
            epoch = item["op"].epoch if fencing else 0

            if arm.startswith("relay_") and n["permanent"] and n["servable"] \
                    and rng.random() < relay_availability:
                arrived, _ = link.exchange(n, "data_write")
                if arrived:
                    relay_buf[n["nid"]].append((op_id, epoch, item))
                continue

            arrived, replied = link.exchange(n, "data_write")
            if not arrived:
                continue
            outcome, did = sinks[n["nid"]].apply(op_id, epoch, item["payload"], t)
            if did:
                outcomes[item["intent"]] = outcomes.get(item["intent"], 0) + 1
            if replied:
                reg.settle(op, outcome, t, "replied")
                item["done"] = True
            else:
                reg.observe(op, Observation.UNKNOWN)
                if arm in ("ours", "ours_plain_sink", "ablate_identity", "ablate_fencing",
                           "ablate_receipts", "ablate_scope"):
                    # reconciliation is itself a communication operation
                    state, verdict = channel_read(n, "reconcile_read")
                    if verdict == "reply":
                        if arm == "ablate_scope":
                            # the unscoped question: "has anything ever landed here?", which an
                            # earlier round answers yes to
                            hit = bool(sinks[n["nid"]].applied_writes)
                        else:
                            hit = sinks[n["nid"]].read_receipt(op.operation_id) is Outcome.APPLIED
                        if hit:
                            reg.settle(op, Outcome.APPLIED, t, "reconciled")
                            item["done"] = True

        # ---------------- the relay's own delivery attempts ----------------
        if arm.startswith("relay_"):
            for n in nodes:
                if not relay_buf[n["nid"]] or rng.random() >= RELAY_DELIVERY:
                    continue
                rop, repoch, item = relay_buf[n["nid"]][0]
                arrived, replied = link.exchange(n, "data_write")
                if not arrived:
                    continue
                _o, did = sinks[n["nid"]].apply(rop, repoch, item["payload"], t)
                if did:
                    outcomes[item["intent"]] = outcomes.get(item["intent"], 0) + 1
                relay_buf[n["nid"]].pop(0)
                if replied:
                    item["done"] = True

    # ---------------------------------------------------------------- metrics
    intents = set(outcomes) | {i["intent"] for i in pending}
    once = sum(1 for i in intents if outcomes.get(i, 0) == 1)
    zero = sum(1 for i in intents if outcomes.get(i, 0) == 0)
    many = sum(1 for i in intents if outcomes.get(i, 0) > 1)
    extra = sum(max(0, outcomes.get(i, 0) - 1) for i in intents)
    total = max(len(intents), 1)

    # The two workloads score different things. `operation` asks whether each command was
    # executed exactly once. `state_setting` asks whether the desired state was in force at the
    # end of each round, and a round whose target was already satisfied needs no execution at
    # all -- counting it as a zero-effect failure is what the operation metric would do, and it
    # is the wrong question for this workload.
    satisfied = 0
    rounds = max(1, hours // cmd_period)
    if workload == "state_setting":
        for n in nodes:
            tl = sinks[n["nid"]].rate_timeline
            for r in range(rounds):
                target = STATE_SCHEDULE[r % len(STATE_SCHEDULE)]
                boundary = min((r + 1) * cmd_period, hours - 1)
                # the rate in force at the end of this round
                in_force = tl[0][1]
                for (tt, rate) in tl:
                    if tt <= boundary:
                        in_force = rate
                    else:
                        break
                if in_force == target:
                    satisfied += 1
        state_rate = satisfied / max(len(nodes) * rounds, 1)
    else:
        state_rate = float("nan")

    m = link.msg
    return {
        "arm": arm, "workload": workload, "intents": total,
        "exactly_once": once, "zero_times": zero, "more_than_once": many,
        "duplicate_applications": extra,
        "exactly_once_rate": once / total, "zero_rate": zero / total,
        "dup_rate": many / total, "state_satisfied_rate": state_rate,
        "rounds_created": rounds_created,
        "data_writes": m["data_write"], "verify_reads": m["verify_read"],
        "reconcile_reads": m["reconcile_read"], "replies": m["replies"],
        "reply_lost": m["reply_lost"],
        "protocol_messages": m["data_write"] + m["verify_read"] + m["reconcile_read"] + m["replies"],
        "airtime_s": link.airtime_ms_total / 1000.0,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=180)
    ap.add_argument("--cmd-period", type=int, default=6)
    ap.add_argument("--reach", type=int, default=12)
    ap.add_argument("--blocked", type=int, default=4)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--no-energy", action="store_true")
    ap.add_argument("--heated", type=float, default=None)
    ap.add_argument("--retry-budget", type=int, default=RETRY_BUDGET)
    ap.add_argument("--workload", default="operation",
                    choices=["operation", "state_setting", "both"])
    ap.add_argument("--relay", action="store_true")
    ap.add_argument("--relay-availability", type=float, default=RELAY_AVAILABILITY)
    ap.add_argument("--arms", default="")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    hours = args.days * 24
    use_energy = not args.no_energy
    hf = HEATED_FRACTION if args.heated is None else args.heated
    workloads = ["operation", "state_setting"] if args.workload == "both" else [args.workload]
    arms = RELAY_ARMS if args.relay else ARMS
    if args.arms:
        want = tuple(x.strip() for x in args.arms.split(","))
        arms = tuple(a for a in arms if a in want)

    print(f"对照实验：{args.days} 天，{args.reach + args.blocked} 个节点，"
          f"每 {args.cmd_period} h 一条命令")
    print(f"workload {', '.join(workloads)}   重试预算 {args.retry_budget}   "
          f"加热比例 {hf}   能量模型 {'开' if use_energy else '关'}")
    print("写入 / 验证读 / 调和读 / 回复 全部走同一条链路并计入空口")
    print()

    rows = []
    for wl in workloads:
        print(f"===== workload: {wl} =====")
        hdr = (f"{'runtime':22s} {'恰好一次':>8s} {'零次':>7s} {'多余':>7s} {'重复':>8s} "
               f"{'写入':>7s} {'验证读':>7s} {'调和读':>7s} {'回复':>8s} {'空口h':>7s}")
        print(hdr); print("-" * len(hdr))
        for arm in arms:
            acc = []
            for s in range(args.seeds):
                rng = np.random.default_rng(1000 + s)
                nodes = make_nodes(args.reach, args.blocked, rng, use_energy, hf)
                acc.append(run_arm(arm, nodes, hours, args.cmd_period, 2000 + s, use_energy,
                                   wl, retry_budget=args.retry_budget, relay=args.relay,
                                   relay_availability=args.relay_availability))
            agg = {k: float(np.mean([a[k] for a in acc])) for k in acc[0]
                   if isinstance(acc[0][k], (int, float))}
            agg["arm"] = arm; agg["workload"] = wl
            rows.append(agg)
            print(f"{arm:22s} {100*agg['exactly_once_rate']:7.1f}% {100*agg['zero_rate']:6.1f}% "
                  f"{100*agg['dup_rate']:6.1f}% {agg['duplicate_applications']:8.1f} "
                  f"{agg['data_writes']:7.0f} {agg['verify_reads']:7.0f} "
                  f"{agg['reconcile_reads']:7.0f} {agg['replies']:8.0f} {agg['airtime_s']/3600:7.1f}"
                  + (f"  {100*agg['state_satisfied_rate']:6.1f}%" if wl == "state_setting" else ""))
        print()

    tag = f"_{args.tag}" if args.tag else ""
    path = OUT.replace(".json", f"{tag}.json")
    with open(path, "w") as f:
        json.dump({"config": vars(args), "results": rows}, f, indent=2, ensure_ascii=False)
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
