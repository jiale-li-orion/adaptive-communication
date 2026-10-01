#!/usr/bin/env python3
"""Run a real model consumer through R3 full physics for O2 benchmark episodes."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
ROOT = CODE.parent
for p in (
    CODE,
    CODE / "monitoring",
    CODE / "runtime",
    CODE / "v3joint",
    CODE / "instance",
    CODE / "physics",
    CODE / "experiments",
    CODE / "analysis",
    CODE / "monitoring",
):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from agentic_communication.episodes import (  # noqa: E402
    o2_localized_risk_escalation_task,
    o2_risk_escalation_task,
)
from agentic_communication.metrics import metric_delta, physical_signature  # noqa: E402
from agentic_communication.model_protocol import PROTOCOL_REVISION  # noqa: E402
from agentic_communication.planner import (  # noqa: E402
    BackendPlannerConsumer,
    BudgetedPlannerConsumer,
)
from agentic_communication.replay import audit_trace  # noqa: E402
from agentic_communication.run import run_agentic_episode, run_reference_comply  # noqa: E402


def _safe_model_name(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in name)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--variant", choices=("global", "localized"), default="global")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument(
        "--context-mode",
        choices=("task_conditioned", "full_dump", "generic_react"),
        default="task_conditioned",
    )
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--api-key-env", default="OPENAI_API_KEY")
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--max-model-calls", type=int, default=128)
    ap.add_argument("--out", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    task = (
        o2_risk_escalation_task()
        if args.variant == "global"
        else o2_localized_risk_escalation_task()
    )
    base_url = args.base_url or os.environ.get("OPENAI_BASE_URL")
    key_present = bool(os.environ.get(args.api_key_env))
    config = {
        "mode": "R3_full_simulator",
        "protocol_revision": PROTOCOL_REVISION,
        "model": args.model,
        "variant": args.variant,
        "seed": args.seed,
        "context_mode": args.context_mode,
        "max_model_calls": args.max_model_calls,
        "base_url": base_url,
        "api_key_env": args.api_key_env,
        "api_key_present": key_present,
        "operational_task": task.model_dump(mode="json"),
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

    from llm_planner import make_real_backend  # noqa: E402

    backend, reason = make_real_backend(
        model=args.model,
        base_url=base_url,
        api_key=api_key,
        timeout=args.timeout,
    )
    if backend is None:
        raise SystemExit(f"model backend unavailable: {reason}")
    base_consumer = BackendPlannerConsumer(
        backend,
        consumer_id=f"r3:{getattr(backend, 'name', 'backend')}:{args.model}",
        provider=str(getattr(backend, "name", "openai-compatible")),
        model=args.model,
    )
    consumer = BudgetedPlannerConsumer(base_consumer, args.max_model_calls)

    reference, _, _ = run_reference_comply(seed=args.seed, operational_task=task)
    result, policy, _, _ = run_agentic_episode(
        seed=args.seed,
        operational_task=task,
        context_mode=args.context_mode,
        planner_consumer=consumer,
    )
    safe_model = _safe_model_name(args.model)
    out = (
        Path(args.out)
        if args.out
        else ROOT / "results" / "agentic" / "r3-model" / safe_model / args.variant / f"seed-{args.seed:03d}"
    )
    out.mkdir(parents=True, exist_ok=True)
    trace_path = out / "runtime_trace.jsonl"
    policy.trace.write_jsonl(trace_path)
    replay = audit_trace(trace_path, context_mode=args.context_mode)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "config": {**config, "dry_run": False, "api_key_present": True},
        "communication_metrics": result["agentic"]["communication_metrics"],
        "agent_metrics": result["agentic"]["agent_metrics"],
        "delta_vs_legacy": metric_delta(
            result["agentic"]["communication_metrics"],
            reference["agentic"]["communication_metrics"] if "agentic" in reference else {},
        ),
        "physical_equal_legacy": physical_signature(result) == physical_signature(reference),
        "model_calls_consumed": consumer.calls,
        "replay_audit": replay,
        "trace": str(trace_path),
    }
    # Reference runs do not carry agentic wrappers; compute communication delta directly.
    from agentic_communication.metrics import communication_metrics  # noqa: E402
    payload["delta_vs_legacy"] = metric_delta(
        result["agentic"]["communication_metrics"], communication_metrics(reference)
    )
    (out / "summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"out": str(out), **payload}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
