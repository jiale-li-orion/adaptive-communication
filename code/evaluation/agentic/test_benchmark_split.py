#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(CODE)
if CODE not in sys.path:
    sys.path.insert(0, CODE)

from agentic_communication.benchmark_split import (  # noqa: E402
    BenchmarkSplit,
    benchmark_coordinates,
    nasa_power_path,
    split_summary,
)


def main() -> int:
    rows = benchmark_coordinates(seeds=(0,), windows=("w2",))
    summary = split_summary(rows)
    assert len(rows) == 18, len(rows)  # 3 source years x 6 task families
    assert summary["train"]["years"] == [2022]
    assert summary["dev"]["years"] == [2023]
    assert summary["test"]["years"] == [2024]
    assert {x.split for x in rows} == {
        BenchmarkSplit.TRAIN,
        BenchmarkSplit.DEV,
        BenchmarkSplit.TEST,
    }
    for year in (2022, 2023, 2024):
        assert nasa_power_path(ROOT, year).is_file(), year
    # Random seed cannot move a source period between splits.
    all_rows = benchmark_coordinates(task_templates=("O2",), seeds=(0, 99), windows=("w2",))
    for year in (2022, 2023, 2024):
        splits = {x.split for x in all_rows if x.irradiance_year == year}
        assert len(splits) == 1, (year, splits)
    print("PASS benchmark split: source year precedes seed; O1-O6 coordinates are replayable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
