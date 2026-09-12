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


def run_episode(policy: Policy, hours: int = 72, seed: int = 0,
                profile: LoRaProfile | None = None, downlink_per_uplink: int = 1,
                grant_announcement: bool = True) -> tuple[RunRecord, dict, ControlPlane]:
    """Run one episode and return the ground-truth record, per-node state and the channel.

    Profile changes reach a node only through the channel: the center enqueues a command, the
    gateway delivers it inside an opportunity, and the node applies it. Nothing about the
    demanded schedule is visible to the node unless a command carried it there, which is what
    makes the local-rules arm a real comparison rather than a strawman.
    """
    deployment = build_deployment(seed)
    plane = ControlPlane(profile or LoRaProfile(), seed=seed,
                         downlink_per_uplink=downlink_per_uplink)

    nodes = {n.nid: n for n in deployment.nodes}
    runtimes = {n.nid: NodeRuntime(node_id=n.nid, role=n.role) for n in deployment.nodes}
    status: dict[str, dict] = {}

    in_flight: dict[str, PendingCommand] = {}
    view_in_flight: frozenset = frozenset()
    heard_uplinks: list[tuple[str, int]] = []
    command_seq = 0
    uplink_attempt = 0
    config_mismatch_s = 0.0

    for t_s in range(0, hours * 3600, TICK_S):
        hour = t_s / 3600.0

        # ---- what the scenario demands, disclosed to the policy only if it is granted ----
        # The center knows the whole schedule once it holds the announcement, including when the
        # risk window ends. Disclosing only the non-normal stretches would leave every node in the
        # dense profile for the rest of the run: the policy would have nothing to say outside a
        # window, and the recovery half of the workflow would never be exercised at all.
        demanded = {}
        if grant_announcement:
            wanted = profile_for_hour(hour, RISK_WINDOWS_H)
            demanded = {nid: wanted for nid in runtimes}

        view = WorldView(t_s=t_s, node_ids=tuple(runtimes), status=status,
                         demanded_profile=demanded,
                         center_has_announcement=bool(demanded),
                         in_flight=view_in_flight)

        # ---- the center tries to send ----
        for node_id, payload in policy.plan(view):
            command_seq += 1
            identity = f"{node_id}:profile:{payload['profile']}:{command_seq}"
            message = DownlinkMessage(identity=identity, kind="command",
                                      payload_bytes=38, enqueued_at=t_s,
                                      expires_at=t_s + 6 * 3600)
            if plane.center_send(node_id, message, int(hour)):
                in_flight[identity] = PendingCommand(identity=identity, node_id=node_id,
                                                     payload=payload, issued_at=t_s,
                                                     expires_at=message.expires_at)

        view_in_flight = frozenset(c.node_id for c in in_flight.values())

        # ---- nodes sample, upload, and receive whatever the window carries ----
        for node_id, rt in runtimes.items():
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
                rt.upload_result(packet, heard=rec.arrived, arrival_s=t_s)
                if rec.arrived:
                    heard_uplinks.append((node_id, t_s))
                    # The packet carries the node's status and acknowledges what arrived.
                    rt.confirm([s.sample_id for s in packet])
                    status[node_id] = rt.snapshot(t_s)

                for delivery in rec.delivered:
                    command = in_flight.pop(delivery.message.identity, None)
                    if command is not None and "profile" in command.payload:
                        rt.set_profile(command.payload["profile"], t_s)
                        command.confirmed = True
                        if isinstance(policy, OraclePolicy):
                            policy.note_confirmed(node_id, command.payload["profile"])

    record = RunRecord(
        demands=build_demand(deployment, hours=hours, seed=seed),
        taken=[s for rt in runtimes.values() for s in rt.taken],
        arrived=[(s, arrival) for rt in runtimes.values() for s, arrival in rt.received],
        heard_uplinks=heard_uplinks,
        node_ids=tuple(runtimes),
        radio_wh={nid: e.total_wh for nid, e in plane.energy.items()},
        airtime_ms=plane.airtime_uplink_ms + plane.airtime_downlink_ms,
        config_mismatch_s=config_mismatch_s,
        spurious_measurements=0,
        log_entries=0,
    )
    state = {nid: rt for nid, rt in runtimes.items()}
    return record, state, plane
