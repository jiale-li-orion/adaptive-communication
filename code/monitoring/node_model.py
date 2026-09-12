#!/usr/bin/env python3
"""
node_model.py — where the data actually originates.

The center never sees the sample schedule. It sees what arrives, when it arrives, and nothing
else. Separating the node's own record of what it measured from the center's record of what it
received is what makes the service metric meaningful: "a valid sample arrived before the
deadline" is a statement about the second record, and the first is the ground truth the scorer
holds outside the agent.

A node keeps its records until the center acknowledges them, and retransmits what is still
unacknowledged on later uploads. That is what makes `upload_records(range, cursor, budget)`
possible at all: a gap the center can name is a gap the node can fill. The history is bounded, so
a node that stays unreachable loses the oldest records, and the loss is counted rather than
hidden.

The clock is one minute. The reference workload's risk-window deadline is ten minutes, which an
hourly model cannot represent: at hourly granularity the deadline and the sampling interval are
the same number of ticks, and a scheduler that is merely "fast enough" is indistinguishable from
one that is late.

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

from task_generator import MONITORING_PROFILES, PROFILE_NORMAL

TICK_S = 60                      # A: the run clock's granularity, one minute

# A-layer device parameters. These describe a device class, not a measured unit.
DEFAULT_BUFFER_CAPACITY = 2880   # records, about two days at the normal 5-minute cadence
SAMPLE_BYTES = {"displacement": 6, "rainfall": 4}   # A: compact on-wire encoding per record

# One LoRa packet's application payload budget. Twelve five-minute displacement readings at six
# bytes each is 72 bytes, which fits: the nominal profile needs one packet per upload and the
# burst only grows when the node is falling behind, which is when extra packets are warranted.
PACKET_BYTES_MAX = 100

# An upload carries every unacknowledged record, split across as many packets as that takes.
# A fixed records-per-upload cap equal to the generation rate would be self-defeating: any single
# lost uplink would leave the oldest records permanently at the head of the queue, newer readings
# could never be sent at all, and the buffer would grow without bound even with a working channel.
DEFAULT_BATCH_MAX = 240

# The station's role and the measurement a demand asks for are different names for a related
# thing, and they drifted apart once already: a node's role is "deformation", the demand it can
# satisfy asks for "displacement", and a scorer comparing the two strings directly matched nothing
# at all. The mapping lives next to the sample construction so there is one place to be wrong, and
# the fairness audit asserts it is total over both vocabularies.
MEASUREMENT_BY_ROLE = {"deformation": "displacement", "rainfall": "rainfall"}


def measurement_of(role: str) -> str:
    try:
        return MEASUREMENT_BY_ROLE[role]
    except KeyError:
        raise ValueError(f"no measurement type is defined for node role {role!r}") from None


@dataclass(frozen=True)
class Sample:
    """One measurement. `sample_id` is stable and independent of any transport attempt."""

    sample_id: str
    node_id: str
    taken_at: int                # seconds since run start
    measurement_type: str
    payload_bytes: int
    # Set when this sample answers an explicit request. A requested measurement is a different
    # sample from the one the schedule would have taken, even at the same instant, so the identity
    # has to say which question it answers -- otherwise a cached reading could be passed off as the
    # fresh one that was asked for, which is exactly what the interface forbids.
    request_id: str | None = None

    @staticmethod
    def make(node_id: str, taken_at: int, measurement_type: str,
             request_id: str | None = None) -> "Sample":
        suffix = f":r{request_id}" if request_id is not None else ""
        return Sample(sample_id=f"{node_id}:{taken_at}{suffix}", node_id=node_id, taken_at=taken_at,
                      measurement_type=measurement_type,
                      payload_bytes=SAMPLE_BYTES.get(measurement_type, 20),
                      request_id=request_id)

    @staticmethod
    def for_role(node_id: str, taken_at: int, role: str,
                 request_id: str | None = None) -> "Sample":
        """Build a sample for a station, resolving its role to the measurement it produces."""
        return Sample.make(node_id, taken_at, measurement_of(role), request_id=request_id)


@dataclass
class NodeRuntime:
    """One node's sampling schedule, local record buffer and upload schedule.

    `profile` is a versioned assignment from the center. Changing it changes when samples are
    taken and when uploads happen, which is the point: a profile the node acknowledges but does
    not act on would make the whole execution question vacuous.
    """

    node_id: str
    role: str
    profile: str = PROFILE_NORMAL
    buffer_capacity: int = DEFAULT_BUFFER_CAPACITY
    batch_max: int = DEFAULT_BATCH_MAX
    tick_s: int = TICK_S

    # --- local state ---
    records: list[Sample] = field(default_factory=list)      # taken, not yet acknowledged
    # The newest instant the center holds for this node, carried as records arrive. Recomputing it
    # by scanning `received` was O(ticks x records): a per-tick pass over a list that grows for the
    # whole run, which cost more than the simulation it was measuring.
    newest_received_at: int | None = None
    # Every sample id the centre holds. This is the receiver's dedup set, and it is also what makes
    # a gap nameable: the gap is the ids between the acknowledged cursor and the node's report that
    # are not in here.
    received_ids: set[str] = field(default_factory=set)
    duplicate_deliveries: int = 0
    taken: list[Sample] = field(default_factory=list)        # ground truth: everything sampled
    received: list[tuple[Sample, int]] = field(default_factory=list)   # sample, arrival second
    profile_history: list[tuple[int, str]] = field(default_factory=list)

    # --- counters ---
    dropped_overflow: int = 0
    uploads_attempted: int = 0
    uploads_heard: int = 0
    records_sent: int = 0
    records_acked: int = 0

    _next_sample_at: int = 0
    _next_upload_at: int = 0
    _last_seen_s: int = 0

    # --- outstanding interface orders ---
    # request_id -> (window_start, deadline). A measurement request is answered by the first sample
    # the node takes inside the window, and by nothing else: not by the buffer, not by the schedule.
    pending_requests: dict[str, tuple[int, int]] = field(default_factory=dict)
    # The outstanding backfill order, if any: (start_s, end_s, send_cursor, budget). One at a time,
    # newest wins, because a second order for the same node supersedes the range the first named.
    backfill: tuple[int, int, int, int] | None = None
    # The acknowledged cursor: how far the center has confirmed it has. Distinct from the send
    # cursor, which is how far the node has offered. Conflating them either re-sends everything or
    # skips whatever was lost, and the interface exists to keep them apart.
    # Cursors are sample instants, not sample ids. A cursor exists to be compared, and sample ids
    # sort as strings, so comparing them would put ":10800" before ":3600" and quietly resume the
    # backfill at the wrong place.
    acked_cursor: int = 0
    sent_cursor: int = 0
    requests_answered: int = 0
    requests_expired: int = 0
    backfill_served: int = 0

    # A boot identity. It changes on every restart, which is what lets the center tell "this is the
    # same node with a new buffer" apart from "this is the same buffer".
    incarnation: int = 0

    # ------------------------------------------------------------- construction
    def __post_init__(self) -> None:
        if not self.profile_history:
            self.profile_history = [(0, self.profile)]
        self._next_sample_at = 0
        self._next_upload_at = self._interval_s("upload_s")

    # ------------------------------------------------------------------ profile
    def _interval_s(self, key: str) -> int:
        return int(MONITORING_PROFILES[self.profile][key])

    def set_profile(self, profile: str, at_s: int) -> None:
        """Apply a new monitoring profile.

        The schedule is re-based from the moment of application rather than carried over, so a
        profile change takes effect immediately in both directions. A denser profile that waited
        out the old, longer interval would miss exactly the window it was sent for.
        """
        if profile not in MONITORING_PROFILES:
            raise ValueError(f"unknown monitoring profile {profile!r}")
        if profile == self.profile:
            return
        self.profile = profile
        self.profile_history.append((at_s, profile))
        self._next_sample_at = at_s
        self._next_upload_at = at_s + self._interval_s("upload_s")

    def demand_measurement(self, request_id: str, window_start_s: int, deadline_s: int) -> None:
        """Accept a request for a fresh measurement. It is answered by a new sample or by nothing."""
        self.pending_requests[request_id] = (window_start_s, deadline_s)

    def order_backfill(self, start_s: int, end_s: int, send_cursor: int, budget: int) -> None:
        """Accept a backfill order. The next upload serves it instead of the default schedule."""
        self.backfill = (start_s, end_s, send_cursor, budget)

    def profile_at(self, t_s: int) -> str:
        current = self.profile_history[0][1]
        for at, name in self.profile_history:
            if at <= t_s:
                current = name
            else:
                break
        return current

    # ----------------------------------------------------------------- sampling
    def maybe_sample(self, t_s: int) -> list[Sample]:
        """Take every sample that came due since the last call. Returns what was taken."""
        taken: list[Sample] = []
        period = self._interval_s("sample_s")
        while self._next_sample_at <= t_s:
            at = self._next_sample_at
            # The first sample inside a request's window answers it. Tagging happens here rather
            # than at delivery so that a request answered by a sample taken before the request
            # arrived cannot exist: the tag is attached when the measurement is made.
            answering = [rid for rid, (start, deadline) in self.pending_requests.items()
                         if start <= at <= deadline]
            request_id = sorted(answering)[0] if answering else None
            if request_id is not None:
                self.pending_requests.pop(request_id, None)
                self.requests_answered += 1
            sample = Sample.for_role(self.node_id, at, self.role, request_id=request_id)
            self.records.append(sample)
            self.taken.append(sample)
            taken.append(sample)
            self._next_sample_at += period
            self._enforce_capacity()
        # Requests whose window has closed unanswered are expired, not silently forgotten. A node
        # that could not measure inside the window has to say so by not answering, and the center
        # learns it from the absence.
        for rid in [r for r, (_s, d) in self.pending_requests.items() if d < t_s]:
            self.pending_requests.pop(rid, None)
            self.requests_expired += 1
        return taken

    def _enforce_capacity(self) -> None:
        """Bound the local history, oldest first.

        A node unreachable for longer than its capacity loses its oldest unacknowledged records.
        Dropping is a real outcome of the deployment, so it is counted here rather than papered
        over by an unbounded buffer.
        """
        overflow = len(self.records) - self.buffer_capacity
        if overflow > 0:
            del self.records[:overflow]
            self.dropped_overflow += overflow

    @property
    def buffer_level(self) -> int:
        return len(self.records)

    # ------------------------------------------------------------------ upload
    def upload_due(self, t_s: int) -> bool:
        return t_s >= self._next_upload_at

    def begin_upload(self, t_s: int) -> list[Sample]:
        """Records to send on this upload: everything still unacknowledged, oldest first.

        Unacknowledged records are retransmitted, which is what lets the center close a gap it
        can name. The node does not need to be told which ones to resend; it resends what it has
        not been told arrived. The caller splits the batch into as many packets as the byte budget
        requires, so a backlog drains in a burst rather than blocking behind its oldest record.
        """
        self._next_upload_at = t_s + self._interval_s("upload_s")
        self.uploads_attempted += 1
        if self.backfill is not None:
            # A backfill order names a range, a resume point and a cap. The node serves that range
            # from that point and stops at the cap, which is what makes history compete with new
            # data for the same opportunity instead of draining the buffer wholesale.
            start_s, end_s, cursor, budget = self.backfill
            self.backfill = None
            window = [s for s in self.records if start_s <= s.taken_at <= end_s]
            window.sort(key=lambda s: s.taken_at)
            batch = [s for s in window if s.taken_at >= cursor][:max(0, budget)]
            self.backfill_served += len(batch)
            if batch:
                self.sent_cursor = batch[-1].taken_at
            self.records_sent += len(batch)
            return batch
        batch = self.records[:self.batch_max]
        if batch:
            self.sent_cursor = batch[-1].taken_at
        self.records_sent += len(batch)
        return batch

    def pack(self, batch: list[Sample]) -> list[list[Sample]]:
        """Split a batch into packets that fit the on-wire budget, preserving order."""
        packets: list[list[Sample]] = []
        current: list[Sample] = []
        used = 0
        for sample in batch:
            size = sample.payload_bytes
            if current and used + size > PACKET_BYTES_MAX:
                packets.append(current)
                current, used = [], 0
            current.append(sample)
            used += size
        if current:
            packets.append(current)
        return packets

    def upload_result(self, batch: list[Sample], heard: bool, arrival_s: int) -> None:
        """Record what happened to an upload. Acknowledgement is separate and explicit."""
        if heard:
            self.uploads_heard += 1
            for sample in batch:
                # The receiver deduplicates by sample id. A record the node retransmits because the
                # centre's confirmation was lost must not enter the archive a second time: the
                # archive is what the platform reports from, and a record counted twice inflates it
                # while telling the operator nothing new. Contract §4 requires this explicitly.
                if sample.sample_id in self.received_ids:
                    self.duplicate_deliveries += 1
                    continue
                self.received_ids.add(sample.sample_id)
                self.received.append((sample, arrival_s))
                if self.newest_received_at is None or sample.taken_at > self.newest_received_at:
                    self.newest_received_at = sample.taken_at

    def confirm(self, sample_ids) -> int:
        """The center acknowledged these sample ids. They leave the local history."""
        ids = set(sample_ids)
        if not ids:
            return 0
        kept = [s for s in self.records if s.sample_id not in ids]
        confirmed = len(self.records) - len(kept)
        self.records = kept
        self.records_acked += confirmed
        if sample_ids:
            # The acknowledged cursor is where the center says it has got to. It is not derived from
            # the send cursor, because the whole reason two cursors exist is that they differ.
            newest = max((s.taken_at for s in self.taken if s.sample_id in ids), default=None)
            if newest is not None:
                self.acked_cursor = max(self.acked_cursor, newest)
        return confirmed

    def unacknowledged_ids(self) -> list[str]:
        return [s.sample_id for s in self.records]

    def archive_gap(self, reported_newest: int, sample_interval_s: int) -> tuple[int, int] | None:
        """核验缺口：中心自报最新点与它实际持有的记录之间，缺了哪个区间。

        The centre can only name a gap it can bound. The node's report gives the newest instant it
        holds; the archive gives what actually arrived. A span wider than one sampling interval with
        nothing in the archive over it is a gap, and reporting it is what lets an operator see that
        the platform is missing data rather than merely idle.
        """
        if not self.received:
            return None
        expected_newest = int(reported_newest)
        held = {sample.taken_at for sample, _arrival in self.received}
        missing = [t for t in range(int(self.newest_received_at) + sample_interval_s,
                                    expected_newest + 1, sample_interval_s)
                   if t not in held]
        if not missing:
            return None
        return missing[0], missing[-1]

    # ------------------------------------------------------------------ reading
    def snapshot(self, t_s: int) -> dict:
        """What a status read may see of this node.

        Deliberately narrow: the current profile, the local buffer level and the newest sample
        timestamp. It does not expose the sample schedule, the unacknowledged id set, or anything
        about the channel. A read that could see the schedule would let a coordinator compute
        what it is supposed to have received instead of discovering what it did.
        """
        newest = max((s.taken_at for s in self.taken), default=None)
        return {
            "node_id": self.node_id,
            "read_at": t_s,                      # 时间戳
            "incarnation": self.incarnation,     # 启动标识
            "profile": self.profile,             # 配置版本
            "profile_since": self.profile_history[-1][0],
            "profile_version": len(self.profile_history),
            "battery_wh": None,                  # 电量估计，由供电模型填写
            "buffer_level": self.buffer_level,   # 缓存水位
            "newest_sample_at": newest,
            "acked_cursor": self.acked_cursor,
            "send_cursor": self.sent_cursor,
            "pending_requests": len(self.pending_requests),
        }
