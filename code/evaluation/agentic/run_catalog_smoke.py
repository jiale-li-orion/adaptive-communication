#!/usr/bin/env python3
"""Run one paired R3 smoke for every O1--O6 Operational Task family."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
ROOT = CODE.parent
for p in (
    CODE,
    CODE / "substrate" / "joint",
    CODE / "substrate" / "instance",
    CODE / "substrate" / "monitoring",
    CODE / "substrate" / "physics",
    CODE / "substrate" / "runtime",
    CODE / "evaluation" / "agentic",
    CODE / "legacy-communication" / "analysis",
):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from agentic_communication.episodes import benchmark_episode_catalog  # noqa: E402
from agentic_communication.metrics import physical_signature  # noqa: E402
from agentic_communication.planner import DeterministicComplyPlannerConsumer  # noqa: E402
from agentic_communication.run import run_agentic_episode, run_reference_comply  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument(
        "--out",
        default=str(ROOT / "results" / "agentic" / "catalog-smoke-v1.json"),
    )
    args = ap.parse_args()
    rows = []
    all_equal = True
    for key, template in benchmark_episode_catalog().items():
        ref, _, _ = run_reference_comply(
            seed=args.seed,
            operational_task=template.task,
            simulator_kwargs=template.simulator_overrides,
        )
        cur, policy, _, _ = run_agentic_episode(
            seed=args.seed,
            operational_task=template.task,
            planner_consumer=DeterministicComplyPlannerConsumer(),
            simulator_kwargs=template.simulator_overrides,
        )
        equal = physical_signature(ref) == physical_signature(cur)
        all_equal = all_equal and equal
        rows.append(
            {
                "template": key,
                "task_id": template.task.task_id,
                "family": template.task.family.value,
                "physical_equal_legacy_comply": equal,
                "difficulty_axes": template.difficulty_axes,
                "communication_metrics": cur["agentic"]["communication_metrics"],
                "agent_metrics": cur["agentic"]["agent_metrics"],
            }
        )
    payload = {
        "experiment_id": "agentic-task-catalog-smoke-v1",
        "seed": args.seed,
        "status": "PASS" if all_equal else "FAIL",
        "claim_ceiling": (
            "Infrastructure conformance only: O1-O6 compile and execute through the same typed "
            "live planner/runtime without changing legacy-comply physical behavior."
        ),
        "rows": rows,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if all_equal else 1


if __name__ == "__main__":
    raise SystemExit(main())
