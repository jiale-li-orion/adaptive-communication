#!/usr/bin/env python3
"""Freeze the Layer-2 v2 structural descriptor using train/dev only.

The descriptor follows the dimensions named in cache06.md rather than IDs or
random seeds:

* obligation count and maximum temporal obligation overlap;
* maximum obligation/opportunity conflict-component width;
* a normalized event-interleaving skeleton over execution, asynchronous
  feedback, and owner-query observations.

This audit itself intentionally reads only train/dev artifacts.  However, the
repository's seven hard ``test`` signatures were already evaluated at the
earlier planning-kernel checkpoint ``fdc0846``.  Therefore this descriptor is a
coverage/structure diagnostic only: it must not relabel that previously
exposed split as a pristine unseen structural holdout for the later full v2
method.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from compositional_recipe_generator_v0_1 import core_recipes
from dynamic_world_materializer_v0_1 import materialize_recipe


ROOT = Path(__file__).resolve().parents[3]
TRAIN = ROOT / "results/agentic/layer2-v2-conflict-frontier-train-flowcut.json"
DEV = ROOT / "results/agentic/layer2-v2-conflict-frontier-dev-flowcut.json"


def _max_overlap(obligations: list[dict[str, Any]]) -> int:
    boundaries = sorted(
        {int(row["release_s"]) for row in obligations}
        | {int(row["deadline_s"]) for row in obligations}
    )
    return max(
        (
            sum(
                int(row["release_s"]) <= t <= int(row["deadline_s"])
                for row in obligations
            )
            for t in boundaries
        ),
        default=0,
    )


def _event_class(raw: str) -> str:
    if raw == "ROOT":
        return "ROOT"
    if raw.startswith("OBSERVATION:query:"):
        return "OWNER_QUERY_OBSERVATION"
    if raw.startswith("OBSERVATION:"):
        return "OTHER_OBSERVATION"
    if raw in {
        "SATELLITE_COMMIT",
        "TERRESTRIAL_COMMIT",
        "QUERY_EVENT",
        "DELIVERY_ASYNC_EVENT",
        "DELIVERY_COMPLETION",
        "TIME_OR_ASYNC_EVENT",
    }:
        return raw
    return "OTHER_EVENT"


def _event_skeleton(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    out: list[str] = []
    for row in rows:
        value = _event_class(str(row["event_from_parent"]))
        if not out or out[-1] != value:
            out.append(value)
    return tuple(out)


def _case_descriptor(case: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    rows = case["result"]["rows"]
    events: dict[str, int] = {}
    for row in rows:
        key = _event_class(str(row["event_from_parent"]))
        events[key] = events.get(key, 0) + 1
    descriptor = {
        "obligation_count": len(bundle["obligations"]),
        "max_obligation_overlap": _max_overlap(list(bundle["obligations"])),
        "max_conflict_width": max((int(row["max_component_width"]) for row in rows), default=0),
        "event_classes_present": sorted(events),
        "event_first_occurrence_order": list(dict.fromkeys(_event_class(str(row["event_from_parent"])) for row in rows)),
        "compressed_event_skeleton": list(_event_skeleton(rows)),
    }
    structural_key = json.dumps(descriptor, sort_keys=True, separators=(",", ":"))
    return {
        "signature": case["signature"],
        "recipe_id": case["recipe_id"],
        "descriptor": descriptor,
        "structural_key": structural_key,
        "event_counts": dict(sorted(events.items())),
    }


def _load_rows(path: Path, bundles: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    artifact = json.loads(path.read_text(encoding="utf-8"))
    return [
        _case_descriptor(case, bundles[str(case["recipe_id"])])
        for case in artifact["cases"]
    ]


def main() -> int:
    recipes = {row.recipe_id: row for row in core_recipes()}
    recipe_ids = {
        str(case["recipe_id"])
        for path in (TRAIN, DEV)
        for case in json.loads(path.read_text(encoding="utf-8"))["cases"]
    }
    bundles = {
        recipe_id: materialize_recipe(recipes[recipe_id])
        for recipe_id in recipe_ids
    }
    train = _load_rows(TRAIN, bundles)
    dev = _load_rows(DEV, bundles)
    train_keys = {row["structural_key"] for row in train}
    dev_keys = {row["structural_key"] for row in dev}
    unseen_dev = [row for row in dev if row["structural_key"] not in train_keys]
    artifact = {
        "schema_version": "0.1",
        "status": "DESCRIPTOR_FROZEN_AFTER_PRIOR_TEST_EXPOSURE",
        "descriptor_contract": {
            "dimensions": [
                "obligation_count",
                "max_obligation_overlap",
                "max_conflict_width",
                "event_classes_present",
                "event_first_occurrence_order",
                "compressed_event_skeleton",
            ],
            "forbidden_holdout_keys": ["recipe_id", "signature", "seed", "start_phase_only"],
            "this_audit_reads_test": False,
            "repository_test_accessed_previously": True,
            "prior_test_exposure_commit": "fdc0846",
            "prior_test_artifact": "results/agentic/layer2-v2-matrix-test-all-recursive.json",
            "final_rule": "the existing seven-signature test split is regression evidence only; any claim of independent structural generalization requires a separately preregistered cohort/protocol that is not selected using current method outcomes",
        },
        "coverage": {
            "train_signature_count": len(train),
            "dev_signature_count": len(dev),
            "train_structural_key_count": len(train_keys),
            "dev_structural_key_count": len(dev_keys),
            "train_dev_shared_key_count": len(train_keys & dev_keys),
            "dev_structurally_unseen_vs_train_count": len(unseen_dev),
        },
        "train": train,
        "dev": dev,
        "dev_structurally_unseen_vs_train": unseen_dev,
    }
    out = ROOT / "results/agentic/layer2-v2-structural-descriptor-freeze.json"
    out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": artifact["status"], "coverage": artifact["coverage"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
