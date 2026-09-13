#!/usr/bin/env python3
"""
interfaces.py — the four actions the center can take, and the evidence each one leaves.

A command's effect and the center's knowledge of that effect are different things, and this module
keeps them apart on purpose. Every action returns an `ActionRecord` carrying:

  applied_at        when the node applied it, as the node reported it. None if it never did.
  observed_at       when the center learned the outcome. None while the outcome is unknown.
  currently_active  whether the effect is in force now. A profile that was applied and was later
                    superseded by a legitimate update leaves applied_at set and currently_active
                    false: the earlier success is not retracted by a later one.

Three of the four actions need a downlink and therefore consume a control opportunity. The fourth,
`read_status`, usually does not: a node's telemetry already carries its status, so a read is
answered from the last report whenever that report is young enough. Only a read whose evidence is
older than the caller's `max_age` has to be asked for, and only then does it cost an opportunity.
That is the difference between "ask the far side" and "use what the far side already told you", and
it is the difference the whole opportunity budget turns on.

`request_measurement` is the one action whose effect the center cannot deduce from configuration.
A sample either exists with a timestamp inside the request's window or it does not, and an old
cached reading cannot be passed off as a new acquisition: the record carries the request id and the
sample's own timestamp, and the two have to agree.

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

from node_model import TICK_S
from opportunity import DownlinkMessage

# Outcomes. `unknown` is a first-class result: it says the center asked and did not learn, which is
# not the same as learning that nothing happened.
APPLIED = "applied"
REJECTED = "rejected"
UNKNOWN = "unknown"
SUPERSEDED = "superseded"

# Conflict domain: two actions in the same domain mutate the same node-side setting, so their
# order matters and an older one must never be applied over a newer one. Actions in different
# domains commute.
# How long a backfill order stays valid. A: chosen to outlast the node's own upload cadence by a
# margin, because an order that expires inside the cadence it waits on cannot be served at all.
UPLOAD_ORDER_TTL_S = 6 * 3600

DOMAIN_PROFILE = "profile"
DOMAIN_MEASUREMENT = "measurement"
DOMAIN_TRANSFER = "transfer"
DOMAIN_STATUS = "status"


@dataclass
class ActionRecord:
    """One action, its parameters, and the evidence it produced."""

    identity: str                    # stable logical identity, unchanged across retries
    kind: str
    node_id: str
    parameters: dict
    conflict_domain: str
    issued_at: int
    deadline: int | None = None
    applied_at: int | None = None
    observed_at: int | None = None
    declared_at: int | None = None
    declared_without_evidence: bool = False
    overwritten_after_settle: bool = False
    currently_active: bool | None = None
    outcome: str = UNKNOWN
    opportunities_spent: int = 0
    attempts: int = 0
    detail: str = ""

    @property
    def evidence_age_s(self) -> int | None:
        """How old the evidence is. None while there is no evidence to age."""
        if self.observed_at is None:
            return None
        return max(0, self.issued_at - self.observed_at)

    def as_dict(self) -> dict:
        return {"identity": self.identity, "kind": self.kind, "node_id": self.node_id,
                "parameters": self.parameters, "conflict_domain": self.conflict_domain,
                "issued_at": self.issued_at, "deadline": self.deadline,
                "applied_at": self.applied_at, "observed_at": self.observed_at,
                "declared_at": self.declared_at,
                "declared_without_evidence": self.declared_without_evidence,
                "overwritten_after_settle": self.overwritten_after_settle,
                "currently_active": self.currently_active, "outcome": self.outcome,
                "opportunities_spent": self.opportunities_spent, "attempts": self.attempts}


@dataclass
class StatusResult:
    """The answer to `read_status`, plus how the answer was obtained."""

    node_id: str
    read_at: int
    source: str                      # "passive" (piggybacked telemetry) | "queried" | "none"
    max_age_s: int
    payload: dict | None = None
    age_s: int | None = None
    record: ActionRecord | None = None

    @property
    def fresh(self) -> bool:
        return self.payload is not None and self.age_s is not None and self.age_s <= self.max_age_s


class AgentInterface:
    """The center's four actions, each leaving an auditable record.

    The interface does not touch the node directly. Anything that needs the node to do something
    becomes a downlink message on the control plane, and anything learned comes back either
    piggybacked on telemetry or not at all.
    """

    def __init__(self, plane, runtime_by_node: dict, journal=None):
        self.plane = plane
        self.runtime = runtime_by_node
        self.records: dict[str, ActionRecord] = {}
        self.pending: dict[str, ActionRecord] = {}       # identity -> record awaiting delivery
        self.passive_status: dict[str, tuple[int, dict]] = {}   # node -> (reported_at, payload)
        self._seq = 0
        # Durable storage is a capability of the center, not of the far side. An arm that has it can
        # say what it had in flight when the process died; one that does not can only re-issue and
        # hope the far side recognises the repeats. `journal` is the only difference between the two
        # on a restart, which is what makes the restart comparison about the runtime.
        self.journal = journal
        self.recovered_unresolved: list[str] = []

    # ------------------------------------------------------------------ helpers
    def _next_identity(self, node_id: str, kind: str) -> str:
        self._seq += 1
        return f"{node_id}:{kind}:{self._seq}"

    def note_telemetry(self, node_id: str, at_s: int, payload: dict) -> None:
        """Record the status a node piggybacked on its own uplink.

        This is what makes a read free when the evidence is young enough. It costs nothing because
        the node was transmitting anyway; the alternative is to ask, which costs an opportunity.
        """
        self.passive_status[node_id] = (at_s, dict(payload))

    def _enqueue(self, record: ActionRecord, payload_bytes: int, ttl_s: int,
                 contract_logical: str | None = None,
                 contract_version: int | None = None) -> ActionRecord:
        message = DownlinkMessage(identity=record.identity, kind=record.kind,
                                  payload_bytes=payload_bytes, enqueued_at=record.issued_at,
                                  expires_at=(record.deadline if record.deadline is not None
                                              else record.issued_at + ttl_s))
        # The path is the sender's choice and it is carried on the message. A policy that knows
        # about a second path can name it; one that does not keeps using the primary, which is the
        # comparison the independent-management-path control exists to make.
        accepted = self.plane.center_send(record.node_id, message, record.issued_at // 3600,
                                          path=int(record.parameters.get("path", 0)))
        if not accepted:
            # The center could not even hand it to the gateway. The action has not been dispatched,
            # so it is not `unknown` in the sense of "may have taken effect" -- nothing left the
            # center. It stays unresolved and will be retried by the caller.
            record.detail = "backhaul refused; not dispatched"
            return record
        record.attempts += 1
        self.pending[record.identity] = record
        self.records[record.identity] = record
        if self.journal is not None:
            # Registered before it is sent, and sent means dispatched. The order matters: an
            # operation written after its dispatch is one a crash can lose while its effect stands.
            # The two contract fields the far side fences on are part of the record; without them
            # a replay cannot tell a restarted sender which versions it has already used, and the
            # counter it rebuilds starts over against a far side that still remembers.
            self.journal.record("register", incarnation="c0", operation_id=record.identity,
                                entity_id=record.node_id, capability=record.kind,
                                arguments_hash=str(sorted(record.parameters.items())),
                                logical_intent=record.identity, epoch=record.attempts,
                                side_effect=True, contract_logical=contract_logical,
                                contract_version=contract_version, at=record.issued_at)
            self.journal.record("dispatched", operation_id=record.identity,
                                attempts=record.attempts, at=record.issued_at)
        return record

    def note_applied(self, identity: str, applied_at: int) -> None:
        """The node applied the command. This is the node's truth, not the center's knowledge.

        Kept separate from `note_observed` because the whole point of the observation dimension is
        that a thing can be true at the node while the center does not yet know it. Writing both
        timestamps in one call was what made the knowledge delay structurally zero.
        """
        record = self.records.get(identity)
        if record is None:
            return
        record.opportunities_spent += 1
        if record.applied_at is None:
            record.applied_at = applied_at

    def note_observed(self, identity: str, observed_at: int,
                      reply: dict | None = None) -> None:
        """The center learned the effect was in force, by whatever path reached it."""
        record = self.pending.pop(identity, None)
        if record is None:
            record = self.records.get(identity)
            if record is None:
                return
        record.observed_at = observed_at
        record.outcome = APPLIED
        if reply:
            record.detail = reply.get("detail", record.detail)
        if self.journal is not None:
            self.journal.record("settle", operation_id=identity, outcome=APPLIED,
                                detail=record.detail, at=observed_at)

    def note_rejected(self, identity: str, at_s: int, reason: str) -> None:
        """The remote refused the operation and told the center so.

        A rejection the center never hears is indistinguishable from a loss, and the two call for
        opposite responses: one means stop re-asserting, the other means assert again.
        """
        record = self.pending.pop(identity, None) or self.records.get(identity)
        if record is None:
            return
        record.observed_at = at_s
        record.outcome = REJECTED
        record.detail = reason

    def note_overwritten(self, identity: str, at_s: int, by_issued_at: int) -> None:
        """A record the center had settled was replaced by an older intent.

        This is the second half of the 7.6 definition of a false success: the value was in force
        when the center settled it, and was then overwritten by a write that had been superseded.
        The operators were told something true that stopped being true for a reason they never saw.
        """
        record = self.records.get(identity)
        if record is None:
            return
        record.overwritten_after_settle = True
        record.detail = f"overwritten at {at_s} by a write issued at {by_issued_at}"

    def note_delivered(self, identity: str, at_s: int, applied_at: int | None,
                       reply: dict | None = None) -> None:
        """Apply and observe at the same instant, for callers with no separate knowledge path."""
        self.note_applied(identity, applied_at if applied_at is not None else at_s)
        self.note_observed(identity, at_s, reply=reply)

    def declare(self, identity: str, at_s: int) -> None:
        """The center told its operators the effect was in force, without evidence of it.

        This is the move 7.7.1 forbids. It exists as a call so that the false-success metric can
        count what it costs rather than argue about it: the count is zero for a runtime that
        settles after evidence and positive for one that settles at dispatch.
        """
        record = self.records.get(identity)
        if record is None:
            return
        record.declared_at = at_s
        record.declared_without_evidence = record.observed_at is None

    def knowledge_latency(self, identity: str) -> int | None:
        """How long the center took to learn an effect the node had already applied."""
        record = self.records.get(identity)
        if record is None or record.applied_at is None or record.observed_at is None:
            return None
        return record.observed_at - record.applied_at

    def expire(self, now_s: int) -> list[ActionRecord]:
        """Actions whose deadline passed without evidence. Their outcome stays unknown.

        A timeout is not a failure and not a success. Recording it as either would be the exact
        mistake this whole layer exists to avoid, so the record keeps `outcome = unknown` and
        `applied_at = None`, and the caller is free to reconcile.
        """
        expired = []
        for identity, record in list(self.pending.items()):
            if record.deadline is not None and now_s > record.deadline:
                self.pending.pop(identity, None)
                expired.append(record)
        return expired

    # ------------------------------------------------------------------ actions
    def read_status(self, node_id: str, max_age_s: int, now_s: int) -> StatusResult:
        """Read a node's status, preferring what it already told us.

        A recent telemetry report answers the read for free. Only when the newest report is older
        than `max_age_s` is a query sent, and a query consumes an opportunity.
        """
        cached = self.passive_status.get(node_id)
        if cached is not None:
            reported_at, payload = cached
            age = now_s - reported_at
            if age <= max_age_s:
                return StatusResult(node_id=node_id, read_at=now_s, source="passive",
                                    max_age_s=max_age_s, payload=dict(payload), age_s=age)

        identity = self._next_identity(node_id, "read_status")
        record = ActionRecord(identity=identity, kind="read_status", node_id=node_id,
                              parameters={"max_age_s": max_age_s}, conflict_domain=DOMAIN_STATUS,
                              issued_at=now_s, deadline=now_s + max_age_s)
        self._enqueue(record, payload_bytes=8, ttl_s=max_age_s)
        age = None if cached is None else now_s - cached[0]
        return StatusResult(node_id=node_id, read_at=now_s, source="queried" if record.attempts
                            else "none", max_age_s=max_age_s,
                            payload=None if cached is None else dict(cached[1]), age_s=age,
                            record=record)

    def set_monitoring_profile(self, node_id: str, profile: str, generation: int,
                               expires_at: int | None, now_s: int,
                               path: int = 0, logical: str | None = None,
                               version: int | None = None) -> ActionRecord:
        """Assign a monitoring profile. A versioned assignment in the profile conflict domain.

        Re-sending the same value costs an opportunity and is not harmful: applying a profile twice
        leaves the same schedule in force. That is why it is scored as cost and not as a fault.

        `logical` and `version` are the fields the sender chose to put on the wire for the far
        side's receipt and fencing. They are passed in rather than minted here because they are the
        sender's contract choices, and they are written to the journal so that a restarted sender
        can reconstruct the values it has already used.
        """
        identity = self._next_identity(node_id, f"profile:{profile}:g{generation}")
        record = ActionRecord(identity=identity, kind="set_monitoring_profile", node_id=node_id,
                              parameters={"profile": profile, "generation": generation,
                                          "path": path},
                              conflict_domain=DOMAIN_PROFILE, issued_at=now_s,
                              deadline=expires_at)
        return self._enqueue(record, payload_bytes=16, ttl_s=6 * 3600,
                             contract_logical=logical, contract_version=version)

    def replay_contract_state(self) -> dict[str, dict]:
        """What the journal says this coordinator last put on the wire, per node.

        Empty without a journal: a center that kept no durable record cannot answer this, and
        returning an empty map is the honest answer rather than a guess.
        """
        if self.journal is None:
            return {}
        from operations import replay_contract_state
        return replay_contract_state(self.journal)

    def request_measurement(self, node_id: str, request_id: str, deadline: int,
                            now_s: int) -> ActionRecord:
        """Ask for a fresh measurement, carrying the id the answer must quote back."""
        identity = self._next_identity(node_id, f"measure:{request_id}")
        record = ActionRecord(identity=identity, kind="request_measurement", node_id=node_id,
                              parameters={"request_id": request_id, "window_start": now_s},
                              conflict_domain=DOMAIN_MEASUREMENT, issued_at=now_s,
                              deadline=deadline)
        return self._enqueue(record, payload_bytes=12, ttl_s=max(1, deadline - now_s))

    def upload_records(self, node_id: str, start_s: int, end_s: int, cursor: int,
                       budget: int, now_s: int,
                       deadline_s: int | None = None) -> ActionRecord:
        """Ask for records in a range to be transferred, resuming from a send cursor.

        The send cursor and the acknowledged cursor are different numbers and both are carried: a
        request that asked from the acknowledged cursor would re-send everything already delivered,
        and one that asked from the send cursor would skip whatever was lost in flight.

        The deadline defaults to the same order of magnitude as a profile command rather than to one
        upload interval. A backfill order that expires in exactly the cadence it has to wait for is
        not a comparison of backfill policies, it is a guaranteed non-delivery, and the opportunity
        rate here is low enough that a one-hour window would almost never be served.
        """
        identity = self._next_identity(node_id, f"upload:{start_s}-{end_s}:c{cursor}")
        deadline = deadline_s if deadline_s is not None else now_s + UPLOAD_ORDER_TTL_S
        record = ActionRecord(identity=identity, kind="upload_records", node_id=node_id,
                              parameters={"range": [start_s, end_s], "cursor": cursor,
                                          "budget": budget},
                              conflict_domain=DOMAIN_TRANSFER, issued_at=now_s,
                              deadline=deadline)
        return self._enqueue(record, payload_bytes=16, ttl_s=max(1, deadline - now_s))

    # ------------------------------------------------------------------ reading
    def forget_volatile_state(self) -> list[str]:
        """What a coordinator loses when the process dies and keeps when it has a journal.

        Without durable storage the center cannot say which of its outstanding operations the far
        side has already carried out, so it re-issues them; the far side sees repeats and, if it has
        receipts, refuses them. With storage the unresolved set is reconstructed and the run can
        require it to be reconciled before anything new is dispatched. The returned list is what the
        volatile center believed was in flight, kept so the recovery arm can be told what it lost.
        """
        lost = list(self.pending)
        self.pending = {}
        self.recovered_unresolved = []
        if self.journal is not None:
            from operations import recover
            registry = recover(self.journal)
            self.recovered_unresolved = [op.operation_id for op in registry.ops.values()
                                         if op.unresolved]
        return lost

    def audit_trail(self) -> list[dict]:
        """Every action this interface took, in issue order, as plain records."""
        return [r.as_dict() for r in sorted(self.records.values(), key=lambda x: x.issued_at)]

    def unresolved(self) -> list[ActionRecord]:
        return list(self.pending.values())
