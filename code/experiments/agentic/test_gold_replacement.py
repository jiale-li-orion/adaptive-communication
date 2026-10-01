#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(os.path.dirname(HERE))
if CODE not in sys.path:
    sys.path.insert(0, CODE)

from agentic_communication.gold_replacement import apply_gold_replacement  # noqa: E402
from agentic_communication.trajectory_eval import (  # noqa: E402
    CapabilityStep,
    GoldReplacementLayer,
    trajectory_metrics,
)


def step(cid: str, resource: str, target: int) -> CapabilityStep:
    return CapabilityStep(cid, cid, resource, {"target_s": target})


def main() -> int:
    gold = [
        step("communication.config.set_sampling_interval", "n01", 300),
        step("communication.config.set_report_period", "n01", 300),
    ]
    # Candidate chooses the wrong second tool and wrong arguments for the first.
    candidate = [
        step("communication.config.set_sampling_interval", "n02", 600),
        step("communication.fallback.gateway_backup", "gw0", 0),
    ]
    base = trajectory_metrics(candidate, gold)
    selection = apply_gold_replacement(
        candidate, gold, [GoldReplacementLayer.CAPABILITY_SELECTION]
    )
    assert selection.executable is False
    assert selection.unresolved_argument_slots == (1,)
    # Gold selection fixes identities but deliberately leaves the newly selected
    # report-period slot without fabricated arguments.
    sel_score = trajectory_metrics(list(selection.steps), gold)
    assert sel_score["tool_any_order_recall"] == 1.0
    assert sel_score["argument_grounding_accuracy"] < 1.0

    with_args = apply_gold_replacement(
        candidate,
        gold,
        [
            GoldReplacementLayer.CAPABILITY_SELECTION,
            GoldReplacementLayer.CAPABILITY_ORDER,
            GoldReplacementLayer.CAPABILITY_ARGUMENTS,
        ],
    )
    assert with_args.executable
    fixed = trajectory_metrics(list(with_args.steps), gold)
    assert fixed["tool_exact_match"] is True
    assert fixed["argument_grounding_accuracy"] == 1.0
    assert base["tool_exact_match"] is False
    print("PASS gold replacement: selection/order/arguments remain separately attributable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
