#!/usr/bin/env python3
"""Small semantic regressions for the v0.6 pre-oracle generator."""
from __future__ import annotations

from generate_layer1_v06_cases import (
    Obligation,
    _geometry_catalog,
    _id,
    _min_backup_demand,
    _read_json,
    _service_support,
    AXES_PATH,
    ROOT,
)


def main() -> int:
    # Service-support definitions are structural, not sampled.
    full = _service_support(3, "FULL_BINARY_SUPPORT")
    single = _service_support(3, "SINGLE_RECOVERY")
    reinterrupt = _service_support(3, "REINTERRUPTIBLE")
    assert len(full) == 8
    assert set(single) <= set(reinterrupt) <= set(full)
    assert (False, True, False) not in single
    assert (False, True, False) in reinterrupt

    obs = [Obligation("A0", "A", 0, 0, 100)]
    terr = [{"time_s": 50, "capacity_units": 1, "service_stage_index": 0}]
    sat = [{"time_s": 75, "capacity_units": 1}]
    assert _min_backup_demand(obs, terr, sat, (True,)) == 0
    assert _min_backup_demand(obs, terr, sat, (False,)) == 1
    assert _min_backup_demand(obs, terr, [], (False,)) is None

    payload = {"b": 2, "a": [1, 3]}
    assert _id("X", payload) == _id("X", {"a": [1, 3], "b": 2})

    axes = _read_json(AXES_PATH)
    trace = _read_json(ROOT / axes["model_derived"]["satellite_geometry"]["trace_path"])
    a, sa = _geometry_catalog(trace, axes, 3600)
    b, sb = _geometry_catalog(trace, axes, 3600)
    assert sa == sb
    assert [row["geometry_signature_id"] for row in a] == [row["geometry_signature_id"] for row in b]
    assert [row["rounded_shape_s"] for row in a] == [row["rounded_shape_s"] for row in b]

    print("PASS Layer-1 v0.6 generator semantic regressions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

