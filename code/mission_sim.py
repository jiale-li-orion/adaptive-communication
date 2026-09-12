#!/usr/bin/env python3
"""
mission_sim.py — the paper's core experiment: does the mission keep reporting while the
communication entities churn?

Everything before this file built the pieces. This drives them as an actual monitoring mission
and measures what a disaster-monitoring operator cares about: what fraction of the required
readings eventually arrive, how late, and at what energy cost.

Churn has three sources, and the point of the model is that they are NOT interchangeable:

  permanent   terrain blocks the path; no retry, no spreading factor, no power setting helps.
              Only an architecture change helps (relay, different site, different backhaul).
  transient   the link is up and down in bursts. Retrying works, and is what you should do.
  seasonal    the node is alive but cannot charge because it is cold. Waiting works; retrying
              burns the little energy it has left.

An agent that cannot tell these apart must pick one behaviour for all three, and every choice is
wrong for two of them. This file quantifies the cost of that.

Ground truth comes from the environment, never from what the agent believes:
  - terrain reachability and loss: results/coverage_grid.csv (real SRTM + Longley-Rice ITM)
  - transient churn: Gilbert-Elliott fitted to ChirpBox, p(g->b)=0.0712, p(b->g)=0.1567
  - seasonal death: the LiFePO4 + temperature-gate model in energy.py
  - relay coverage of permanently-blocked points: 24.4%, from the greedy relay siting run in
    results/coverage_summary.txt

Deps: numpy only.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import statistics as st
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
GRID = os.path.join(ROOT, "results", "coverage_grid.csv")
OUT = os.path.join(ROOT, "results", "mission_sim.json")
sys.path.insert(0, HERE)

POLICY_LIST = ("blind", "store_fwd", "eager_relay", "churn_aware")

P_GOOD_TO_BAD = 0.071211        # ChirpBox, hourly, 420 directed links, 878万 transfers
P_BAD_TO_GOOD = 0.156721
RELAY_COVERAGE = 0.244          # share of permanently-blocked points one relay can serve
RELAY_DELIVERY = 0.85           # delivery probability once the relay path exists
HEATED_FRACTION = 0.5           # share of sites whose battery box is heated (removes the gate)

SENS = {7: -123.0, 8: -126.0, 9: -129.0, 10: -132.0, 11: -134.5, 12: -137.0}
TX_DBM, G_TX, G_RX, FEEDER = 14.0, 2.0, 2.0, 1.0
TX_MA, TX_V = 44.0, 3.6
RETENTION_H = 168               # a sample older than 7 days is dropped from the node buffer
# streak at which each policy concludes "permanent" and orders a relay; None = never orders
RELAY_TAU = {"blind": None, "store_fwd": None, "never_relay": None,
             "eager_relay": 3, "churn_aware": 12}
DEPLOY_H = 48                   # hours from ordering a relay to it being in service

_DEM = None


def airtime_ms(sf: int, payload_b: int = 38, bw_khz: float = 125.0) -> float:
    bitrate = {7: 5469, 8: 3125, 9: 1758, 10: 977, 11: 537, 12: 293}[sf]
    return 8 * payload_b / (bitrate * bw_khz / 125.0) * 1000.0


def tx_wh(sf: int) -> float:
    return TX_MA * TX_V / 1000.0 * (airtime_ms(sf) / 1000.0) / 3600.0


def load_terrain() -> tuple[list[dict], list[dict]]:
    reach, blocked = [], []
    with open(GRID) as f:
        for r in csv.DictReader(f):
            sf = int(r["best_sf(-1=unreachable)"])
            rec = {"lat": float(r["lat"]), "lon": float(r["lon"]),
                   "loss_db": float(r["loss_dB"]), "sf": sf}
            (reach if sf > 0 else blocked).append(rec)
    return reach, blocked


def success_prob_given_good(loss_db: float, sf: int) -> float:
    """Terrain loss sets how much margin a node has even while the link is in its good state."""
    margin = TX_DBM + G_TX + G_RX - FEEDER - loss_db - SENS[sf]
    return float(1.0 / (1.0 + math.exp(-margin / 5.0)))


def elevation(rec: dict) -> float:
    global _DEM
    if _DEM is None:
        from dem_to_mitsuba import load_tile
        _DEM = load_tile()
    from dem_to_mitsuba import elev_at
    return elev_at(_DEM, rec["lat"], rec["lon"])


class Node:
    __slots__ = ("nid", "sf", "loss_db", "permanent", "servable", "via_relay", "energy",
                 "good", "sched", "delivered", "late", "latency", "tx", "energy_wh")

    def __init__(self, nid, sf, loss_db, permanent, via_relay, energy):
        self.nid, self.sf, self.loss_db = nid, sf, loss_db
        self.permanent, self.servable, self.via_relay = permanent, via_relay, False
        self.energy = energy
        self.good = True
        self.sched = self.delivered = self.late = self.tx = 0
        self.latency: list[int] = []
        self.energy_wh = 0.0


def make_nodes(n_reach: int, n_blocked: int, rng, use_energy: bool) -> list[Node]:
    reach, blocked = load_terrain()
    # pick nodes spread over the terrain rather than clustered: take the farthest-apart sample
    def spread(pool, k):
        idx = rng.choice(len(pool), min(k, len(pool)), replace=False)
        return [pool[i] for i in idx]

    nodes: list[Node] = []
    from energy import NodeEnergy

    def mk(r, nid, permanent, relay):
        # a permanently-blocked point has no usable SF; it would transmit at the slowest one
        sf = 12 if permanent else r["sf"]
        if not use_energy:
            return Node(nid, sf, r["loss_db"], permanent, relay, None)
        # Real deployments differ in whether the battery box is heated. A heated box removes the
        # +5 C charge gate and the node survives; an unheated one cannot charge for most of the
        # year and goes seasonally silent. That difference IS the third churn source, so the mix
        # is part of the scenario rather than a tuning knob.
        e = NodeEnergy(elev_m=elevation(r), rng=rng, heated=bool(rng.random() < HEATED_FRACTION))
        return Node(nid, sf, r["loss_db"], permanent, relay, e)

    for k, r in enumerate(spread(reach, n_reach)):
        nodes.append(mk(r, f"r{k:02d}", False, False))
    for k, r in enumerate(spread(blocked, n_blocked)):
        # whether a relay CAN serve this point is terrain-determined and unknown in advance;
        # only RELAY_COVERAGE of blocked points are servable at all
        nodes.append(mk(r, f"b{k:02d}", True, bool(rng.random() < RELAY_COVERAGE)))
    return nodes


class Agent:
    """The coordinator. Its knowledge comes ONLY from the outcomes of its own attempts.

    It never reads the node's energy state, never sees whether the terrain blocks the path, and
    never learns the true outage length. Everything below is inferred from a sequence of
    successes and failures, which is precisely why permanent and transient are hard to separate.
    """

    def __init__(self, nodes: list[Node], tau: int, deploy_h: int):
        self.nodes = nodes
        self.tau = tau                     # failure streak at which a node is called permanent
        self.deploy_h = deploy_h
        self.streak = {n.nid: 0 for n in nodes}
        self.ever_ok = {n.nid: False for n in nodes}
        self.ordered: dict[str, int] = {}  # nid -> hour the relay was ordered
        self.relays_ordered = 0
        self.relays_wasted = 0

    def note(self, n: Node, ok: bool) -> None:
        if ok:
            self.ever_ok[n.nid] = True
            self.streak[n.nid] = 0
        else:
            self.streak[n.nid] += 1

    def belief(self, n: Node) -> str:
        """Observation-only classification. No ground truth is consulted."""
        if n.via_relay:
            return "relayed"
        if n.nid in self.ordered:
            return "relay_pending"
        st = self.streak[n.nid]
        if st >= self.tau and not self.ever_ok[n.nid]:
            return "permanent"
        if st >= self.tau and self.ever_ok[n.nid]:
            # it worked once and has been silent for a long time: a seasonal silence or a very
            # long fade, not a terrain block. Waiting is correct; ordering a relay is not.
            return "long_silence"
        return "transient"

    def consider_relay(self, n: Node, t: int, policy: str) -> None:
        """Decide whether to spend on an architecture change. This is the actual tradeoff."""
        if n.nid in self.ordered or n.via_relay:
            return
        tau = RELAY_TAU.get(policy)
        if tau is None:
            return                          # this policy never orders relays
        if self.streak[n.nid] < tau:
            return
        if self.ever_ok[n.nid]:
            # It worked once. A ChirpBox down-burst has p99 = 42 h, so a long silence here is
            # far more likely to be the tail of a transient fade than a terrain block. Ordering a
            # relay on this evidence is how an impatient coordinator wastes its budget.
            return
        self.ordered[n.nid] = t
        self.relays_ordered += 1

    def poll_deploy(self, t: int) -> None:
        for nid, t0 in list(self.ordered.items()):
            if t - t0 < self.deploy_h:
                continue
            n = next(x for x in self.nodes if x.nid == nid)
            if not n.permanent or not n.servable:
                # either it was never blocked (a transient called permanent) or terrain makes
                # this point unservable by any relay. Both are money spent for nothing.
                self.relays_wasted += 1
            n.via_relay = n.permanent and n.servable
            del self.ordered[nid]


def should_attempt(policy: str, agent: Agent, n: Node, t: int, oldest: int) -> bool:
    if policy == "blind":
        return True
    bel = agent.belief(n)
    if bel == "permanent":
        # The direct path is written off; only the relay can carry this node's data now.
        return False
    if bel == "relay_pending":
        return False
    # transient AND long_silence both keep retrying: a node that has ever delivered must never
    # be written off, because the outage distribution has a 42 h p99 tail and writing it off is
    # irreversible while waiting costs almost nothing.
    return (t - oldest) < RETENTION_H


def run_mission(policy: str, nodes: list[Node], hours: int, period_h: int,
                seed: int, tau: int = 12, cmd_period_h: int = 24,
                use_energy: bool = True) -> dict:
    rng = np.random.default_rng(seed)
    agent = Agent(nodes, tau=tau, deploy_h=DEPLOY_H)
    pending: dict[str, list[int]] = {n.nid: [] for n in nodes}
    daily_ok: dict[str, set] = {n.nid: set() for n in nodes}
    scheduled = delivered = late = dropped = 0
    cmd_issued = cmd_applied = cmd_dup = cmd_miss = 0

    for t in range(hours):
        doy = t // 24
        agent.poll_deploy(t)
        for n in nodes:
            if n.energy is not None:
                n.energy.step(doy)
            alive = (n.energy is None) or n.energy.alive

            if not n.permanent:
                if n.good:
                    if rng.random() < P_GOOD_TO_BAD:
                        n.good = False
                elif rng.random() < P_BAD_TO_GOOD:
                    n.good = True

            fresh = (t % period_h == 0)
            if fresh:
                pending[n.nid].append(t)
                n.sched += 1
                scheduled += 1
            # expire what has been held too long
            keep = [s for s in pending[n.nid] if t - s <= RETENTION_H]
            dropped += len(pending[n.nid]) - len(keep)
            pending[n.nid] = keep

            if not alive:
                # a dead node keeps its queued samples; the agent does not know yet
                continue
            bufs = pending[n.nid]
            if not bufs:
                continue
            if policy == "blind":
                # no store-and-forward: attempt once for the sample that is due this hour and
                # drop it if that attempt fails. Anything older is discarded without an attempt.
                if not fresh:
                    pending[n.nid] = [t]
                    continue
                dropped += len(bufs) - 1
                bufs = pending[n.nid] = [t]
            elif not should_attempt(policy, agent, n, t, bufs[0]):
                continue

            n.tx += 1
            cost = tx_wh(n.sf)
            n.energy_wh += cost
            if n.energy is not None:
                n.energy.bat_wh = max(0.0, n.energy.bat_wh - cost)

            if n.permanent:
                ok = n.via_relay and (rng.random() < RELAY_DELIVERY)
                delay = 1
            else:
                ok = n.good and (rng.random() < success_prob_given_good(n.loss_db, n.sf))
                delay = 0
            agent.note(n, ok)
            agent.consider_relay(n, t, policy)
            if not ok:
                if policy == "blind":
                    bufs.clear()          # dropped: this is what "no store-and-forward" means
                    dropped += 1
                continue

            for s in list(bufs):
                age = t - s + delay
                n.delivered += 1
                delivered += 1
                n.latency.append(age)
                if age > period_h:
                    n.late += 1
                    late += 1
                daily_ok[n.nid].add(s // 24)
            bufs.clear()

        # ------------------------------------------------------- downlink command
        if t % cmd_period_h == 0:
            for n in nodes:
                alive = (n.energy is None) or n.energy.alive
                if not alive:
                    cmd_miss += 1
                    continue
                if n.permanent and not n.via_relay:
                    cmd_miss += 1
                    continue
                cmd_issued += 1
                ok = (rng.random() < RELAY_DELIVERY) if n.permanent else (
                    n.good and rng.random() < success_prob_given_good(n.loss_db, n.sf))
                if ok:
                    cmd_applied += 1
                elif policy in ("blind", "retry"):
                    # a coordinator with no stable intent re-sends under a FRESH identity,
                    # so a second application of the same logical command is possible
                    cmd_issued += 1
                    ok2 = (rng.random() < RELAY_DELIVERY) if n.permanent else (
                        n.good and rng.random() < success_prob_given_good(n.loss_db, n.sf))
                    if ok2:
                        cmd_applied += 1
                        cmd_dup += 1

    total_days = hours // 24
    possible_days = len(nodes) * total_days
    lat = [x for n in nodes for x in n.latency]
    return {
        "policy": policy,
        "scheduled": scheduled,
        "delivered": delivered,
        "reporting_rate": delivered / max(1, scheduled),
        "on_time_rate": (delivered - late) / max(1, scheduled),
        "daily_resolution_rate": sum(len(v) for v in daily_ok.values()) / max(1, possible_days),
        "latency_median_h": st.median(lat) if lat else None,
        "latency_p90_h": float(np.quantile(lat, 0.9)) if lat else None,
        "latency_p99_h": float(np.quantile(lat, 0.99)) if lat else None,
        "dropped_expired": dropped,
        "tx_per_node": sum(n.tx for n in nodes) / len(nodes),
        "wh_per_node": sum(n.energy_wh for n in nodes) / len(nodes),
        "nodes_alive_end": sum(1 for n in nodes if n.energy is None or n.energy.alive),
        "nodes_total": len(nodes),
        "cmd_issued": cmd_issued,
        "cmd_applied": cmd_applied,
        "cmd_duplicates": cmd_dup,
        "cmd_missed": cmd_miss,
        "relays_ordered": agent.relays_ordered,
        "relays_wasted": agent.relays_wasted,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=180)
    ap.add_argument("--period", type=int, default=1)
    ap.add_argument("--reach", type=int, default=12)
    ap.add_argument("--blocked", type=int, default=4)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--no-energy", action="store_true")
    ap.add_argument("--tau", type=int, default=12, help="failure streak that means permanent")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    hours = args.days * 24
    use_energy = not args.no_energy
    n = args.reach + args.blocked
    print(f"监测 mission：{args.days} 天（{hours} 个逐小时步长）")
    print(f"节点：{args.reach} 个地形可达 + {args.blocked} 个永久遮挡   上报间隔 {args.period} h")
    print(f"能量模型：{'开启' if use_energy else '关闭'}   随机种子 {args.seeds}")
    print(f"churn：GE p(g->b)={P_GOOD_TO_BAD:.4f} p(b->g)={P_BAD_TO_GOOD:.4f}，"
          f"中继覆盖 {100*RELAY_COVERAGE:.1f}% 的遮挡点")
    print()

    inner = (f"{'policy':13s} {'到报率':>8s} {'准时率':>8s} {'日均分辨率':>10s} "
             f"{'时延中位':>9s} {'p90':>6s} {'TX/节点':>8s} {'Wh/节点':>10s} "
             f"{'存活':>6s} {'命令重复':>9s} {'中继':>6s} {'白架':>6s}")
    print(inner)
    print("-" * len(inner))

    rows = []
    for policy in POLICY_LIST:
        acc = []
        for s in range(args.seeds):
            rng = np.random.default_rng(1000 + s)
            nodes = make_nodes(args.reach, args.blocked, rng, use_energy)
            acc.append(run_mission(policy, nodes, hours, args.period, 2000 + s,
                                   tau=args.tau, use_energy=use_energy))
        keys = [k for k in acc[0] if acc[0][k] is not None and k != "policy"]
        agg = {k: float(np.mean([a[k] for a in acc])) for k in keys}
        agg["policy"] = policy
        rows.append(agg)
        print(f"{policy:13s} {100*agg['reporting_rate']:7.1f}% {100*agg['on_time_rate']:7.1f}% "
              f"{100*agg['daily_resolution_rate']:9.1f}% {agg['latency_median_h']:9.1f} "
              f"{agg['latency_p90_h']:6.1f} {agg['tx_per_node']:8.1f} {agg['wh_per_node']:10.5f} "
              f"{agg['nodes_alive_end']:3.0f}/{agg['nodes_total']:<2.0f} "
              f"{agg['cmd_duplicates']:9.1f} {agg['relays_ordered']:6.1f} {agg['relays_wasted']:6.1f}")

    print()
    b = next(r for r in rows if r["policy"] == "blind")
    for r in rows:
        if r["policy"] == "blind":
            continue
        d = (r["reporting_rate"] - b["reporting_rate"]) * 100
        e = r["wh_per_node"] / max(b["wh_per_node"], 1e-12)
        print(f"  {r['policy']:13s} 到报率 {100*b['reporting_rate']:.1f}% -> "
              f"{100*r['reporting_rate']:.1f}%  ({d:+.1f} 个百分点)   "
              f"能耗 {e:.2f}x 盲发   命令重复 {r['cmd_duplicates']:.0f} "
              f"中继 {r['relays_ordered']:.0f} 个（白架 {r['relays_wasted']:.0f}）")

    tag = f"_{args.tag}" if args.tag else ""
    path = OUT.replace(".json", f"{tag}.json")
    with open(path, "w") as f:
        json.dump({"config": vars(args), "results": rows}, f, indent=2, ensure_ascii=False)
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
