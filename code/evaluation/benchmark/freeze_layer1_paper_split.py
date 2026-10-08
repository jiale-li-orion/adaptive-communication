#!/usr/bin/env python3
"""Freeze a paper-facing execution split without running the test cohort.

The old v0.2 structural test was exposed and the legacy 2024/w1 Qili cohort was
used in prior model-transfer work.  This split therefore freezes *new execution
identities* on already pinned NASA POWER source data:

  train: 2022, w0..w3, seeds 0..9
  dev:   2023, w0..w3, seeds 0..9
  test:  2024, w0/w2/w3, seeds 100..109

for canonical release templates O1/O2/O3/O4/O6.  O5 is excluded because its
recovery-reconciliation objective is still SOURCE_GAP / OBJECTIVE_AMBIGUOUS.

The 2024 test coordinates are not claimed to be historically unknown: the
weather windows were named in an earlier split definition.  The stronger and
auditable claim is ``fresh execution cohort`` -- these exact seed/window/task
identities have no tracked result artifact before this freeze.  The script only
materializes IDs and input digests; it never instantiates or executes test envs.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from agentic_communication.benchmark_split import WINDOW_START_HOURS  # noqa: E402
from agentic_communication.episodes import benchmark_episode_catalog  # noqa: E402


OUT = ROOT / "results/benchmark/layer1-paper-split.json"
TASKS = ("O1", "O2", "O3", "O4", "O6")
SPLIT_RULE = {
    "train": {"year": 2022, "windows": ("w0", "w1", "w2", "w3"), "seeds": tuple(range(10))},
    "dev": {"year": 2023, "windows": ("w0", "w1", "w2", "w3"), "seeds": tuple(range(10))},
    "test": {"year": 2024, "windows": ("w0", "w2", "w3"), "seeds": tuple(range(100, 110))},
}


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _canonical_digest(value: Any) -> str:
    blob = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(blob).hexdigest()


def _weather_path(year: int) -> Path:
    return ROOT / "data/downloads/nasa_power_irradiance" / f"power_hourly_{year}_30.33N_94.78E.csv"


def _coordinate(split: str, task: str, year: int, window: str, seed: int) -> dict[str, Any]:
    template = benchmark_episode_catalog()[task]
    start_hour = int(WINDOW_START_HOURS[window])
    overrides = dict(template.simulator_overrides)
    overrides.update(
        {
            "harvest_mode": "irradiance",
            "irradiance_year": year,
            "irradiance_start_hour": start_hour,
        }
    )
    row = {
        "coordinate_id": f"paper:{split}:{task}:{year}:{window}:seed-{seed:03d}",
        "split": split,
        "task_template": task,
        "task_id": template.task.task_id,
        "seed": seed,
        "irradiance_year": year,
        "window_id": window,
        "irradiance_start_hour": start_hour,
        "simulator_overrides": overrides,
        "difficulty_axes": dict(template.difficulty_axes),
        "source_coordinate": {
            "dataset": "NASA_POWER_hourly_irradiance_T2M",
            "year": year,
            "start_hour": start_hour,
            "window_design_layer": "A",
        },
    }
    row["coordinate_sha256"] = _canonical_digest(row)
    return row


def _prior_test_result_refs() -> list[str]:
    """Search tracked result artifacts for the exact *new* test identity family."""

    # Exact test IDs use seed 100..109 and w0/w2/w3.  Old split declarations
    # used seed 0..4, while prior Qili execution used 2024/w1.
    pattern = r"paper:test:O[12346]:2024:w[023]:seed-10[0-9]"
    proc = subprocess.run(
        ["git", "grep", "-n", "-E", pattern, "--", "results"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    hits = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        if line.startswith(str(OUT.relative_to(ROOT)) + ":"):
            continue
        hits.append(line)
    return hits


def build() -> dict[str, Any]:
    catalog = benchmark_episode_catalog()
    assert set(TASKS).issubset(catalog)
    rows: dict[str, list[dict[str, Any]]] = {"train": [], "dev": [], "test": []}
    for split, rule in SPLIT_RULE.items():
        for window in rule["windows"]:
            for task in TASKS:
                for seed in rule["seeds"]:
                    rows[split].append(_coordinate(split, task, rule["year"], window, seed))

    ids = [row["coordinate_id"] for values in rows.values() for row in values]
    prior_hits = _prior_test_result_refs()
    weather = {
        str(year): {
            "path": str(_weather_path(year).relative_to(ROOT)),
            "sha256": _sha(_weather_path(year)),
        }
        for year in (2022, 2023, 2024)
    }
    payload = {
        "stage": "LAYER1_PAPER_EXECUTION_SPLIT_FREEZE",
        "status": "FROZEN_COORDINATES_TEST_NOT_EXECUTED_BY_THIS_SCRIPT",
        "split_rule": {
            split: {
                "year": rule["year"],
                "windows": list(rule["windows"]),
                "seeds": list(rule["seeds"]),
                "task_templates": list(TASKS),
            }
            for split, rule in SPLIT_RULE.items()
        },
        "counts": {split: len(values) for split, values in rows.items()},
        "coordinates": rows,
        "inputs": {
            "weather_files": weather,
            "episodes_py_sha256": _sha(ROOT / "code/agentic_communication/episodes.py"),
            "task_surface_registry_sha256": _sha(ROOT / "research/benchmark/TASK-SURFACE-REGISTRY.v0.1.json"),
            "release_tracks_sha256": _sha(ROOT / "research/benchmark/LAYER1-RELEASE-TRACKS.json"),
        },
        "excluded": {
            "O5": "T1.S5 recovery-reconciliation remains objective-ambiguous/source-gap",
            "2024_w1": "historically executed in Qili held-out/model-transfer lineage",
            "legacy_test_seeds_0_4": "declared by the earlier CONFORMANCE-SPLIT and not reused for the fresh execution cohort"
        },
        "contamination_audit": {
            "exact_new_test_identity_prior_result_hits": prior_hits,
            "passed": not prior_hits,
            "claim": (
                "Fresh execution cohort: exact paper:test identities have no tracked result artifact before freeze. "
                "The 2024 weather year/windows themselves are existing benchmark coordinates and are not claimed historically unseen."
            ),
        },
        "checks": {
            "coordinate_ids_unique": len(ids) == len(set(ids)),
            "train_count_200": len(rows["train"]) == 200,
            "dev_count_200": len(rows["dev"]) == 200,
            "test_count_150": len(rows["test"]) == 150,
            "test_uses_only_2024": {r["irradiance_year"] for r in rows["test"]} == {2024},
            "test_excludes_historically_executed_w1": all(r["window_id"] != "w1" for r in rows["test"]),
            "fresh_test_seed_range": {r["seed"] for r in rows["test"]} == set(range(100, 110)),
            "no_prior_exact_test_result_identity": not prior_hits,
        },
        "access_policy": {
            "test_outcomes_locked": True,
            "allowed_before_policy_freeze": "identity/digest/coverage audits only; no simulator execution or policy scoring",
            "unlock_condition": "paper baseline/policy protocol frozen and recorded in git",
            "method_holdout_note": "This benchmark execution cohort is not a substitute for a future pristine Future-Choice-Stress method holdout."
        },
    }
    assert all(payload["checks"].values()), payload["checks"]
    return payload


def main() -> int:
    payload = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(OUT), **payload["counts"], **payload["checks"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
