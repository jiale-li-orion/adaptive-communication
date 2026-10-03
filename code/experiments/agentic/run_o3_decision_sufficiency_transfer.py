#!/usr/bin/env python3
"""Validate/run the O3 Decision Sufficiency transfer-safety model probe."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[3]
CODE = ROOT / "code"
for p in (CODE, CODE / "monitoring", CODE / "experiments"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from agentic_communication.runtime_contracts import PlannerDecisionProposal  # noqa: E402


DEFAULT_INPUT = ROOT / "results" / "agentic" / "o3-decision-sufficiency-transfer-devset-v1"
DEFAULT_OUT = ROOT / "results" / "agentic" / "o3-decision-sufficiency-transfer-model-probe-v1"


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_backend_json(text: str) -> dict:
    raw = (text or "").strip()
    if raw.startswith("```") and raw.endswith("```"):
        lines = raw.splitlines()
        if lines and lines[0].strip().lower() in {"```", "```json"}:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise TypeError("model output must be one JSON object")
    return value


def decision_class(proposal: PlannerDecisionProposal) -> str:
    kinds = []
    for inv in proposal.invocations:
        cid = inv.capability_id
        if cid.startswith("communication.config."):
            kinds.append("config")
        elif cid.startswith("communication.fallback."):
            kinds.append("fallback")
        elif cid.startswith("communication.gateway.") or cid.startswith("communication.center."):
            kinds.append("query")
        else:
            kinds.append("other")
    if "fallback" in kinds:
        return "act_fallback"
    if "config" in kinds:
        return "act_config"
    if "query" in kinds:
        return "query"
    if proposal.stop:
        return "stop"
    return "empty"


def evaluate(raw: dict, env: dict, expected: str) -> dict:
    proposal = PlannerDecisionProposal.model_validate(raw)
    cls = decision_class(proposal)
    legal = {str(c.get("capability_id")) for c in env.get("capabilities", [])}
    illegal = sorted(
        {
            inv.capability_id
            for inv in proposal.invocations
            if inv.capability_id not in legal
        }
    )
    query_inv = [
        inv for inv in proposal.invocations
        if inv.capability_id.startswith("communication.gateway.")
        or inv.capability_id.startswith("communication.center.")
    ]
    return {
        "valid_schema": True,
        "expected_primary_class": expected,
        "decision_class": cls,
        "primary_class_correct": cls == expected,
        "invocation_count": len(proposal.invocations),
        "query_invocation_count": len(query_inv),
        "illegal_capabilities": illegal,
        "stop": proposal.stop,
        "reason_codes": list(proposal.reason_codes),
    }


def backend(args):
    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        raise SystemExit(f"{args.api_key_env} is not set")
    from llm_planner import make_real_backend  # noqa: E402

    b, reason = make_real_backend(
        model=args.model,
        base_url=args.base_url,
        api_key=api_key,
        timeout=args.timeout,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        reasoning_effort=args.reasoning_effort,
        json_object=True,
    )
    if b is None:
        raise SystemExit(f"model backend unavailable: {reason}")
    return b


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=("validate", "r1"), default="validate")
    ap.add_argument("--input-root", default=str(DEFAULT_INPUT))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--model", default=None)
    ap.add_argument("--contexts", default=None)
    ap.add_argument("--base-url", default="https://api.deepseek.com")
    ap.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max-tokens", type=int, default=8192)
    ap.add_argument("--reasoning-effort", choices=("low", "high", "max"), default="low")
    ap.add_argument("--timeout", type=float, default=90.0)
    args = ap.parse_args()

    root = Path(args.input_root)
    out = Path(args.out)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    contexts = (
        [x.strip() for x in args.contexts.split(",") if x.strip()]
        if args.contexts
        else list(manifest["contexts"])
    )
    unknown = sorted(set(contexts) - set(manifest["contexts"]))
    if unknown:
        raise SystemExit(f"unknown contexts: {unknown}")
    rows = []

    if args.stage == "validate":
        for event in manifest["events"]:
            event_id = event["event_id"]
            expected = manifest["structural_oracle"][event_id]["expected_primary_class"]
            for mode in contexts:
                env = json.loads(
                    (root / "inputs" / event_id / f"{mode}.json").read_text(encoding="utf-8")
                )
                rows.append(
                    {
                        "event_id": event_id,
                        "context_mode": mode,
                        "expected_primary_class": expected,
                        "protocol_json_bytes": len(
                            json.dumps(env, ensure_ascii=False, sort_keys=True).encode("utf-8")
                        ),
                    }
                )
        result = {
            "stage": "validate",
            "generated_at": datetime.now(UTC).isoformat(),
            "rows": rows,
            "structural_oracle": manifest["structural_oracle"],
        }
        dump(out / "validate.json", result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if not args.model:
        raise SystemExit("--model required for r1")
    b = backend(args)
    for event in manifest["events"]:
        event_id = event["event_id"]
        expected = manifest["structural_oracle"][event_id]["expected_primary_class"]
        for mode in contexts:
            env = json.loads(
                (root / "inputs" / event_id / f"{mode}.json").read_text(encoding="utf-8")
            )
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a communication-operations planner. Follow the supplied typed "
                        "protocol exactly. The current task_contract is authoritative. Return one "
                        "JSON object matching output_schema and do not add prose."
                    ),
                },
                {"role": "user", "content": json.dumps(env, ensure_ascii=False, sort_keys=True)},
            ]
            t0 = time.perf_counter()
            text = b.complete(messages)
            latency_ms = (time.perf_counter() - t0) * 1000.0
            try:
                raw = parse_backend_json(text)
                ev = evaluate(raw, env, expected)
                error = None
            except Exception as exc:
                ev = {"valid_schema": False, "expected_primary_class": expected}
                error = f"{type(exc).__name__}: {exc}"
            row = {
                "event_id": event_id,
                "context_mode": mode,
                "model": args.model,
                "latency_ms": latency_ms,
                "provider_metadata": getattr(b, "last_metadata", None),
                "evaluation": ev,
                "error": error,
                "raw_output": text,
            }
            rows.append(row)
            dump(out / "r1" / event_id / f"{mode}.json", row)
    result = {
        "stage": "r1",
        "generated_at": datetime.now(UTC).isoformat(),
        "model": args.model,
        "contexts": contexts,
        "generation": {
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "reasoning_effort": args.reasoning_effort,
        },
        "rows": rows,
        "claim_ceiling": (
            "Three-event single-model transfer-safety diagnosis. It tests whether O5 stopping semantics "
            "preserve query behavior when fallback evidence is genuinely decision-relevant."
        ),
    }
    dump(out / "r1" / "summary.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
