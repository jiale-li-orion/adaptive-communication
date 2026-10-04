#!/usr/bin/env python3
"""Materialize source-resolved Layer-1 cases and pre-oracle dispositions."""
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
from oracle_preflight import preflight_universe  # noqa: E402
from source_derivation import expand_source_ranges  # noqa: E402


BASE = ROOT / "local_research/current/benchmark/task-design/operational-needs"
DEFAULT_REGISTRY = BASE / "SOURCE-PROFILE-REGISTRY.v0.1.json"
DEFAULT_CAPS = BASE / "CAPABILITY-PROFILE-REGISTRY.v0.1.json"
DEFAULT_MAPPING = BASE / "T1-SIMULATOR-MAPPING.v0.1.json"
DEFAULT_OUT = ROOT / "local_research/current/benchmark/generated/case-universe-v0.2"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    ap.add_argument("--capabilities", type=Path, default=DEFAULT_CAPS)
    ap.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    profiles = _load(args.registry)["profiles"]
    capabilities = _load(args.capabilities)["profiles"]
    mapping = _load(args.mapping)

    nominal = compile_ready_registry(profiles)
    cases = expand_source_ranges(nominal)
    preflight = preflight_universe(
        cases,
        mapping=mapping,
        capability_profiles=capabilities,
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

    status = Counter(
        "ORACLE_READY" if row["oracle_ready"] else row["mapping_disposition"]
        for row in preflight
    )
    blockers = Counter(
        blocker for row in preflight for blocker in row["blocking_fields"]
    )
    manifest = {
        "schema_version": "0.2",
        "generator": "source-profile-v0.2",
        "case_count": len(cases),
        "nominal_parent_count": len(nominal),
        "release_status": "VALIDITY_PENDING",
        "validity_stage": "V0_PLUS_MAPPING_PREFLIGHT",
        "by_family": dict(
            sorted(Counter(case["family"] for case in cases).items())
        ),
        "by_source_profile": dict(
            sorted(Counter(case["source_profiles"][0] for case in cases).items())
        ),
        "pre_oracle_status": dict(sorted(status.items())),
        "blocking_fields": dict(sorted(blockers.items())),
        "notes": [
            "Source ranges are resolved only with explicit boundary coverage rules.",
            "No model-dependent hardness, hidden evidence, or arbitrary reward has been added.",
            "No case is V1 SOLVABLE until pre-oracle blockers are cleared and a full-state solver runs.",
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
