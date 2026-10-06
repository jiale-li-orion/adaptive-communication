#!/usr/bin/env python3
"""Certify the v0.6 blind-satellite shortcut over the full frozen r4 universe.

This is a benchmark-validity audit, not a policy benchmark.  It proves a
construction-level degeneracy:

* every ALL_WORLD_PHYSICAL base contains an ALL_DOWN terrestrial world;
* therefore worst-world TIGHT backup demand equals the obligation count;
* every fallback mode in the materialized cases is consequently capped at that
  same full backup budget;
* ALL_DOWN physical feasibility implies a public satellite-only schedule exists;
* the same public schedule is a blind open-loop completion plan in every world.

The result invalidates v0.6 as a hard decision benchmark while preserving it as
a reproducible generator/shortcut-regression lineage.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import argparse
import gzip
import json
from pathlib import Path
import subprocess
from typing import Any

from generate_layer1_v06_cases import Obligation, _edf_feasible


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RUN = ROOT / "local_research/current/benchmark/generated/layer1-v0.6-preoracle-r4"
PILOT = ROOT / "results/benchmark/layer1-v0.6-oracle-pilot-r4.json"


def _rows(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def _sha(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True
    ).stdout.strip()


def _obligations(base: dict[str, Any]) -> list[Obligation]:
    return [
        Obligation(
            oid=str(o["oid"]),
            stream=str(o["stream"]),
            ordinal=int(o["ordinal"]),
            release_s=int(o["release_s"]),
            deadline_s=int(o["deadline_s"]),
        )
        for o in base["composition"]["obligations"]
    ]


def audit(run: Path) -> dict[str, Any]:
    manifest = json.loads((run / "MANIFEST.json").read_text(encoding="utf-8"))
    physical_base_ids: set[str] = set()
    base_count = 0
    all_down_count = 0
    tight_equals_n = 0
    satellite_only_feasible = 0
    by_family: Counter[str] = Counter()
    obligation_counts: Counter[int] = Counter()

    for base in _rows(run / "base-scenarios.jsonl.gz"):
        if str(base["physical"]["status"]) != "ALL_WORLD_PHYSICAL":
            continue
        base_count += 1
        bid = str(base["base_id"])
        physical_base_ids.add(bid)
        obligations = _obligations(base)
        n = len(obligations)
        obligation_counts[n] += 1
        family = str(base["service_process"]["family"])
        by_family[family] += 1

        worlds = list(base["service_process"]["worlds"])
        has_all_down = any(all(str(x) == "DOWN" for x in w["service_by_stage"]) for w in worlds)
        if has_all_down:
            all_down_count += 1
        tight = int(base["physical"]["tight_fallback_budget_units"])
        if tight == n:
            tight_equals_n += 1
        sat_ok = _edf_feasible(obligations, tuple(range(n)), list(base["satellite"]["opportunities"]))
        if sat_ok:
            satellite_only_feasible += 1

    case_count = 0
    case_budget_equals_n = 0
    fallback_counts: Counter[str] = Counter()
    fallback_budget_values: Counter[tuple[str, int, int]] = Counter()
    case_base_outside_physical = 0
    # Base obligation count is needed for every case, but only two values occur;
    # retain the compact map rather than full base payloads.
    base_n: dict[str, int] = {}
    for base in _rows(run / "base-scenarios.jsonl.gz"):
        if str(base["base_id"]) in physical_base_ids:
            base_n[str(base["base_id"])] = len(base["composition"]["obligations"])

    for case in _rows(run / "cases.jsonl.gz"):
        case_count += 1
        bid = str(case["base_id"])
        if bid not in base_n:
            case_base_outside_physical += 1
            continue
        n = base_n[bid]
        mode = str(case["fallback_budget_mode"])
        budget = int(case["fallback_budget_units"])
        fallback_counts[mode] += 1
        fallback_budget_values[(mode, n, budget)] += 1
        if budget == n:
            case_budget_equals_n += 1

    pilot = json.loads(PILOT.read_text(encoding="utf-8")) if PILOT.exists() else None
    pilot_blind = None
    if pilot:
        pilot_blind = int(pilot["disposition_counts"].get("BLIND_OPEN_LOOP_SOLVED", 0))

    proof_pass = all(
        (
            base_count > 0,
            all_down_count == base_count,
            tight_equals_n == base_count,
            satellite_only_feasible == base_count,
            case_count == int(manifest["counts"]["cases"]),
            case_budget_equals_n == case_count,
            case_base_outside_physical == 0,
        )
    )
    if not proof_pass:
        raise AssertionError("v0.6 shortcut-collapse proof preconditions did not hold globally")

    return {
        "schema_version": "0.1",
        "stage": "V06_GLOBAL_SHORTCUT_VALIDITY_AUDIT",
        "official_generation_run": run.name,
        "generation_manifest_sha256": _sha(run / "MANIFEST.json"),
        "audit_git_commit": _git_head(),
        "all_world_physical_bases": base_count,
        "all_down_support_bases": all_down_count,
        "tight_budget_equals_obligation_count_bases": tight_equals_n,
        "public_satellite_only_feasible_bases": satellite_only_feasible,
        "dynamic_cases": case_count,
        "cases_with_fallback_budget_equal_obligation_count": case_budget_equals_n,
        "case_base_outside_all_world_physical": case_base_outside_physical,
        "base_counts_by_service_family": dict(sorted(by_family.items())),
        "base_counts_by_obligation_count": {str(k): v for k, v in sorted(obligation_counts.items())},
        "case_counts_by_fallback_mode": dict(sorted(fallback_counts.items())),
        "fallback_budget_value_counts": [
            {"mode": mode, "obligation_count": n, "budget": budget, "count": count}
            for (mode, n, budget), count in sorted(fallback_budget_values.items())
        ],
        "oracle_pilot": None
        if pilot is None
        else {
            "axis_cells": int(pilot["axis_cell_count"]),
            "blind_open_loop_solved": pilot_blind,
            "artifact": str(PILOT.relative_to(ROOT)),
        },
        "proof": [
            "Every admitted physical support contains an ALL_DOWN terrestrial world.",
            "In ALL_DOWN, every successful plan uses satellite for every obligation; hence TIGHT=max_w(min backup demand)=obligation_count.",
            "BALANCED is capped at obligation_count and SLACK_CONTROL equals obligation_count, so all three materialized fallback modes expose the same full backup budget.",
            "ALL_DOWN physical feasibility certifies that the public satellite opportunities alone schedule every obligation.",
            "Satellite opportunities are public and world-invariant, so that same satellite-only schedule is a blind open-loop policy over the entire support.",
        ],
        "disposition": "V06_BENCHMARK_VALIDITY_FAIL_GLOBAL_BLIND_SATELLITE_SHORTCUT",
        "generator_disposition": "RETAIN_AS_REPRODUCIBLE_NEGATIVE_LINEAGE_AND_SHORTCUT_REGRESSION",
        "claim_boundary": [
            "This does not invalidate source grounding or generation reproducibility.",
            "It invalidates v0.6 as a decision-hardness benchmark because V3/common-safe open-loop policy is guaranteed by construction.",
            "The next generation must be versioned; r4 axes/artifacts remain frozen and are not edited in place.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, default=DEFAULT_RUN)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    payload = audit(args.run.resolve())
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
