#!/usr/bin/env python3
"""
policies.py — the strong baselines the contract requires (README D9, contract §7).

The paper asks whether a runtime layer beats device-management practice that already exists.
That question is only answered if the practice is implemented at its own best: the same node-side
contract, the same opportunity budget, the same autonomy floor. A strawman would let the runtime
win for a reason that has nothing to do with the runtime.

Two of the five baselines live here.

  versioned_config  the desired/reported pattern of a mature IoT platform (a device shadow).
                    The center keeps a desired configuration per node, writes it when the last
                    configuration the node reported differs, and stops once the node reports the
                    value back. Writes carry a version so an older desired value cannot land on
                    top of a newer one.

  vtc_style         the published verify-then-act pattern. A command is issued, then the center
                    verifies whether the intended effect is in place, with three outcomes: true
                    (in place, stop), false (not in place, re-issue), unknown (inconclusive, back
                    off without hammering). One logical command keeps one identity across all of
                    its attempts.

WHAT THESE DELIBERATELY DO NOT DO. Neither policy asks a node for its status before writing. The
node's configuration arrives piggybacked on its own telemetry, so `WorldView.status` is the
reported value whenever a report exists; spending an opportunity on an extra remote read before
every write would make the comparison unfair (contract §7, "可缓存或从报告获得版本，不强制每次写前
额外远程读"). Neither policy uses the demanded schedule to compute anything the interface does not
give it: the same demand/status/in-flight facts the runner hands to every arm are all that is
read.

WHAT "STOP" MEANS. Both stop on the same evidence: the node reports the desired configuration, or
the write's TTL has run out. A node that never reports back does not leave the policy retrying
forever — the versioned baseline waits `write_dwell_s` between identical writes and gives up when
the desired version expires, and the VTC baseline backs off on every inconclusive read and gives up
the same way. Retrying at the node's own upload cadence is the honest comparison: that is what the
opportunity budget allows, and a baseline that retried harder would be the unfair one.

Deps: standard library only. This module imports nothing from `runner`, so the comparison arms stay
independent of the code that runs them.
"""
from __future__ import annotations

# --- module resolution -------------------------------------------------------
# The two baselines have no dependencies inside the project, so the only thing this shim does is
# let the file run both as `monitoring.policies` and as a flat module on sys.path.
try:                                    # package import, e.g. from monitoring
    from .task_generator import MONITORING_PROFILES, PROFILE_NORMAL, PROFILE_RISK
except ImportError:                     # flat import, e.g. with code/monitoring on sys.path
    import os as _os, sys as _sys
    _HERE = _os.path.dirname(_os.path.abspath(__file__))
    if _HERE not in _sys.path:
        _sys.path.insert(0, _HERE)
    from task_generator import MONITORING_PROFILES, PROFILE_NORMAL, PROFILE_RISK
# -----------------------------------------------------------------------------

from typing import Callable

# The only payload shape the execution runtime understands today. A policy that returned anything
# else would be silently skipped by the runtime, which would look like a quiet policy rather than
# a broken one, so the payload is built in exactly one place per policy.
OP_SET_PROFILE = "set_monitoring_profile"
OP_REQUEST_MEASUREMENT = "request_measurement"
OP_UPLOAD_RECORDS = "upload_records"
OP_READ_STATUS = "read_status"

# Every op the center may ask for. The runner routes on this field and refuses anything outside the
# set, so a policy cannot reach the far side through a path the contract did not name.
OPS = (OP_SET_PROFILE, OP_REQUEST_MEASUREMENT, OP_UPLOAD_RECORDS, OP_READ_STATUS)

# Field names inside a status snapshot. A snapshot may be minimal in a regression harness: the
# reported configuration is the one field the policy needs, everything else is only recorded.
F_PROFILE = "profile"
F_NODE_ID = "node_id"
F_READ_AT = "read_at"

# Three-valued verification result (VTC). These are the policy's own values; they are not the
# interface's outcome vocabulary, and importing it would tie a baseline to the runtime's internals.
VERDICT_TRUE = "true"
VERDICT_FALSE = "false"
VERDICT_UNKNOWN = "unknown"

# The dwell between two identical writes, seconds. A: five minutes, the shortest upload interval a
# node runs in the reference workload. Retrying faster than the node uploads cannot help: a
# downlink needs an opportunity, and an opportunity comes from an uplink.
DWELL_S = 300

# The logical lifetime of one desired value, seconds. A: six hours, the TTL the execution runtime
# gives a profile command. Once it has passed, the center's desired value is no longer something
# the node could still be acting on, so a baseline stops re-asserting it.
COMMAND_TTL_S = 6 * 3600

# The VTC backoff shape, seconds. A: fifteen minutes before the first re-issue, doubling up to four
# hours. A verification loop that re-issued every tick would spend the whole downlink budget on one
# node and would make the memoryless retry arm look like a strategy.
VTC_BACKOFF_BASE_S = 900
VTC_BACKOFF_MAX_S = 4 * 3600


def _field(payload: dict | None, key: str, default=None):
    """Read one field out of a status snapshot without assuming the snapshot's shape."""
    if isinstance(payload, dict):
        return payload.get(key, default)
    return default


def measurement_command(request_id: str, window_start_s: int, deadline_s: int) -> dict:
    """Ask for a fresh measurement the node has not taken yet.

    The request carries the window it must be answered in. A sample from the buffer is not an
    answer to it and the node is written so that it cannot be: the answer is tagged at the moment
    the measurement is made, so no cached reading can acquire the tag afterwards.
    """
    return {"op": OP_REQUEST_MEASUREMENT, "request_id": request_id,
            "window_start": int(window_start_s), "deadline": int(deadline_s)}


def upload_command(start_s: int, end_s: int, cursor: int, budget: int) -> dict:
    """Ask for a range of history to be transferred, resuming from a named point.

    `cursor` is the send cursor, not the acknowledged one. Asking from the acknowledged cursor
    re-sends everything already delivered; asking from a cursor the center invented skips whatever
    was lost in flight. Both mistakes are cheap to make and expensive to notice, so the cursor is
    always carried explicitly.
    """
    return {"op": OP_UPLOAD_RECORDS, "start": int(start_s), "end": int(end_s),
            "cursor": int(cursor), "budget": int(budget)}


def profile_command(profile: str, version: int | None = None,
                    logical: str | None = None) -> dict:
    """The single payload shape a policy may return to the runtime.

    `version` and `logical` are optional and travel on the wire when a policy chooses to send them.
    A device shadow that keeps its versioning in the center's head while sending a bare value has
    handed the remote nothing to fence on, and the remote cannot reject an ordering it cannot see.
    Sending them is what makes the remote contract reachable, so a baseline that holds versions is
    given the same chance to send them as the runtime is.
    """
    command = {"op": OP_SET_PROFILE, "profile": profile}
    if version is not None:
        command["version"] = int(version)
    if logical is not None:
        command["logical"] = str(logical)
    return command


class VersionedConfigPolicy:
    """版本化 desired/reported 配置调和。

    A device shadow, implemented to the letter: per node the center holds a desired value with a
    version, a reported value, and the version it last put on the wire. A write happens when the
    desired value differs from the reported one, carries a strictly higher version than any write
    already issued for that node, and is never issued while a command for that node is still
    unconfirmed.
    """

    name = "versioned_config"

    def __init__(self, write_dwell_s: int = DWELL_S, write_ttl_s: int = COMMAND_TTL_S) -> None:
        if write_dwell_s < 0:
            raise ValueError("write_dwell_s must not be negative")
        if write_ttl_s <= 0:
            raise ValueError("write_ttl_s must be positive")
        self.write_dwell_s = write_dwell_s
        self.write_ttl_s = write_ttl_s

        # per-node center state: the desired value is absent when the center holds no announcement
        self.desired: dict[str, str] = {}
        self.desired_version: dict[str, int] = {}      # version of the current desired value
        self.issued_version: dict[str, int] = {}       # version of the newest write put on the wire
        self.issued_profile: dict[str, str] = {}
        self.issued_at: dict[str, int] = {}
        self.deadline: dict[str, int] = {}             # when the issued desired value stops mattering

        # reported side: what the node last told the center, and what the center kept from it
        self.reported: dict[str, str] = {}
        self.reported_version: dict[str, int] = {}     # version a report is evidence for
        self.reported_source: dict[str, str] = {}      # where the reported value came from
        self.reported_at: dict[str, int] = {}

        # counters, exposed for the regression test and for the audit log
        self.writes = 0
        self.supersessions = 0
        self.identities: dict[str, int] = {}
        self.last_decision: dict[str, dict] = {}

    # ------------------------------------------------------------------ reading
    def version_of(self, node_id: str) -> int:
        """The version currently attached to this node's desired value (0 when none)."""
        return self.desired_version.get(node_id, 0)

    def identity_of(self, node_id: str) -> int:
        """The logical command identity for this node's current desired value.

        Logically one command: it does not move while the desired value stays the same, so all of
        its attempts share one identity, and it moves when a new value is desired.
        """
        return self.identities.get(node_id, 0)

    def desired_of(self, node_id: str) -> str | None:
        return self.desired.get(node_id)

    def forget(self, node_id: str) -> None:
        """Drop the center's intent for one node.

        Used when the demand disappears and when the issued version expires. Dropping the intent
        does not unmake anything that may have already happened at the node: the next announcement
        is a new instruction and gets a new version, which is what keeps a stale intent from
        overwriting a newer one after a reconnect.
        """
        self.desired.pop(node_id, None)
        self.desired_version.pop(node_id, None)
        self.deadline.pop(node_id, None)
        # issued_version and reported stay: they are history the next comparison needs.

    # ------------------------------------------------------------------ planning
    def plan(self, view) -> list[tuple[str, dict]]:
        """Return the writes the center should try to enqueue this tick.

        Only the documented WorldView attributes are read: `t_s`, `node_ids`, `status`,
        `demanded_profile` and `in_flight`.
        """
        now = view.t_s
        status = view.status
        in_flight = view.in_flight
        demanded = view.demanded_profile
        out: list[tuple[str, dict]] = []

        # The reported configuration arrives piggybacked on the node's own telemetry, so the status
        # map is where the center learns it. No read is bought before a write: that would spend the
        # opportunity the policy is supposed to be allocating (contract §7).
        for node_id, payload in sorted(status.items()):
            reported = _field(payload, F_PROFILE)
            if reported is not None:
                if self.reported.get(node_id) != reported:
                    # A report whose value differs from the last one is new information, and the
                    # version it can be evidence for is the newest the center had written when this
                    # report arrived. A report that repeats the same value carries no new information
                    # and keeps the version it was first tagged with.
                    self.reported_version[node_id] = self.issued_version.get(node_id, 0)
                self.reported[node_id] = reported
                self.reported_source[node_id] = "status"
                self.reported_at[node_id] = _field(payload, F_READ_AT, now)

        # The center acts on what it holds. With no demanded value in hand it has nothing to
        # reconcile, and issuing a write would be inventing an instruction the scenario never
        # announced; the demand carries the recovery half of the workflow just as explicitly.
        for node_id in list(self.desired):
            if node_id not in demanded:
                self.forget(node_id)

        for node_id, wanted in sorted(demanded.items()):
            record = {"node_id": node_id, "t_s": now, "desired": wanted}
            self.last_decision[node_id] = record

            # reconcile: a new desired value gets a new version, and the version never goes down
            # for a value this node has already been sent.
            previous = self.desired.get(node_id)
            if previous != wanted:
                self.desired[node_id] = wanted
                self.desired_version[node_id] = self.identities.get(node_id, 0) + 1
                self.identities[node_id] = self.desired_version[node_id]
                self.deadline[node_id] = now + self.write_ttl_s
                record.update(event="desired", fresh_intent=True,
                              version=self.desired_version[node_id])
            else:
                record.update(event="desired", fresh_intent=False, version=self.identity_of(node_id))

            # what the node last reported, if anything, and which version that report is evidence for
            reported = self.reported.get(node_id)
            reported_version = self.reported_version.get(node_id, 0)
            record["reported"] = reported
            record["reported_source"] = self.reported_source.get(node_id, "-")
            record["reported_version"] = reported_version

            version = self.desired_version[node_id]
            issued_version = self.issued_version.get(node_id, 0)
            # A strictly newer desired value supersedes whatever is already on the wire. Refusing to
            # write it because an older command is still unconfirmed would mean a node that never
            # confirms could never be told the newer value, and the node would keep applying the
            # superseded one. That is not a re-issue: it is a different desired value, and it is
            # exactly what a shadow platform does when the desired configuration changes.
            supersedes = issued_version > 0 and version > issued_version
            record["supersedes"] = bool(supersedes)

            if reported == wanted:
                # The node reports the desired configuration back: it is running the value the
                # center wants, so there is nothing to correct, and waiting for a second
                # confirmation of a value the node already reported is how a reconciliation loop
                # turns into a retry loop. Whether the report is evidence for this exact version is
                # recorded for the audit, but the value match is what ends the reconciliation: a
                # snapshot's internal sequencing is not something this interface exposes, and
                # ending on the value keeps the loop from re-writing a configuration that matches.
                record.update(action="stop", reason="reported_matches_desired")
                continue

            if node_id in in_flight and not supersedes:
                # The center already has a command out for this node and it has not been confirmed.
                # Treating "I asked" as "it is handled" would give up silently whenever the send was
                # refused, so the write stays open and is reconsidered once it is resolved.
                record.update(action="skip", reason="in_flight")
                continue

            if issued_version > version:
                # A newer desired value has already been written for this node, so this older
                # demand is a delayed arrival and must not be re-asserted over it.
                record.update(action="skip", reason="stale_demand", issued_version=issued_version)
                continue

            if supersedes:
                record.update(action="write", reason="newer_desired_value", version=version)
                out.append((node_id, profile_command(
                    wanted, version=version, logical=f"{node_id}:{self.identity_of(node_id)}")))
                continue

            if issued_version == 0:
                record.update(action="write", reason="first_write", version=version)
                out.append((node_id, profile_command(
                    wanted, version=version, logical=f"{node_id}:{self.identity_of(node_id)}")))
                continue

            since = now - self.issued_at.get(node_id, now)
            if since < self.write_dwell_s:
                # A report that disagrees can be older than the write it disagrees with, so a
                # mismatch right after a write is not evidence that the write failed.
                record.update(action="wait", reason="dwell", since_s=since,
                              dwell_s=self.write_dwell_s)
                continue

            if now > self.deadline.get(node_id, now):
                # The version the center was asserting has expired. Nothing new is desired, so the
                # intent is dropped rather than refreshed forever.
                self.forget(node_id)
                record.update(action="stop", reason="expired")
                continue

            record.update(action="write", reason="reported_differs_after_dwell", version=version,
                          since_s=since)
            out.append((node_id, profile_command(
                wanted, version=version, logical=f"{node_id}:{self.identity_of(node_id)}")))

        for node_id, payload in out:
            self.issued_version[node_id] = self.desired_version[node_id]
            self.issued_profile[node_id] = payload["profile"]
            self.issued_at[node_id] = now
            self.writes += 1
            self.last_decision[node_id].update(
                issued=True, issued_profile=payload["profile"],
                issued_version=self.issued_version[node_id])
            self.reported_source[node_id] = self.reported_source.get(node_id, "-")

        return out


class VTCPolicy:
    """VTC 风格验证恢复：稳定身份 + True/False/Unknown + 退避。

    Issue, then verify, with a three-valued outcome. The read the verification uses is the status
    the node piggybacked on its own telemetry: a policy that had to buy a read would be spending
    the opportunity it is trying to allocate, and the interface already hands every arm the
    reported value for free.
    """

    name = "vtc_style"

    def __init__(self, base_backoff_s: int = VTC_BACKOFF_BASE_S,
                 max_backoff_s: int = VTC_BACKOFF_MAX_S,
                 command_ttl_s: int = COMMAND_TTL_S) -> None:
        if base_backoff_s < 0:
            raise ValueError("base_backoff_s must not be negative")
        if max_backoff_s < base_backoff_s:
            raise ValueError("max_backoff_s must be at least base_backoff_s")
        if command_ttl_s <= 0:
            raise ValueError("command_ttl_s must be positive")
        self.base_backoff_s = base_backoff_s
        self.max_backoff_s = max_backoff_s
        self.command_ttl_s = command_ttl_s
        self._normal_profile = PROFILE_NORMAL
        self.reset()

    def reset(self) -> None:
        self.target: dict[str, str] = {}              # the effect the center wants in place
        self.issued: dict[str, str] = {}              # the value last put on the wire
        self.issued_at: dict[str, int] = {}
        self.deadline: dict[str, int] = {}
        self.attempts: dict[str, int] = {}            # all attempts of the current logical command
        self.verdict: dict[str, str] = {}
        self.unknown_streak: dict[str, int] = {}
        self.backoff_s: dict[str, int] = {}
        self.logical: dict[str, int] = {}             # one logical command identity per node
        self.issues: dict[str, list[tuple[int, str, str]]] = {}   # (t_s, profile, identity)
        self.unresponsive: dict[str, int] = {}
        self.last_decision: dict[str, dict] = {}

    # ------------------------------------------------------------- stable identity
    def command_of(self, node_id: str) -> str:
        """The stable identity of the logical command currently open for this node.

        Stable means every attempt of the same logical command carries this string; it changes only
        when the center wants a different effect, which is also when the previous command has been
        completed, abandoned or superseded.
        """
        return f"vtc:{node_id}:{self.logical.get(node_id, 0)}"

    def attempts_of(self, node_id: str) -> int:
        """How many times the current logical command has been issued."""
        return self.attempts.get(node_id, 0)

    def verdict_of(self, node_id: str) -> str:
        """The last three-valued verification result for this node."""
        return self.verdict.get(node_id, VERDICT_UNKNOWN)

    def target_of(self, node_id: str) -> str | None:
        return self.target.get(node_id)

    def forget(self, node_id: str) -> None:
        """Close the logical command for one node and drop the intent behind it."""
        self.target.pop(node_id, None)
        self.deadline.pop(node_id, None)

    # ------------------------------------------------------------------ planning
    def plan(self, view) -> list[tuple[str, dict]]:
        """Return the commands the center should try to enqueue this tick.

        Only the documented WorldView attributes are read: `t_s`, `status`, `demanded_profile` and
        `in_flight`. The verification read is the reported configuration out of `status`; nothing is
        asked of the node to obtain it.
        """
        now = view.t_s
        status = view.status
        in_flight = view.in_flight
        demanded = view.demanded_profile
        out: list[tuple[str, dict]] = []

        for node_id in list(self.target):
            if node_id not in demanded:
                self.forget(node_id)

        for node_id, wanted in sorted(demanded.items()):
            record = {"node_id": node_id, "t_s": now, "desired": wanted}
            self.last_decision[node_id] = record
            self._reconcile(node_id, wanted, now, record)
            record["command"] = self.command_of(node_id)
            record["attempts"] = self.attempts_of(node_id)

            if node_id in in_flight:
                record.update(action="skip", reason="in_flight")
                continue

            verdict = self._verify(node_id, wanted, status.get(node_id), now, record)
            self.verdict[node_id] = verdict
            record["verdict"] = verdict

            if verdict == VERDICT_TRUE:
                record.update(action="stop", reason="effect_in_place")
                continue

            if verdict == VERDICT_UNKNOWN:
                # Inconclusive. Waiting is the action: re-issuing on an inconclusive read turns an
                # unobservable outcome into a retry storm, and it spends the opportunity budget of
                # every other node to do it.
                if not self._backoff_elapsed(node_id, now):
                    record.update(action="wait", reason="unknown_backoff",
                                  backoff_s=self.backoff_s.get(node_id, self.base_backoff_s))
                    continue
            elif not self._backoff_elapsed(node_id, now):
                # A conclusive mismatch does not license an immediate retry either. The backoff is
                # the time the previous attempt needs to have had a chance to land; retrying inside
                # it spends an opportunity on evidence that has not changed.
                record.update(action="wait", reason="retry_backoff",
                              backoff_s=self.backoff_s.get(node_id, self.base_backoff_s))
                continue

            if self._expired(node_id, now):
                self.forget(node_id)
                record.update(action="stop", reason="expired")
                continue

            if verdict == VERDICT_UNKNOWN:
                n = self.unknown_streak.get(node_id, 0) + 1
                self.unknown_streak[node_id] = n
                self.backoff_s[node_id] = min(self.max_backoff_s, self.base_backoff_s * (2 ** n))
                record["unknown_streak"] = n
                record["next_backoff_s"] = self.backoff_s[node_id]
            else:
                self.unknown_streak[node_id] = 0
                self.backoff_s[node_id] = self.base_backoff_s

            self._issue(node_id, wanted, now, record)
            out.append((node_id, profile_command(wanted)))

        return out

    # ------------------------------------------------------------------ internals
    def _reconcile(self, node_id: str, wanted: str, now: int, record: dict) -> None:
        """Bind the current demand to a logical command, opening a new one only for a new effect."""
        if self.target.get(node_id) == wanted:
            record.update(event="command", fresh=False, logical=self.logical.get(node_id, 0))
            return
        self.logical[node_id] = self.logical.get(node_id, 0) + 1
        self.target[node_id] = wanted
        self.issued.pop(node_id, None)
        self.attempts[node_id] = 0
        self.unknown_streak[node_id] = 0
        self.backoff_s[node_id] = self.base_backoff_s
        self.verdict[node_id] = VERDICT_UNKNOWN
        self.deadline[node_id] = now + self.command_ttl_s
        record.update(event="command", fresh=True, logical=self.logical[node_id])

    def _verify(self, node_id: str, wanted: str, payload, now: int, record: dict) -> str:
        """Three-valued verification of the intended effect.

        true     the node reports the desired configuration is in place: stop.
        false    the node reports a configuration that differs from the desired one.
        unknown  nothing was reported, or what was reported cannot be placed in time relative to
                 the command, or the node has stopped transmitting and carries no meaning at all.
        """
        if payload is None:
            record["evidence"] = "none"
            return VERDICT_UNKNOWN

        reported = _field(payload, F_PROFILE)
        if reported is None:
            record["evidence"] = "report_without_profile"
            return VERDICT_UNKNOWN

        record["evidence"] = "status"
        record["reported"] = reported
        if reported == wanted:
            return VERDICT_TRUE

        if self._unresponsive(node_id, payload):
            # The last report a node sent before it stopped agreeing with what it was told carries
            # no information about the command that was queued behind it. Reading it as "false"
            # would re-issue on evidence older than the command itself.
            n = self.unresponsive.get(node_id, 0) + 1
            self.unresponsive[node_id] = n
            record["unresponsive"] = n
            return VERDICT_UNKNOWN

        return VERDICT_FALSE

    def _unresponsive(self, node_id: str, payload) -> bool:
        """Whether the report predates the command and the node has not sent anything since.

        Two signals raise this. The node's reported configuration differs from the value the center
        last wrote, which means the report was composed before the write landed; and the node is on
        a profile of its own, which is what a node reverts to after a restart and says nothing about
        the center's command either way. Such a report is exactly the "inconclusive read" the VTC
        pattern answers with a backoff rather than with an immediate re-issue.
        """
        if self.issued.get(node_id) is not None and _field(payload, F_PROFILE) != self.issued[node_id]:
            return True
        return _field(payload, F_PROFILE) == self._normal_profile

    def _expired(self, node_id: str, now: int) -> bool:
        """Whether the command's validity has passed with no confirmation."""
        issued_at = self.issued_at.get(node_id)
        if issued_at is None:
            return False
        deadline = self.deadline.get(node_id, issued_at + self.command_ttl_s)
        return now > deadline

    def _backoff_elapsed(self, node_id: str, now: int) -> bool:
        issued_at = self.issued_at.get(node_id)
        if issued_at is None:
            return True
        wait = self.backoff_s.get(node_id, self.base_backoff_s)
        return now - issued_at >= max(wait, 0)

    def _issue(self, node_id: str, wanted: str, now: int, record: dict) -> None:
        """Put the command on the wire and advance the retry state of the same logical command."""
        self.issued[node_id] = wanted
        self.issued_at[node_id] = now
        self.attempts[node_id] = self.attempts.get(node_id, 0) + 1
        self.issues.setdefault(node_id, []).append((now, wanted, self.command_of(node_id)))
        record.update(action="issue", issued_profile=wanted,
                      issued_version=self.attempts[node_id])


# Registry for a comparison harness. Importing this mapping is optional: an arm can also name the
# class directly. It exists so a runner can enumerate the baselines without importing them by name.
STRONG_BASELINES: dict[str, Callable[[], object]] = {
    VersionedConfigPolicy.name: VersionedConfigPolicy,
    VTCPolicy.name: VTCPolicy,
}

# The profile a recovery resets to when the center has no announcement of its own. Exported for
# callers that need the name without importing the task generator.
NORMAL_PROFILE = PROFILE_NORMAL


def build_baseline(name: str, **kwargs) -> object:
    """Construct one of the strong baselines by its registry name."""
    try:
        factory = STRONG_BASELINES[name]
    except KeyError:
        raise ValueError(f"unknown baseline {name!r}; have {sorted(STRONG_BASELINES)}") from None
    return factory(**kwargs)


if __name__ == "__main__":          # a small self-check; the regression test is the real gate
    class _View:
        def __init__(self, t_s, demanded, status=None, in_flight=frozenset()):
            self.t_s = t_s
            self.node_ids = ("r00", "r01")
            self.status = status or {}
            self.demanded_profile = demanded
            self.center_has_announcement = bool(demanded)
            self.in_flight = in_flight

    for cls in (VersionedConfigPolicy, VTCPolicy):
        pol = cls()
        print(cls.name, "empty demand ->", pol.plan(_View(0, {})))
        print(cls.name, "risk demand  ->", pol.plan(_View(0, {"r00": "risk"})))


class RuntimePolicy:
    """本文 runtime：稳定逻辑身份、单调 epoch、证据晚于写入才允许结算。

    与版本化配置臂的三点差别，每一点都对应一个已测出的失效：

    一、同一逻辑命令的多次尝试携带**同一个** `logical`，因此远端能把重发认成同一件事而不是
        新指令；配置值不变时 `logical` 不动，配置值变了才动。
    二、每次写入带**单调递增**的 `version`，远端可以据此拒绝比当前生效值更旧的写入。
    三、一个与期望相符的上报**只有在它晚于最后一次写入时才算证据**。版本化臂把值相符当成
        调和的终点，于是一份写入之前产生的陈旧上报也能结束一次尚未生效的写入，中心据此
        宣告成功——这正是 `stale_command` 下那条臂留下 2 次误报成功的原因。
    """

    name = "ours"

    def __init__(self, dwell_s: int = DWELL_S, ttl_s: int = COMMAND_TTL_S) -> None:
        if dwell_s < 0:
            raise ValueError("dwell_s must not be negative")
        if ttl_s <= 0:
            raise ValueError("ttl_s must be positive")
        self.dwell_s = dwell_s
        self.ttl_s = ttl_s

        self.desired: dict[str, str] = {}
        self.logical: dict[str, int] = {}       # moves only when the desired value moves
        self.version: dict[str, int] = {}       # monotonic per node, never reused
        self.issued_at: dict[str, int] = {}
        self.issued_version: dict[str, int] = {}
        self.deadline: dict[str, int] = {}

        self.reported: dict[str, str] = {}
        self.reported_at: dict[str, int] = {}   # when the node produced the report, not when it arrived
        self.settled_version: dict[str, int] = {}   # newest version whose effect has been evidenced

        # W1/W2 knobs. The backfill budget is the share of one opportunity the past may take; the
        # status age is what "fresh" means for the free read.
        self.backfill_budget = 8
        self.status_max_age_s = 3600
        self.measure_retry_s = 900
        self.backfill_ordered: dict[str, tuple[int, int]] = {}
        # node -> (request_id, deadline of the outstanding measurement request)
        self.measure_outstanding: dict[str, tuple[str, int]] = {}
        # How many upload cadences the request window spans. A window shorter than the cadence it
        # has to wait for cannot be served at all: the command has to reach the node in a downlink
        # opportunity, and those arrive at the node's own rhythm, not the center's.
        self.measure_window_mult = 2
        self.backfills_ordered = 0
        self.measurements_asked = 0

        self.writes = 0
        self.settled = 0
        self.reconciles = 0                     # writes refused because the evidence was too old
        self.last_decision: dict[str, dict] = {}

    def identity_of(self, node_id: str) -> str:
        return f"{node_id}:{self.logical.get(node_id, 0)}"

    # ------------------------------------------------------------------ W1/W2/W3
    def read_status(self, view, node_id: str, max_age_s: int):
        """`read_status(node, max_age)`: what the node last told us, and how old that is.

        Answered from telemetry the node already sent, which is what the contract allows: a fresh
        passive report answers the read for free, and only a read that must be newer than anything
        on hand would cost a message. Returns `(payload, age_s)` with `payload` None when the node
        has never reported.
        """
        payload = view.status.get(node_id)
        if not payload:
            return None, None
        read_at = payload.get("read_at")
        if read_at is None:
            return payload, None
        return payload, max(0, view.t_s - int(read_at))

    def _w1_needs_fresh_measurement(self, view, node_id: str, want: str) -> bool:
        """Whether the risk-window demand needs a measurement the node has not taken.

        A denser profile only helps once it is in force. While the change is still in flight the
        window is running and the center holds nothing from it, so it asks for the measurement
        explicitly rather than waiting for a schedule that may arrive after the window closed.
        """
        if want != PROFILE_RISK:
            return False
        # One outstanding request per node. Asking again while the first is unanswered spends a
        # second opportunity on the same question and starves the profile writes, which is how a
        # policy that looks responsive ends up serving fewer demands than one that waits.
        # A request stays outstanding until its own deadline. The center cannot tell an answered
        # request from one still in flight, and re-asking on the strength of a guess is exactly the
        # move the unknown outcome is supposed to forbid -- so it waits the deadline out.
        outstanding = self.measure_outstanding.get(node_id)
        if outstanding is not None:
            if view.t_s <= outstanding[1]:
                return False
            del self.measure_outstanding[node_id]
        newest = view.archive_newest.get(node_id)
        if newest is None:
            return False                      # nothing to compare against yet; the profile loop acts
        return view.t_s - newest > MONITORING_PROFILES[PROFILE_RISK]["sample_s"] * 2

    def _w2_gap(self, view, node_id: str):
        """The gap between the center's archive and what the node says it holds, if any.

        Returns `(start_s, end_s, cursor, budget)` for a bounded backfill, or None. The budget is
        capped so that history cannot take every opportunity: the point of the interface is that
        the center chooses how much of the scarce channel goes to the past, and an unbounded
        backfill is the head-of-line blocking the contract warns about.
        """
        payload, _age = self.read_status(view, node_id, self.status_max_age_s)
        if not payload:
            return None
        newest = payload.get("newest_sample_at")
        if newest is None:
            return None
        cursor = view.archive_newest.get(node_id, 0)
        if newest - cursor <= MONITORING_PROFILES[PROFILE_NORMAL]["sample_s"]:
            return None                      # the archive is current; there is nothing to recover
        if self.backfill_ordered.get(node_id) == (cursor, newest):
            return None                      # this exact gap already has an order outstanding
        return cursor, int(newest), int(cursor), self.backfill_budget

    def plan(self, view) -> list[tuple[str, dict]]:
        now = view.t_s
        status = view.status
        in_flight = view.in_flight
        demanded = view.demanded_profile
        out: list[tuple[str, dict]] = []

        # ---- W2: recover what the archive is missing, with a bounded slice of the channel ----
        for node_id in sorted(demanded):
            gap = self._w2_gap(view, node_id)
            if gap is None:
                continue
            start_s, end_s, cursor, budget = gap
            # The cursor is the archive's own newest point, not a number the center invents. Asking
            # from the acknowledged point re-sends what already arrived; asking from anywhere else
            # skips whatever was lost.
            self.backfill_ordered[node_id] = (cursor, end_s)
            self.backfills_ordered += 1
            out.append((node_id, upload_command(cursor, end_s, cursor, budget)))

        # ---- W1: ask for a measurement the node would not otherwise take in time ----
        for node_id, want in sorted(demanded.items()):
            if not self._w1_needs_fresh_measurement(view, node_id, want):
                continue
            window = MONITORING_PROFILES[PROFILE_NORMAL]["upload_s"] * self.measure_window_mult
            request_id = f"{node_id}:{now}"
            self.measure_outstanding[node_id] = (request_id, now + window)
            self.measurements_asked += 1
            out.append((node_id, measurement_command(request_id, now, now + window)))

        # A report is evidence about the moment the node produced it, not the moment it arrived.
        # The backhaul can hold it for hours, and treating arrival as the evidence time is how a
        # center ends up declaring a write successful on the strength of a reading taken before
        # the write was even sent.
        for node_id, payload in sorted(status.items()):
            reported = _field(payload, F_PROFILE)
            if reported is None:
                continue
            self.reported[node_id] = reported
            self.reported_at[node_id] = max(self.reported_at.get(node_id, 0),
                                            _field(payload, F_READ_AT, now))

        for node_id in list(self.desired):
            if node_id not in demanded:
                self.desired.pop(node_id, None)
                self.deadline.pop(node_id, None)

        for node_id, wanted in sorted(demanded.items()):
            record = {"node_id": node_id, "t_s": now}
            self.last_decision[node_id] = record

            if self.desired.get(node_id) != wanted:
                # A new instruction: the logical identity moves with it, so a retry of the old one
                # is a different operation from this one and the remote can tell them apart.
                self.desired[node_id] = wanted
                self.logical[node_id] = self.logical.get(node_id, 0) + 1
                self.version[node_id] = self.version.get(node_id, 0) + 1
                self.deadline[node_id] = now + self.ttl_s
                record.update(fresh_intent=True, logical=self.identity_of(node_id))
            else:
                record.update(fresh_intent=False, logical=self.identity_of(node_id))

            version = self.version[node_id]
            issued_version = self.issued_version.get(node_id, 0)
            reported = self.reported.get(node_id)
            reported_at = self.reported_at.get(node_id, 0)
            record.update(reported=reported, reported_at=reported_at)

            issued_at = self.issued_at.get(node_id, 0)
            # A report is information about the write only if the node produced it after the write
            # went out. Reports from before that describe a state the write has already replaced,
            # and both of the moves below would be wrong if taken on them: settling on one declares
            # a success nothing supports, and re-asserting on one spends an opportunity because the
            # node held still before being asked.
            fresh_evidence = reported_at > issued_at

            if reported == wanted and fresh_evidence:
                # The node reported the wanted value from a moment after the newest write went out.
                # The effect is evidenced, and only now may the center settle it.
                self.settled_version[node_id] = issued_version
                self.settled += 1
                record.update(action="settle", reason="report_postdates_write",
                              evidenced_version=issued_version)
                continue

            if reported == wanted and issued_version:
                # The value matches but the report predates the write it would be used to confirm.
                # It is evidence of an older state, so it settles nothing and the write stays open.
                self.reconciles += 1
                record.update(action="reconcile", reason="report_predates_write",
                              issued_version=issued_version, reported_at=reported_at,
                              issued_at=issued_at)

            if node_id in in_flight:
                record.update(action="skip", reason="in_flight")
                continue

            if issued_version and not fresh_evidence:
                # Nothing has reported since the newest write. There is no information yet, so a
                # second write spends an opportunity on a guess; the deadline is what ends this.
                if now <= self.deadline.get(node_id, now):
                    record.update(action="wait", reason="no_evidence_since_write")
                    continue

            if issued_version and fresh_evidence:
                since = now - issued_at
                if since < self.dwell_s:
                    # A report that disagrees can have been produced moments after the write and
                    # still be describing the state before it. The dwell is what keeps a mismatch
                    # from being read as a failure it does not yet evidence.
                    record.update(action="wait", reason="dwell", since_s=since)
                    continue

            # Assert, carrying both the logical identity and a version strictly above anything this
            # node has accepted. A retry of an unresolved operation reuses the identity and only
            # the version moves, which is what lets the remote dedup without losing the retry.
            if issued_version >= version:
                self.version[node_id] = issued_version + 1
                version = self.version[node_id]
            record.update(action="write", version=version, reason="assert")
            out.append((node_id, profile_command(wanted, version=version,
                                                 logical=self.identity_of(node_id))))

        for node_id, payload in out:
            # Only a profile write carries a version. The W1 and W2 commands are different
            # interfaces with their own identities, and booking them as writes would corrupt the
            # version this node's reconciliation is keyed on.
            if payload.get("op") != OP_SET_PROFILE:
                continue
            self.issued_version[node_id] = payload["version"]
            self.issued_at[node_id] = now
            self.writes += 1
            self.last_decision[node_id].update(issued=True, issued_version=payload["version"])

        return out


class RuntimeNoEvidencePolicy(RuntimePolicy):
    """本文 runtime 的消融：去掉"证据必须晚于写入"这条规则。

    去掉之后，一份与期望相符的上报就足以结束一次写入，无论它产生在写入之前还是之后。这正是
    版本化配置臂的规则，因此这条消融检验的是：`ack_lost` 上本文臂那段知晓时延优势，究竟来自
    证据规则，还是来自别处。若两者读数相同，则该规则的贡献为零，本文臂的优势另有来源。
    """

    name = "ours_no_evidence"

    def plan(self, view) -> list[tuple[str, dict]]:
        # Settle any matching report immediately, dated to when it was produced. The rest of the
        # runtime is untouched, so a difference between this arm and `ours` is attributable to the
        # rule and to nothing else.
        for node_id, payload in sorted(view.status.items()):
            reported = _field(payload, F_PROFILE)
            if reported is None:
                continue
            self.reported[node_id] = reported
            self.reported_at[node_id] = max(self.reported_at.get(node_id, 0),
                                            _field(payload, F_READ_AT, view.t_s))
        for node_id, wanted in sorted(view.demanded_profile.items()):
            if self.reported.get(node_id) == wanted:
                self.settled_version[node_id] = self.issued_version.get(node_id, 0)
                self.settled += 1
        return super().plan(view)


class RuntimeNoContractPolicy(RuntimePolicy):
    """本文 runtime 的消融：不发版本与逻辑身份，只发值。

    远端只能按它看得见的字段防护，报文字段缺席时它退回无防护行为。这条消融把"契约字段在
    链路上市本文臂与版本化臂共同的收益来源"这件事直接测出来：去掉字段后，陈旧覆盖应当重新
    出现。
    """

    name = "ours_no_contract"

    def plan(self, view) -> list[tuple[str, dict]]:
        out = super().plan(view)
        return [(node_id, {"op": payload["op"], "profile": payload["profile"]})
                for node_id, payload in out]

# Every arm the business layer compares, in the order the result tables report them. The runtime
# is listed with the baselines because a comparison that omits it cannot say anything about it,
# which is what the first P1 round did.
BUSINESS_ARMS: dict[str, str] = {
    "local_rules": "runner:LocalRulesPolicy",
    VersionedConfigPolicy.name: "policies:VersionedConfigPolicy",
    VTCPolicy.name: "policies:VTCPolicy",
    RuntimePolicy.name: "policies:RuntimePolicy",
    RuntimeNoEvidencePolicy.name: "policies:RuntimeNoEvidencePolicy",
    RuntimeNoContractPolicy.name: "policies:RuntimeNoContractPolicy",
    "oracle": "runner:OraclePolicy",
}


def build_arm(name: str, **kwargs) -> object:
    """Instantiate one business-layer arm by name, without importing the runner eagerly.

    `runner` imports this module, so naming the two policies that live there has to be a late
    lookup rather than a top-level import.
    """
    try:
        target = BUSINESS_ARMS[name]
    except KeyError:
        raise ValueError(f"unknown arm {name!r}; have {sorted(BUSINESS_ARMS)}") from None
    module_name, _, class_name = target.partition(":")
    module = __import__(module_name)
    return getattr(module, class_name)(**kwargs)
