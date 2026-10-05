#!/usr/bin/env python3
"""Causal continuation witnesses with reusable query/satellite resource domains.

Three modes share one AND/OR search: exact memo, ordinary resource-monotone
memo, and policy-witness-tightened domains. This is a method prototype, not a
replacement generator/oracle label pipeline or a claim of algorithmic novelty.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from hashlib import sha256
import json
from time import perf_counter
from typing import Any

from causal_evidence_process_v0_1 import attach_causal_evidence
from exact_reference_oracle_v0_1 import LocalState, _normalize, _expired, _success
from v8_policy_baselines_v0_1 import _legal_actions, _step


MODES = ('exact_memo', 'monotone_memo', 'witness_domain')


@dataclass(frozen=True)
class Witness:
    queries: int
    satellite: int
    policy: dict[str, Any]

    @property
    def requirement(self):
        return (self.queries, self.satellite)


class ExpansionLimit(RuntimeError):
    pass


def _leq(a, b):
    return a[0] <= b[0] and a[1] <= b[1]


def _boundary(t, states):
    # Retain all execution/information state except the one monotone physical
    # budget. Time, support and pending operations are part of this boundary.
    return (t, tuple(sorted((wid, replace(st, satellite_budget=0)) for wid, st in states.items())))


def _common_budget(states):
    budgets = {st.satellite_budget for st in states.values()}
    if len(budgets) != 1 or not states:
        raise ValueError('shared action history requires a nonempty support with common SAT budget')
    budget = next(iter(budgets))
    if budget < 0:
        raise ValueError('negative budget')
    return budget


class ContinuationPlanner:
    """One immutable process session; explicit boundaries prevent stale reuse."""

    def __init__(self, bundle, *, mode='witness_domain', observer=None, separator_key_fn=None):
        if mode not in MODES:
            raise ValueError(mode)
        self.bundle = deepcopy(bundle)
        self.process = attach_causal_evidence(self.bundle)
        if self.process['direct_observation']:
            raise ValueError('direct-current-state observations expose budget; transfer not supported')
        self.mode = mode
        self.observer = observer
        self.separator_key_fn = separator_key_fn
        self.process_digest = sha256(json.dumps(self.bundle, sort_keys=True).encode()).hexdigest()
        self._memo = {}
        self._success_domains = {}
        self._failure_domains = {}
        self._separator_success = {}
        self.counts = dict(expanded=0, exact_hits=0, domain_hits=0, negative_domain_hits=0,
                           domain_comparisons=0, recursive_calls=0,
                           separator_hits=0, separator_replay_checks=0,
                           separator_replay_failures=0, separator_replay_wall_s=0.0,
                           separator_comparisons=0)

    def _lookup(self, boundary, resources):
        full = (boundary, resources)
        if full in self._memo:
            self.counts['exact_hits'] += 1
            return True, self._memo[full]
        if self.mode == 'exact_memo':
            return False, None
        for requirement, witness in self._success_domains.get(boundary, ()):
            self.counts['domain_comparisons'] += 1
            if _leq(requirement, resources):
                self.counts['domain_hits'] += 1
                return True, witness
        for upper in self._failure_domains.get(boundary, ()):
            self.counts['domain_comparisons'] += 1
            if _leq(resources, upper):
                self.counts['negative_domain_hits'] += 1
                return True, None
        return False, None

    def _store(self, boundary, resources, witness):
        self._memo[(boundary, resources)] = witness
        if self.mode == 'exact_memo':
            return
        if witness is None:
            rows = self._failure_domains.setdefault(boundary, [])
            if any(_leq(resources, upper) for upper in rows):
                return
            rows[:] = [upper for upper in rows if not _leq(upper, resources)]
            rows.append(resources)
        else:
            requirement = witness.requirement if self.mode == 'witness_domain' else resources
            rows = self._success_domains.setdefault(boundary, [])
            if any(_leq(lower, requirement) for lower, _ in rows):
                return
            rows[:] = [(lower, w) for lower, w in rows if not _leq(requirement, lower)]
            rows.append((requirement, witness))

    def _store_separator_success(self, t, support, witness):
        if self.separator_key_fn is None or witness is None:
            return
        key = self.separator_key_fn(t, support)
        rows = self._separator_success.setdefault(key, [])
        digest = sha256(json.dumps(witness.policy, sort_keys=True).encode()).hexdigest()
        if any(row[2] == digest for row in rows):
            return
        # Keep multiple policies even when one resource requirement dominates
        # another.  Under a compressed boundary, replay validity can differ.
        rows.append((witness.requirement, witness, digest))

    def _lookup_separator_success(self, t, support, remaining_q, resources):
        if self.separator_key_fn is None:
            return False, None
        key = self.separator_key_fn(t, support)
        rows = self._separator_success.get(key, ())
        for requirement, witness, _digest in sorted(rows, key=lambda x: (sum(x[0]), x[0], x[2])):
            self.counts['separator_comparisons'] += 1
            if not _leq(requirement, resources):
                continue
            self.counts['separator_replay_checks'] += 1
            started = perf_counter()
            try:
                actual = verify_witness(
                    self.bundle, t, dict(support), witness.policy,
                    query_budget=remaining_q,
                )
            except Exception:
                self.counts['separator_replay_failures'] += 1
                self.counts['separator_replay_wall_s'] += perf_counter() - started
                continue
            self.counts['separator_replay_wall_s'] += perf_counter() - started
            actual_requirement = (int(actual[0]), int(actual[1]))
            if not _leq(actual_requirement, resources):
                self.counts['separator_replay_failures'] += 1
                continue
            self.counts['separator_hits'] += 1
            return True, Witness(actual_requirement[0], actual_requirement[1], witness.policy)
        return False, None

    def solve(self, at_s: int, states: dict[str, LocalState], *, query_budget: int,
              max_expansions: int = 50000):
        if query_budget < 0 or max_expansions < 0:
            raise ValueError('negative search/resource limit')
        _common_budget(states)
        if not set(states) <= {w['world_id'] for w in self.bundle['worlds']}:
            raise ValueError('unknown world support')
        before = dict(self.counts)
        started = perf_counter()

        def rec(t, support, remaining_q):
            self.counts['recursive_calls'] += 1
            branches = _normalize(self.bundle, self.process, t, support)
            if len(branches) != 1 or next(iter(branches)) != 'same':
                children = []; q = s = 0
                for observation, child in sorted(branches.items()):
                    witness = rec(t, child, remaining_q)
                    if witness is None:
                        return None
                    q = max(q, witness.queries); s = max(s, witness.satellite)
                    children.append(dict(observation=observation, worlds=sorted(child),
                                         subpolicy=witness.policy))
                return Witness(q, s, dict(time_s=t, event='OBSERVATION', children=children))
            support = next(iter(branches.values()))
            boundary = _boundary(t, support)
            resources = (remaining_q, _common_budget(support))
            if self.observer is not None:
                self.observer(t, support, remaining_q)
            found, witness = self._lookup(boundary, resources)
            if found:
                return witness
            found, witness = self._lookup_separator_success(t, support, remaining_q, resources)
            if found:
                self._store(boundary, resources, witness)
                return witness
            if any(_expired(self.bundle, st, t) for st in support.values()):
                self._store(boundary, resources, None)
                return None
            if all(_success(self.bundle, st) for st in support.values()):
                return Witness(0, 0, {'terminal': True})
            if self.counts['expanded'] - before['expanded'] >= max_expansions:
                raise ExpansionLimit()
            self.counts['expanded'] += 1
            for action in _legal_actions(self.bundle, self.process, support, t):
                dq = int(action[0] == 'ISSUE_QUERY')
                ds = int(action[0] == 'SEND_SAT')
                if dq > remaining_q:
                    continue
                stepped = _step(self.bundle, self.process, support, t, action)
                if stepped is None:
                    continue
                child, next_t = stepped
                continuation = rec(next_t, child, remaining_q - dq)
                if continuation is None:
                    continue
                witness = Witness(dq + continuation.queries, ds + continuation.satellite,
                                  dict(time_s=t, action=action[0], arg=action[1],
                                       worlds=sorted(support), subpolicy=continuation.policy))
                assert _leq(witness.requirement, resources)
                self._store(boundary, resources, witness)
                self._store_separator_success(t, support, witness)
                return witness
            self._store(boundary, resources, None)
            return None

        try:
            witness = rec(at_s, dict(states), query_budget)
            status = 'EXACT'; solvable = witness is not None
        except ExpansionLimit:
            witness = None; status = 'SEARCH_LIMIT'; solvable = None
        # Returning a copy prevents callers from corrupting stored certificates.
        policy = deepcopy(witness.policy) if witness is not None else None
        elapsed = perf_counter() - started
        metrics = {k: self.counts[k] - before[k] for k in before}
        metrics.update(wall_s=elapsed, memo_entries=len(self._memo))
        return dict(status=status, solvable=solvable,
                    requirement=list(witness.requirement) if witness else None,
                    policy=policy, metrics=metrics,
                    context=dict(can_stop_acquiring=(witness.queries == 0) if witness else None,
                                 requirement=list(witness.requirement) if witness else None,
                                 completeness='one certified continuation, not all optimal actions',
                                 validity='same time/support/non-budget execution state and process',
                                 process_digest=self.process_digest))


def verify_witness(bundle, at_s, states, policy, *, query_budget):
    """Replay a certificate in the target budgets, not its construction budgets.

    Reuses the declared transition kernel, independently traverses the policy,
    checks every compatible observation branch and counts actual future actions.
    This checks transfer soundness; it is not independent physical validation of
    the shared transition model (the Layer-1 evaluator owns that separately).
    """
    process = attach_causal_evidence(bundle)

    def visit(t, support, node, qleft):
        branches = _normalize(bundle, process, t, support)
        if len(branches) != 1 or next(iter(branches)) != 'same':
            assert node.get('event') == 'OBSERVATION' and node['time_s'] == t
            children = {r['observation']: r for r in node['children']}
            assert set(children) == set(branches)
            costs = []
            for obs, child in branches.items():
                entry = children[obs]
                assert entry['worlds'] == sorted(child)
                costs.append(visit(t, child, entry['subpolicy'], qleft))
            return [max(p[0] for p in costs), max(p[1] for p in costs)]
        support = next(iter(branches.values()))
        assert not any(_expired(bundle, st, t) for st in support.values())
        if node.get('terminal'):
            assert all(_success(bundle, st) for st in support.values())
            return [0, 0]
        assert node['time_s'] == t and node['worlds'] == sorted(support)
        action = (node['action'], node['arg'])
        assert action in _legal_actions(bundle, process, support, t)
        dq = int(action[0] == 'ISSUE_QUERY'); ds = int(action[0] == 'SEND_SAT')
        assert dq <= qleft
        stepped = _step(bundle, process, support, t, action)
        assert stepped is not None
        child, next_t = stepped
        q, s = visit(next_t, child, node['subpolicy'], qleft - dq)
        return [dq + q, ds + s]

    return visit(at_s, dict(states), policy, query_budget)
