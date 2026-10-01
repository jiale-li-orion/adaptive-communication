#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
ROOT = CODE.parent


def main() -> int:
    cmd = [
        sys.executable,
        str(HERE / "run_r1_model_eval.py"),
        "--model",
        "fixture/model",
        "--dry-run",
        "--limit",
        "2",
    ]
    env = dict(os.environ)
    env.pop("OPENAI_API_KEY", None)
    env.pop("OPENAI_BASE_URL", None)
    proc = subprocess.run(cmd, cwd=ROOT, env=env, text=True, capture_output=True, check=False)
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["dry_run"] is True
    assert payload["api_key_present"] is False
    assert payload["protocol_revision"] == "communication-planner-json-v1"
    assert len(payload["trace_sha256"]) == 64
    print("PASS R1 model-eval CLI: dry-run freezes trace/protocol and never requires/fakes a model backend")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
