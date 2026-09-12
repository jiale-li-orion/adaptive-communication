#!/usr/bin/env python3
"""
operations.py — the runtime failure model of README §9, as executable code.

The environment previously modelled 4 states (committed / timeout / outcome_unknown /
unavailable). README §9 requires 11, and §9's failure list requires 11 distinct failure
cases that the benchmark must be able to produce and count.

This module owns:
  * Operation — one tool invocation, with a full lifecycle and a stable intent identity
  * OperationRegistry — pending / forgotten / budget-exhausted / replay-order bookkeeping

Nothing here decides policy; it only records what happened, so an agent cannot hide a
failure and a scorer can count it.

Deps: stdlib only.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# README §9 — the eleven lifecycle states
STATES = (
    "not_started",     # created, never dispatched
    "running",         # dispatched, no outcome yet
    "committed",       # executed AND confirmed
    "failed",          # executed, definitively failed
    "retryable",       # failed but safe to retry (idempotent)
    "timeout",         # we stopped waiting — tells us nothing about the far side
    "outcome_unknown", # epistemically indeterminate: may or may not have taken effect
    "stale_result",    # returned a value from an earlier sampling epoch
    "unavailable",     # capability unreachable; not dispatched
    "recovering",      # node is back; reconciliation in progress
    "compensating",    # a compensating action is being applied
)

TERMINAL = {"committed", "failed", "outcome_unknown", "stale_result"}

# whether the effect MAY have landed on the far side
MAY_HAVE_EFFECT = {"committed", "outcome_unknown", "timeout", "stale_result"}


@dataclass
class Operation:
    """One logical invocation. `intent` is the stable identity across retries."""

    op_id: str
    node: str
    tool: str
    intent: str
    created: int
    side_effect: bool
    state: str = "not_started"
    attempts: int = 0
    first_dispatch: int | None = None
    settled: int | None = None
    # per README §9: a retry budget, and the tick at which the budget ran out
    budget: int = 3
    budget_exhausted_at: int | None = None
    # replay bookkeeping (README §9: wrong replay order after recovery)
    buffered_at: int | None = None
    replayed_at: int | None = None
    stale_age: int = 0
    note: str = ""

    @property
    def open(self) -> bool:
        return self.state not in TERMINAL

    def transition(self, new: str, tick: int, note: str = "") -> None:
        self.state = new
        if new in TERMINAL:
            self.settled = tick
        if note:
            self.note = note


class OperationRegistry:
    """Records every operation and every way it can go wrong (README §9)."""

    def __init__(self) -> None:
        self.ops: dict[str, Operation] = {}
        self._n = 0
        # counters for the failure cases of README §9
        self.counts: dict[str, int] = {}

    # ------------------------------------------------------------------ create
    def new(self, node: str, tool: str, intent: str, tick: int,
            side_effect: bool, budget: int = 3) -> Operation:
        self._n += 1
        op = Operation(f"op{self._n:05d}", node, tool, intent, tick, side_effect, budget=budget)
        self.ops[op.op_id] = op
        self.bump("operations_created")
        return op

    def bump(self, key: str, n: int = 1) -> None:
        self.counts[key] = self.counts.get(key, 0) + n

    # ----------------------------------------------------------- failure cases
    # README §9, one method per failure case, so each is explicit and countable.

    def f01_node_lost_after_dispatch(self, op: Operation, tick: int) -> None:
        """RPC sent, then the node dropped: we learn nothing about the effect."""
        op.transition("outcome_unknown", tick, "node lost after dispatch")
        self.bump("F01_node_lost_after_dispatch")

    def f02_ack_lost_after_execution(self, op: Operation, tick: int) -> None:
        """The action RAN and the ACK was lost. Ground truth knows; the agent cannot."""
        op.transition("outcome_unknown", tick, "executed, ACK lost")
        self.bump("F02_ack_lost_after_execution")

    def f03_duplicate_side_effect(self, op: Operation, tick: int) -> None:
        """A blind retry after timeout applied the same logical effect twice."""
        self.bump("F03_duplicate_side_effect")

    def f04_pending_forgotten(self, op: Operation, tick: int) -> None:
        """The capability went away and the pending invocation was never revisited."""
        op.transition("unavailable", tick, "pending invocation forgotten")
        self.bump("F04_pending_forgotten")

    def f05_stale_used_as_current(self, op: Operation, tick: int, age: int) -> None:
        """A stale observation was treated as the present state."""
        op.state = "stale_result"
        op.stale_age = age
        self.bump("F05_stale_used_as_current")

    def f06_wrong_replay_order(self, op: Operation, tick: int) -> None:
        """After recovery the buffered results were replayed out of order."""
        op.replayed_at = tick
        self.bump("F06_wrong_replay_order")

    def f07_retry_budget_exhausted(self, op: Operation, tick: int) -> None:
        op.budget_exhausted_at = tick
        op.transition("failed", tick, "retry budget exhausted")
        self.bump("F07_retry_budget_exhausted")

    def f08_starvation_hol(self, op: Operation, tick: int) -> None:
        """A permanently failing operation blocked the head of a FIFO queue."""
        self.bump("F08_starvation_head_of_line")

    def f09_gateway_flapping(self, tick: int) -> None:
        """A gateway/relay toggled state repeatedly, so no action could settle."""
        self.bump("F09_gateway_flapping")

    def f10_partition_divergence(self, tick: int) -> None:
        """After a partition the two sides held different views of the state."""
        self.bump("F10_partition_state_divergence")

    def f11_coordinator_restart(self, tick: int) -> None:
        """The long-running coordinator restarted and lost in-memory state."""
        self.bump("F11_coordinator_restart")

    # ------------------------------------------------------------- inspection
    def open_ops(self) -> list[Operation]:
        return [o for o in self.ops.values() if o.open]

    def by_state(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for o in self.ops.values():
            out[o.state] = out.get(o.state, 0) + 1
        return out

    def unresolved(self) -> list[Operation]:
        """Operations whose effect status is epistemically undetermined."""
        return [o for o in self.ops.values() if o.state in ("outcome_unknown", "timeout")]

    def summary(self) -> dict:
        return {
            "states": self.by_state(),
            "failure_counts": dict(sorted(self.counts.items())),
            "open": len(self.open_ops()),
            "unresolved": len(self.unresolved()),
        }
