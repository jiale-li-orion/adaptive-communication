#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "code" / "evaluation" / "agentic" / "run_model_context_matrix.py"


def main() -> int:
    env = dict(os.environ)
    env.pop("OPENAI_API_KEY", None)
    env.pop("OPENAI_BASE_URL", None)
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--model",
            "fixture-model",
            "--stage",
            "both",
            "--dry-run",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["contexts"] == ["task_conditioned", "full_dump", "generic_react"]
    assert payload["api_key_present"] is False
    assert payload["protocol_revision"]

    live = subprocess.run(
        [sys.executable, str(SCRIPT), "--model", "fixture-model", "--stage", "r1"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert live.returncode != 0
    msg = (live.stdout + live.stderr).lower()
    assert (
        "no scripted fallback" in msg
        or "base_url/--base-url is required" in msg
    ), msg
    print("PASS model-context matrix CLI: three fair contexts, no credential fallback")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
