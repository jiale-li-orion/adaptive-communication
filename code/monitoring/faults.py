#!/usr/bin/env python3
"""
faults.py — the six diagnostic faults of the reference workload, each constructed on its own.

WHAT THIS MODULE IS. Contract §5 lists six fault classes and asks for one trajectory per class plus
a fault-free control, all of them auditable event by event:

  request_lost         the center's downlink request does not reach the gateway or the node
  ack_lost             the node applies the command; the acknowledgement never comes back
  stale_command        an older command arrives after a newer one has already taken effect
  coordinator_restart  the center process dies and comes back; memory-only state is gone
  node_restart         a node loses power and reboots, losing volatile state
  backhaul_only        the gateway is up and still talking to the nodes; nothing reaches the center

A trajectory injects exactly ONE class. That is what makes an injection attributable: when a number
in a result moves, the event that moved it can be pointed at. The classes are for semantic
validation, not for significance, so nothing here is drawn from a natural fault frequency. Every
injection is definite: the seed decides WHICH node is hit and, for the classes whose start is not
scheduled in reality, the exact instant — it never decides whether an injection exists. A count that
wandered with the seed would make "this trajectory differs from the control" unreadable.

WHAT AN INJECTION IS. An injection is a half-open coverage window `[at_s, at_s + duration_s)` on the
run clock (one-minute ticks, `node_model.TICK_S`), naming the path it acts on. `events()` lists
them for an audit; `active(kind, at_s, node_id)` answers whether this instant is covered. The
per-kind consequences, and what a runner has to do physically to realize them:

  request_lost          requests addressed to this node inside the window do not arrive. The window
                        is short, so it removes an opportunity rather than a phase. `detail["hop"]`
                        says which leg lost it, and the two legs differ: a loss on the backhaul leg
                        means the gateway never had the request (center_send refuses), a loss on the
                        access leg means the gateway holds it in its queue and may deliver it on a
                        later opportunity, so the request arrives late instead of never.
  ack_lost              deliveries to this node inside the window are applied and their
                        acknowledgements are dropped. The effect happens; the center's outcome
                        stays unknown. `detail["effect_in_force_until_s"]` bounds how long the
                        effect is in force while the center has no evidence of it.
  stale_command         a command issued at `detail["issued_at_s"]` is released at the event's
                        instant. `detail["stale_against"]` names the ordering that makes it stale:
                        any command issued after `issued_at_s` and in force before the arrival is
                        newer. The transport holds it; the runtime has to decide what to do with it.
  coordinator_restart   the center process is down for the window and comes back having lost what
                        it held only in memory. The backhaul and the gateway are untouched, so this
                        is not a connectivity fault and cannot be read as one.
  node_restart          the node is down for the window, then returns with its volatile state gone.
                        Sampling and uplinks stop for the whole window; `detail["recovered_at_s"]`
                        marks the return.
  backhaul_only         nothing crosses the center-gateway leg for hours while the gateway keeps
                        serving the nodes. Uplinks are still heard at the gateway and buffered
                        there; the center receives nothing and can send nothing.

WHAT THIS MODULE DOES NOT DECIDE. It says what is injected and when. Which of these facts a runtime
must act on, what it should have persisted, whether it re-sends or verifies or waits — that belongs
to the runtime, and nothing here assumes an answer. In particular the module never decides whether a
delivery, an application or a recovery really happened beyond the premise stated in `detail`: the
premise is part of the injection, and a runtime that ignores it is testing a different fault.

EVIDENCE LAYER. Every default below is **A: a research reference assumption** (README D16). None is
a geohazard safety standard, a customer SLA, a measured fault rate or an acceptance figure. The
frequencies have case background (README §四 records a 6.38 h mean outage burst with a 42 h p99
from the coverage study, and a reorder group that withheld 1–36 h of writes against a 12 h command
interval), but the instants, durations and the combination are diagnostic choices for the 72 h
reference load of contract §5. Sensitivity belongs in a scan, not in the default.

Deps: standard library plus this package.
"""
from __future__ import annotations

# --- module resolution -------------------------------------------------------
import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, *(_os.path.join(_CODE, d) for d in ("physics", "runtime",
                                                     "experiments", "analysis"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)
# -----------------------------------------------------------------------------

from dataclasses import dataclass
from types import MappingProxyType

from deterministic import stable_uniform
from node_model import TICK_S
from task_generator import DEFAULT_HOURS, RISK_WINDOWS_H, build_deployment

__all__ = [
    "KINDS",
    "KIND_SCOPE",
    "KIND_DEFAULTS",
    "MIN_PROFILE_GAP_S",
    "PROFILE_CHANGE_INSTANTS_S",
    "PROFILE_COMMAND_VALIDITY_S",
    "FaultSpec",
    "InjectedEvent",
    "FaultInjector",
    "FaultFree",
    "reference_node_ids",
]

KINDS = ("request_lost", "ack_lost", "stale_command",
         "coordinator_restart", "node_restart", "backhaul_only")

# Which entity an injection names. A node-scoped fault names the station it acts on; a
# network-scoped fault names no station, because what fails is the path or the center, not a
# station. The two restart classes are distinguishable by exactly this: `coordinator_restart`
# names no node, `node_restart` always names one.
KIND_SCOPE = {
    "request_lost": "node",
    "ack_lost": "node",
    "stale_command": "node",
    "coordinator_restart": "network",
    "node_restart": "node",
    "backhaul_only": "network",
}

# The node position of a draw key holds this literal when the fault is network-wide, so the address
# still names what is being drawn.
NETWORK_SCOPE = "network"

# The runner issues a profile command with a six hour expiry (`runner.py`, and the `ttl_s` fallback
# in `interfaces.py::set_monitoring_profile`), so an applied profile is in force for at least six
# hours unless superseded. This default follows those call sites; if they change, it has to follow.
PROFILE_COMMAND_VALIDITY_S = 6 * 3600


def reference_node_ids() -> tuple[str, ...]:
    """The station ids of the reference deployment, sorted.

    Architecture A fixes 16 nodes in 2 slope groups (README D2), and the deployment does not depend
    on the seed. A node-scoped fault whose scope is left empty draws from these stations, so the
    default trajectory addresses the deployment the demand set is built on rather than an
    assumption about the caller's run.
    """
    global _REFERENCE_NODE_IDS
    if _REFERENCE_NODE_IDS is None:
        _REFERENCE_NODE_IDS = tuple(sorted(n.nid for n in build_deployment(0).nodes))
    return _REFERENCE_NODE_IDS


_REFERENCE_NODE_IDS: tuple[str, ...] | None = None


def _profile_change_instants_s() -> tuple[int, ...]:
    """Instants at which the reference load changes the demanded profile, in seconds.

    Read from `RISK_WINDOWS_H` rather than written out as hours, so a change to the reference
    windows moves this with it. The run start is an edge as well: the first phase begins there.
    """
    edges = {0}
    total_s = DEFAULT_HOURS * 3600
    for start_h, end_h in RISK_WINDOWS_H:
        for edge_h in (start_h, end_h):
            edge_s = int(round(edge_h * 3600))
            if 0 < edge_s < total_s:
                edges.add(edge_s)
    return tuple(sorted(edges))


PROFILE_CHANGE_INSTANTS_S = _profile_change_instants_s()

# The shortest interval between two instants at which the load changes the demanded profile. A
# command held for less than this cannot end up behind a newer one, so this is the unit the holdout
# band is expressed in. For the reference load it is 6 h (12 h -> 18 h).
MIN_PROFILE_GAP_S = min(b - a for a, b in zip(PROFILE_CHANGE_INSTANTS_S,
                                              PROFILE_CHANGE_INSTANTS_S[1:]))


def _frozen(**kw) -> MappingProxyType:
    return MappingProxyType(kw)


# =============================================================== A-layer defaults
# Each entry is the default for one kind. `count=None` means the schedule fills the run;
# `delay_s=None` means the holdout is drawn from the band documented below. The fixed counts
# belong to the 72 h reference load: a diagnostic trajectory is meant to be read event by event,
# so it shows the shape
# of its fault rather than accumulating instances of it. A longer run needs an explicit count and
# period; the periodic classes already fill whatever run they are given. EVERY NUMBER IS A: a
# diagnostic parameter of this study, not a measured rate (README D16, contract §5).
KIND_DEFAULTS = MappingProxyType({
    # A request lost before it reaches a node. The window is 5 min, one dense-cadence upload
    # interval: at the risk cadence (one upload every 5 min) it removes exactly one opportunity, and
    # at the normal cadence the request is simply retried at the next one, so the window removes an
    # opportunity rather than a phase. Slots every 12 h from the first hour leave six injections
    # across the 72 h load, some of them inside a risk window (13 h, 49 h) and some outside, because
    # contract §5 warns against making fault and risk co-occur by construction.
    "request_lost": _frozen(first_at_s=1 * 3600, period_s=12 * 3600, duration_s=5 * 60,
                            count=None, jitter_s=0),
    # An applied command whose acknowledgement is dropped. The coverage window is 1 h, the normal
    # upload interval (MONITORING_PROFILES[PROFILE_NORMAL]["upload_s"]): a node on the slow cadence
    # uplinks once an hour, so a shorter window could contain no delivery at all and the trajectory
    # would record an injection with no observable consequence. This window is an addressing choice
    # rather than a physical outage: what physically happens is that one acknowledgement is lost.
    # The effect stays in force for the command's own validity, and 15 h puts the first injection
    # inside a risk window without putting it on the window's edge.
    "ack_lost": _frozen(first_at_s=15 * 3600, period_s=24 * 3600, duration_s=1 * 3600,
                        count=None, jitter_s=0, in_force_s=PROFILE_COMMAND_VALIDITY_S),
    # A command held by the transport and released late. Holdout band [2, 4] x the load's shortest
    # profile-change gap, i.e. 12 h to 24 h against a 6 h gap: the lower bound has to cross at least
    # one change or the released command is not behind a newer one, and the upper bound follows the
    # reorder group's rule that the holdout reach two to three times the interval it has to cross
    # (README §六, `--cmd-period 12 --stale-max 36`). Arrivals every 12 h from 24 h give four
    # releases, with issue instants between 0 h and 48 h. The coverage window is one tick: the
    # injection's fact is the arrival, and the holdout is recorded in the detail.
    "stale_command": _frozen(first_at_s=24 * 3600, period_s=12 * 3600, duration_s=TICK_S,
                             count=None, jitter_s=0, delay_s=None),
    # The center process dies and comes back. One restart per 72 h trajectory, at the same cadence
    # the mechanism-layer restart group used (README §六: one coordinator restart every 72 h). The
    # downtime is 10 min of A-layer assumption: a supervised process restarts in seconds, and the
    # interval that matters here is the one in which the center cannot act at all — restart plus
    # whatever it must read back before it can act. Thirty minutes of jitter keeps the start
    # unscheduled, because a crash is not on a timetable.
    "coordinator_restart": _frozen(first_at_s=30 * 3600, period_s=24 * 3600, duration_s=10 * 60,
                                   count=1, jitter_s=30 * 60),
    # A node loses power and reboots. Two restarts 24 h apart, on different stations, so the
    # trajectory shows more than a single event. The outage is 5 min: the boot itself is seconds,
    # and the figure covers the cold boot, the network rejoin and the first uplink attempt at the
    # dense cadence. Five minutes is also the shortest disconnection the contract's sensitivity row
    # scans (5 / 30 / 120 min), so the diagnostic default sits on that axis instead of beside it.
    "node_restart": _frozen(first_at_s=20 * 3600, period_s=24 * 3600, duration_s=5 * 60,
                            count=2, jitter_s=30 * 60),
    # Nothing crosses the backhaul for hours. One outage of 4 h at 33 h: longer than every value on
    # the contract's 5 / 30 / 120 min disconnection axis, because a fault that only lasts as long as
    # a packet-level gap would not exercise the store-and-forward behaviour this deployment has, and
    # shorter than the 6.38 h mean burst the coverage study reports, so the default stays inside the
    # range the study already describes. It deliberately starts outside both risk windows.
    "backhaul_only": _frozen(first_at_s=33 * 3600, period_s=24 * 3600, duration_s=4 * 3600,
                             count=1, jitter_s=30 * 60),
})

# Knobs that mean something for one class only. A spec that sets one of these to a non-default value
# for another class is rejected rather than quietly ignored: a knob nobody reads is a trajectory
# that does something other than what its author asked for.
_KIND_SPECIFIC_KNOBS = {"delay_s": ("stale_command",), "in_force_s": ("ack_lost",)}


def _check_kind(kind: str) -> None:
    if kind not in KINDS:
        raise ValueError(f"unknown fault kind {kind!r}; KINDS are {KINDS}")


@dataclass(frozen=True)
class FaultSpec:
    """One fault class, for one trajectory.

    `nodes` restricts a node-scoped fault to named stations; empty means the reference deployment.
    The window knobs are in seconds on the run clock and must be multiples of `TICK_S`, because an
    instant the runner never visits cannot be observed. `None` on a window knob means the class
    default from `KIND_DEFAULTS`.

    `jitter_s` moves each injection's start by a keyed offset in [0, jitter_s), which is what makes
    a crash or a power loss unscheduled rather than a timetable entry. It moves the gap between two
    injections by the same amount, so consecutive starts sit within jitter_s of the period on either
    side; the period stays larger than the jitter, so injections cannot reorder or overlap.

    Kind-specific knobs:

      delay_s      stale_command only. The holdout. None draws it uniformly from [2, 4] x the
                   reference load's shortest profile-change gap (12-24 h).
      in_force_s   ack_lost only. How long the injected effect is in force while the center is
                   blind. Defaults to the profile command validity the runner issues (6 h).
    """

    kind: str
    seed: int = 0
    hours: int = DEFAULT_HOURS
    nodes: tuple[str, ...] = ()
    first_at_s: int | None = None
    period_s: int | None = None
    duration_s: int | None = None
    count: int | None = None
    jitter_s: int | None = None
    delay_s: int | None = None
    in_force_s: int | None = None

    def __post_init__(self) -> None:
        _check_kind(self.kind)
        if self.seed < 0:
            raise ValueError(f"seed {self.seed} is negative; the split scheme starts at 0")
        if self.hours < 1:
            raise ValueError(f"hours {self.hours} is not a positive number of hours")
        if KIND_SCOPE[self.kind] == "network" and self.nodes:
            raise ValueError(f"{self.kind} is network-wide and names no station; "
                             f"drop nodes={self.nodes!r}")
        if len(set(self.nodes)) != len(self.nodes):
            raise ValueError(f"nodes {self.nodes!r} repeat a station id")
        for nid in self.nodes:
            if not isinstance(nid, str) or not nid:
                raise ValueError(f"node ids must be non-empty strings, got {nid!r}")
        for name in ("first_at_s", "period_s", "duration_s", "jitter_s", "delay_s", "in_force_s"):
            value = getattr(self, name)
            if value is None:
                continue
            if value <= 0:
                raise ValueError(f"{name}={value} is not positive")
            if value % TICK_S:
                raise ValueError(f"{name}={value} is not a multiple of the {TICK_S} s run clock; "
                                 f"the runner never visits that instant")
        if self.duration_s is not None and self.duration_s < TICK_S:
            raise ValueError(f"duration_s={self.duration_s} is shorter than one tick; a window "
                             f"the runner cannot observe is not an injection")
        if self.count is not None and self.count < 1:
            raise ValueError(f"count={self.count} is not a positive number of injections")
        for name, kinds in _KIND_SPECIFIC_KNOBS.items():
            if getattr(self, name) is not None and self.kind not in kinds:
                raise ValueError(f"{name} means nothing for {self.kind}; it applies to {kinds}")


@dataclass(frozen=True)
class InjectedEvent:
    """One injection, with enough detail to audit it without reading the code that made it."""

    at_s: int
    kind: str
    node_id: str | None
    detail: dict


def _subject(node_id: str | None) -> str:
    """The node position of a draw key, for a fault that names no station."""
    return node_id if node_id else NETWORK_SCOPE


def _sort_key(event: InjectedEvent) -> tuple:
    """The documented order: (at_s, kind, node_id), with a network-scoped event sorting first."""
    return (event.at_s, event.kind, event.node_id or "")


class FaultInjector:
    """One fault class, injected into one trajectory.

    Deterministic and order-free: every draw is addressed by (seed, kind, node, instant) through
    `stable_uniform`, so nothing here depends on how many draws happened before it, on the order of
    the caller's questions, or on whether `events()` was asked for once or ten times.
    """

    def __init__(self, spec: FaultSpec) -> None:
        self.spec = spec
        self._events: tuple[InjectedEvent, ...] | None = None

    # ---------------------------------------------------------------- public API
    def events(self) -> list[InjectedEvent]:
        """Every injection this fault produces, sorted by (at_s, kind, node_id).

        Idempotent: the trajectory is built once and answered from the cache afterwards, so asking
        twice cannot change it. The returned events are copies, so a caller that edits what it was
        handed edits its own copy and not the audit record.
        """
        if self._events is None:
            self._events = tuple(sorted(self._build(), key=_sort_key))
        return [InjectedEvent(e.at_s, e.kind, e.node_id, dict(e.detail)) for e in self._events]

    def active(self, kind: str, at_s: int, node_id: str | None = None) -> bool:
        """Whether an injection of `kind` covers this instant.

        Coverage is half-open: `at_s` is covered, `at_s + duration_s` is not. `node_id=None` asks
        whether any injection of this kind covers the instant, so a node-scoped injection answers
        True for its own station and for a node-less query, and a network-scoped injection answers
        True for every station. An unknown kind raises: a typo that returned False would look
        exactly like a runtime that never meets the fault.
        """
        _check_kind(kind)
        for event in self.events():
            if event.kind != kind:
                continue
            if not event.at_s <= at_s < event.at_s + event.detail["coverage_s"]:
                continue
            if node_id is None or event.node_id is None or event.node_id == node_id:
                return True
        return False

    def describe(self) -> dict:
        """One-line-auditable summary: kind, count, first and last instant, nodes touched."""
        events = self.events()
        return {
            "kind": self.spec.kind,
            "count": len(events),
            "first_at_s": events[0].at_s if events else None,
            "last_at_s": events[-1].at_s if events else None,
            "nodes": tuple(sorted({e.node_id for e in events if e.node_id})),
            "scope": KIND_SCOPE[self.spec.kind],
            "seed": self.spec.seed,
            "hours": self.spec.hours,
            "covered_s": sum(e.detail["coverage_s"] for e in events),
        }

    # ------------------------------------------------------------------ drawing
    def _draw(self, node_id: str | None, slot_s: int, tag: str = "") -> float:
        """A draw addressed by (seed, kind, node, slot), plus an optional field tag.

        The key names the slot, never the instant a jittered draw produced, so a draw cannot depend
        on its own result. The node position holds the scope name when the fault names no station.
        """
        seed, kind = self.spec.seed, self.spec.kind
        if tag:
            return stable_uniform(seed, kind, _subject(node_id), slot_s, tag)
        return stable_uniform(seed, kind, _subject(node_id), slot_s)

    def _pick_node(self, candidates: tuple[str, ...], slot_s: int) -> str:
        """Which station this injection hits, when the spec does not name one.

        A keyed tournament: every candidate's own draw addresses (seed, kind, node, slot) and the
        lowest wins, so there is no separate selection draw whose key would have to leave the node
        out, and the result cannot depend on the order the candidates were listed in. The seed moves
        the trajectory from station to station; it does not move the number of injections.
        """
        return min(sorted(candidates), key=lambda nid: self._draw(nid, slot_s))

    def _pick_jitter(self, node_id: str | None, slot_s: int, jitter_s: int) -> int:
        """A keyed offset in [0, jitter_s) on the tick grid, for starts nobody schedules."""
        ticks = jitter_s // TICK_S
        if ticks <= 0:
            return 0
        return int(self._draw(node_id, slot_s, "jitter") * ticks) * TICK_S

    def _pick_delay(self, node_id: str | None, slot_s: int, delay_s: int | None) -> int:
        """The holdout of a delayed command: the knob when given, otherwise the documented band."""
        if delay_s is not None:
            return delay_s
        low, high = 2 * MIN_PROFILE_GAP_S, 4 * MIN_PROFILE_GAP_S
        ticks = (high - low) // TICK_S
        return low + int(self._draw(node_id, slot_s, "delay") * ticks) * TICK_S

    def _pick_hop(self, node_id: str | None, slot_s: int) -> str:
        """Which leg of the downlink lost the request.

        A: the reference trajectory splits the injections evenly across the two legs, because no
        evidence in hand says which leg dominates in this deployment and assuming one would decide
        the question by default. The two legs are not interchangeable: a loss on the backhaul leg
        means the gateway never held the request, a loss on the access leg means it did.
        """
        return "backhaul" if self._draw(node_id, slot_s, "hop") < 0.5 else "access"

    # ---------------------------------------------------------------- schedule
    def _config(self) -> dict:
        """The spec's knobs with the class defaults filled in, plus the node scope."""
        defaults = KIND_DEFAULTS[self.spec.kind]
        cfg = {name: (getattr(self.spec, name) if getattr(self.spec, name) is not None else default)
               for name, default in defaults.items()}
        cfg["nodes"] = tuple(sorted(self.spec.nodes or reference_node_ids()))
        return cfg

    def _slots(self, cfg: dict) -> list[tuple[int, str | None, int]]:
        """(slot, node_id, at_s) for every injection this spec produces.

        A slot is the kind's scheduled instant; `at_s` is the slot after jitter. An injection whose
        covered window would leave the run is not scheduled at all, and the test uses the largest
        jitter the spec allows so that the count of injections does not depend on the seed: a
        truncated window would misreport its own length, and a count that moved with the seed would
        make the trajectory's shape unreadable.
        """
        total_s = self.spec.hours * 3600
        network_scope = KIND_SCOPE[self.spec.kind] == "network"
        out: list[tuple[int, str | None, int]] = []
        index = 0
        while cfg["count"] is None or index < cfg["count"]:
            slot_s = cfg["first_at_s"] + index * cfg["period_s"]
            index += 1
            if slot_s + cfg["jitter_s"] + cfg["duration_s"] > total_s:
                break                     # every later slot is later still, so nothing after fits
            node_id = None if network_scope else self._pick_node(cfg["nodes"], slot_s)
            at_s = slot_s + self._pick_jitter(node_id, slot_s, cfg["jitter_s"])
            out.append((slot_s, node_id, at_s))
        return out

    def _detail(self, cfg: dict, slot_s: int, node_id: str | None, at_s: int) -> dict:
        """What was injected, in enough detail to audit this event on its own."""
        kind = self.spec.kind
        if kind == "request_lost":
            hop = self._pick_hop(node_id, slot_s)
            return {
                "hop": hop,
                "coverage_s": cfg["duration_s"],
                "request_arrives": False,
                "gateway_received": hop == "access",
                "center_send_refused": hop == "backhaul",
            }
        if kind == "ack_lost":
            return {
                "effect": "applied",
                "coverage_s": cfg["duration_s"],
                "ack_arrives": False,
                "center_outcome_known": False,
                "effect_in_force_s": cfg["in_force_s"],
                # The earliest instant the effect can end: a delivery later inside the window
                # pushes this later, never earlier.
                "effect_in_force_until_s": at_s + cfg["in_force_s"],
            }
        if kind == "stale_command":
            delay_s = self._pick_delay(node_id, slot_s, cfg["delay_s"])
            return {
                "issued_at_s": at_s - delay_s,
                "arrives_at_s": at_s,
                "delay_s": delay_s,
                "coverage_s": cfg["duration_s"],
                # How many whole profile-change gaps the holdout spans. Zero means the released
                # command cannot be behind a newer one, which is a legitimate sensitivity point but
                # not the default this class is for.
                "holdout_gaps": delay_s // MIN_PROFILE_GAP_S,
                # The ordering this injection is for: whatever the runtime issued after
                # `newer_issued_after_s` and had in force before `in_force_before_s` is newer than
                # the command released here. Whether such a command exists is a property of the run,
                # checked against the run's own command log, not asserted by the injector.
                "stale_against": {"newer_issued_after_s": at_s - delay_s,
                                  "in_force_before_s": at_s},
            }
        if kind == "coordinator_restart":
            return {
                "process": "center",
                "crashed_at_s": at_s,
                "coverage_s": cfg["duration_s"],
                "downtime_s": cfg["duration_s"],
                "resumed_at_s": at_s + cfg["duration_s"],
                "volatile_state_lost": True,
                # The fault is the process, not the path: the backhaul and the gateway are up, so a
                # runtime cannot read this as connectivity loss.
                "backhaul_up": True,
                "gateway_up": True,
            }
        if kind == "node_restart":
            return {
                "cause": "power_loss",
                "coverage_s": cfg["duration_s"],
                "outage_s": cfg["duration_s"],
                "recovered_at_s": at_s + cfg["duration_s"],
                "volatile_state_lost": True,
                "sampling_suspended": True,
                "uplinks_suspended": True,
            }
        if kind == "backhaul_only":
            return {
                "hop": "backhaul",
                "coverage_s": cfg["duration_s"],
                "outage_s": cfg["duration_s"],
                "restored_at_s": at_s + cfg["duration_s"],
                "center_process_up": True,
                "gateway_up": True,
                "access_up": True,
                "gateway_buffers_uplinks": True,
                "center_receives_uplinks": False,
            }
        raise AssertionError(f"no detail is defined for {kind!r}")

    def _build(self) -> list[InjectedEvent]:
        cfg = self._config()
        out: list[InjectedEvent] = []
        epochs: dict[str, int] = {}
        for slot_s, node_id, at_s in self._slots(cfg):
            detail = self._detail(cfg, slot_s, node_id, at_s)
            if self.spec.kind in ("coordinator_restart", "node_restart"):
                # An audit ordinal, incremented per subject: the k-th restart of this station, or of
                # the center, inside this trajectory. It is not a claim about the device's own boot
                # counter, which the runtime reads from the node, not from here.
                key = _subject(node_id)
                epochs[key] = epochs.get(key, 0) + 1
                detail["restart_epoch"] = epochs[key]
            out.append(InjectedEvent(at_s=at_s, kind=self.spec.kind, node_id=node_id,
                                     detail=detail))
        return out


class FaultFree:
    """The control trajectory: the same run with no injection at all.

    Same interface as `FaultInjector`, so a table of trajectories can hold the control beside the
    six classes and nothing has to special-case it. A spec may be passed to carry the run's seed and
    length into `describe()`; its kind is ignored, because the control injects nothing whatever the
    spec says.
    """

    kind = "fault_free"

    def __init__(self, spec: FaultSpec | None = None) -> None:
        self.spec = spec

    def events(self) -> list[InjectedEvent]:
        return []

    def active(self, kind: str, at_s: int, node_id: str | None = None) -> bool:
        _check_kind(kind)
        return False

    def describe(self) -> dict:
        spec = self.spec
        return {
            "kind": "fault_free",
            "count": 0,
            "first_at_s": None,
            "last_at_s": None,
            "nodes": (),
            "scope": "none",
            "seed": spec.seed if spec is not None else 0,
            "hours": spec.hours if spec is not None else DEFAULT_HOURS,
            "covered_s": 0,
        }
