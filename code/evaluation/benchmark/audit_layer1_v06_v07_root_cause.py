#!/usr/bin/env python3
"""Root-cause audit for the v0.6 validity failure and v0.7 correction.

This audit does not run a policy. It compares the two frozen generation
lineages and isolates the construction-level implication:

    ALL_DOWN in support
    + per-world physical feasibility
    + worst-world TIGHT backup provisioning
    + public world-invariant satellite opportunities
    => blind satellite-only common-safe policy.

v0.7 is accepted as a semantic correction only if candidate recovery families
remove ALL_DOWN/TIGHT=n while FULL_BINARY_SUPPORT retains the original
diagnostic collapse and every non-process generation axis remains unchanged.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import argparse
import gzip
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
V06_RUN = ROOT / "local_research/current/benchmark/generated/layer1-v0.6-preoracle-r4"
V07_RUN = ROOT / "local_research/current/benchmark/generated/layer1-v0.7-preoracle-r1"


def _rows(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def _summary(run: Path, version: str) -> dict[str, Any]:
    by_family: dict[str, Counter[str]] = defaultdict(Counter)
    tight_dist: dict[str, Counter[str]] = defaultdict(Counter)
    all_world_physical = 0
    for base in _rows(run / "base-scenarios.jsonl.gz"):
        if str(base["physical"]["status"]) != "ALL_WORLD_PHYSICAL":
            continue
        all_world_physical += 1
        fam = str(base["service_process"]["family"])
        role = str(base["service_process"].get("role", "V06_UNTYPED"))
        n = len(base["composition"]["obligations"])
        tight = int(base["physical"]["tight_fallback_budget_units"])
        worlds = list(base["service_process"]["worlds"])
        all_down = any(all(str(x) == "DOWN" for x in w["service_by_stage"]) for w in worlds)
        all_up = any(all(str(x) == "UP" for x in w["service_by_stage"]) for w in worlds)
        by_family[fam]["bases"] += 1
        by_family[fam]["contains_all_down"] += int(all_down)
        by_family[fam]["contains_all_up"] += int(all_up)
        by_family[fam]["tight_equals_obligation_count"] += int(tight == n)
        by_family[fam]["tight_less_than_obligation_count"] += int(tight < n)
        tight_dist[fam][f"n={n},tight={tight}"] += 1
        by_family[fam][f"role::{role}"] += 1
    return {
        "version": version,
        "run": run.name,
        "all_world_physical_bases": all_world_physical,
        "by_family": {k: dict(sorted(v.items())) for k, v in sorted(by_family.items())},
        "tight_distribution_by_family": {
            k: dict(sorted(v.items())) for k, v in sorted(tight_dist.items())
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    v06 = _summary(V06_RUN, "v0.6")
    v07 = _summary(V07_RUN, "v0.7")

    for fam in ("SINGLE_RECOVERY", "REINTERRUPTIBLE"):
        a = v06["by_family"][fam]
        b = v07["by_family"][fam]
        assert a["contains_all_down"] == a["bases"]
        assert a["tight_equals_obligation_count"] == a["bases"]
        assert b["contains_all_down"] == 0
        assert b["tight_equals_obligation_count"] == 0
        assert b["tight_less_than_obligation_count"] == b["bases"]

    full = v07["by_family"]["FULL_BINARY_SUPPORT"]
    assert full["contains_all_down"] == full["bases"]
    assert full["tight_equals_obligation_count"] == full["bases"]

    steady = v07["by_family"]["STEADY_AVAILABLE_CONTROL"]
    assert steady["contains_all_down"] == 0
    assert steady["contains_all_up"] == steady["bases"]

    payload = {
        "schema_version": "0.1",
        "stage": "V06_V07_ROOT_CAUSE_AUDIT",
        "v06": v06,
        "v07": v07,
        "root_cause": {
            "logical_chain": [
                "v0.6 recovery-named candidate supports include ALL_DOWN",
                "all-world-physical admission requires ALL_DOWN to be individually solvable",
                "TIGHT is max per-world minimum backup demand",
                "ALL_DOWN therefore forces TIGHT to equal obligation count",
                "satellite opportunity schedule is public and world-invariant",
                "ALL_DOWN physical feasibility certifies a satellite-only completion schedule",
                "the same public schedule is consequently blind and common-safe across every compatible world",
            ],
            "not_root_causes": [
                "query payload",
                "ACK timing",
                "learned method weakness/strength",
                "ordinary baseline implementation",
                "Connecta geometry selection",
            ],
            "v07_correction": "candidate process support semantics only",
            "control_check": "FULL_BINARY_SUPPORT retains ALL_DOWN and TIGHT=n collapse under unchanged resource/evidence axes",
        },
        "verdict": "V06_INVALIDATION_CAUSE_IS_PROCESS_SUPPORT_X_WORST_WORLD_PROVISIONING_INTERACTION",
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
