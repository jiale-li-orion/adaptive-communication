#!/usr/bin/env python3
"""UAV domain adapter for the generic :class:`FutureChoiceEngine`.

The adapter owns routing-specific transition/certificate semantics only.  The
generic engine owns carried-certificate → U=0 → L=1 → exact-fallback ordering.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Any

from future_choice_engine import FutureChoiceCertificate
from run_uav_attention_future_choice_lu import FutureChoiceRouteFrontier


def _cid(prefix: str, witness: Any) -> str:
    return sha256((prefix + repr(witness)).encode()).hexdigest()[:20]


class UAVFutureChoiceAdapter:
    def __init__(self, frontier: FutureChoiceRouteFrontier):
        self.front = frontier
        self.metrics = {
            "exact_new_states": 0,
            "lower_calls": 0,
            "exact_calls": 0,
            "carried_validations": 0,
        }

    def action_key(self, action: int):
        return int(action)

    def _state(self, context):
        return self.front.state(context)

    def _child(self, context, action: int):
        return self.front.post(self._state(context), int(action))

    def optimistic_possible(self, context, action: int) -> bool:
        child = self._child(context, action)
        return child is not None and self.front.upper_possible(child)

    def carried_certificate_valid(
        self,
        context,
        action: int,
        certificate: FutureChoiceCertificate,
    ) -> bool:
        self.metrics["carried_validations"] += 1
        route = tuple(certificate.witness["route"])
        if not route or int(route[0]) != int(action):
            return False
        state = self._state(context)
        for a in route:
            state = self.front.post(state, int(a))
            if state is None:
                return False
        return state.visited == self.front.all_mask and state.current == 0

    @staticmethod
    def _cert(action: int, route_tail: tuple[int, ...], source: str):
        route = (int(action), *map(int, route_tail))
        witness = {"route": route, "source": source}
        return FutureChoiceCertificate(
            _cid("uav", witness),
            witness,
            frozenset({"route_state", "battery", "elapsed_time", "deadlines"}),
        )

    def lower_certificate(self, context, action: int):
        self.metrics["lower_calls"] += 1
        child = self._child(context, action)
        if child is None:
            return None
        route = self.front.bounded_lower_certificate(child)
        return None if route is None else self._cert(action, route, "bounded-lower")

    def exact_certificate(self, context, action: int):
        self.metrics["exact_calls"] += 1
        child = self._child(context, action)
        if child is None:
            return None
        route, new = self.front.exact_with_delta(child)
        self.metrics["exact_new_states"] += int(new)
        return None if route is None else self._cert(action, route, "exact")

    def carry_after_commit(
        self,
        context,
        action: int,
        certificate: FutureChoiceCertificate,
    ):
        route = tuple(certificate.witness["route"])
        if not route or int(route[0]) != int(action):
            return None
        suffix = route[1:]
        if not suffix:
            return None
        witness = {"route": suffix, "source": "carried-suffix"}
        return FutureChoiceCertificate(
            _cid("uav-carry", witness),
            witness,
            certificate.dependencies,
        )
