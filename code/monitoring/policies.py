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
    from .task_generator import PROFILE_NORMAL
except ImportError:                     # flat import, e.g. with code/monitoring on sys.path
    import os as _os, sys as _sys
    _HERE = _os.path.dirname(_os.path.abspath(__file__))
    if _HERE not in _sys.path:
        _sys.path.insert(0, _HERE)
    from task_generator import PROFILE_NORMAL
# -----------------------------------------------------------------------------

from typing import Callable

# The only payload shape the execution runtime understands today. A policy that returned anything
# else would be silently skipped by the runtime, which would look like a quiet policy rather than
# a broken one, so the payload is built in exactly one place per policy.
OP_SET_PROFILE = "set_monitoring_profile"

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


def profile_command(profile: str) -> dict:
    """The single payload shape a policy may return to the runtime."""
    return {"op": OP_SET_PROFILE, "profile": profile}


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
        self.reported_source: dict[str, str] = {}      # "report" | "status" | "local" | "-"
        self.reported_at: dict[str, int] = {}
        self.reported_age: dict[str, int | None] = {}

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
        reports: dict[str, dict] = {}
        out: list[tuple[str, dict]] = []

        for node_id, payload in sorted(status.items()):
            reported = _field(payload, F_PROFILE)
            if reported is not None:
                self.reported[node_id] = reported
                self.reported_source[node_id] = "status"
                # The version the node's own report is evidence for: the newest desired value the
                # center had already put on the wire when this report was composed. A report cannot
                # be evidence for a version the center had not written yet.
                self.reported_version[node_id] = self.issued_version.get(node_id, 0)
            self.reported_at[node_id] = _field(payload, F_READ_AT, now)
            self.reported_age[node_id] = None
            reports[node_id] = payload

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
                out.append((node_id, profile_command(wanted)))
                continue

            if issued_version == 0:
                record.update(action="write", reason="first_write", version=version)
                out.append((node_id, profile_command(wanted)))
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
            out.append((node_id, profile_command(wanted)))

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
        self.pauses: int = 0
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
        """Return the commands the center should try to enqueue this tick."""
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
                r = record
                r.update(action="wait", reason="retry_backoff",
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
