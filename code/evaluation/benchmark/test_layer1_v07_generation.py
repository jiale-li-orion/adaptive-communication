#!/usr/bin/env python3
"""Cross-version semantic regressions for the v0.7 pre-oracle generator."""
from __future__ import annotations

import generate_layer1_v06_cases as v06
import generate_layer1_v07_cases as v07


def main() -> int:
    # All non-process source/model construction must remain identical.
    assert v06._task_cells() == v07._task_cells()
    old_axes = v06._read_json(v06.AXES_PATH)
    new_axes = v07._read_json(v07.AXES_PATH)
    old_trace = v06._read_json(v06.ROOT / old_axes["model_derived"]["satellite_geometry"]["trace_path"])
    new_trace = v07._read_json(v07.ROOT / new_axes["model_derived"]["satellite_geometry"]["trace_path"])
    assert old_trace == new_trace

    for horizon in (3600, 21600, 43200, 54000):
        a, sa = v06._geometry_catalog(old_trace, old_axes, horizon)
        b, sb = v07._geometry_catalog(new_trace, new_axes, horizon)
        assert sa == sb
        assert a == b

    obs6 = v06._obligations(21600, 2, "HALF_PERIOD_OFFSET")
    obs7 = v07._obligations(21600, 2, "HALF_PERIOD_OFFSET")
    assert [o.__dict__ for o in obs6] == [o.__dict__ for o in obs7]
    terr6 = v06._terr_opportunities(obs6, 21600, [0.25, 0.75], 1)
    terr7 = v07._terr_opportunities(obs7, 21600, [0.25, 0.75], 1)
    assert terr6 == terr7

    # v0.7 candidate process semantics must actually recover/reinterrupt.
    all_down3 = (False, False, False)
    all_up3 = (True, True, True)
    steady = v07._service_support(3, "STEADY_AVAILABLE_CONTROL")
    single = v07._service_support(3, "SINGLE_RECOVERY")
    reint = v07._service_support(3, "REINTERRUPTIBLE")
    full = v07._service_support(3, "FULL_BINARY_SUPPORT")
    assert steady == [all_up3]
    assert all_down3 not in single and all_up3 not in single
    assert all_down3 not in reint and all_up3 not in reint
    assert (False, True, False) not in single
    assert (False, True, False) in reint
    assert all_down3 in full and all_up3 in full

    # Physical backup derivation itself is unchanged.
    one6 = [v06.Obligation("A0", "A", 0, 0, 100)]
    one7 = [v07.Obligation("A0", "A", 0, 0, 100)]
    terr = [{"time_s": 50, "capacity_units": 1, "service_stage_index": 0}]
    sat = [{"time_s": 75, "capacity_units": 1}]
    assert v06._min_backup_demand(one6, terr, sat, (True,)) == v07._min_backup_demand(one7, terr, sat, (True,)) == 0
    assert v06._min_backup_demand(one6, terr, sat, (False,)) == v07._min_backup_demand(one7, terr, sat, (False,)) == 1

    print("PASS Layer-1 v0.7 generator: non-process construction matches v0.6; recovery support semantics are corrected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
