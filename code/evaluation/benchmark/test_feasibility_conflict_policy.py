#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from feasibility_conflict_planner import choose_first_step  # noqa: E402
from scenario_generator_v0_2 import generate  # noqa: E402
from scenario_tree_oracle import solve  # noqa: E402


def main() -> int:
    rows = generate()
    decisions = Counter()
    solved = 0

    for row in rows:
        bundle = row["bundle"]
        d = choose_first_step(bundle)
        decisions[(row["kind"], d.reason_code, d.action[0])] += 1

        if d.action[0] == "QUERY":
            result = solve(
                bundle,
                allow_query=True,
                forced_first_action=("QUERY", None),
            )
        else:
            result = solve(
                bundle,
                allow_query=False,
                forced_first_action=d.action,
            )
        solved += int(result["solvable"])

    assert solved == len(rows) == 72
    assert decisions[("QUERY_REQUIRED", "RESOLVE_FEASIBILITY_CONFLICT", "QUERY")] == 24
    assert sum(
        n for (kind, reason, _), n in decisions.items()
        if kind == "QUERY_HARMFUL" and reason != "RESOLVE_FEASIBILITY_CONFLICT"
    ) == 24
    assert sum(
        n for (kind, reason, action), n in decisions.items()
        if kind == "PASSIVE_BETTER" and action == "WAIT"
    ) == 24

    print(
        "PASS conflict-guided first-step policy: 72/72 mechanism bundles solved; "
        "query only selected for the 24 genuine query-required cases"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
