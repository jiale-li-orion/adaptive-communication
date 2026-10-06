#!/usr/bin/env python3
"""Persistent conditional future-choice frontier for Layer-2 v2.

The planning kernel in :mod:`layer2_v2_future_choice` proves one causal policy
from a reached Layer-1 v0.2 boundary.  This module turns that proof into a
persistent decision object rather than discarding it after one action.

Each successful causal policy is decomposed into conditional certificates for
every reachable decision prefix.  A certificate is valid on a *resource
domain* rather than at one exact budget point:

    same non-resource execution/information boundary
    AND remaining paid-query budget >= certificate query requirement
    AND remaining satellite budget >= certificate satellite requirement.

Observation branches are indexed separately.  Hence an ACK/query response does
not force a global replan when the new boundary is already a proved child of
the carried policy.  A boundary outside all certified domains falls back to the
sound L/U + exact kernel.  This is deliberately conservative: the module never
reuses a certificate across an execution/evidence change that has not already
been represented by a causal policy branch.

The object therefore provides a first executable version of the cache06.md
"conditional frontier / validity domain / exact fallback" contract without
claiming unsafe cross-boundary equivalences.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from hashlib import sha256
import json
from time import perf_counter
from typing import Any, Mapping

from causal_evidence_process_v0_1 import attach_causal_evidence
from exact_reference_oracle_v0_1 import LocalState, _normalize
from layer1_v02_exact_continuation import replay_continuation_policy
from layer2_v2_conflict_frontier import IncrementalConflictFrontier
from layer2_v2_future_choice import FutureChoiceExactFallback
from v8_policy_baselines_v0_1 import _legal_actions, _step


Action = tuple[str, str | None]


def _common_satellite_budget(states: Mapping[str, LocalState]) -> int:
    values = {int(state.satellite_budget) for state in states.values()}
    if not states or len(values) != 1:
        raise ValueError("shared causal boundary requires one common satellite budget")
    return next(iter(values))


def _boundary_core(at_s: int, states: Mapping[str, LocalState]) -> tuple[Any, ...]:
    """Exact information/execution boundary with the monotone SAT budget removed."""

    return (
        int(at_s),
        tuple(
            sorted(
                (
                    str(world_id),
                    replace(state, satellite_budget=0),
                )
                for world_id, state in states.items()
            )
        ),
    )


def _boundary_digest(core: tuple[Any, ...]) -> str:
    return sha256(repr(core).encode("utf-8")).hexdigest()


def policy_resource_requirement(policy: Mapping[str, Any]) -> tuple[int, int]:
    """Worst-branch future (paid-query, satellite-send) requirement of a policy."""

    if policy.get("terminal"):
        return 0, 0
    if policy.get("event") == "OBSERVATION":
        rows = [policy_resource_requirement(row["subpolicy"]) for row in policy["children"]]
        return max((row[0] for row in rows), default=0), max((row[1] for row in rows), default=0)
    q, sat = policy_resource_requirement(policy["subpolicy"])
    return q + int(policy["action"] == "ISSUE_QUERY"), sat + int(policy["action"] == "SEND_SAT")


def _dependency_tokens(states: Mapping[str, LocalState]) -> tuple[str, ...]:
    """Auditable execution/evidence dependencies for a conservative certificate.

    These tokens are descriptive rather than an unsafe projection key.  Reuse is
    still gated by the exact non-resource boundary core.  Later work can prove
    coarser equivalence classes and safely remove tokens from that key.
    """

    tokens: set[str] = set()
    for world_id, state in states.items():
        tokens.add(f"world:{world_id}")
        for oid in state.delivered:
            tokens.add(f"delivered:{oid}")
        for window_id, used in state.terrestrial_used:
            tokens.add(f"terr-used:{window_id}:{used}")
        for window_id, used in state.satellite_used:
            tokens.add(f"sat-used:{window_id}:{used}")
        if state.pending_query is not None:
            tokens.add(f"pending-query:{state.pending_query.arrive_at_s}")
        if state.last_query_signature is not None:
            tokens.add(f"query-signature:{state.last_query_signature}")
        if state.last_direct_signature is not None:
            tokens.add(f"direct-signature:{state.last_direct_signature}")
        for pending in state.pending_deliveries:
            tokens.add(
                "pending-delivery:"
                f"{pending.obligation_id}:{int(pending.accepted)}:"
                f"{pending.gateway_receipt_at_s}:{pending.final_ack_at_s}:"
                f"{pending.negative_observation_at_s}:{int(pending.gateway_receipt_seen)}"
            )
    return tuple(sorted(tokens))


@dataclass(frozen=True)
class ConditionalCertificate:
    certificate_id: str
    boundary_digest: str
    boundary_core: tuple[Any, ...]
    min_query_budget: int
    min_satellite_budget: int
    policy: dict[str, Any]
    dependency_tokens: tuple[str, ...]
    source: str

    def valid_for(
        self,
        *,
        at_s: int,
        states: Mapping[str, LocalState],
        query_budget: int,
    ) -> bool:
        return (
            self.boundary_core == _boundary_core(at_s, states)
            and int(query_budget) >= self.min_query_budget
            and _common_satellite_budget(states) >= self.min_satellite_budget
        )


class PersistentFutureChoiceFrontier:
    """Maintain conditional success certificates across sequential execution."""

    def __init__(
        self,
        bundle: Mapping[str, Any],
        *,
        upper_mode: str = "all_recursive",
        use_lower: bool = True,
    ):
        self.bundle = deepcopy(bundle)
        self.process = attach_causal_evidence(self.bundle)
        self.solver = FutureChoiceExactFallback(
            self.bundle,
            upper_mode=upper_mode,
            use_lower=use_lower,
        )
        self._domains: dict[str, list[ConditionalCertificate]] = {}
        self.metrics = {
            "certificate_lookups": 0,
            "certificate_hits": 0,
            "kernel_fallbacks": 0,
            "certificates_indexed": 0,
            "dominated_certificates_skipped": 0,
        }

    def _lookup(
        self,
        at_s: int,
        states: Mapping[str, LocalState],
        query_budget: int,
    ) -> ConditionalCertificate | None:
        core = _boundary_core(at_s, states)
        digest = _boundary_digest(core)
        self.metrics["certificate_lookups"] += 1
        candidates = sorted(
            self._domains.get(digest, ()),
            key=lambda row: (row.min_query_budget + row.min_satellite_budget,
                             row.min_query_budget, row.min_satellite_budget,
                             row.certificate_id),
        )
        for certificate in candidates:
            if certificate.valid_for(
                at_s=at_s,
                states=states,
                query_budget=query_budget,
            ):
                self.metrics["certificate_hits"] += 1
                return certificate
        return None

    def lookup_certificate(
        self,
        *,
        at_s: int,
        states: Mapping[str, LocalState],
        query_budget: int,
    ) -> ConditionalCertificate | None:
        """Read-only domain lookup used by prefix/invalidation audits."""

        branches = _normalize(self.bundle, self.process, at_s, states)
        if len(branches) != 1 or next(iter(branches)) != "same":
            raise ValueError("certificate lookup requires a normalized decision boundary")
        support = next(iter(branches.values()))
        return self._lookup(at_s, support, query_budget)

    def _store_certificate(
        self,
        *,
        at_s: int,
        states: Mapping[str, LocalState],
        policy: Mapping[str, Any],
        source: str,
    ) -> ConditionalCertificate:
        core = _boundary_core(at_s, states)
        digest = _boundary_digest(core)
        min_query, min_sat = policy_resource_requirement(policy)
        payload = {
            "boundary": digest,
            "min_query": min_query,
            "min_sat": min_sat,
            "policy": policy,
        }
        certificate_id = sha256(
            json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        certificate = ConditionalCertificate(
            certificate_id=certificate_id,
            boundary_digest=digest,
            boundary_core=core,
            min_query_budget=min_query,
            min_satellite_budget=min_sat,
            policy=deepcopy(dict(policy)),
            dependency_tokens=_dependency_tokens(states),
            source=source,
        )
        rows = self._domains.setdefault(digest, [])
        # If an existing certificate needs no more of either monotone resource,
        # the new domain adds no coverage.  Keep the older witness stable.
        if any(
            row.boundary_core == core
            and row.min_query_budget <= min_query
            and row.min_satellite_budget <= min_sat
            for row in rows
        ):
            self.metrics["dominated_certificates_skipped"] += 1
            return certificate
        rows[:] = [
            row
            for row in rows
            if not (
                row.boundary_core == core
                and min_query <= row.min_query_budget
                and min_sat <= row.min_satellite_budget
            )
        ]
        rows.append(certificate)
        self.metrics["certificates_indexed"] += 1
        return certificate

    def _index_policy(
        self,
        *,
        at_s: int,
        states: Mapping[str, LocalState],
        query_budget: int,
        policy: Mapping[str, Any],
        source: str,
    ) -> None:
        """Index every causal child as a conditional validity domain."""

        branches = _normalize(self.bundle, self.process, at_s, states)
        if len(branches) != 1 or next(iter(branches)) != "same":
            if policy.get("event") != "OBSERVATION":
                raise AssertionError("policy misses a required observation branch")
            children = {str(row["observation"]): row for row in policy["children"]}
            if set(children) != set(branches):
                raise AssertionError("policy observation support mismatch")
            for observation, child in branches.items():
                entry = children[observation]
                self._index_policy(
                    at_s=at_s,
                    states=child,
                    query_budget=query_budget,
                    policy=entry["subpolicy"],
                    source=source,
                )
            return

        support = next(iter(branches.values()))
        self._store_certificate(
            at_s=at_s,
            states=support,
            policy=policy,
            source=source,
        )
        if policy.get("terminal"):
            return
        action: Action = (str(policy["action"]), policy.get("arg"))
        if action not in _legal_actions(self.bundle, self.process, support, at_s):
            raise AssertionError("certificate policy contains an illegal action")
        dq = int(action[0] == "ISSUE_QUERY")
        if dq > query_budget:
            raise AssertionError("certificate exceeds query budget")
        stepped = _step(self.bundle, self.process, support, at_s, action)
        if stepped is None:
            raise AssertionError("certificate action cannot be executed")
        child, next_t = stepped
        self._index_policy(
            at_s=next_t,
            states=child,
            query_budget=query_budget - dq,
            policy=policy["subpolicy"],
            source=source,
        )

    def ensure(
        self,
        *,
        at_s: int,
        states: Mapping[str, LocalState],
        query_budget: int,
        max_expansions: int = 200_000,
    ) -> dict[str, Any]:
        """Return a valid causal continuation, reusing a domain or falling back."""

        branches = _normalize(self.bundle, self.process, at_s, states)
        if len(branches) != 1 or next(iter(branches)) != "same":
            raise ValueError("ensure() requires a decision boundary after observation normalization")
        support = next(iter(branches.values()))
        certificate = self._lookup(at_s, support, query_budget)
        if certificate is not None:
            replay_continuation_policy(
                self.bundle,
                at_s=at_s,
                states=support,
                policy=certificate.policy,
                query_budget=query_budget,
            )
            return {
                "solvable": True,
                "source": "certificate-domain",
                "policy": deepcopy(certificate.policy),
                "certificate": certificate,
            }

        self.metrics["kernel_fallbacks"] += 1
        result = self.solver.solve(
            at_s,
            support,
            query_budget=query_budget,
            max_expansions=max_expansions,
        )
        if result["solvable"] is not True:
            return {
                "solvable": result["solvable"],
                "source": "kernel-fallback",
                "policy": result.get("policy"),
                "certificate": None,
                "kernel": result,
            }
        replay_continuation_policy(
            self.bundle,
            at_s=at_s,
            states=support,
            policy=result["policy"],
            query_budget=query_budget,
        )
        self._index_policy(
            at_s=at_s,
            states=support,
            query_budget=query_budget,
            policy=result["policy"],
            source="kernel-fallback",
        )
        certificate = self._lookup(at_s, support, query_budget)
        if certificate is None:
            raise AssertionError("newly indexed policy is not reusable at its source boundary")
        return {
            "solvable": True,
            "source": "kernel-fallback",
            "policy": deepcopy(result["policy"]),
            "certificate": certificate,
            "kernel": result,
        }

    def exact_action_frontier(
        self,
        *,
        at_s: int,
        states: Mapping[str, LocalState],
        query_budget: int,
    ) -> dict[str, bool | None]:
        """Persistent exact action-feasibility frontier using certificate reuse."""

        branches = _normalize(self.bundle, self.process, at_s, states)
        if len(branches) != 1 or next(iter(branches)) != "same":
            raise ValueError("frontier requires a normalized decision boundary")
        support = next(iter(branches.values()))
        out: dict[str, bool | None] = {}
        for action in _legal_actions(self.bundle, self.process, support, at_s):
            dq = int(action[0] == "ISSUE_QUERY")
            key = f"{action[0]}:{action[1] if action[1] is not None else '-'}"
            if dq > query_budget:
                out[key] = False
                continue
            stepped = _step(self.bundle, self.process, support, at_s, action)
            if stepped is None:
                out[key] = False
                continue
            child, next_t = stepped
            # If the action immediately produces an observation at next_t,
            # exact feasibility requires every resulting branch to remain
            # solvable.  The kernel handles that AND condition.
            result = self.solver.solve(
                next_t,
                child,
                query_budget=query_budget - dq,
            )
            if result["solvable"] is True:
                replay_continuation_policy(
                    self.bundle,
                    at_s=next_t,
                    states=child,
                    policy=result["policy"],
                    query_budget=query_budget - dq,
                )
                self._index_policy(
                    at_s=next_t,
                    states=child,
                    query_budget=query_budget - dq,
                    policy=result["policy"],
                    source=f"action-frontier:{key}",
                )
            out[key] = result["solvable"]
        return out

    def _certify_post_action(
        self,
        *,
        at_s: int,
        states: Mapping[str, LocalState],
        query_budget: int,
    ) -> tuple[bool, list[str]]:
        """Check whether every immediate observation branch has a valid certificate."""

        branches = _normalize(self.bundle, self.process, at_s, states)
        certificate_ids: list[str] = []
        if len(branches) == 1 and next(iter(branches)) == "same":
            support = next(iter(branches.values()))
            certificate = self._lookup(at_s, support, query_budget)
            if certificate is None:
                return False, []
            return True, [certificate.certificate_id]
        for child in branches.values():
            certificate = self._lookup(at_s, child, query_budget)
            if certificate is None:
                return False, []
            certificate_ids.append(certificate.certificate_id)
        return True, certificate_ids

    def build_frontier(
        self,
        *,
        at_s: int,
        states: Mapping[str, LocalState],
        query_budget: int,
        max_expansions: int = 200_000,
    ) -> dict[str, Any]:
        """Build the exact live action-feasibility frontier with shared reuse.

        This is the Layer-2 compiler-facing operation.  Existing conditional
        certificates are checked first.  Only unresolved post-action boundaries
        invoke the shared L/U + exact kernel; successful fallbacks are indexed
        immediately for later events/actions.
        """

        branches = _normalize(self.bundle, self.process, at_s, states)
        if len(branches) != 1 or next(iter(branches)) != "same":
            raise ValueError("build_frontier requires a normalized decision boundary")
        support = next(iter(branches.values()))
        before_solver = self.solver.metrics.as_dict()
        before_runtime = dict(self.metrics)
        started = perf_counter()
        actions: dict[str, dict[str, Any]] = {}
        for action in _legal_actions(self.bundle, self.process, support, at_s):
            dq = int(action[0] == "ISSUE_QUERY")
            key = f"{action[0]}:{action[1] if action[1] is not None else '-'}"
            if dq > query_budget:
                actions[key] = {"solvable": False, "source": "query-budget"}
                continue
            stepped = _step(self.bundle, self.process, support, at_s, action)
            if stepped is None:
                actions[key] = {"solvable": False, "source": "illegal-step"}
                continue
            child, next_t = stepped
            certified, certificate_ids = self._certify_post_action(
                at_s=next_t,
                states=child,
                query_budget=query_budget - dq,
            )
            if certified:
                actions[key] = {
                    "solvable": True,
                    "source": "certificate-domain",
                    "certificate_ids": certificate_ids,
                }
                continue

            self.metrics["kernel_fallbacks"] += 1
            result = self.solver.solve(
                next_t,
                child,
                query_budget=query_budget - dq,
                max_expansions=max_expansions,
            )
            if result["solvable"] is True:
                replay_continuation_policy(
                    self.bundle,
                    at_s=next_t,
                    states=child,
                    policy=result["policy"],
                    query_budget=query_budget - dq,
                )
                self._index_policy(
                    at_s=next_t,
                    states=child,
                    query_budget=query_budget - dq,
                    policy=result["policy"],
                    source=f"frontier-fallback:{key}",
                )
            actions[key] = {
                "solvable": result["solvable"],
                "source": "kernel-fallback",
            }

        elapsed = perf_counter() - started
        after_solver = self.solver.metrics.as_dict()
        after_runtime = dict(self.metrics)
        return {
            "actions": actions,
            "wall_s": elapsed,
            "solver_delta": {
                key: after_solver[key] - before_solver[key]
                for key in after_solver
            },
            "runtime_delta": {
                key: after_runtime[key] - before_runtime[key]
                for key in after_runtime
            },
        }

    def inventory(self) -> dict[str, Any]:
        certificates = [row for rows in self._domains.values() for row in rows]
        return {
            "boundary_domain_count": len(self._domains),
            "certificate_count": len(certificates),
            "query_requirement_histogram": {
                str(value): sum(row.min_query_budget == value for row in certificates)
                for value in sorted({row.min_query_budget for row in certificates})
            },
            "satellite_requirement_histogram": {
                str(value): sum(row.min_satellite_budget == value for row in certificates)
                for value in sorted({row.min_satellite_budget for row in certificates})
            },
            "metrics": dict(self.metrics),
        }
