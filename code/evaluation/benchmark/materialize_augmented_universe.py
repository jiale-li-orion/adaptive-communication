#!/usr/bin/env python3
"""Materialize DB44 × LEO capability × geometry-sensitivity Layer-1 worlds."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import argparse
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from case_augmentation import augment_db44_universe  # noqa: E402
from case_generation import compile_ready_registry  # noqa: E402
from oracle_preflight import preflight_universe  # noqa: E402
from source_derivation import expand_source_ranges  # noqa: E402

BASE = ROOT / "local_research/current/benchmark/task-design/operational-needs"
DEFAULT_OUT = ROOT / "local_research/current/benchmark/generated/case-universe-v0.3"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    task_profiles = load(BASE / "SOURCE-PROFILE-REGISTRY.v0.1.json")["profiles"]
    caps = load(BASE / "CAPABILITY-PROFILE-REGISTRY.v0.1.json")["profiles"]
    traces = load(BASE / "TRACE-PROFILE-REGISTRY.v0.1.json")["profiles"]
    mapping = load(BASE / "T1-SIMULATOR-MAPPING.v0.1.json")

    source_cases = expand_source_ranges(compile_ready_registry(task_profiles))
    cap = next(
        row for row in caps
        if row["capability_profile_id"] == "PLAN_S_CONNECTA_IOT_MODULE_D2S"
    )
    trace = next(
        row for row in traces
        if row["trace_profile_id"] == "CONNECTA_20260922_SIHUI_GEOMETRY_48H"
    )
    trace_payload = load(ROOT / trace["trace_ref"])
    cases = augment_db44_universe(
        source_cases,
        capability_profile=cap,
        trace_profile=trace,
        trace_payload=trace_payload,
    )
    preflight = preflight_universe(
        cases,
        mapping=mapping,
        capability_profiles=caps,
    )
    by_case = {row["case_id"]: row for row in preflight}

    args.out.mkdir(parents=True, exist_ok=True)
    case_dir = args.out / "cases"
    case_dir.mkdir(exist_ok=True)
    for old in case_dir.glob("*.json"):
        old.unlink()

    for case in cases:
        enriched = dict(case)
        enriched["pre_oracle"] = by_case[case["case_id"]]
        safe = case["case_id"].replace("::", "__").replace("/", "_")
        (case_dir / f"{safe}.json").write_text(
            json.dumps(enriched, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    blockers = Counter(
        blocker for row in preflight for blocker in row["blocking_fields"]
    )
    by_mask = Counter(
        str(case["world"]["path_geometry"]["elevation_mask_deg"])
        for case in cases
    )
    by_warning = Counter(
        str(case["world"]["warning_state"])
        for case in cases
    )
    manifest = {
        "schema_version": "0.3",
        "generator": "source-profile-v0.3",
        "parent_source_case_count": len([
            c for c in source_cases
            if c["source_profiles"] == ["DB44T2457_2024_warning_reporting"]
        ]),
        "augmented_world_count": len(cases),
        "family": "T1_MONITORING_INFORMATION_CONTINUITY",
        "task_profile": "DB44T2457_2024_warning_reporting",
        "capability_profile": cap["capability_profile_id"],
        "trace_profile": trace["trace_profile_id"],
        "release_status": "VALIDITY_PENDING",
        "validity_stage": "V0_PLUS_CAPABILITY_TRACE_PREFLIGHT",
        "by_elevation_mask_deg": dict(sorted(by_mask.items(), key=lambda x: int(x[0]))),
        "by_warning_state": dict(sorted(by_warning.items())),
        "blocking_fields": dict(sorted(blockers.items())),
        "oracle_ready_count": sum(row["oracle_ready"] for row in preflight),
        "notes": [
            "135 is an augmented world count, not a count of admitted benchmark tasks.",
            "Each world is traceable to a task profile, a normative capability profile, a pinned model-derived trace, and an explicit geometry stress cell.",
            "Geometry visibility is not interpreted as measured contact or successful service.",
            "V1 remains blocked until payload and service-success semantics are explicit.",
        ],
    }
    (args.out / "PREFLIGHT.json").write_text(
        json.dumps(preflight, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.out / "MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
