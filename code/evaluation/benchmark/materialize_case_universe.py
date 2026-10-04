#!/usr/bin/env python3
"""Materialize the nominal Layer-1 case universe from READY source profiles."""
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

from case_generation import compile_ready_registry  # noqa: E402

DEFAULT_REGISTRY = (
    ROOT
    / "local_research/current/benchmark/task-design/operational-needs"
    / "SOURCE-PROFILE-REGISTRY.v0.1.json"
)
DEFAULT_OUT = (
    ROOT
    / "local_research/current/benchmark/generated/case-universe-v0.1"
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    payload = json.loads(args.registry.read_text(encoding="utf-8"))
    profiles = payload["profiles"]
    cases = compile_ready_registry(profiles)

    args.out.mkdir(parents=True, exist_ok=True)
    cases_dir = args.out / "cases"
    cases_dir.mkdir(exist_ok=True)
    for old in cases_dir.glob("*.json"):
        old.unlink()

    for case in cases:
        safe = case["case_id"].replace("::", "__").replace("/", "_")
        (cases_dir / f"{safe}.json").write_text(
            json.dumps(case, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    by_profile = Counter(case["source_profiles"][0] for case in cases)
    by_family = Counter(case["family"] for case in cases)
    by_regime = Counter(regime for case in cases for regime in case["regime"])
    profile_status = Counter(p["generator_status"] for p in profiles)

    manifest = {
        "schema_version": "0.1",
        "generator": "source-profile-v0.1",
        "registry": str(args.registry.relative_to(ROOT)),
        "case_count": len(cases),
        "release_status": "VALIDITY_PENDING",
        "validity_stage": "V0_SOURCE_COMPLETE",
        "profile_status": dict(sorted(profile_status.items())),
        "by_profile": dict(sorted(by_profile.items())),
        "by_family": dict(sorted(by_family.items())),
        "by_regime": dict(sorted(by_regime.items())),
        "excluded_profiles": [
            {
                "profile_id": p["profile_id"],
                "generator_status": p["generator_status"],
                "unknowns": p.get("unknowns", []),
            }
            for p in profiles
            if p["generator_status"] != "READY"
        ],
        "notes": [
            "Nominal universe only: no controlled stress or hidden-state augmentation.",
            "V1-V9 and Q0-Q12 are not implied by materialization.",
            "PARTIAL_SOURCE_GAP profiles remain visible in the manifest but generate no cases.",
        ],
    }
    (args.out / "MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
