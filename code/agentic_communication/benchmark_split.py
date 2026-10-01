"""Source-period-separated benchmark coordinates for Agentic Communication."""
from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field

from .episodes import benchmark_episode_catalog


class BenchmarkSplit(StrEnum):
    TRAIN = "train"
    DEV = "dev"
    TEST = "test"


YEAR_SPLIT = {
    2022: BenchmarkSplit.TRAIN,
    2023: BenchmarkSplit.DEV,
    2024: BenchmarkSplit.TEST,
}

# Window selection is A-layer benchmark design, not a claim that these dates
# correspond to historical landslide events.  All windows are long enough for
# the frozen 12h task + 1h tail.
WINDOW_START_HOURS = {
    "w0": 30 * 24,
    "w1": 120 * 24,
    "w2": 151 * 24,
    "w3": 270 * 24,
}


class BenchmarkCoordinate(BaseModel):
    coordinate_id: str
    split: BenchmarkSplit
    task_template: str
    task_id: str
    seed: int = Field(ge=0)
    irradiance_year: int
    irradiance_start_hour: int = Field(ge=0)
    window_id: str
    simulator_overrides: dict
    difficulty_axes: dict
    source_coordinate: dict


def nasa_power_path(repo_root: str | Path, year: int) -> Path:
    return (
        Path(repo_root)
        / "data"
        / "downloads"
        / "nasa_power_irradiance"
        / f"power_hourly_{year}_30.33N_94.78E.csv"
    )


def benchmark_coordinates(
    *,
    task_templates: tuple[str, ...] = ("O1", "O2", "O3", "O4", "O5", "O6"),
    seeds: tuple[int, ...] = (0, 1, 2, 3, 4),
    windows: tuple[str, ...] = ("w0", "w1", "w2", "w3"),
) -> list[BenchmarkCoordinate]:
    catalog = benchmark_episode_catalog()
    out: list[BenchmarkCoordinate] = []
    for year, split in YEAR_SPLIT.items():
        for window in windows:
            start_hour = WINDOW_START_HOURS[window]
            for task_key in task_templates:
                template = catalog[task_key]
                for seed in seeds:
                    overrides = dict(template.simulator_overrides)
                    overrides.update(
                        {
                            "harvest_mode": "irradiance",
                            "irradiance_year": year,
                            "irradiance_start_hour": start_hour,
                        }
                    )
                    out.append(
                        BenchmarkCoordinate(
                            coordinate_id=(
                                f"{split.value}:{task_key}:{year}:{window}:seed-{seed:03d}"
                            ),
                            split=split,
                            task_template=task_key,
                            task_id=template.task.task_id,
                            seed=seed,
                            irradiance_year=year,
                            irradiance_start_hour=start_hour,
                            window_id=window,
                            simulator_overrides=overrides,
                            difficulty_axes=dict(template.difficulty_axes),
                            source_coordinate={
                                "dataset": "NASA_POWER_hourly_irradiance_T2M",
                                "year": year,
                                "start_hour": start_hour,
                                "window_design_layer": "A",
                            },
                        )
                    )
    return out


def split_summary(rows: list[BenchmarkCoordinate]) -> dict:
    out = {}
    for split in BenchmarkSplit:
        subset = [x for x in rows if x.split == split]
        out[split.value] = {
            "n_coordinates": len(subset),
            "years": sorted({x.irradiance_year for x in subset}),
            "task_templates": sorted({x.task_template for x in subset}),
            "window_ids": sorted({x.window_id for x in subset}),
            "seeds": sorted({x.seed for x in subset}),
        }
    return out
