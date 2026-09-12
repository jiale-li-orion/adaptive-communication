#!/usr/bin/env python3
"""
runner.py — one episode of the monitoring workflow, and the record it leaves behind.

The runner owns the clock and the ground truth. It advances the node model and the control plane,
lets a policy decide what the center should try to send, and writes down everything that happened.
The policy is the only thing that varies between arms; the demand set, the weather, the node
schedules and the scoring are shared.

WHAT THE POLICY MAY SEE. A policy is handed a `WorldView`: the current time, the nodes it can
address, the demanded profile schedule if the scenario grants it, and for each node the last
status that a status read actually returned. It is not handed the sample schedule, the arrival
records, or the demand list. That boundary is the experiment: a policy that could read the ground
truth would be solving a different problem, and the leak test in the scorer's regression file
exists to keep the boundary from eroding.

WHAT "ORACLE" MEANS HERE. The oracle policy is not allowed to bypass the channel. It knows exactly
which profile each node should be on and when, it never spends an opportunity on a read it does
not need, and it never re-sends a command it has evidence has landed. That is an upper bound on
execution quality under the real channel, which is the bound that matters: a bound that also
assumed perfect delivery would say nothing about whether the execution layer is worth building.

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

from dataclasses import dataclass, field

from task_generator import (build_deployment, build_demand, profile_for_hour,
                            RISK_WINDOWS_H, PROFILE_NORMAL)
from node_model import NodeRuntime, TICK_S
from opportunity import ControlPlane, LoRaProfile, DownlinkMessage
from scorer import RunRecord
from interfaces import AgentInterface
# `policies` resolves the two policies that live here by name rather than importing them, so this
# direction of the dependency is the one that stays acyclic.
from faults import PROFILE_CHANGE_INSTANTS_S
from policies import OP_REQUEST_MEASUREMENT, OP_SET_PROFILE, OP_UPLOAD_RECORDS, OPS

SF_BY_ROLE = {"deformation": 9, "rainfall": 8}     # A: a denser site uses a lower spreading factor
UPLINK_PAYLOAD_BYTES = 20                          # A: header plus a batch of record ids


@dataclass
class WorldView:
    """Everything a policy is allowed to know at a given instant."""

    t_s: int
    node_ids: tuple[str, ...]
    status: dict                      # node_id -> last status read that actually returned
    demanded_profile: dict = field(default_factory=dict)   # node_id -> profile the scenario wants
    center_has_announcement: bool = False
    # Nodes whose profile command is still unconfirmed. A policy must not treat "I asked" as
    # "it is handled": the center can refuse the send outright when the backhaul is down, and
    # nothing has been delivered until the node said so.
    in_flight: frozenset = frozenset()
    # The newest sample instant the center itself holds for each node. This is the center's own
    # archive, not the node's buffer: a gap is the distance between the two, and a policy that
    # could only see the node's side would be reading the simulator rather than its own records.
    archive_newest: dict = field(default_factory=dict)


@dataclass
class PendingCommand:
    identity: str
    node_id: str
    payload: dict
    issued_at: int
    expires_at: int | None = None
    confirmed: bool = False


class Policy:
    """Base class. A policy decides what the center tries to send this tick."""

    name = "policy"

    def plan(self, view: WorldView) -> list[tuple[str, dict]]:
        """Return (node_id, payload) pairs to enqueue this tick."""
        return []


class LocalRulesPolicy(Policy):
    """No central control at all.

    The node follows its own schedule. This is the engineering status quo the paper has to beat:
    everything already deployed does something like this, and if it is sufficient for the demand
    set, then the execution layer has nothing to add.
    """

    name = "local_rules"

    def plan(self, view: WorldView) -> list[tuple[str, dict]]:
        return []


class OraclePolicy(Policy):
    """Knows the demanded profile and never wastes an opportunity.

    It issues the profile command the instant the demanded profile changes, addresses only the
    nodes that need it, and stops re-sending once it has evidence the command landed. It does not
    know whether the channel will carry the command, and it cannot retry outside an opportunity.
    """

    name = "oracle"

    def __init__(self, command_ttl_s: int = 3600) -> None:
        self.command_ttl_s = command_ttl_s
        self.confirmed: dict[str, str] = {}     # node_id -> profile the node confirmed

    def note_confirmed(self, node_id: str, profile: str) -> None:
        self.confirmed[node_id] = profile

    def plan(self, view: WorldView) -> list[tuple[str, dict]]:
        out = []
        for node_id, wanted in view.demanded_profile.items():
            # Ask again only while nothing is in flight and the node has not confirmed this very
            # profile. Treating "I asked" as "it is handled" would give up silently whenever the
            # center refused the send, which is a failure of the policy, not of the channel.
            if node_id in view.in_flight or self.confirmed.get(node_id) == wanted:
                continue
            out.append((node_id, {"op": "set_monitoring_profile", "profile": wanted}))
        return out


def _after_coordinator_restart(policy, lost=(), unresolved=()):
    """Give a policy the chance to forget what it kept only in memory.

    The run does not decide what a runtime loses on restart; it only guarantees the restart
    happened. A policy that keeps durable state across the restart simply does not implement the
    hook, and one that holds it in memory does. Without this the restart fault would be a no-op and
    would measure nothing.
    """
    hook = getattr(policy, "on_restart", None)
    if callable(hook):
        hook(lost=list(lost), unresolved=list(unresolved))
    return policy


def run_episode(policy: Policy, hours: int = 72, seed: int = 0,
                profile: LoRaProfile | None = None, downlink_per_uplink: int = 1,
                grant_announcement: bool = True, supply=None,
                fault=None, paths=None) -> tuple[RunRecord, dict, ControlPlane]:
    """Run one episode and return the ground-truth record, per-node state and the channel.

    Profile changes reach a node only through the channel: the center enqueues a command, the
    gateway delivers it inside an opportunity, and the node applies it. Nothing about the
    demanded schedule is visible to the node unless a command carried it there, which is what
    makes the local-rules arm a real comparison rather than a strawman.

    `supply` couples the run to the power model. When it is given, a node without power does
    nothing: it takes no sample, opens no window and creates no opportunity, and the energy its
    radio spends is charged back into its own battery. Without it the run assumes every node is
    powered throughout, which is what the mechanism-isolation layer wants and what no energy claim
    may be made from.

    `fault` injects the diagnostic faults. It is consulted at four points -- backhaul, uplink,
    downlink and restart -- so a fault trajectory is a property of the run rather than of any arm.
    """
    deployment = build_deployment(seed)
    plane = ControlPlane(profile or LoRaProfile(), seed=seed,
                         downlink_per_uplink=downlink_per_uplink)

    nodes = {n.nid: n for n in deployment.nodes}
    runtimes = {n.nid: NodeRuntime(node_id=n.nid, role=n.role) for n in deployment.nodes}
    status: dict[str, dict] = {}

    in_flight: dict[str, PendingCommand] = {}
    view_in_flight: frozenset = frozenset()
    # Every command the center issues goes through the interface layer, so the run leaves an
    # auditable trail of what was asked, what was observed, and what is in force.
    # Durable storage is a capability of the center. `journal` is the only thing that differs
    # between the two kinds of coordinator on a restart, which is what makes the restart comparison
    # about the runtime rather than about the fault.
    from opportunity import PathSpec as _PathSpec
    if paths:
        plane.paths = [_PathSpec(str(name), float(p_good)) for name, p_good in paths]
    from operations import Journal as _Journal
    journal = _Journal() if getattr(policy, "durable_storage", False) else None
    iface = AgentInterface(plane, runtimes, journal=journal)
    drained_wh = {nid: 0.0 for nid in runtimes}
    stale_hold: list[tuple[int, str, str]] = []      # (release_at_s, identity, node_id)
    stale_arm: dict[str, int] = {}                   # identity -> the instant it may arrive

    def faulted(kind: str, at_s: int, node_id: str | None = None) -> bool:
        return fault is not None and fault.active(kind, at_s, node_id)

    # Discrete faults are handled at their own instants rather than through `active()`. A restart
    # covers a window, and treating every tick inside it as a fresh restart would fire the recovery
    # hook ten times for one crash; a delayed command is defined by when it was issued, not by when
    # it lands, and `active()` is true only for the one-minute arrival slot.
    restart_at: set[int] = set()
    node_down: dict[str, list[tuple[int, int]]] = {}
    stale_plan: dict[tuple[str, int], int] = {}
    # Faults that are properties of one action -- a lost request, a lost confirmation, a command
    # held back until a newer one has landed -- cannot be scheduled on the clock. A clock instant
    # lands on whatever the deployment happens to be doing at that minute, and for a node that
    # receives a command six times in 72 hours that is usually nothing. The event table then reads
    # non-empty while no action was ever touched. These are armed by nominal instant and consumed
    # by the next real action on the scoped node, which keeps them deterministic and effective.
    armed: dict[str, list[tuple[int, str]]] = {}      # kind -> [(nominal_at_s, node_id), ...]
    if fault is not None:
        for event in fault.events():
            detail = event.detail
            if event.kind == "coordinator_restart":
                restart_at.add(event.at_s)
            elif event.kind == "node_restart":
                start = event.at_s
                end = int(detail.get("recovered_at_s", start))
                node_down.setdefault(event.node_id, []).append((start, end))
                restart_at.add(start)
            elif event.kind == "stale_command":
                issued = int(detail["issued_at_s"])
                arrives = int(detail["arrives_at_s"])
                stale_plan[(event.node_id, issued)] = arrives
                armed.setdefault("stale_command", []).append((issued, event.node_id, arrives - issued))
            elif event.kind in ("request_lost", "ack_lost"):
                armed.setdefault(event.kind, []).append((event.at_s, event.node_id, 0))
        # Only the backhaul fault reaches into the channel's own draw. It can take the backhaul
        # down and never bring it up, so it cannot advantage any arm.
        plane.backhaul_gate = lambda hour: not faulted("backhaul_only", int(hour) * 3600)

    def spans_a_change(at_s: int, delay: int) -> bool:
        """Whether a command issued at `at_s` and released `delay` later straddles a profile change.

        This is what makes an ordering fault able to do domain harm. A command whose value nothing
        supersedes before it lands writes the value already in force, so it reorders the protocol
        and changes nothing at the node. Observed: with the holdout inside the command's validity
        window but shorter than the interval between demand changes, every injection produced a
        reorder and no overwrite.
        """
        for change in PROFILE_CHANGE_INSTANTS_S:
            if at_s < change <= at_s + delay:
                return True
        return False

    def take_armed(kind: str, at_s: int, node_id: str) -> tuple[bool, int]:
        """Consume the earliest armed hit of `kind` once a real action for `node_id` arrives.

        Returns whether the fault applies, plus the delay the fault carries (zero for the faults
        that only need to destroy something). The nominal instant is a lower bound: the fault waits
        for the node to actually do something rather than expiring unused.
        """
        for index, entry in enumerate(armed.get(kind, ())):
            nominal_at, node = entry[0], entry[1]
            if node != node_id or at_s < nominal_at:
                continue
            armed[kind].pop(index)
            return True, entry[2]
        return False, 0

    def mark_applied_at(node_id: str, payload: dict, t_s: int) -> None:
        """Remember when a logical operation actually took effect, for later dedups to quote."""
        logical = payload.get("logical")
        if logical is not None:
            applied_logical_at.setdefault((node_id, logical), t_s)

    def observed_at_for(node_id: str, payload: dict, now_s: int) -> int:
        """When the centre may date its knowledge of this operation."""
        logical = payload.get("logical")
        if logical is None:
            return now_s
        return applied_logical_at.get((node_id, logical), now_s)

    def expires_before(command, t_s: int) -> bool:
        """Whether a command reached the node after its own deadline.

        An expired order must not be carried out. A measurement request that arrives after its
        window has closed asks for something that is no longer wanted, and letting the node take it
        anyway would credit the center with a service it did not deliver on time -- the deadline is
        part of the instruction, not metadata about it.
        """
        return command.expires_at is not None and t_s > command.expires_at

    def apply_command_effect(rt, node_id: str, payload: dict, t_s: int) -> None:
        """What the node does when a command reaches it, by interface.

        `set_monitoring_profile` changes the schedule; `request_measurement` creates an obligation
        to take a new sample inside a window; `upload_records` orders a bounded range of history.
        They are different effects on different node state, which is why they are dispatched here
        rather than collapsed into one payload shape.
        """
        op = payload.get("op")
        if op == OP_SET_PROFILE:
            rt.set_profile(payload["profile"], t_s)
            profile_timeline.append((node_id, t_s, payload["profile"]))
        elif op == OP_REQUEST_MEASUREMENT:
            rt.demand_measurement(payload["request_id"], payload["window_start"],
                                  payload["deadline"])
        elif op == OP_UPLOAD_RECORDS:
            rt.order_backfill(payload["start"], payload["end"], payload["cursor"],
                              payload["budget"])

    def remote_apply(node_id: str, payload: dict) -> str:
        """The remote's decision for one delivered operation: `applied`, `duplicate`, or `fenced`.

        Both ways a command can reach a node -- the ordinary window and the release of one the
        network held -- go through here. Having a second path that wrote the profile directly is
        what let a stale command overwrite a newer one even when the sender had put a version on
        the wire, which is the exact hazard the ordering fault is supposed to create.
        """
        nonlocal reaccepted, fenced
        logical = payload.get("logical")
        version = payload.get("version")
        if logical is not None and logical in applied_logicals.get(node_id, ()):
            reaccepted += 1
            return "duplicate"
        if version is not None and version < applied_version.get(node_id, 0):
            fenced += 1
            return "fenced"
        if logical is not None:
            applied_logicals.setdefault(node_id, set()).add(logical)
        if version is not None:
            applied_version[node_id] = version
        return "applied"

    def node_suspended(node_id: str, t_s: int) -> bool:
        """Whether a node is inside an outage an injected restart put it in."""
        for start, end in node_down.get(node_id, ()):
            if start <= t_s < end:
                return True
        return False

    def charge_radio(node_id: str) -> None:
        """Move the radio energy a node has spent into its own battery."""
        if supply is None:
            return
        spent = plane.energy.get(node_id)
        if spent is None:
            return
        delta = spent.total_wh - drained_wh[node_id]
        if delta > 0:
            supply.drain_wh(node_id, delta)
            drained_wh[node_id] = spent.total_wh

    def powered(node_id: str, t_s: int) -> bool:
        return True if supply is None else supply.alive(node_id, t_s)
    heard_uplinks: list[tuple[str, int]] = []
    command_seq = 0
    uplink_attempt = 0
    config_mismatch_s = 0.0
    # The node's own profile history. The false-success metric needs to ask what was actually in
    # force at the instant the center settled a record, so the history has to exist.
    profile_timeline: list[tuple[str, int, str]] = [
        (nid, 0, rt.profile) for nid, rt in runtimes.items()]
    # Records the center has applied but not yet learned about, per node. `ack_lost` removes the
    # fast confirmation, so the center has to wait for the node's next ordinary telemetry report.
    awaiting_observation: dict[str, list[str]] = {}
    # Remote-side contract state: what each node has already applied, and the newest version it
    # has accepted. Reset by a restart of the node, not of the center.
    # When each logical operation actually took effect. A retry that the remote dedups was not
    # applied now -- the operation it repeats was applied then, and saying otherwise would date the
    # centre's knowledge to the retry and make the knowledge-latency metric measure the wrong pair.
    applied_logicals: dict[str, set[str]] = {}
    applied_logical_at: dict[tuple[str, str], int] = {}
    applied_version: dict[str, int] = {}
    reaccepted = 0
    fenced = 0
    # Two different events, kept apart because they have different owners. `stale_reorders` is a
    # protocol-level ordering violation: a write issued earlier took effect after one issued later.
    # `stale_overwrites` is the domain harm: that violation actually put a value back which the
    # node had already moved past. A reorder that writes the same value is not an overwrite, and
    # conflating them would credit the ordering metric with harm that did not happen.
    stale_reorders = 0
    stale_overwrites = 0
    stale_armed_real = 0
    stale_held = 0
    stale_released = 0
    # One row per released held command: what it was, when it landed, and what had landed before.
    # The ordering fault is only meaningful if a newer intent got in first, so that has to be
    # legible rather than inferred from a counter that could be zero for either reason.
    stale_trace: list[dict] = []
    refused_actions = 0
    expired_commands = 0
    # Time during which the center was waiting on at least one operation whose effect it could not
    # establish. This is the duration of the ambiguity itself, not of any one command's timeout: a
    # tick with three unresolved operations counts once, because the harm is the interval in which
    # the center did not know, not how many things it did not know about.
    unknown_s = 0.0
    llm_calls = 0
    llm_illegal = 0
    restart_events = 0
    restart_unresolved = 0     # operations a journaled center knew were outstanding after a restart
    restart_lost = 0           # operations a volatile center could not say anything about
    # A command the network is holding is no longer pending at the center. Keeping it in `in_flight`
    # told every policy that the node still had a command outstanding, so none of them issued the
    # newer write that the held one is supposed to arrive after -- and the ordering hazard silently
    # required no ordering. The command object is kept here instead.
    held_commands: dict[str, object] = {}
    # The newest intent each node has actually applied, by issue time. A release from the network
    # that lands after this is an older write replacing a newer one: the hazard itself, as opposed
    # to `fenced`, which counts the hazard being refused.
    newest_applied: dict[str, tuple[int, str, str | None]] = {}

    for t_s in range(0, hours * 3600, TICK_S):
        hour = t_s / 3600.0
        if supply is not None:
            supply.step_to(t_s)
        if t_s in restart_at:
            # A node that loses power reboots: its volatile configuration is gone and it comes back
            # on the default profile. Its flash-resident record buffer survives, which is why the
            # archive can still be recovered afterwards. A-layer: which state is volatile is a
            # property of the device, not of this model.
            for node_id in node_down:
                if any(start == t_s for start, _ in node_down[node_id]):
                    runtimes[node_id].set_profile(PROFILE_NORMAL, t_s)
                    in_flight = {k: v for k, v in in_flight.items() if v.node_id != node_id}
            if fault is not None and any(e.at_s == t_s and e.kind == "coordinator_restart"
                                         for e in fault.events()):
                # The center forgot what it only knew from memory. Whatever a runtime keeps
                # durably is its own business; the run only guarantees the amnesia is real.
                lost = iface.forget_volatile_state()
                restart_events += 1
                if journal is not None:
                    restart_unresolved += len(iface.recovered_unresolved)
                else:
                    restart_lost += len(lost)
                policy = _after_coordinator_restart(policy, lost=lost,
                                                    unresolved=iface.recovered_unresolved)

        # ---- what the scenario demands, disclosed to the policy only if it is granted ----
        # The center knows the whole schedule once it holds the announcement, including when the
        # risk window ends. Disclosing only the non-normal stretches would leave every node in the
        # dense profile for the rest of the run: the policy would have nothing to say outside a
        # window, and the recovery half of the workflow would never be exercised at all.
        demanded = {}
        if grant_announcement:
            wanted = profile_for_hour(hour, RISK_WINDOWS_H)
            demanded = {nid: wanted for nid in runtimes}

        archive_newest = {nid: rt_.newest_received_at for nid, rt_ in runtimes.items()
                          if rt_.newest_received_at is not None}
        if iface.pending:
            unknown_s += TICK_S

        view = WorldView(t_s=t_s, node_ids=tuple(runtimes), status=status,
                         demanded_profile=demanded,
                         center_has_announcement=bool(demanded),
                         in_flight=view_in_flight,
                         archive_newest=archive_newest)

        # ---- the center tries to send ----
        for node_id, payload in policy.plan(view):
            # The four interfaces are the whole action surface. Anything outside the set is refused
            # here rather than silently dropped: a policy that asks for something the contract does
            # not name has made an error, and swallowing it would make the policy look harmless
            # while the demand it was trying to serve went unserved.
            op = payload.get("op")
            if op == OP_SET_PROFILE and "profile" not in payload:
                refused_actions += 1
                continue
            if op == OP_SET_PROFILE:
                record = iface.set_monitoring_profile(
                    node_id, payload["profile"], generation=command_seq,
                    expires_at=t_s + 6 * 3600, now_s=t_s,
                    path=int(payload.get("path", 0)))
            elif op == OP_REQUEST_MEASUREMENT:
                record = iface.request_measurement(
                    node_id, payload["request_id"], payload["deadline"], now_s=t_s)
            elif op == OP_UPLOAD_RECORDS:
                record = iface.upload_records(
                    node_id, payload["start"], payload["end"], payload["cursor"],
                    payload["budget"], now_s=t_s)
            else:
                # `read_status` is answered from telemetry the node already sent; it is never
                # dispatched as an action, and anything else is not an interface at all.
                refused_actions += 1
                continue
            command_seq += 1
            if record.attempts:
                if (node_id, t_s) in stale_plan:
                    stale_arm[record.identity] = stale_plan[(node_id, t_s)]
                else:
                    held, delay = take_armed("stale_command", t_s, node_id)
                    if held and spans_a_change(t_s, delay):
                        # Re-anchored to the dispatch that really happened, keeping the fault's own
                        # delay. The hazard is the same -- an old command landing after a newer one.
                        stale_arm[record.identity] = t_s + delay
                        stale_armed_real += 1
                    elif held:
                        # Armed, but this dispatch is not one the holdout can make stale. Holding a
                        # command whose value nothing supersedes produces a reorder that writes the
                        # value already in force: a protocol-level ordering violation and no domain
                        # harm. Keeping the fault armed until a dispatch it can actually make stale
                        # come along is what separates the two. The entry is put back, so the
                        # injection is delayed rather than spent.
                        armed.setdefault("stale_command", []).append((t_s, node_id, delay))
                in_flight[record.identity] = PendingCommand(
                    identity=record.identity, node_id=node_id, payload=payload, issued_at=t_s,
                    expires_at=record.deadline)

        # Commands the network held are released here, possibly long after a newer one landed.
        still_held = []
        for release_at, identity, node_id in stale_hold:
            if release_at > t_s:
                still_held.append((release_at, identity, node_id))
                continue
            command = held_commands.pop(identity, None)
            if command is None:
                continue
            if expires_before(command, t_s):
                expired_commands += 1
                iface.note_rejected(identity, t_s, "arrived after its own deadline")
                continue
            stale_released += 1
            _prior = newest_applied.get(node_id)
            stale_trace.append({"node": node_id, "released_at": t_s,
                                "issued_at": command.issued_at,
                                "prior_issued_at": _prior[0] if _prior else None,
                                "prior_identity": _prior[1] if _prior else None})
            verdict = remote_apply(node_id, command.payload)
            if verdict == "fenced":
                iface.note_rejected(identity, t_s, "stale write fenced by applied version")
                continue
            if verdict == "duplicate":
                iface.note_observed(identity, observed_at_for(node_id, command.payload, t_s))
                continue
            prior = newest_applied.get(node_id)
            if prior is not None and prior[0] > command.issued_at:
                # A newer intent had already been applied and this older one has just landed.
                stale_reorders += 1
                if prior[2] is not None and command.payload.get("profile") != prior[2]:
                    stale_overwrites += 1
                    iface.note_overwritten(prior[1], t_s, command.issued_at)
            apply_command_effect(runtimes[node_id], node_id, command.payload, t_s)
            mark_applied_at(node_id, command.payload, t_s)
            iface.note_applied(identity, t_s)
            iface.note_observed(identity, t_s)
            command.confirmed = True
            newest_applied[node_id] = (command.issued_at, identity,
                                       command.payload.get("profile"))
        stale_hold = still_held

        # The backhaul hands whatever the gateway has been holding to the center. Until this runs
        # for an item, no part of the center -- its status, its records, its interface -- has seen
        # it. A backhaul outage therefore delays telemetry by its own duration.
        for item in plane.backhaul_forward(t_s, delay_s=plane.backhaul_delay_s):
            rt = runtimes[item.node_id]
            records = item.payload or []
            rt.upload_result(records, heard=True, arrival_s=t_s)
            rt.confirm(item.sample_ids)
            status[item.node_id] = item.snapshot
            iface.note_telemetry(item.node_id, t_s, item.snapshot)
            # Now that the node's report is in front of the center, any effect the center had
            # applied but not confirmed is observed -- at this instant, not at the instant the
            # node applied it. The gap between the two is the knowledge latency.
            for identity in awaiting_observation.pop(item.node_id, ()):
                iface.note_observed(identity, t_s)

        view_in_flight = frozenset(c.node_id for c in in_flight.values())

        # ---- nodes sample, upload, and receive whatever the window carries ----
        for node_id, rt in runtimes.items():
            # A node without power does nothing at all: no sample, no window, no opportunity.
            # This is the coupling that makes a blackout a monitoring gap rather than a footnote.
            if not powered(node_id, t_s) or node_suspended(node_id, t_s):
                continue
            rt.maybe_sample(t_s)

            # profile mismatch time: what the scenario wants versus what the node is running
            if grant_announcement:
                want = profile_for_hour(hour, RISK_WINDOWS_H)
                if rt.profile != want:
                    config_mismatch_s += TICK_S

            if not rt.upload_due(t_s):
                continue
            batch = rt.begin_upload(t_s)
            if not batch:
                continue
            # One upload may be several packets. Each packet is its own uplink and therefore its
            # own opportunity, which is also how a backlog drains: the burst grows exactly when
            # the node has fallen behind.
            for packet in rt.pack(batch):
                payload_bytes = sum(s.payload_bytes for s in packet)
                rec = plane.uplink(node_id, hour=int(hour),
                                   sf=SF_BY_ROLE.get(nodes[node_id].role, 9),
                                   payload_bytes=max(payload_bytes, UPLINK_PAYLOAD_BYTES),
                                   attempt_index=uplink_attempt)
                uplink_attempt += 1
                charge_radio(node_id)
                rt.upload_result(packet, heard=rec.arrived, arrival_s=t_s)
                if rec.arrived:
                    # The gateway heard it. The center has not: the records and the status the
                    # packet carried sit at the gateway until the backhaul carries them, which is
                    # the hop that makes a backhaul outage a monitoring gap.
                    heard_uplinks.append((node_id, t_s))
                    plane.gateway_ingest(node_id, t_s, [s.sample_id for s in packet],
                                         rt.snapshot(t_s), payload=list(packet))

                for delivery in rec.delivered:
                    identity = delivery.message.identity
                    lost_request, _ = take_armed("request_lost", t_s, node_id)
                    if lost_request:
                        # The command was carried into the window and did not reach the node. The
                        # center learns nothing, which is what the fault is for.
                        continue
                    if identity in stale_arm:
                        # Held by the network from the moment it was issued. It is released at the
                        # instant the fault names, after newer commands have had their chance,
                        # which is the ordering hazard the fault exists to make.
                        stale_hold.append((stale_arm.pop(identity), identity, node_id))
                        held_commands[identity] = in_flight.pop(identity, None)
                        stale_held += 1
                        continue
                    command = in_flight.pop(identity, None)
                    if command is None:
                        continue
                    if expires_before(command, t_s):
                        expired_commands += 1
                        iface.note_rejected(identity, t_s, "arrived after its own deadline")
                        continue

                    # ---- the remote contract -------------------------------------------------
                    # The node applies an operation once and refuses one that is older than what it
                    # already has. Both halves are keyed on fields the sender chose to put on the
                    # wire, so a sender that leaves them out gets the unguarded behaviour and one
                    # that includes them is protected. This is the contract, not a policy.
                    verdict = remote_apply(node_id, command.payload)
                    if verdict == "duplicate":
                        # C1: this logical operation already took effect. Applying it again would be
                        # a second effect from one intent, which is the receipt exists to stop. The
                        # center is told it landed so it can settle rather than re-assert forever --
                        # dated to when it landed, not to this retry.
                        iface.note_observed(identity, observed_at_for(node_id, command.payload, t_s))
                        continue
                    if verdict == "fenced":
                        # C2: an older write than the one in force. The center is told it was
                        # refused, so it stops re-asserting instead of waiting out a timeout.
                        iface.note_rejected(identity, t_s, "stale write fenced by applied version")
                        continue
                    # --------------------------------------------------------------------------

                    prior = newest_applied.get(node_id)
                    if prior is not None and prior[0] > command.issued_at:
                        stale_reorders += 1
                        if prior[2] is not None and command.payload.get("profile") != prior[2]:
                            stale_overwrites += 1
                            iface.note_overwritten(prior[1], t_s, command.issued_at)
                    newest_applied[node_id] = (command.issued_at, identity,
                                               command.payload.get("profile"))
                    apply_command_effect(rt, node_id, command.payload, t_s)
                    mark_applied_at(node_id, command.payload, t_s)
                    command.confirmed = True
                    # Applied at the moment the node applied it, observed at the moment the center
                    # learned that it had. The two are the same only because this model has no
                    # separate acknowledgement hop on top of the delivery.
                    # The node applied it. That is true whether or not any confirmation survives,
                    # so the node-side fact is recorded unconditionally.
                    iface.note_applied(identity, t_s)
                    if "profile" in command.payload:
                        profile_timeline.append((node_id, t_s, command.payload["profile"]))
                    lost_ack, _ = take_armed("ack_lost", t_s, node_id)
                    if lost_ack:
                        # The confirmation did not survive. The effect is in force at the node while
                        # the center's record stays unresolved, and the center will only learn it
                        # from the node's next ordinary telemetry report -- which is late enough to
                        # matter, and is what gives this fault a consequence at all.
                        iface.pending.pop(identity, None)
                        awaiting_observation.setdefault(node_id, []).append(identity)
                        continue
                    iface.note_observed(identity, t_s)
                    if isinstance(policy, OraclePolicy) and "profile" in command.payload:
                        policy.note_confirmed(node_id, command.payload["profile"])

    # A model planner keeps its own call accounting; it is read here rather than pushed from the
    # planner so that a policy cannot report a number the run did not produce.
    _planner = getattr(policy, "planner", policy)
    llm_calls = int(getattr(_planner, "calls", 0) or 0)
    llm_illegal = int(getattr(_planner, "illegal", 0) or 0)

    record = RunRecord(
        hours=float(hours),
        demands=build_demand(deployment, hours=hours, seed=seed),
        taken=[s for rt in runtimes.values() for s in rt.taken],
        arrived=[(s, arrival) for rt in runtimes.values() for s, arrival in rt.received],
        heard_uplinks=heard_uplinks,
        node_ids=tuple(runtimes),
        radio_wh={nid: e.total_wh for nid, e in plane.energy.items()},
        airtime_ms=plane.airtime_uplink_ms + plane.airtime_downlink_ms,
        config_mismatch_s=config_mismatch_s,
        spurious_measurements=0,
        log_entries=len(iface.records),
        profile_timeline=profile_timeline,
        action_records=[r.as_dict() for r in iface.records.values()],
        reaccepted=reaccepted, fenced=fenced, stale_overwrites=stale_overwrites,
        refused_actions=refused_actions, expired_commands=expired_commands,
        unknown_s=unknown_s, llm_calls=llm_calls, llm_illegal=llm_illegal,
        restart_events=restart_events, restart_unresolved=restart_unresolved,
        restart_lost=restart_lost,
        stale_reorders=stale_reorders,
        stale_held=stale_held, stale_released=stale_released, stale_trace=stale_trace,
    )
    record.audit_trail = iface.audit_trail()
    if supply is not None:
        for node_id in runtimes:
            charge_radio(node_id)
        record.supply_ledger = supply.ledger()
        record.dead_node_ticks = sum(
            1 for nid in runtimes for t_s in range(0, hours * 3600, TICK_S)
            if not supply.alive(nid, t_s))
    state = {nid: rt for nid, rt in runtimes.items()}
    return record, state, plane
