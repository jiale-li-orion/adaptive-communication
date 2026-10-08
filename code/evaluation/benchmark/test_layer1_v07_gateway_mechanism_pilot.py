#!/usr/bin/env python3
"""Unit tests for staged gateway-local pilot classification."""
from __future__ import annotations

import audit_layer1_v07_gateway_mechanism_pilot as pilot


def ref(status: str, solvable: bool | None) -> dict:
    return {
        "status": status,
        "solvable": solvable,
        "memo_nodes": 1,
        "attempt_lattice_size": 2,
    }


def run(sequence: dict[str, dict]):
    calls = []
    original = pilot.solve_gateway_reference

    def fake(_base, _case, name, *, max_memo_nodes):
        assert max_memo_nodes == 7
        calls.append(name)
        return sequence[name]

    pilot.solve_gateway_reference = fake
    try:
        result = pilot.staged_disposition({}, {}, max_memo_nodes=7)
    finally:
        pilot.solve_gateway_reference = original
    return result, calls


def main() -> int:
    (disposition, _refs, decisive), calls = run(
        {"blind_open_loop": ref("EXACT", True)}
    )
    assert disposition == "BLIND_OPEN_LOOP_SOLVED"
    assert decisive == "blind_open_loop"
    assert calls == ["blind_open_loop"]

    (disposition, _refs, decisive), calls = run(
        {"blind_open_loop": ref("SEARCH_LIMIT", None)}
    )
    assert disposition == "UNRESOLVED_COMPUTATION"
    assert decisive == "blind_open_loop"
    assert calls == ["blind_open_loop"]

    (disposition, _refs, decisive), calls = run(
        {
            "blind_open_loop": ref("EXACT", False),
            "full_current": ref("EXACT", False),
        }
    )
    assert disposition == "FULL_CURRENT_CAUSAL_INFEASIBLE"
    assert decisive == "full_current"
    assert calls == ["blind_open_loop", "full_current"]

    (disposition, _refs, decisive), calls = run(
        {
            "blind_open_loop": ref("EXACT", False),
            "full_current": ref("EXACT", True),
            "natural_feedback": ref("EXACT", True),
        }
    )
    assert disposition == "GATEWAY_NATURAL_FEEDBACK_REQUIRED_CANDIDATE"
    assert decisive == "natural_feedback"
    assert calls == ["blind_open_loop", "full_current", "natural_feedback"]

    (disposition, _refs, decisive), _calls = run(
        {
            "blind_open_loop": ref("EXACT", False),
            "full_current": ref("EXACT", True),
            "natural_feedback": ref("EXACT", False),
        }
    )
    assert disposition == "INFORMATION_INFEASIBLE_UNDER_GATEWAY_HISTORY"
    assert decisive == "natural_feedback"

    print("PASS v0.7 gateway pilot: staged dispositions and SEARCH_LIMIT boundary are exact")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
