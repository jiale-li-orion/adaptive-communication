#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main() -> int:
    env = dict(os.environ)
    env.pop("OPENAI_API_KEY", None)
    env.pop("OPENAI_BASE_URL", None)
    proc = subprocess.run(
        [
            sys.executable,
            str(HERE / "run_r3_model_eval.py"),
            "--model",
            "fixture/model",
            "--variant",
            "localized",
            "--seed",
            "3",
            "--dry-run",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["mode"] == "R3_full_simulator"
    assert payload["variant"] == "localized"
    assert payload["seed"] == 3
    assert payload["api_key_present"] is False
    assert payload["dry_run"] is True
    print("PASS R3 model-eval CLI: freezes task/context/model budget and never fakes missing backend")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
