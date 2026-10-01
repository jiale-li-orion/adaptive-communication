#!/usr/bin/env python3
"""Generate/check the source-period-separated Agentic benchmark manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from agentic_communication.benchmark_split import (  # noqa: E402
    YEAR_SPLIT,
    benchmark_coordinates,
    nasa_power_path,
    split_summary,
)

OUT = ROOT / "research" / "AGENTIC-BENCHMARK-SPLIT.v1.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def build() -> dict:
    rows = benchmark_coordinates()
    sources = {}
    for year, split in YEAR_SPLIT.items():
        path = nasa_power_path(ROOT, year)
        if not path.is_file():
            raise FileNotFoundError(path)
        sources[str(year)] = {
            "split": split.value,
            "path": str(path.relative_to(ROOT)),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
    return {
        "schema_revision": "1",
        "rule": (
            "source years are split before random seeds; window positions are A-layer "
            "benchmark coordinates and are not historical-disaster claims"
        ),
        "source_years": sources,
        "summary": split_summary(rows),
        "coordinates": [x.model_dump(mode="json") for x in rows],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    expected = json.dumps(build(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    current = OUT.read_text(encoding="utf-8") if OUT.exists() else None
    if args.check:
        if current != expected:
            print("Agentic benchmark split manifest is stale; run scripts/make_agentic_benchmark_manifest.py")
            return 1
        print("Agentic benchmark split manifest matches source data")
        return 0
    if current != expected:
        OUT.write_text(expected, encoding="utf-8")
        print(f"updated {OUT.relative_to(ROOT)}")
    else:
        print("Agentic benchmark split manifest already current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
