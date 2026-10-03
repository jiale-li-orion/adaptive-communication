#!/usr/bin/env python3
"""O5 h8/h9/h10 Context-representation matrix on frozen protocol envelopes."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys
import time


HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
ROOT = CODE.parent
for p in (
    CODE,
    CODE / "substrate" / "joint",
    CODE / "substrate" / "instance",
    CODE / "substrate" / "monitoring",
    CODE / "substrate" / "physics",
    CODE / "substrate" / "runtime",
    CODE / "evaluation" / "agentic",
    CODE / "legacy-communication" / "analysis",
    HERE,
):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from agentic_communication.model_protocol import assert_no_evaluator_leakage  # noqa: E402
from run_o5_context_update_model_probe import (  # noqa: E402
    evaluate_decision,
    fresh_gold,
    parse_backend_json,
)


DEFAULT_INPUT = ROOT / "results" / "agentic" / "o5-context-transition-devset-v1"
DEFAULT_OUT = ROOT / "results" / "agentic" / "o5-transition-context-model-probe-v1"
DEFAULT_CONTEXTS = (
    "task_conditioned",
    "full_dump",
    "generic_react",
    "action_conditioned_compact",
)


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def real_backend(args):
    base_url = args.base_url or os.environ.get("OPENAI_BASE_URL")
    api_key = os.environ.get(args.api_key_env)
    if not base_url:
        raise SystemExit("OPENAI_BASE_URL/--base-url is required")
    if not api_key:
        raise SystemExit(f"{args.api_key_env} is not set")
    from llm_planner import make_real_backend  # noqa: E402

    backend, reason = make_real_backend(
        model=args.model,
        base_url=base_url,
        api_key=api_key,
        timeout=args.timeout,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        reasoning_effort=args.reasoning_effort,
        json_object=True,
    )
    if backend is None:
        raise SystemExit(f"model backend unavailable: {reason}")
    return backend, base_url


def load_manifest(root: Path) -> dict:
    return json.loads((root / "manifest.json").read_text(encoding="utf-8"))


def load_env(root: Path, event_id: str, context: str) -> dict:
    return json.loads(
        (root / "inputs" / event_id / f"{context}.json").read_text(encoding="utf-8")
    )


def validate_inputs(root: Path, out: Path, contexts: list[str]) -> dict:
    manifest = load_manifest(root)
    rows = []
    for event in manifest["events"]:
        event_id = event["event_id"]
        gold_env = load_env(root, event_id, "action_conditioned_compact")
        gold = fresh_gold(gold_env)
        for context in contexts:
            env = load_env(root, event_id, context)
            assert_no_evaluator_leakage(env)
            rows.append(
                {
                    "event_id": event_id,
                    "context_mode": context,
                    "current_required_period_s": int(
                        env["task_contract"]["desired_state"]["required_period_s"]
                    ),
                    "candidate_required_period_s": (
                        env.get("candidate_action_context") or {}
                    ).get("required_period_s"),
                    "protocol_json_bytes": len(
                        json.dumps(
                            env,
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        ).encode()
                    ),
                    "gold_supported_config_invocations": len(gold),
                    "physical_consequence_ref": event.get("physical_consequence_ref"),
                }
            )
    result = {
        "stage": "validate",
        "generated_at": datetime.now(UTC).isoformat(),
        "input_root": str(root),
        "contexts": contexts,
        "rows": rows,
        "claim_ceiling": "Frozen-input validation only; no model-quality claim.",
    }
    dump(out / "validate.json", result)
    return result


def run_r1(root: Path, out: Path, args, contexts: list[str]) -> dict:
    manifest = load_manifest(root)
    backend, base_url = real_backend(args)
    rows = []
    for event in manifest["events"]:
        event_id = event["event_id"]
        gold_env = load_env(root, event_id, "action_conditioned_compact")
        gold = fresh_gold(gold_env)
        for context in contexts:
            row_path = out / "r1" / event_id / f"{context}.json"
            if args.resume and row_path.exists():
                rows.append(json.loads(row_path.read_text(encoding="utf-8")))
                continue
            env = load_env(root, event_id, context)
            assert_no_evaluator_leakage(env)
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a communication-operations planner. Follow the supplied typed "
                        "protocol exactly. The current task_contract is authoritative. Return one "
                        "JSON object matching output_schema and do not add prose."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(env, ensure_ascii=False, sort_keys=True),
                },
            ]
            t0 = time.perf_counter()
            output_text = backend.complete(messages)
            latency_ms = (time.perf_counter() - t0) * 1000.0
            try:
                raw = parse_backend_json(output_text)
                evaluation = evaluate_decision(raw, env, gold, gold_env=gold_env)
                error = None
            except Exception as exc:
                evaluation = {"valid_schema": False}
                error = f"{type(exc).__name__}: {exc}"
            row = {
                "event_id": event_id,
                "context_mode": context,
                "model": args.model,
                "base_url": base_url,
                "latency_ms": latency_ms,
                "provider_metadata": getattr(backend, "last_metadata", None),
                "evaluation": evaluation,
                "physical_consequence_ref": event.get("physical_consequence_ref"),
                "error": error,
                "raw_output": output_text,
            }
            rows.append(row)
            dump(row_path, row)
    result = {
        "stage": "r1",
        "generated_at": datetime.now(UTC).isoformat(),
        "model": args.model,
        "base_url": base_url,
        "generation": {
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "reasoning_effort": args.reasoning_effort,
            "response_format": "json_object",
        },
        "contexts": contexts,
        "rows": rows,
        "claim_ceiling": (
            "Frozen O5 event-context model diagnosis only; full simulator continuation remains separate."
        ),
    }
    dump(out / "r1" / "summary.json", result)
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=("validate", "r1"), default="validate")
    ap.add_argument("--model", default=None)
    ap.add_argument("--contexts", default=",".join(DEFAULT_CONTEXTS))
    ap.add_argument("--input-root", default=str(DEFAULT_INPUT))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--api-key-env", default="OPENAI_API_KEY")
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--reasoning-effort", choices=("low", "high", "max"), default="low")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()
    contexts = [x.strip() for x in args.contexts.split(",") if x.strip()]
    root, out = Path(args.input_root), Path(args.out)
    config = {
        "stage": args.stage,
        "model": args.model,
        "contexts": contexts,
        "input_root": str(root),
        "out": str(out),
        "base_url": args.base_url or os.environ.get("OPENAI_BASE_URL"),
        "api_key_present": bool(os.environ.get(args.api_key_env)),
        "resume": args.resume,
        "generation": {
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "reasoning_effort": args.reasoning_effort,
            "response_format": "json_object",
        },
    }
    if args.dry_run:
        print(json.dumps(config, ensure_ascii=False, indent=2))
        return 0
    if args.stage == "r1" and not args.model:
        raise SystemExit("--model required for r1")
    result = (
        validate_inputs(root, out, contexts)
        if args.stage == "validate"
        else run_r1(root, out, args, contexts)
    )
    print(json.dumps({"out": str(out), "result": result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
