#!/usr/bin/env python3
"""
operations.py — operation runtime semantics for remote actuation over disrupted links.

This replaces an earlier single 11-state enum. That enum conflated four different things —
the runtime's own lifecycle, the remote physical effect, the evidence the agent holds, and the
reachability of the entity — and it contradicted itself outright: `outcome_unknown` appeared in
TERMINAL yet was also returned by `unresolved()`, so "open" and "unresolved" disagreed about the
same state.

The split below follows a small set of runtime design principles that a well-built execution
runtime tends to converge on, and which are worth stating because they decide the whole shape of
the state model:

  * the runtime owns identity and lifecycle; the executor owns the execution resource;
  * the lifecycle vocabulary is small, and everything kind-specific goes into `detail` rather
    than into a new state;
  * `wait()` returning on timeout means the CALLER stopped waiting. It does not cancel the work
    and does not change the work's true lifecycle;
  * settlement is first-wins: one terminal record, even against a late outcome;
  * readers get a fresh projected snapshot, never live mutable internal state.

What does NOT transfer, and is this paper's actual subject: in a harness the producer is a local
process whose `done` eventually resolves. Here the effect lands on a far side that may never be
reachable again, so "did it happen" can stay genuinely undecided forever. A process-local
registry has no such state.

Three dimensions, deliberately orthogonal:

    lifecycle    registered -> running -> stopping -> settled     (runtime-owned)
    outcome      unknown | applied | rejected | failed | superseded   (remote effect)
    observation  fresh | unknown | stale | unavailable            (agent's evidence)

And the former states now map cleanly:
    timeout           -> a WAIT EVENT, never a state
    outcome_unknown   -> outcome=unknown
    stale_result      -> observation=stale
    unavailable       -> observation=unavailable
    recovering        -> a recovery procedure, not a state
    compensating      -> a separate operation

Deps: stdlib only.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from enum import Enum


class Violation(RuntimeError):
    """An illegal runtime transition. Raised loudly rather than absorbed.

    The harness this design follows enforces its stage order the same way: a repeated
    pre-execute, an execute that did not follow a pre-execute, a post-execute that followed
    neither — each one fails immediately. A runtime that silently accepts an out-of-order
    transition cannot be used to argue anything about correctness, because the argument's
    premises are only as strong as the enforcement.
    """


class Lifecycle(str, Enum):
    """What the RUNTIME owns. Nothing about the far side belongs here."""
    REGISTERED = "registered"   # durably recorded, not yet sent
    RUNNING = "running"         # dispatched, not settled
    STOPPING = "stopping"       # cancellation requested, producer still holds resources
    SETTLED = "settled"         # first-wins terminal record committed


class Outcome(str, Enum):
    """What happened on the FAR SIDE. `unknown` is a legitimate, often permanent answer."""
    UNKNOWN = "unknown"
    APPLIED = "applied"
    REJECTED = "rejected"       # the entity refused it (stale epoch, failed precondition)
    FAILED = "failed"
    SUPERSEDED = "superseded"   # a later operation's effect is the one in force


class Observation(str, Enum):
    """What the AGENT currently holds as evidence. Says nothing about the far side."""
    FRESH = "fresh"
    UNKNOWN = "unknown"
    STALE = "stale"
    UNAVAILABLE = "unavailable"


TERMINAL_OUTCOMES = {Outcome.APPLIED, Outcome.REJECTED, Outcome.FAILED, Outcome.SUPERSEDED}

# The effect may have landed even though we cannot tell. Anything else is safe to forget.
MAY_HAVE_EFFECT = {Outcome.UNKNOWN, Outcome.APPLIED}


@dataclass
class Operation:
    """One logical remote action. `logical_intent` and `epoch` are stable across retries."""

    operation_id: str
    entity_id: str
    capability: str
    arguments_hash: str
    logical_intent: str
    epoch: int
    side_effect: bool
    created_at: int
    first_dispatch_at: int | None = None
    attempts: int = 0

    lifecycle: Lifecycle = Lifecycle.REGISTERED
    outcome: Outcome = Outcome.UNKNOWN
    observation: Observation = Observation.UNKNOWN
    settled_at: int | None = None

    # kind-specific facts. Never a new lifecycle state, never a new outcome.
    detail: str = ""
    # evidence that arrived after settlement; recorded, and deliberately unable to rewrite truth
    late_evidence: list = field(default_factory=list)

    # --- non-lifecycle bookkeeping. These are quantities, not states: a retry budget is a
    # number, a buffer timestamp is a time. Promoting any of them into the lifecycle is exactly
    # the conflation this module replaces.
    budget: int = 3
    budget_exhausted_at: int | None = None
    buffered_at: int | None = None
    replayed_at: int | None = None
    stale_age: int = 0

    @property
    def open(self) -> bool:
        """Not yet settled, by lifecycle alone."""
        return self.lifecycle is not Lifecycle.SETTLED

    @property
    def unresolved(self) -> bool:
        """Settled or not, we still do not know whether the effect landed.

        This is the state a process-local registry cannot have, and it is what the paper is
        about. It is NOT the same question as `open`: an operation can settle as `outcome=
        unknown` and stay here forever.
        """
        return self.outcome is Outcome.UNKNOWN

    def snapshot(self) -> dict:
        """A fresh projection. Callers never see the mutable record."""
        return asdict(self) | {"lifecycle": self.lifecycle.value,
                               "outcome": self.outcome.value,
                               "observation": self.observation.value}


@dataclass
class WaitEvent:
    """The result of `wait()`. A wait event never mutates the operation."""
    operation_id: str
    kind: str          # "settled" | "timeout"
    at: int


class JournalError(RuntimeError):
    """A durable log that cannot be replayed faithfully.

    Raised rather than skipped. A replay that guesses is worse than one that refuses, because
    every judgement the recovered runtime makes afterwards rests on it: a wrong state produced
    silently is indistinguishable from a correct one until something unrelated fails later, and
    by then the log has usually been rotated away.
    """


# Schema of the durable log, per entry kind. Each kind carries its own version because the kinds
# evolve independently: changing how operations are recorded gives no reason to bump the version
# of how decisions are recorded, and one shared version would force the two to move together.
# The field set is declared exactly, in both directions, so that a field added on the write side
# and unknown on the read side fails at startup instead of producing a plausible wrong operation.
JOURNAL_SCHEMA: dict[str, tuple[int, frozenset[str]]] = {
    "register": (1, frozenset({"incarnation", "operation_id", "entity_id", "capability",
                               "arguments_hash", "logical_intent", "epoch", "side_effect",
                               "at"})),
    "dispatched": (1, frozenset({"operation_id", "attempts", "at"})),
    "observe": (1, frozenset({"operation_id", "observation"})),
    "settle": (1, frozenset({"operation_id", "outcome", "detail", "at"})),
    # Decision-context entries share the log with registry entries but not their schema family.
    "decision": (1, frozenset({"key", "value"})),
}

# The two families, named so that a change to one can be reasoned about without the other.
REGISTRY_KINDS = ("register", "dispatched", "observe", "settle")
DECISION_KINDS = ("decision",)


class Journal:
    """Append-only record of registry events.

    The protocol's first rule is that an operation is registered BEFORE it is sent. That rule
    only buys anything if the registration outlives the process that made it: without a journal,
    a coordinator that restarts has no record of what it had in flight, so it re-issues those
    actions under fresh identities. The far side sees new operations, its epoch fencing has
    nothing to fence, and the retries land as second effects.

    Appending is the whole interface. Replay is deliberately separate, because a journal that
    cannot be replayed is just a log, and a log nobody reads is how a "durable" runtime turns out
    not to be one.

    Every entry is stamped with the version of its own kind and checked against the declared
    field set on the way in. Replay validates the whole log first, so a log this build cannot
    read faithfully is rejected before it can produce a state.
    """

    def __init__(self) -> None:
        self.entries: list[dict] = []

    def record(self, kind: str, **fields) -> None:
        spec = JOURNAL_SCHEMA.get(kind)
        if spec is None:
            raise JournalError(f"unknown journal entry kind {kind!r}")
        version, allowed = spec
        self._check_fields(kind, set(fields), allowed, where="append")
        self.entries.append({"kind": kind, "v": version, **fields})

    @staticmethod
    def _check_fields(kind: str, present: set[str], allowed: frozenset[str], where: str) -> None:
        extra = present - allowed
        missing = allowed - present
        if extra or missing:
            raise JournalError(
                f"{kind} entry has the wrong field set on {where}: "
                f"extra={sorted(extra)} missing={sorted(missing)}")

    def validate(self) -> None:
        """Refuse the whole log if any entry cannot be read faithfully.

        Called before replay. The failure is loud on purpose: the alternative is a recovered
        runtime that is wrong in a way nothing downstream can detect.
        """
        for i, entry in enumerate(self.entries):
            kind = entry.get("kind")
            spec = JOURNAL_SCHEMA.get(kind)
            if spec is None:
                raise JournalError(f"entry {i}: unknown journal entry kind {kind!r}")
            version, allowed = spec
            if entry.get("v") != version:
                raise JournalError(
                    f"entry {i} ({kind}): unsupported version {entry.get('v')!r}; "
                    f"this build replays version {version}")
            self._check_fields(kind, set(entry) - {"kind", "v"}, allowed, where=f"entry {i}")

    def __len__(self) -> int:
        return len(self.entries)


class DurableDecisionStore:
    """The decision context a recovered coordinator needs in order to replay an action.

    Identity continuity is not enough on its own. An ad-hoc action's identity is derived from a
    choice made at the moment of acting -- which alarm to acknowledge, which site to re-measure --
    and the payload carries that choice. Recomputing the identity without the choice produces a
    name for an action the coordinator can no longer describe, so what comes back is either a
    different action under a new name or no action at all.

    This store keeps (key -> decision) in the same append-only journal the operations use, so a
    recovered coordinator rebuilds the payload and not only the name. It is a declared component
    rather than a dictionary in the calling script on purpose: a side map that happens to survive a
    restart models nothing, and a runtime that depended on one would not be reproducible from its
    durable state.

    Keys are the address of the decision -- here `<entity>:<action>:<slot>` -- and values are the
    choice itself.
    """

    KIND = "decision"

    def __init__(self, journal: Journal) -> None:
        self.journal = journal
        self._decisions: dict[str, object] = {}

    def recall(self, key: str):
        """The decision this coordinator made for `key`, or None if it never made one."""
        return self._decisions.get(key)

    def commit(self, key: str, value) -> None:
        """Record a decision. Writing is what makes it survive the process."""
        if key in self._decisions:
            return
        self._decisions[key] = value
        self.journal.record(self.KIND, key=key, value=value)

    def __len__(self) -> int:
        return len(self._decisions)

    @classmethod
    def replay(cls, journal: Journal) -> "DurableDecisionStore":
        """Rebuild the store from the journal, the way a restarted process rebuilds anything."""
        journal.validate()
        store = cls(journal)
        for entry in journal.entries:
            if entry.get("kind") == cls.KIND:
                store._decisions[entry["key"]] = entry["value"]
        return store


class RemoteSink:
    """The far side. It owns a durable epoch and, optionally, per-operation receipts.

    Its acceptance rule is the whole reason a lost ACK is not automatically a duplicate:

        epoch <  last_accepted_epoch  -> reject as stale
        epoch == last_accepted_epoch  -> already accepted; return the recorded outcome
        epoch >  last_accepted_epoch  -> apply effect AND advance epoch atomically

    The atomicity matters. If the effect is applied and the epoch is not advanced in the same
    step, a crash in between reopens the duplicate window the epoch was introduced to close.
    """

    def __init__(self, entity_id: str, idempotent_by_key: bool = True,
                 durable_epoch: bool = True, dedup_by_operation_id: bool = True):
        self.entity_id = entity_id
        self.idempotent_by_key = idempotent_by_key
        self.durable_epoch = durable_epoch
        # a real entity may keep no per-operation receipt at all: it remembers only the epoch it
        # last accepted. Without both, a retry is simply a second effect.
        self.dedup_by_operation_id = dedup_by_operation_id
        self.last_accepted_epoch = 0
        self.receipts: dict[str, Outcome] = {}
        self.applied_count = 0

    def accept(self, op: Operation) -> tuple[Outcome, bool]:
        """Returns (outcome, did_apply). `did_apply` is the ground truth a scorer counts."""
        # 1. operation-level receipt, if the entity keeps one
        if self.dedup_by_operation_id:
            prev = self.receipts.get(op.operation_id)
            if prev is not None:
                # it was accepted before. If a later epoch is now in force, report that rather
                # than "applied", so the caller does not conclude its effect is the current one.
                if self.durable_epoch and self.last_accepted_epoch > op.epoch:
                    return Outcome.SUPERSEDED, False
                return prev, False

        # 2. epoch fencing
        if self.durable_epoch:
            if op.epoch < self.last_accepted_epoch:
                return Outcome.REJECTED, False
            if op.epoch == self.last_accepted_epoch and self.last_accepted_epoch > 0:
                return Outcome.SUPERSEDED, False

        # 3. apply, and advance the epoch in the same acceptance boundary
        self.applied_count += 1
        if self.durable_epoch:
            self.last_accepted_epoch = op.epoch
        if self.dedup_by_operation_id:
            self.receipts[op.operation_id] = Outcome.APPLIED
        return Outcome.APPLIED, True


class OperationRegistry:
    """The runtime. Owns identity and lifecycle; the entity owns the execution resource."""

    def __init__(self, journal: Journal | None = None, incarnation: str = "") -> None:
        self.ops: dict[str, Operation] = {}
        self._n = 0
        self._epoch = 0
        self.counts: dict[str, int] = {}
        self.journal = journal
        # A restarted coordinator must not reuse operation ids. Real systems issue UUIDs or
        # prefix them with a boot id; a bare counter that restarts at zero would otherwise
        # produce ids the far side has already seen, and its receipt table would then silently
        # suppress a write that was meant to be new.
        self.incarnation = incarnation

    # ------------------------------------------------------------------ identity
    def register(self, entity_id: str, capability: str, arguments: dict,
                 logical_intent: str, tick: int, side_effect: bool,
                 epoch: int | None = None) -> Operation:
        """Durably record the operation BEFORE anything is sent.

        Sending first and recording second leaves a window where the coordinator can crash
        having dispatched an effect it has no record of: a ghost operation that may run, may
        have run, and can never be reconciled. There is no such window here.
        """
        self._n += 1
        self._epoch = self._epoch + 1 if epoch is None else max(epoch, self._epoch + 1)
        op = Operation(
            operation_id=f"{self.incarnation}op{self._n:05d}",
            entity_id=entity_id,
            capability=capability,
            arguments_hash=hashlib.sha256(
                json.dumps(arguments, sort_keys=True).encode()).hexdigest()[:12],
            logical_intent=logical_intent,
            epoch=self._epoch,
            side_effect=side_effect,
            created_at=tick,
        )
        self.ops[op.operation_id] = op
        self.bump("registered")
        if self.journal is not None:
            self.journal.record("register", incarnation=self.incarnation,
                                operation_id=op.operation_id,
                                entity_id=entity_id, capability=capability,
                                arguments_hash=op.arguments_hash,
                                logical_intent=logical_intent, epoch=op.epoch,
                                side_effect=side_effect, at=tick)
        return op

    def bump(self, key: str, n: int = 1) -> None:
        self.counts[key] = self.counts.get(key, 0) + n

    # ------------------------------------------------------------------- invariants
    def _known(self, op: Operation) -> Operation:
        if self.ops.get(op.operation_id) is not op:
            raise Violation(f"{op.operation_id} is not registered in this registry")
        return op

    # ------------------------------------------------------------------- lifecycle
    def dispatched(self, op: Operation, tick: int) -> None:
        """A retry re-sends the SAME operation_id and epoch; it is not a new registration."""
        self._known(op)
        if op.lifecycle is Lifecycle.STOPPING:
            raise Violation(f"{op.operation_id} is stopping; a stop and a dispatch cannot race")
        if op.lifecycle is Lifecycle.SETTLED and not op.unresolved:
            # Its effect is KNOWN. Re-sending it would be a second logical write, not a retry.
            raise Violation(
                f"{op.operation_id} settled as {op.outcome.value} and cannot be dispatched again")
        # Re-dispatching an operation whose outcome is still UNKNOWN is the whole point: the
        # runtime keeps resending the SAME operation_id and epoch, which the sink's fencing
        # turns into at-most-once acceptance. Settlement is not a reason to give up.
        if op.side_effect and op.first_dispatch_at is not None and op.epoch != op.epoch:
            raise Violation("retry changed the epoch")   # unreachable, kept as documentation
        if op.first_dispatch_at is None:
            op.first_dispatch_at = tick
        op.attempts += 1
        op.lifecycle = Lifecycle.RUNNING
        self.bump("dispatched")
        if self.journal is not None:
            self.journal.record("dispatched", operation_id=op.operation_id,
                                attempts=op.attempts, at=tick)

    def assert_retry_reuses_identity(self, original: Operation, retry: Operation) -> None:
        """A retry must be the same logical write, not a new one.

        This is the property whose absence produces duplicate effects, so the runtime checks it
        rather than trusting the caller. Two operations with the same logical_intent but
        different epochs are two different writes.
        """
        if original.logical_intent != retry.logical_intent:
            raise Violation("a retry must carry the original logical_intent")
        if original.epoch != retry.epoch:
            raise Violation("a retry must carry the original epoch")

    def request_stop(self, op: Operation) -> None:
        self._known(op)
        if op.open:
            op.lifecycle = Lifecycle.STOPPING

    def settle(self, op: Operation, outcome: Outcome, tick: int, detail: str = "") -> bool:
        """First-wins. A late outcome cannot rewrite a committed terminal record."""
        self._known(op)
        if op.lifecycle is Lifecycle.SETTLED:
            self.bump("late_outcome_ignored")
            return False
        if op.lifecycle is Lifecycle.REGISTERED:
            # settling something that was never sent would record an effect that cannot exist
            raise Violation(f"{op.operation_id} settled before any dispatch")
        op.lifecycle = Lifecycle.SETTLED
        op.outcome = outcome
        op.settled_at = tick
        if detail:
            op.detail = detail
        self.bump("settled")
        if self.journal is not None:
            self.journal.record("settle", operation_id=op.operation_id,
                                outcome=outcome.value, detail=detail, at=tick)
        return True

    # ------------------------------------------------------------------ observation
    def observe(self, op: Operation, observation: Observation) -> None:
        op.observation = observation
        if self.journal is not None:
            self.journal.record("observe", operation_id=op.operation_id,
                                observation=observation.value)

    def wait(self, op: Operation, deadline: int, tick: int) -> WaitEvent:
        """Wait for settlement OR the deadline. A timeout is a WAIT EVENT, not a state.

        The caller stopped waiting. The operation is untouched: it stays RUNNING, its outcome
        stays UNKNOWN, and it remains in the registry to be reconciled later. This is the single
        most important semantic in the module — collapsing it into `running -> timeout` is what
        makes an unresolved remote effect look like a failure.
        """
        if op.lifecycle is Lifecycle.SETTLED:
            return WaitEvent(op.operation_id, "settled", tick)
        if tick >= deadline:
            op.observation = Observation.UNKNOWN
            self.bump("wait_timeout")
            return WaitEvent(op.operation_id, "timeout", tick)
        return WaitEvent(op.operation_id, "waiting", tick)

    # ------------------------------------------------------------- reconciliation
    def unresolved_for(self, entity_id: str) -> list[Operation]:
        """Operations whose effect is undecided, for one entity, oldest first."""
        return sorted((o for o in self.ops.values()
                       if o.entity_id == entity_id and o.unresolved
                       and o.lifecycle is not Lifecycle.REGISTERED),
                      key=lambda o: o.created_at)

    def reconcile(self, op: Operation, sink: RemoteSink, tick: int) -> Outcome:
        """Resolve one operation against the entity, scoped to THIS operation's epoch.

        The scoping is not a detail. Asking "has this effect ever been applied here?" is
        answered YES by an earlier operation, so a policy that believes it stops retrying a
        write that never happened. The question must name the operation or its epoch.
        """
        self._known(op)
        if op.first_dispatch_at is None:
            raise Violation(f"{op.operation_id} cannot be reconciled before it was dispatched")
        receipt = sink.receipts.get(op.operation_id)
        if receipt is not None:
            op.observation = Observation.FRESH
            self.settle(op, receipt, tick, "resolved from operation receipt")
            return receipt
        if sink.durable_epoch:
            if sink.last_accepted_epoch > op.epoch:
                op.observation = Observation.FRESH
                self.settle(op, Outcome.SUPERSEDED, tick, "a later epoch is in force")
                return Outcome.SUPERSEDED
            if sink.last_accepted_epoch < op.epoch:
                # the write never became current; retrying the same epoch is now safe
                op.observation = Observation.FRESH
                return Outcome.UNKNOWN
        op.observation = Observation.UNAVAILABLE
        return Outcome.UNKNOWN

    def late_evidence(self, op: Operation, what: str, tick: int) -> None:
        """Evidence arriving after settlement is recorded and cannot rewrite the record."""
        op.late_evidence.append({"at": tick, "what": what})
        self.bump("late_evidence_recorded")

    # ---------------------------------------------------------------- failure cases
    # The F01..F11 accounting of the earlier model, re-expressed in the three dimensions.

    def f01_node_lost_after_dispatch(self, op, tick):
        self.observe(op, Observation.UNAVAILABLE)
        self.bump("F01_node_lost_after_dispatch")

    def f02_ack_lost_after_execution(self, op, tick):
        # the sink DID apply it; only our knowledge is missing
        self.observe(op, Observation.UNKNOWN)
        self.settle(op, Outcome.UNKNOWN, tick, "executed, ACK lost")
        self.bump("F02_ack_lost_after_execution")

    def f03_duplicate_side_effect(self, op, tick):
        self.bump("F03_duplicate_side_effect")

    def f04_pending_forgotten(self, op, tick):
        self.observe(op, Observation.UNAVAILABLE)
        self.bump("F04_pending_forgotten")

    def f05_stale_used_as_current(self, op, tick, age: int = 0):
        op.stale_age = age
        self.observe(op, Observation.STALE)
        self.bump("F05_stale_used_as_current")

    def f06_wrong_replay_order(self, op, tick):
        op.replayed_at = tick
        self.bump("F06_wrong_replay_order")

    def f07_retry_budget_exhausted(self, op, tick):
        op.budget_exhausted_at = tick
        self.settle(op, Outcome.UNKNOWN, tick, "retry budget exhausted, effect still undecided")
        self.bump("F07_retry_budget_exhausted")

    def f08_starvation_hol(self, op, tick):
        self.bump("F08_starvation_head_of_line")

    def f09_gateway_flapping(self, tick):
        self.bump("F09_gateway_flapping")

    def f10_partition_divergence(self, tick):
        self.bump("F10_partition_state_divergence")

    def f11_coordinator_restart(self, tick):
        self.bump("F11_coordinator_restart")

    # ----------------------------------------------------------------- inspection
    def by_lifecycle(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for o in self.ops.values():
            out[o.lifecycle.value] = out.get(o.lifecycle.value, 0) + 1
        return out

    def by_outcome(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for o in self.ops.values():
            out[o.outcome.value] = out.get(o.outcome.value, 0) + 1
        return out

    def summary(self) -> dict:
        return {
            "lifecycle": self.by_lifecycle(),
            "outcome": self.by_outcome(),
            "open": sum(1 for o in self.ops.values() if o.open),
            "unresolved": sum(1 for o in self.ops.values() if o.unresolved),
            "failure_counts": dict(sorted(self.counts.items())),
        }


def recover(journal: Journal) -> OperationRegistry:  # noqa: D401
    """Rebuild a registry from its journal, as a restarted coordinator would.

    Replay is order-preserving and idempotent in the same sense the live registry is: the last
    settle for an operation wins nothing, because settle is first-wins on replay too.
    """
    # The journal may hold entries other than registry events -- a decision store writes its own.
    # Take the incarnation from the first entry that actually carries one rather than assuming the
    # registry wrote first.
    journal.validate()
    reg = OperationRegistry(journal, incarnation=next(
        (e["incarnation"] for e in journal.entries if "incarnation" in e), ""))
    for e in journal.entries:
        k = e["kind"]
        if k == "register":
            op = Operation(
                operation_id=e["operation_id"], entity_id=e["entity_id"],
                capability=e["capability"], arguments_hash=e["arguments_hash"],
                logical_intent=e["logical_intent"], epoch=e["epoch"],
                side_effect=e["side_effect"], created_at=e["at"])
            reg.ops[op.operation_id] = op
            n = int(op.operation_id.rsplit("op", 1)[1])
            reg._n = max(reg._n, n)
            reg._epoch = max(reg._epoch, op.epoch)
        elif k == "dispatched":
            op = reg.ops.get(e["operation_id"])
            if op is not None:
                op.attempts = e["attempts"]
                op.lifecycle = Lifecycle.RUNNING
                op.first_dispatch_at = op.first_dispatch_at or e["at"]
        elif k == "observe":
            op = reg.ops.get(e["operation_id"])
            if op is not None:
                op.observation = Observation(e["observation"])
        elif k == "settle":
            op = reg.ops.get(e["operation_id"])
            if op is not None and op.lifecycle is not Lifecycle.SETTLED:
                op.lifecycle = Lifecycle.SETTLED
                op.outcome = Outcome(e["outcome"])
                op.settled_at = e["at"]
                op.detail = e.get("detail", "")
    return reg


def unresolved_intents(reg: OperationRegistry) -> dict[str, Operation]:
    """The operations a restarted coordinator must reconcile, keyed by logical intent.

    This mapping is the thing whose absence causes duplicates after a restart: without it the
    coordinator cannot tell that the action it is about to re-issue is one it already sent.
    """
    out: dict[str, Operation] = {}
    for op in reg.ops.values():
        out.setdefault(op.logical_intent, op)
    return out


# ----------------------------------------------------------------------- properties
def check_properties(verbose: bool = True) -> dict:
    """The three guarantees, each exercised against a deliberately hostile schedule.

    They are stated as what the protocol actually provides, which is weaker than the usual
    marketing claim and is the honest version:

      At-most-once acceptance  an epoch is accepted by a sink at most once, so a retry can never
                               apply twice. It does NOT promise exactly-once: if the first
                               request never arrives, the effect may never happen at all.
      No stale overwrite       once a higher epoch is accepted, any earlier epoch arriving late
                               is rejected, so a delayed replay cannot resurrect an old command.
      Eventual resolution      under eventual reachability AND intact remote metadata, every
                               unresolved operation resolves. If the entity loses its epoch and
                               receipts in a reboot, no agent-side policy can recover the answer.
    """
    out: dict[str, object] = {}

    # -- at-most-once acceptance: an epoch applied once survives unlimited retries
    reg = OperationRegistry()
    sink = RemoteSink("node17")
    op = reg.register("node17", "set_sampling_rate", {"rate": "5min"}, "intent-1", 0, True)
    applies = 0
    for t in range(1, 6):
        reg.dispatched(op, t)
        outcome, did = sink.accept(op)
        applies += int(did)
    out["at_most_once_acceptance"] = {"epoch_applications": applies, "retries": op.attempts}

    # -- the same retry against a sink that only honours a key it does not know
    reg2 = OperationRegistry()
    blind = RemoteSink("node17", idempotent_by_key=False, durable_epoch=False,
                       dedup_by_operation_id=False)
    op2 = reg2.register("node17", "set_sampling_rate", {"rate": "5min"}, "intent-1", 0, True)
    dup = 0
    for t in range(1, 6):
        reg2.dispatched(op2, t, )
        _, did = blind.accept(op2)
        dup += int(did)
    out["client_key_without_remote_support"] = {"epoch_applications": dup}

    # -- no stale overwrite: a late replay of an older epoch is rejected
    reg3 = OperationRegistry()
    sink3 = RemoteSink("node17")
    o_old = reg3.register("node17", "set_rate", {"r": "10min"}, "old", 0, True)
    o_new = reg3.register("node17", "set_rate", {"r": "5min"}, "new", 0, True)
    reg3.dispatched(o_old, 1); sink3.accept(o_old)
    reg3.dispatched(o_new, 2); sink3.accept(o_new)
    late_outcome, late_did = sink3.accept(o_old)      # the old command arrives again, late
    out["no_stale_overwrite"] = {"late_replay_outcome": late_outcome.value,
                                 "applied_again": late_did,
                                 "epoch_in_force": sink3.last_accepted_epoch}

    # -- first-wins settlement against a late outcome
    reg4 = OperationRegistry()
    op4 = reg4.register("node17", "set_rate", {}, "x", 0, True)
    reg4.dispatched(op4, 1)
    first = reg4.settle(op4, Outcome.SUPERSEDED, 5, "reconciled")
    second = reg4.settle(op4, Outcome.APPLIED, 6, "late ACK")
    reg4.late_evidence(op4, "ACK success arrived at t=6", 6)
    out["first_wins_settlement"] = {"first_committed": first, "late_rewrite_committed": second,
                                    "outcome": op4.outcome.value,
                                    "late_evidence_kept": len(op4.late_evidence)}

    # -- a timeout leaves the operation untouched and still reconcilable
    reg5 = OperationRegistry()
    sink5 = RemoteSink("node17")
    op5 = reg5.register("node17", "set_rate", {}, "y", 0, True)
    reg5.dispatched(op5, 1)
    ev = reg5.wait(op5, deadline=10, tick=11)
    _, did_apply = sink5.accept(op5)                  # the far side had applied it all along
    before = (op5.lifecycle.value, op5.outcome.value)
    outcome5 = reg5.reconcile(op5, sink5, tick=40)
    out["wait_timeout_is_not_failure"] = {
        "wait_event": ev.kind, "state_after_timeout": before,
        "still_in_registry": op5.operation_id in reg5.ops,
        "resolved_later": outcome5.value, "had_actually_applied": did_apply,
    }

    # -- the runtime REFUSES illegal transitions instead of absorbing them
    reg6 = OperationRegistry()
    sink6 = RemoteSink("node17")
    op6 = reg6.register("node17", "set_rate", {}, "z", 0, True)
    illegal: dict[str, str] = {}

    def attempt(label, fn):
        try:
            fn()
            illegal[label] = "NOT RAISED"
        except Violation as e:
            illegal[label] = str(e)

    attempt("settle_before_dispatch", lambda: reg6.settle(op6, Outcome.APPLIED, 1))
    attempt("reconcile_before_dispatch", lambda: reg6.reconcile(op6, sink6, 1))
    reg6.dispatched(op6, 2)
    reg6.settle(op6, Outcome.APPLIED, 3)
    attempt("dispatch_after_settle", lambda: reg6.dispatched(op6, 4))
    stranger = Operation("op99999", "node17", "set_rate", "x", "z", 1, True, 0)
    attempt("settle_unregistered", lambda: reg6.settle(stranger, Outcome.APPLIED, 5))
    retry = reg6.register("node17", "set_rate", {}, "different intent", 6, True)
    attempt("retry_with_new_identity", lambda: reg6.assert_retry_reuses_identity(op6, retry))
    out["runtime_invariants"] = illegal

    if verbose:
        print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    return out


if __name__ == "__main__":
    check_properties()
