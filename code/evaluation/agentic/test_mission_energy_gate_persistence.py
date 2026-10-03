#!/usr/bin/env python3
"""Regression: one-shot mission energy admission persists for a Task revision."""
from __future__ import annotations

from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
for p in (CODE, CODE / "substrate" / "instance", CODE / "substrate" / "joint"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from center import CenterView, SocObservationModel  # noqa: E402
from mission_policy import MissionChangePolicy  # noqa: E402


def view(t_s: int, soc: float, sample: int, report: int) -> CenterView:
    return CenterView(
        t_s=t_s,
        node_ids=("n0",),
        reports={
            "n0": {
                "soc_wh": soc,
                "read_at": t_s,
                "sample_interval_s": sample,
                "report_period_s": report,
            }
        },
        report_at={"n0": t_s},
        newest_taken_at={"n0": t_s},
        in_flight=frozenset(),
        soc_model=SocObservationModel(),
    )


def target_period(cmds) -> set[int]:
    out = set()
    for _nid, payload in cmds:
        if "interval_s" in payload:
            out.add(int(payload["interval_s"]))
        if "period_s" in payload:
            out.add(int(payload["period_s"]))
    return out


def main() -> int:
    schedule = [(0, 3600, "blue"), (3600, 300, "yellow"), (7200, 3600, "blue")]

    low = MissionChangePolicy(
        schedule,
        mode="energy_gate",
        healthy_wh=0.02,
        send_when_unknown=False,
        dwell_s=0,
    )
    # Before revision: already at target, no command.
    assert low.plan(view(0, 0.01, 3600, 3600)) == []
    # First densification revision is rejected.
    assert low.plan(view(3600, 0.01, 3600, 3600)) == []
    assert low.refusals and low.refusals[-1][0:2] == ("n0", 300)
    # Repeated planner ticks in the same Task revision must remain sparse.
    assert low.plan(view(3660, 0.01, 3600, 3600)) == []
    assert low.plan(view(5400, 0.01, 3600, 3600)) == []
    # Downgrade revision remains ordinary and leaves the sparse target unchanged.
    assert low.plan(view(7200, 0.01, 3600, 3600)) == []

    high = MissionChangePolicy(
        schedule,
        mode="energy_gate",
        healthy_wh=0.02,
        send_when_unknown=False,
        dwell_s=0,
    )
    assert high.plan(view(0, 0.03, 3600, 3600)) == []
    first = high.plan(view(3600, 0.03, 3600, 3600))
    assert target_period(first) == {300}, first
    # Until confirmation, retries preserve exactly the same dense target.
    retry = high.plan(view(3660, 0.03, 3600, 3600))
    assert target_period(retry) == {300}, retry
    # Once confirmed, no more command is needed.
    assert high.plan(view(5400, 0.03, 300, 300)) == []
    print("PASS mission energy_gate: rejection/acceptance persists across the Task revision")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
