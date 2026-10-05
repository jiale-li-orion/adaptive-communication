#!/usr/bin/env python3
"""One-command Layer-1 finalization after a real Q11 review is supplied."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
R = ROOT / "results/benchmark"


def _run(args: list[str], *, stdout_path: Path | None = None) -> None:
    if stdout_path is None:
        subprocess.run(args, cwd=ROOT, check=True)
    else:
        with stdout_path.open("w", encoding="utf-8") as f:
            subprocess.run(args, cwd=ROOT, check=True, stdout=f)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("review_json", type=Path)
    args = ap.parse_args()
    py = sys.executable
    bench = ROOT / "code/evaluation/benchmark"

    _run([py, str(bench / "apply_human_source_review_v0_1.py"), str(args.review_json)])
    _run([py, str(bench / "audit_quality_gates_v0_1.py")], stdout_path=R / "layer1-quality-gates-v0.1.json")
    quality = json.loads((R / "layer1-quality-gates-v0.1.json").read_text(encoding="utf-8"))
    if not quality.get("all_pass"):
        blocked = [g["gate_id"] for g in quality["gates"] if g["status"] != "PASS"]
        raise SystemExit(f"quality gates still blocked: {blocked}")
    _run([py, str(bench / "freeze_release_manifest_v0_1.py")], stdout_path=R / "layer1-release-manifest-v0.1.json")
    manifest = json.loads((R / "layer1-release-manifest-v0.1.json").read_text(encoding="utf-8"))
    if manifest.get("known_release_blockers"):
        raise SystemExit(f"release manifest still blocked: {manifest['known_release_blockers']}")
    print(json.dumps({
        "status": "READY_FOR_BENCHMARK_ADMIT",
        "quality_gate_counts": quality["gate_counts"],
        "release_manifest": "results/benchmark/layer1-release-manifest-v0.1.json",
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
