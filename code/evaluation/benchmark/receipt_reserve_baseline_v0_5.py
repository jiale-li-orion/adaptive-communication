#!/usr/bin/env python3
"""Ordinary receipt-aware EDF/reserve, with an explicit public input boundary.

No scenario-tree optimization, hidden outcome, or compatible-world identities
are passed to the controller. A gateway-local variant reads the same receipt
set locally; its local reads are never counted as remote requests.
"""
from __future__ import annotations

from dataclasses import dataclass

import dynamic_scenario_tree_v0_5 as tree


@dataclass(frozen=True)
class PublicReceiptContract:
    obligations: tuple[tree.Obligation, ...]
    dispatch: tuple[tuple[int, str], ...]
    satellite_times: tuple[int, ...]
    receipt_read_times: tuple[int, ...]
    query_id: str
    # In this pilot only, a positive gateway receipt certifies an eventual
    # on-time ACK. This is a MODEL ASSUMPTION, not a property of arbitrary IoT.
    receipt_secures_delivery: bool = True


@dataclass(frozen=True)
class PublicReceiptView:
    at_s: int
    delivered: tuple[str, ...]
    known_receipts: tuple[str, ...]
    last_sample_at_s: int | None
    satellite_budget: int
    in_flight_queries: tuple[str, ...]


def public_view(at_s, state, *, gateway_local=False):
    receipts = set()
    sampled = None
    for event in state.trace:
        if event[0] != 'OBS' or not str(event[2]).startswith('query:'):
            continue
        value = event[3]
        if value.startswith('gateway_received='):
            value = value.split('=', 1)[1]
            if value != 'none':
                receipts.update(value.split(','))
            sampled = max(sampled if sampled is not None else -1,
                          int(event[4].split('@')[1]))
    if gateway_local:
        receipts.update(state.gateway_received)
        sampled = at_s
    return PublicReceiptView(at_s, state.final_delivered, tuple(sorted(receipts)),
                             sampled, state.sat_budget,
                             tuple(q.query_id for q in state.pending_queries))


def common_reserve(contract, view):
    """EDF interval-to-slot matching for a common all-backup continuation.

    True is a sufficient stopping certificate here, not an optimality theorem.
    Release times, deadlines, one-use slots, and remaining budget all matter.
    """
    secured = set(view.delivered)
    if contract.receipt_secures_delivery:
        secured.update(view.known_receipts)
    work = sorted((o for o in contract.obligations if o.oid not in secured),
                  key=lambda o: (o.deadline_s, o.release_s, o.oid))
    if len(work) > view.satellite_budget:
        return False
    slots = list(t for t in contract.satellite_times if t >= view.at_s)
    for obligation in work:
        compatible = [t for t in slots
                      if obligation.release_s <= t <= obligation.deadline_s]
        if not compatible:
            return False
        slots.remove(min(compatible))
    return True


def choose_action(contract, view, *, mode='conditional'):
    t = view.at_s
    secured = set(view.delivered)
    if contract.receipt_secures_delivery:
        secured.update(view.known_receipts)
    # Ordinary business sends remain probes, without charging an extra query.
    for at, oid in contract.dispatch:
        if at == t and oid not in set(view.delivered):
            return 'SEND_TERR', oid
    if (mode != 'passive' and t in contract.receipt_read_times
            and not view.in_flight_queries
            and view.last_sample_at_s != t
            and (mode == 'fixed-read' or not common_reserve(contract, view))):
        return 'ISSUE_QUERY', contract.query_id
    if t in contract.satellite_times and view.satellite_budget:
        pending = sorted((o for o in contract.obligations
                          if o.oid not in secured and o.release_s <= t <= o.deadline_s),
                         key=lambda o: (o.deadline_s, o.oid))
        if pending:
            return 'SEND_SAT', pending[0].oid
    return 'WAIT', None


def solve_receipt_reserve(bundle, contract, *, mode='conditional', gateway_local=False):
    """Evaluate the ordinary controller on every branch, retaining failures."""
    initial = {w.world_id: tree.LocalState(sat_budget=bundle.satellite_budget)
               for w in bundle.worlds}
    results = {}

    def rec(t, states, steps=0):
        if steps > 8 * len(bundle.fixed_event_times):
            raise RuntimeError('controller did not advance')
        norm = tree._normalize(bundle, t, states)
        # Local receipt is a legitimate observation ONLY for the local controller.
        groups = {}
        for ch in norm.values():
            for wid, st in ch.items():
                view = public_view(t, st, gateway_local=gateway_local)
                groups.setdefault(view, {})[wid] = st
        for view, ch in groups.items():
            if any(tree._expired(bundle, s, t) for s in ch.values()):
                for wid, st in ch.items():
                    results[wid] = {'success': False, 'queries': st.next_request_seq,
                                    'satellite_sends': bundle.satellite_budget-st.sat_budget}
                continue
            if all(tree._success(bundle, s) for s in ch.values()):
                for wid, st in ch.items():
                    results[wid] = {'success': True, 'queries': st.next_request_seq,
                                    'satellite_sends': bundle.satellite_budget-st.sat_budget}
                continue
            action = choose_action(contract, view,
                                   mode='passive' if gateway_local else mode)
            assert action in tree._actions(bundle, t, ch), (t, action)
            stepped = tree._step_action(bundle, t, ch, action)
            if stepped is None:
                for wid, st in ch.items():
                    results[wid] = {'success': False, 'queries': st.next_request_seq,
                                    'satellite_sends': bundle.satellite_budget-st.sat_budget}
            else:
                branches, nt = stepped
                for branch in branches.values():
                    rec(nt, branch, steps+1)

    rec(min(bundle.fixed_event_times), initial)
    return {'solvable': all(x['success'] for x in results.values()),
            'worlds_solved': sum(x['success'] for x in results.values()),
            'per_world': results,
            'placement': 'gateway' if gateway_local else 'center'}
