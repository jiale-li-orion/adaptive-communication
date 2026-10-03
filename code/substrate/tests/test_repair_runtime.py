#!/usr/bin/env python3
"""Repair-runtime ordinary baselines: information contract + budget semantics."""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(HERE)
V3 = os.path.join(CODE, "v3joint")
if V3 not in sys.path:
    sys.path.insert(0, V3)

from repair_runtime import (  # noqa: E402
    BackupDemand, BackupRepairView, AccessRepairView,
    HealthFirstBudget, QueueAwareBudget, DeadlinePressureBudget, MinOnDeadlinePressureBudget,
    AccessHealthBudget,
)


def view(*, now=0, primary=False, demands=(), rate=1200, cap=58):
    return BackupRepairView(now_s=now, tick_s=60, primary_available=primary,
                            live_demands=tuple(demands), base_rate_s=rate,
                            base_payload_bytes=cap)


def main():
    # health-first spends whenever the current primary path is down, even with an empty queue.
    h = HealthFirstBudget(120)
    assert h.decide(view(primary=False)) is True
    assert h.decide(view(now=60, primary=False)) is True
    assert h.decide(view(now=120, primary=False)) is False
    assert h.summary()["active_s"] == 120
    assert h.summary()["activation_episodes"] == 1

    # queue-aware does not pay while there is no still-live work.
    q = QueueAwareBudget(120)
    assert q.decide(view(primary=False)) is False
    assert q.decide(view(now=60, primary=False,
                         demands=(BackupDemand(600, 6),))) is True
    assert q.summary()["remaining_s"] == 60
    assert q.summary()["activation_episodes"] == 1

    # Primary-up is a hard no-op for all ordinary failover controllers.
    for cls in (HealthFirstBudget, QueueAwareBudget, DeadlinePressureBudget):
        c = cls(120)
        assert c.decide(view(primary=True, demands=(BackupDemand(600, 1000),))) is False
        assert c.summary()["active_s"] == 0

    # Deadline-pressure: one 6B sample by t=1200 fits one 58B base opportunity at t=1200.
    d = DeadlinePressureBudget(600)
    assert d.decide(view(now=601, primary=False,
                         demands=(BackupDemand(1200, 6),))) is False

    # 60B due at t=1200 cannot fit the one remaining 58B opportunity -> boost.
    d = DeadlinePressureBudget(600)
    assert d.decide(view(now=601, primary=False,
                         demands=(BackupDemand(1200, 60),))) is True
    assert d.summary()["active_s"] == 60
    assert d.summary()["activation_episodes"] == 1

    # Episode accounting distinguishes fragmented minute-ticks from one continuous activation.
    d = DeadlinePressureBudget(300)
    hard = view(now=601, primary=False, demands=(BackupDemand(1200, 60),))
    easy = view(now=660, primary=False, demands=(BackupDemand(1200, 6),))
    hard2 = view(now=721, primary=False, demands=(BackupDemand(1200, 60),))
    assert d.decide(hard) is True
    assert d.decide(easy) is False
    assert d.decide(hard2) is True
    assert d.summary()["activation_episodes"] == 2

    # A standard min-on timer holds the boost without new evidence or prediction.
    m = MinOnDeadlinePressureBudget(600, min_on_s=180)
    assert m.decide(hard) is True          # pressure trigger
    assert m.decide(easy) is True          # held on despite no pressure
    assert m.decide(easy) is True          # third 60s tick completes the 180s minimum
    assert m.decide(easy) is False
    assert m.summary()["active_s"] == 180
    assert m.summary()["activation_episodes"] == 1
    assert m.summary()["min_on_s"] == 180

    # Two deadlines: capacity is checked cumulatively in EDF order, not item-by-item.
    d = DeadlinePressureBudget(600)
    ds = (BackupDemand(1200, 40), BackupDemand(2400, 80))
    # by 1200: 40 <= 58; by 2400: 120 <= 116 -> pressure exists.
    assert d.decide(view(now=601, primary=False, demands=ds)) is True

    # No future/outage-duration field exists in the legal view by construction.
    names = set(BackupRepairView.__dataclass_fields__)
    forbidden = {"future_outage", "outage_end_s", "node_cache", "future_harvest", "truth"}
    assert not (names & forbidden), names & forbidden

    a = AccessHealthBudget(120)
    assert a.decide(AccessRepairView(now_s=0, tick_s=60, access_available=True)) is False
    assert a.decide(AccessRepairView(now_s=60, tick_s=60, access_available=False)) is True
    assert a.summary()["active_s"] == 60

    print("PASS repair-runtime ordinary baselines / legal view / budget semantics")


if __name__ == "__main__":
    main()
