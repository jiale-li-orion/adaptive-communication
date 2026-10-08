#!/usr/bin/env python3
"""Materialize the method-independent v0.7 gateway-local pilot selection.

The frozen v0.7 universe is large enough that repeatedly scanning the full
case/base artifacts for every exact cell is wasteful.  This index performs the
placement-specific, solver-independent selection once and stores only the 36
selected TIGHT candidate cells together with their exact case/base inputs.

No oracle, baseline or Layer-2/3 result is read by this script.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from audit_layer1_v07_gateway_mechanism_pilot import (
    DEFAULT_RUN,
    _base_meta,
    _load_selected_bases,
    _select,
)


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUT = ROOT / "local_research/current/benchmark/v07-gateway-pilot-index.json"


def _sha(path: Path) -> str:
    h = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def materialize(run: Path) -> dict[str, Any]:
    meta = _base_meta(run)
    selected = _select(
        run,
        meta,
        service_roles={"CANDIDATE"},
        fallback_modes={"TIGHT"},
    )
    bases = _load_selected_bases(
        run,
        {str(case["base_id"]) for case in selected.values()},
    )

    rows = []
    for ordinal, (key, case) in enumerate(sorted(selected.items()), start=1):
        base = bases[str(case["base_id"])]
        rows.append(
            {
                "ordinal": ordinal,
                "axis_cell": {
                    "obligations_per_stream": key[0],
                    "phase_mode": key[1],
                    "service_process": key[2],
                    "terr_capacity": key[3],
                    "feedback_profile": key[4],
                    "fallback_mode": key[5],
                    "placement": "GATEWAY_LOCAL_PRIMARY",
                },
                "case": case,
                "base": base,
            }
        )

    return {
        "schema_version": "0.1",
        "stage": "V07_GATEWAY_LOCAL_PILOT_SELECTION_INDEX",
        "placement": "GATEWAY_LOCAL_PRIMARY",
        "official_generation_run": run.name,
        "official_generation_manifest_sha256": _sha(run / "MANIFEST.json"),
        "selection_rule": (
            "one lexicographically-smallest case_id per "
            "composition×candidate-process×capacity×feedback×TIGHT cell after "
            "placement-specific remote-query-delay dedupe"
        ),
        "selection_depends_on_method_or_baseline": False,
        "axis_cell_count": len(rows),
        "rows": rows,
        "claim_boundary": [
            "This artifact fixes pilot selection only; it contains no oracle or baseline outcome.",
            "Remote-query timing is inactive under gateway-local placement and is not a pilot axis.",
            "The index does not alter or replace the frozen v0.7 generator universe.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    payload = materialize(args.run.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "out": str(args.out),
                "axis_cell_count": payload["axis_cell_count"],
                "selection_depends_on_method_or_baseline": False,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
