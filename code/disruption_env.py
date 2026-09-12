#!/usr/bin/env python3
"""
disruption_env.py — a trace-grounded disruption-tolerant tool-execution environment.

Node reachability comes from REAL terrain (the Longley-Rice coverage grid in
results/coverage_grid.csv). Node liveness comes from a power model. Tool calls that cross a
node's death or an ACK loss produce the failure classes defined in
docs/s5-benchmark/s5-1-failure-model.md.

The environment owns the GROUND TRUTH about side effects, so duplicate side effects can be
counted rather than inferred. That is the whole point: the agent cannot know, we can.

Deps: numpy only.
"""
from __future__ import annotations

import csv
import json
import math
import os
from dataclasses import dataclass, field

import numpy as np

from operations import OperationRegistry, MAY_HAVE_EFFECT

HERE = os.path.dirname(os.path.abspath(__file__))
GRID = os.path.normpath(os.path.join(HERE, "..", "results", "coverage_grid.csv"))
LOSS_MODEL = os.path.normpath(os.path.join(HERE, "..", "results", "loss_model.json"))
HGT = os.path.normpath(os.path.join(HERE, "..", "data", "dem", "hgt", "N30E094.hgt"))

_DEM = None


def _dem():
    global _DEM
    if _DEM is None:
        raw = np.fromfile(HGT, dtype=">i2")
        _DEM = raw.reshape(int(round(math.sqrt(raw.size))), -1)
    return _DEM


def elevation_m(lat: float, lon: float) -> float:
    """Real SRTM elevation for a point inside tile N30E094 (lat 30-31 N, lon 94-95 E)."""
    d = _dem()
    n = d.shape[0]
    r = min(max(int(round((31.0 - lat) * (n - 1))), 0), n - 1)
    c = min(max(int(round((lon - 94.0) * (n - 1))), 0), n - 1)
    return float(d[r, c])


_GRID_CACHE: list | None = None


def _grid_rows() -> list:
    """Read the coverage grid once per process (it is 400 KB and never changes)."""
    global _GRID_CACHE
    if _GRID_CACHE is None:
        rows = []
        with open(GRID) as f:
            for r in csv.DictReader(f):
                rows.append((float(r["lat"]), float(r["lon"]),
                             float(r["loss_dB"]), int(r["best_sf(-1=unreachable)"])))
        _GRID_CACHE = rows
    return _GRID_CACHE


def load_ge():
    """Gilbert-Elliott parameters fitted from the real ChirpBox LoRa trace."""
    try:
        with open(LOSS_MODEL) as f:
            d = json.load(f)
        return d["p_good_to_bad"], d["p_bad_to_good"]
    except Exception:
        return None

# tool taxonomy: recovery semantics differ by class, which is the point
TOOLS = {
    "sensor.read":        {"class": "read_only",   "side_effect": False},
    "link.metrics":       {"class": "read_only",   "side_effect": False},
    "sampling.set_rate":  {"class": "state_mut",   "side_effect": False},
    "alert.send":         {"class": "side_effect", "side_effect": True},
    "gateway.failover":   {"class": "side_effect", "side_effect": True},
}


@dataclass
class Node:
    nid: str
    lat: float
    lon: float
    loss_db: float
    sf: int | None            # None => terrain-blocked, never reachable
    elev_m: float = 3000.0
    alive: bool = True
    link_good: bool = True
    energy: object = None     # NodeEnergy, set by the environment
    is_gateway: bool = False
    flap: int = 0             # README §9: gateway/relay flapping counter
    buffered: list = field(default_factory=list)   # results queued while silent

    @property
    def reachable(self) -> bool:
        return self.sf is not None


@dataclass
class EnvState:
    """Ground truth the agent never sees."""
    applied: list = field(default_factory=list)      # (tick, node, tool, key) actually applied
    counts: dict = field(default_factory=dict)


class DisruptionEnv:
    """One episode = a monitoring mission over a set of nodes for T ticks."""

    def __init__(self, seed: int = 0, n_nodes: int = 16, ticks: int = 720,
                 ack_loss_p: float = 0.25, outage_p_per_tick: float = 0.004,
                 channel: str = "iid", energy_model: str = "real",
                 temp_offset_c: float = 0.0, heated_fraction: float = 0.0,
                 enable_partition: bool = True, enable_flapping: bool = True,
                 enable_replay: bool = True, enable_coordinator_restart: bool = True,
                 coordinator_restart_p: float = 0.0015, frozen_episode: dict | None = None):
        self.rng = np.random.default_rng(seed)
        self.channel = channel
        self.energy_model = energy_model
        self.registry = OperationRegistry()
        self.enable_partition = enable_partition
        self.enable_flapping = enable_flapping
        self.enable_replay = enable_replay
        self.enable_coordinator_restart = enable_coordinator_restart
        self.coordinator_restart_p = coordinator_restart_p
        self.partitioned = False
        self.partition_until = 0
        self.coordinator_restarts = 0
        self.frozen_episode = frozen_episode or {}
        ge = load_ge() if channel == "ge" else None
        self.p_gb, self.p_bg = ge if ge else (0.0, 1.0)
        self.ticks = ticks
        self.t = 0
        self.ack_loss_p = ack_loss_p
        self.outage_p = outage_p_per_tick
        self.nodes = self._load_nodes(n_nodes)
        if self.nodes:
            # the gateway is the best-connected node; it is the one that can flap
            self.nodes[0].is_gateway = True
        if energy_model == "real":
            from energy import NodeEnergy
            for nd in self.nodes:
                nd.energy = NodeEnergy(elev_m=nd.elev_m, rng=self.rng,
                                       temp_offset_c=temp_offset_c,
                                       heated=bool(self.rng.random() < heated_fraction))
        self.truth = EnvState()
        self._applied_keys: set = set()
        self._anon: int = 0
        self._by_intent: dict = {}
        self._inflight: dict = {}
        self._f04_seen: set = set()
        self._f08_seen: set = set()
        self._true_val: dict = {}      # node -> true sensor value this tick
        self._episode: dict = {}       # node -> anomaly episode counter
        self._in_ep: dict = {}         # node -> currently in an anomaly episode?
        self.true_anomaly: dict = {}   # (node, episode) -> True
        self._down_since: dict = {}

    # ------------------------------------------------------------------ setup
    def _load_nodes(self, n: int) -> list[Node]:
        rows = _grid_rows()
        # a mix: reachable nodes plus the terrain-blocked ones
        reach = [r for r in rows if r[3] > 0]
        blocked = [r for r in rows if r[3] < 0]
        take_r = min(len(reach), int(n * 0.75))
        take_b = min(len(blocked), n - take_r)
        sel = (list(self.rng.choice(len(reach), take_r, replace=False)) if take_r else [])
        sel_b = (list(self.rng.choice(len(blocked), take_b, replace=False)) if take_b else [])
        out = []
        for k, i in enumerate(sel):
            la, lo, L, sf = reach[i]
            out.append(Node(f"n{k:02d}", la, lo, L, sf, elev_m=elevation_m(la, lo)))
        for k, i in enumerate(sel_b):
            la, lo, L, sf = blocked[i]
            out.append(Node(f"n{len(out)+k:02d}", la, lo, L, None, elev_m=elevation_m(la, lo)))
        return out

    # ------------------------------------------------------------- link model
    def _link_success_p(self, node: Node) -> float:
        """Success probability from the real terrain loss, via LoRa margin headroom."""
        if not node.reachable:
            return 0.0
        # sensitivity at this SF; margin above it maps to success probability
        sens = {7: -123.0, 8: -126.0, 9: -129.0, 10: -132.0, 11: -134.5, 12: -137.0}[node.sf]
        margin = 14.0 + 2.0 + 2.0 - 1.0 - node.loss_db - sens
        # logistic in margin: 0 dB margin -> ~0.5, +10 dB -> ~0.95
        return float(1.0 / (1.0 + math.exp(-margin / 5.0)))

    # ------------------------------------------------------------------ time
    def tick(self) -> None:
        self.t += 1
        if self.channel == "ge":
            for n in self.nodes:
                if n.link_good:
                    if self.rng.random() < self.p_gb:
                        n.link_good = False
                else:
                    if self.rng.random() < self.p_bg:
                        n.link_good = True
        # ground-truth sensor field: the environment knows the real anomaly episodes
        for n in self.nodes:
            v = float(self.rng.normal(10, 1))
            if self.rng.random() < 0.02:          # anomalies start with low probability
                v += 3.0
            self._true_val[n.nid] = v
            hot = v > 11.0
            if hot and not self._in_ep.get(n.nid):
                self._episode[n.nid] = self._episode.get(n.nid, 0) + 1
                self.true_anomaly[(n.nid, self._episode[n.nid])] = True
            self._in_ep[n.nid] = hot
        # ---- README §9 F10: partition. A subset of nodes is cut off from the gateway.
        if self.enable_partition:
            if self.partitioned and self.t >= self.partition_until:
                self.partitioned = False
                self.registry.bump("partitions_ended")
            elif not self.partitioned and self.rng.random() < 0.004:
                self.partitioned = True
                self.partition_until = self.t + int(self.rng.integers(12, 120))
                self.registry.f10_partition_divergence(self.t)

        # ---- README §9 F11: the coordinator restarts and loses in-memory state.
        if self.enable_coordinator_restart and self.rng.random() < self.coordinator_restart_p:
            self.coordinator_restarts += 1
            self.registry.f11_coordinator_restart(self.t)
            self.on_restart()

        # ---- README §9 F09: gateway/relay flapping.
        if self.enable_flapping:
            for n in self.nodes:
                if n.is_gateway and self.rng.random() < 0.02:
                    n.link_good = not n.link_good
                    n.flap += 1
                    if n.flap % 2 == 0 and n.flap > 0:
                        self.registry.f09_gateway_flapping(self.t)

        if self.t % 12 == 0:
            self.sweep_pending()

        doy = 1 + ((self.t // 24) % 365)
        for n in self.nodes:
            if n.energy is not None:
                was = n.alive
                n.alive = n.energy.step(doy)
                if was and not n.alive:
                    self._down_since[n.nid] = self.t
                    self._forget_pending(n)
                if (not was) and n.alive and n.buffered:
                    self._replay(n)
            else:
                # placeholder model, kept for comparison
                n.bat_wh = getattr(n, "bat_wh", 420.0) - 0.67
                if n.bat_wh <= 0:
                    n.alive = False
                    n.bat_wh = 0.0
                else:
                    n.bat_wh = min(420.0, n.bat_wh + 0.05)

    # --------------------------------------------------------------- the call
    def call(self, node: Node, tool: str, intent: str | None = None,
             fresh_observation: bool = True) -> tuple[str, object]:
        """One dispatch attempt. Returns (lifecycle_state, result).

        `intent` is the caller's stable identity for the logical action. Passing the same
        intent across retries keeps ONE Operation, so the retry budget is meaningful; passing
        None invents a fresh identity each time, which is how duplicates arise in practice.
        """
        if intent is None:
            self._anon += 1
            intent = f"anon-{self._anon}"

        # ---- get or create the operation -------------------------------------
        op = self._by_intent.get(intent)
        if op is None:
            op = self.registry.new(node.nid, tool, intent, self.t,
                                   TOOLS[tool]["side_effect"])
            self._by_intent[intent] = op

        # ---- retry budget (README §9 F07) ------------------------------------
        op.attempts += 1
        if op.attempts > op.budget:
            self.registry.f07_retry_budget_exhausted(op, self.t)
            return "failed", None

        op.first_dispatch = op.first_dispatch or self.t
        op.transition("running", self.t)

        # ---- unreachable ------------------------------------------------------
        if self.is_unreachable(node):
            if TOOLS[tool]["side_effect"] and op.buffered_at is None:
                node.buffered.append((self.t, tool, self.logical_key(node)))
                op.buffered_at = self.t
            op.transition("unavailable", self.t)
            return "unavailable", None

        # ---- the channel ------------------------------------------------------
        p = self._link_success_p(node)
        if self.channel == "ge":
            p = p * 0.95 if node.link_good else p * 0.05
        r = self.rng.random()

        if r < p:
            if not fresh_observation:
                # README §9 F05: a stale reading presented as the current one
                age = int(self.rng.integers(4, 48))
                self.registry.f05_stale_used_as_current(op, self.t, age)
                self._maybe_apply(node, tool, intent)
                return "stale_result", self._result(node, tool, stale_age=age)
            self._maybe_apply(node, tool, intent)
            op.transition("committed", self.t)
            return "committed", self._result(node, tool)

        # ---- failure somewhere in the channel ---------------------------------
        if TOOLS[tool]["side_effect"]:
            if r < p + (1 - p) * self.ack_loss_p:
                # F02: it RAN, the ACK died. Ground truth records the effect.
                self._maybe_apply(node, tool, intent)
                self.registry.f02_ack_lost_after_execution(op, self.t)
                return "outcome_unknown", None
            if r < p + (1 - p) * (self.ack_loss_p + 0.15):
                # F01: the node vanished between dispatch and reply
                self.registry.f01_node_lost_after_dispatch(op, self.t)
                return "outcome_unknown", None
        if r < p + (1 - p) * 0.90:
            op.transition("timeout", self.t)
            return "timeout", None
        op.transition("outcome_unknown", self.t)
        return "outcome_unknown", None

    # ---------------------------------------------------- asynchronous dispatch
    def dispatch(self, node: Node, tool: str, intent: str | None = None,
                 latency: int = 2) -> str:
        """Send a call and return its operation id WITHOUT resolving it.

        Asynchrony is what makes the failure model real: an operation can be in flight when
        its node dies (README §9 F01), and a pending operation can be abandoned while the
        capability is gone (F04). A synchronous call cannot express either.
        """
        if intent is None:
            self._anon += 1
            intent = f"anon-{self._anon}"
        op = self.registry.new(node.nid, tool, intent, self.t, TOOLS[tool]["side_effect"])
        op.transition("running", self.t)
        op.first_dispatch = self.t
        self._inflight[op.op_id] = {"resolve_at": self.t + latency, "intent": intent}
        self._by_intent[intent] = op
        return op.op_id

    def poll(self, op_id: str) -> tuple[str, object]:
        """Resolve an in-flight operation, if the world has moved far enough."""
        rec = self._inflight.get(op_id)
        if rec is None:
            return self.registry.ops[op_id].state, None
        op = self.registry.ops[op_id]
        node = next((n for n in self.nodes if n.nid == op.node), None)
        if node is None:
            return op.state, None

        # the node went away while the call was in flight -> F01
        if self.is_unreachable(node):
            if op.side_effect and op.buffered_at is None:
                node.buffered.append((self.t, op.tool, self.logical_key(node)))
                op.buffered_at = self.t
            self.registry.f01_node_lost_after_dispatch(op, self.t)
            del self._inflight[op_id]
            return "outcome_unknown", None

        if self.t < rec["resolve_at"]:
            return "running", None        # still in flight

        del self._inflight[op_id]
        p = self._link_success_p(node)
        if self.channel == "ge":
            p = p * 0.95 if node.link_good else p * 0.05
        if self.rng.random() < p:
            self._maybe_apply(node, op.tool, rec["intent"])
            op.transition("committed", self.t)
            return "committed", self._result(node, op.tool)
        if op.side_effect and self.rng.random() < 0.6:
            self._maybe_apply(node, op.tool, rec["intent"])   # ran, ACK lost -> F02
            self.registry.f02_ack_lost_after_execution(op, self.t)
            return "outcome_unknown", None
        op.transition("timeout", self.t)
        return "timeout", None

    def on_restart(self) -> None:
        """Hook for the coordinator losing in-memory state. Subclasses may override."""
        pass

    def _replay(self, node: Node) -> None:
        """Node is back: flush what it buffered while silent (README §9 F06)."""
        if not self.enable_replay:
            node.buffered.clear()
            return
        items = list(node.buffered)
        node.buffered.clear()
        if len(items) > 1 and self.rng.random() < 0.5:
            items = list(reversed(items))          # out-of-order replay
            self.registry.f06_wrong_replay_order(
                self.registry.new(node.nid, "buffer.flush", "replay", self.t, False), self.t)
        for (_t, tool, logical) in items:
            self.truth.applied.append((self.t, node.nid, tool, logical))

    def _forget_pending(self, node: Node) -> None:
        """README §9 F04: the capability went away; its pending invocations are dropped."""
        for op in list(self.registry.ops.values()):
            if op.node == node.nid and op.open and op.state in ("running", "not_started"):
                self.registry.f04_pending_forgotten(op, self.t)

    def sweep_pending(self) -> None:
        """Scan for operations that were dispatched and then abandoned.

        README §9 F04 (pending invocation forgotten) and F08 (starvation / head-of-line
        blocking) share one structure: an operation stays open while the world moves on.
        Sweeping here — rather than at call time — matches the semantics: being forgotten
        is a property of elapsed time, not of any single call.
        """
        # only sweep operations that could still be pending (recent ones); older ones have
        # already been classified, so rescanning them every tick is wasted work
        open_ops = [o for o in self.registry.ops.values()
                    if o.open and (self.t - o.created) < 600]
        if not open_ops:
            return
        open_ops.sort(key=lambda o: o.created)
        head = open_ops[0]
        head_blocking = head is not None and head.open and (self.t - head.created) > 24
        for k, op in enumerate(open_ops):
            age = self.t - op.created
            # F04 — count each operation exactly once
            node = next((n for n in self.nodes if n.nid == op.node), None)
            node_gone = node is not None and self.is_unreachable(node)
            abandoned = (op.state == "running" and node_gone) or \
                        (op.state == "unavailable" and age > 24) or \
                        (op.buffered_at is not None and op.settled is None and age > 48)
            if abandoned and op.op_id not in self._f04_seen:
                self._f04_seen.add(op.op_id)
                self.registry.f04_pending_forgotten(op, self.t)
            # F08 — count each (starved op, blocking head) pair exactly once
            if k > 0 and age > 12 and head_blocking:
                key = (op.op_id, head.op_id)
                if key not in self._f08_seen:
                    self._f08_seen.add(key)
                    self.registry.f08_starvation_hol(op, self.t)

    def check_starvation(self) -> None:
        """README §9 F08: an old unresolved operation blocks a FIFO queue.

        A later operation that has waited longer than `starvation_slack` while an OLDER
        operation is still unresolved is counted as starved — the head-of-line case.
        """
        open_ops = [o for o in self.registry.ops.values() if o.open]
        if len(open_ops) < 2:
            return
        open_ops.sort(key=lambda o: o.created)
        head = open_ops[0]
        if head.state in ("running", "not_started") and (self.t - head.created) > 24:
            for o in open_ops[1:]:
                if (self.t - o.created) > 12:
                    self.registry.f08_starvation_hol(o, self.t)

    def stale_read(self, node: Node, tool: str) -> tuple[str, object]:
        """Force a stale-observation path (README §9 F05)."""
        return self.call(node, tool, intent=None, fresh_observation=False)

    def is_unreachable(self, node: Node) -> bool:
        """Terrain-blocked, powered down, or cut off by a partition."""
        if not node.reachable or not node.alive:
            return True
        if self.partitioned and not node.is_gateway:
            return True
        return False

    def _maybe_apply(self, node: Node, tool: str, intent: str) -> None:
        """Apply at an idempotent sink. Dedups on `intent`, counting repeats as duplicates."""
        if not TOOLS[tool]["side_effect"]:
            return
        logical = self.logical_key(node)
        if intent.startswith("key:") and intent in self._applied_keys:
            self.truth.deduped = getattr(self.truth, "deduped", 0) + 1
            return
        if intent.startswith("key:"):
            self._applied_keys.add(intent)
        self.truth.applied.append((self.t, node.nid, tool, logical))
        self.truth.counts[tool] = self.truth.counts.get(tool, 0) + 1

    def logical_key(self, node: Node) -> str:
        """The environment's own identity for the logical action on this node right now."""
        return f"{node.nid}:ep{self._episode.get(node.nid, 0)}"

    # ---------------------------------------------------- asynchronous dispatch
    def dispatch(self, node: Node, tool: str, intent: str | None = None,
                 latency: int = 2) -> str:
        """Send a call and return its operation id WITHOUT resolving it.

        Asynchrony is what makes the failure model real: an operation can be in flight when
        its node dies (README §9 F01), and a pending operation can be abandoned while the
        capability is gone (F04). A synchronous call cannot express either.
        """
        if intent is None:
            self._anon += 1
            intent = f"anon-{self._anon}"
        op = self.registry.new(node.nid, tool, intent, self.t, TOOLS[tool]["side_effect"])
        op.transition("running", self.t)
        op.first_dispatch = self.t
        self._inflight[op.op_id] = {"resolve_at": self.t + latency, "intent": intent}
        self._by_intent[intent] = op
        return op.op_id

    def poll(self, op_id: str) -> tuple[str, object]:
        """Resolve an in-flight operation, if the world has moved far enough."""
        rec = self._inflight.get(op_id)
        if rec is None:
            return self.registry.ops[op_id].state, None
        op = self.registry.ops[op_id]
        node = next((n for n in self.nodes if n.nid == op.node), None)
        if node is None:
            return op.state, None

        # the node went away while the call was in flight -> F01
        if self.is_unreachable(node):
            if op.side_effect and op.buffered_at is None:
                node.buffered.append((self.t, op.tool, self.logical_key(node)))
                op.buffered_at = self.t
            self.registry.f01_node_lost_after_dispatch(op, self.t)
            del self._inflight[op_id]
            return "outcome_unknown", None

        if self.t < rec["resolve_at"]:
            return "running", None        # still in flight

        del self._inflight[op_id]
        p = self._link_success_p(node)
        if self.channel == "ge":
            p = p * 0.95 if node.link_good else p * 0.05
        if self.rng.random() < p:
            self._maybe_apply(node, op.tool, rec["intent"])
            op.transition("committed", self.t)
            return "committed", self._result(node, op.tool)
        if op.side_effect and self.rng.random() < 0.6:
            self._maybe_apply(node, op.tool, rec["intent"])   # ran, ACK lost -> F02
            self.registry.f02_ack_lost_after_execution(op, self.t)
            return "outcome_unknown", None
        op.transition("timeout", self.t)
        return "timeout", None

    def on_restart(self) -> None:
        """Hook for the coordinator losing in-memory state. Subclasses may override."""
        pass

    def _replay(self, node: Node) -> None:
        """Node is back: flush what it buffered while silent (README §9 F06)."""
        if not self.enable_replay:
            node.buffered.clear()
            return
        items = list(node.buffered)
        node.buffered.clear()
        if len(items) > 1 and self.rng.random() < 0.5:
            items = list(reversed(items))          # out-of-order replay
            self.registry.f06_wrong_replay_order(
                self.registry.new(node.nid, "buffer.flush", "replay", self.t, False), self.t)
        for (_t, tool, logical) in items:
            self.truth.applied.append((self.t, node.nid, tool, logical))

    def _forget_pending(self, node: Node) -> None:
        """README §9 F04: the capability went away; its pending invocations are dropped."""
        for op in list(self.registry.ops.values()):
            if op.node == node.nid and op.open and op.state in ("running", "not_started"):
                self.registry.f04_pending_forgotten(op, self.t)

    def sweep_pending(self) -> None:
        """Scan for operations that were dispatched and then abandoned.

        README §9 F04 (pending invocation forgotten) and F08 (starvation / head-of-line
        blocking) share one structure: an operation stays open while the world moves on.
        Sweeping here — rather than at call time — matches the semantics: being forgotten
        is a property of elapsed time, not of any single call.
        """
        # only sweep operations that could still be pending (recent ones); older ones have
        # already been classified, so rescanning them every tick is wasted work
        open_ops = [o for o in self.registry.ops.values()
                    if o.open and (self.t - o.created) < 600]
        if not open_ops:
            return
        open_ops.sort(key=lambda o: o.created)
        head = open_ops[0]
        head_blocking = head is not None and head.open and (self.t - head.created) > 24
        for k, op in enumerate(open_ops):
            age = self.t - op.created
            # F04 — count each operation exactly once
            node = next((n for n in self.nodes if n.nid == op.node), None)
            node_gone = node is not None and self.is_unreachable(node)
            abandoned = (op.state == "running" and node_gone) or \
                        (op.state == "unavailable" and age > 24) or \
                        (op.buffered_at is not None and op.settled is None and age > 48)
            if abandoned and op.op_id not in self._f04_seen:
                self._f04_seen.add(op.op_id)
                self.registry.f04_pending_forgotten(op, self.t)
            # F08 — count each (starved op, blocking head) pair exactly once
            if k > 0 and age > 12 and head_blocking:
                key = (op.op_id, head.op_id)
                if key not in self._f08_seen:
                    self._f08_seen.add(key)
                    self.registry.f08_starvation_hol(op, self.t)

    def check_starvation(self) -> None:
        """README §9 F08: an old unresolved operation blocks a FIFO queue.

        A later operation that has waited longer than `starvation_slack` while an OLDER
        operation is still unresolved is counted as starved — the head-of-line case.
        """
        open_ops = [o for o in self.registry.ops.values() if o.open]
        if len(open_ops) < 2:
            return
        open_ops.sort(key=lambda o: o.created)
        head = open_ops[0]
        if head.state in ("running", "not_started") and (self.t - head.created) > 24:
            for o in open_ops[1:]:
                if (self.t - o.created) > 12:
                    self.registry.f08_starvation_hol(o, self.t)

    def stale_read(self, node: Node, tool: str) -> tuple[str, object]:
        """Force a stale-observation path (README §9 F05)."""
        return self.call(node, tool, intent=None, fresh_observation=False)

    def is_unreachable(self, node: Node) -> bool:
        """Terrain-blocked, powered down, or cut off by a partition."""
        if not node.reachable or not node.alive:
            return True
        if self.partitioned and not node.is_gateway:
            return True
        return False

    def _maybe_apply(self, node: Node, tool: str, intent: str) -> None:
        """Apply the side effect at an idempotent sink.

        The sink dedups on `intent`. A caller that keeps a STABLE intent across retries is
        therefore safe; a caller that invents a fresh identity per attempt is not. That is
        the entire difference between the two policies.
        """
        if not TOOLS[tool]["side_effect"]:
            return
        logical = self.logical_key(node)
        # an idempotent sink drops a repeat of a key it has already accepted
        if intent.startswith("key:") and intent in self._applied_keys:
            self.truth.deduped = getattr(self.truth, "deduped", 0) + 1
            return
        if intent.startswith("key:"):
            self._applied_keys.add(intent)
        self.truth.applied.append((self.t, node.nid, tool, logical))
        self.truth.counts[tool] = self.truth.counts.get(tool, 0) + 1

    def _result(self, node: Node, tool: str, stale_age: int = 0):
        if tool in ("sensor.read", "link.metrics"):
            # stale results track how long the node has been silent
            return {"node": node.nid, "value": float(self.rng.normal(10, 1)),
                    "tick": self.t, "stale_age": stale_age}
        return {"ok": True}

    # ------------------------------------------------------------- idempotent
    def verify(self, node: Node, tool: str) -> str:
        """Answer a postcondition-verification query — over the SAME unreliable channel.

        Returns "applied" / "not_applied" / "unknown". The third outcome is the one the
        verification-aware wrapper of arXiv 2608.02645 does not define, and it is exactly
        what a degraded channel produces.
        """
        if not node.alive or not node.reachable:
            return "unknown"                       # the verifier itself is unreachable
        p = self._link_success_p(node)
        if self.channel == "ge":
            p = p * 0.95 if node.link_good else p * 0.05
        if self.rng.random() > p:
            return "unknown"                       # verification query lost
        applied = any((nid == node.nid and tl == tool)
                      for (_t, nid, tl, _l) in self.truth.applied)
        return "applied" if applied else "not_applied"

    def duplicate_side_effects(self) -> int:
        """Count duplicates AND record them as README §9 F03."""
        """Side effects that the SINK accepted more than once for the same intent.

        A stable idempotency key is honoured by the sink and yields 0. A fresh identity per
        retry is not, and is counted.
        """
        seen: dict = {}
        for (_t, _n, tool, logical) in self.truth.applied:
            seen[(logical, tool)] = seen.get((logical, tool), 0) + 1
        dups = sum(v - 1 for v in seen.values() if v > 1)
        if dups:
            self.registry.bump("F03_duplicate_side_effect", dups)
        return dups

    def true_episodes(self) -> int:
        """Number of ground-truth anomaly episodes the mission actually required alerts for."""
        return len(self.true_anomaly)

    def distinct_intents_applied(self) -> int:
        return len({(i, t) for (_tk, _n, t, i) in self.truth.applied})
