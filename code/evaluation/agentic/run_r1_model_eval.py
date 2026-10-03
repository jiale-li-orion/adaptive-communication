#!/usr/bin/env python3
"""Evaluate a real model on frozen R1 PromptAssembly inputs before rerunning physics."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
ROOT = CODE.parent
for p in (CODE, CODE / "substrate" / "monitoring", CODE / "substrate" / "runtime"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from agentic_communication.model_protocol import PROTOCOL_REVISION  # noqa: E402
from agentic_communication.planner import (  # noqa: E402
    BackendPlannerConsumer,
    DeterministicComplyPlannerConsumer,
)
from agentic_communication.r1_evaluation import evaluate_r1_consumers  # noqa: E402
from agentic_communication.replay import load_trace  # noqa: E402


DEFAULT_TRACE = (
    ROOT
    / "results"
    / "agentic"
    / "o2-risk-escalation-v1"
    / "runtime_traces"
    / "seed-000-task_conditioned.jsonl"
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace", default=str(DEFAULT_TRACE))
    ap.add_argument("--model", required=True)
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--api-key-env", default="OPENAI_API_KEY")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--out", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    trace = Path(args.trace).resolve()
    if not trace.is_file():
        raise SystemExit(f"trace not found: {trace}")
    base_url = args.base_url or os.environ.get("OPENAI_BASE_URL")
    key_present = bool(os.environ.get(args.api_key_env))
    config = {
        "trace": str(trace),
        "trace_sha256": sha256(trace),
        "protocol_revision": PROTOCOL_REVISION,
        "model": args.model,
        "base_url": base_url,
        "api_key_env": args.api_key_env,
        "api_key_present": key_present,
        "limit": args.limit,
        "dry_run": args.dry_run,
    }
    if args.dry_run:
        print(json.dumps(config, ensure_ascii=False, indent=2))
        return 0
    if not base_url:
        raise SystemExit("OPENAI_BASE_URL/--base-url is required; no implicit provider endpoint")
    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        raise SystemExit(f"{args.api_key_env} is not set; no scripted fallback is allowed")

    # Reuse the repository's existing reachability-checked OpenAI-compatible backend factory.
    from llm_planner import make_real_backend  # noqa: E402

    backend, reason = make_real_backend(
        model=args.model,
        base_url=base_url,
        api_key=api_key,
        timeout=args.timeout,
    )
    if backend is None:
        raise SystemExit(f"model backend unavailable: {reason}")

    candidate = BackendPlannerConsumer(
        backend,
        consumer_id=f"r1:{getattr(backend, 'name', 'backend')}:{args.model}",
        provider=str(getattr(backend, "name", "openai-compatible")),
        model=args.model,
    )
    gold = DeterministicComplyPlannerConsumer()
    turns, aggregate = evaluate_r1_consumers(
        load_trace(trace),
        candidate=candidate,
        gold=gold,
        limit=args.limit,
    )
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": "R1_frozen_model_input",
        "config": {**config, "dry_run": False, "api_key_present": True},
        "gold_consumer": gold.consumer_id,
        "aggregate": aggregate,
        "turns": [asdict(turn) for turn in turns],
    }
    if args.out:
        out = Path(args.out)
    else:
        safe_model = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in args.model)
        out = ROOT / "results" / "agentic" / "r1-model" / f"{safe_model}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(out), "aggregate": aggregate}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
