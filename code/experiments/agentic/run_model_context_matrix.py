#!/usr/bin/env python3
"""Freeze and evaluate model-facing context baselines on the same Agent runtime.

Workflow:
  freeze -> R1 frozen-input diagnosis -> selected R3 full-physics runs.

No scripted backend is ever substituted for a missing real endpoint/key.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import statistics
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
):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from agentic_communication.episodes import (  # noqa: E402
    o2_localized_risk_escalation_task,
    o2_risk_escalation_task,
)
from agentic_communication.metrics import (  # noqa: E402
    communication_metrics,
    metric_delta,
    physical_signature,
)
from agentic_communication.model_protocol import (  # noqa: E402
    PROTOCOL_REVISION,
    protocol_bytes,
    protocol_hash,
)
from agentic_communication.planner import (  # noqa: E402
    BackendPlannerConsumer,
    BudgetedPlannerConsumer,
    DeterministicComplyPlannerConsumer,
)
from agentic_communication.r1_evaluation import evaluate_r1_consumers  # noqa: E402
from agentic_communication.replay import audit_trace, frozen_r1_inputs, load_trace  # noqa: E402
from agentic_communication.run import run_agentic_episode, run_reference_comply  # noqa: E402


DEFAULT_CONTEXTS = ("task_conditioned", "full_dump", "generic_react")
SUPPORTED_CONTEXTS = DEFAULT_CONTEXTS + (
    "action_conditioned",
    "action_conditioned_compact",
    "action_candidates_full_dump",
)


def _safe(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in value)


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _task(variant: str):
    return o2_risk_escalation_task() if variant == "global" else o2_localized_risk_escalation_task()


def freeze_inputs(*, out: Path, variant: str, seed: int, contexts: list[str]) -> dict:
    task = _task(variant)
    reference, _, _ = run_reference_comply(seed=seed, operational_task=task)
    rows = []
    for mode in contexts:
        result, policy, _, _ = run_agentic_episode(
            seed=seed,
            operational_task=task,
            context_mode=mode,
            planner_consumer=DeterministicComplyPlannerConsumer(),
        )
        if physical_signature(reference) != physical_signature(result):
            raise RuntimeError(f"frozen-input conformance failed for {mode}")
        trace = out / "frozen_inputs" / f"{mode}.jsonl"
        policy.trace.write_jsonl(trace)
        replay = audit_trace(trace, context_mode=mode)
        if not replay.get("passed"):
            raise RuntimeError(f"replay audit failed for {mode}: {replay}")
        records = frozen_r1_inputs(load_trace(trace))
        sizes = [len(protocol_bytes(r.assembly)) for r in records]
        rows.append(
            {
                "context_mode": mode,
                "trace": str(trace.relative_to(ROOT)),
                "trace_sha256": _sha(trace),
                "turns": len(records),
                "protocol_hashes": [protocol_hash(r.assembly) for r in records],
                "protocol_bytes_mean": statistics.fmean(sizes) if sizes else 0.0,
                "protocol_bytes_max": max(sizes) if sizes else 0,
                "physical_equal_legacy": True,
                "replay_audit": replay,
            }
        )
    manifest = {
        "schema_revision": "1",
        "mode": "frozen_model_context_inputs",
        "generator": "code/experiments/agentic/run_model_context_matrix.py",
        "protocol_revision": PROTOCOL_REVISION,
        "variant": variant,
        "seed": seed,
        "task": task.model_dump(mode="json"),
        "contexts": contexts,
        "claim_ceiling": (
            "Input-freeze/conformance only: context variants share the same Operational Task, "
            "capability surface and paired physical reference. No model-quality claim."
        ),
        "rows": rows,
    }
    _dump(out / "frozen_input_manifest.json", manifest)
    return manifest


def _real_backend(args):
    base_url = args.base_url or os.environ.get("OPENAI_BASE_URL")
    api_key = os.environ.get(args.api_key_env)
    if not base_url:
        raise SystemExit("OPENAI_BASE_URL/--base-url is required; no implicit provider endpoint")
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
    return backend, base_url


def run_r1(*, out: Path, input_root: Path, args, contexts: list[str]) -> dict:
    backend, base_url = _real_backend(args)
    gold = DeterministicComplyPlannerConsumer()
    rows = {}
    for mode in contexts:
        trace = input_root / "frozen_inputs" / f"{mode}.jsonl"
        if not trace.is_file():
            raise RuntimeError(f"frozen trace missing: {trace}; run --stage freeze first")
        candidate = BackendPlannerConsumer(
            backend,
            consumer_id=f"matrix:r1:{mode}:{args.model}",
            provider=str(getattr(backend, "name", "openai-compatible")),
            model=args.model,
        )
        turns, aggregate = evaluate_r1_consumers(
            load_trace(trace),
            candidate=candidate,
            gold=gold,
            limit=args.r1_limit,
        )
        payload = {
            "mode": "R1_frozen_model_input",
            "generated_at": datetime.now(UTC).isoformat(),
            "model": args.model,
            "base_url": base_url,
            "context_mode": mode,
            "trace": str(trace.relative_to(ROOT)),
            "trace_sha256": _sha(trace),
            "protocol_revision": PROTOCOL_REVISION,
            "aggregate": aggregate,
            "turns": [asdict(x) for x in turns],
        }
        _dump(out / "r1" / f"{mode}.json", payload)
        rows[mode] = aggregate
    summary = {
        "stage": "R1",
        "model": args.model,
        "contexts": rows,
        "claim_ceiling": "Frozen-input model diagnostics only; no physical consequence claim.",
    }
    _dump(out / "r1" / "summary.json", summary)
    return summary


def run_r3(*, out: Path, args, contexts: list[str], seeds: list[int]) -> dict:
    backend, base_url = _real_backend(args)
    task = _task(args.variant)
    rows = []
    for mode in contexts:
        for seed in seeds:
            reference, _, _ = run_reference_comply(seed=seed, operational_task=task)
            base = BackendPlannerConsumer(
                backend,
                consumer_id=f"matrix:r3:{mode}:{args.model}",
                provider=str(getattr(backend, "name", "openai-compatible")),
                model=args.model,
            )
            consumer = BudgetedPlannerConsumer(base, args.max_model_calls)
            result, policy, _, _ = run_agentic_episode(
                seed=seed,
                operational_task=task,
                context_mode=mode,
                planner_consumer=consumer,
            )
            run_dir = out / "r3" / mode / f"seed-{seed:03d}"
            trace = run_dir / "runtime_trace.jsonl"
            policy.trace.write_jsonl(trace)
            replay = audit_trace(trace, context_mode=mode)
            row = {
                "context_mode": mode,
                "seed": seed,
                "model": args.model,
                "base_url": base_url,
                "model_calls_consumed": consumer.calls,
                "communication_metrics": result["agentic"]["communication_metrics"],
                "agent_metrics": result["agentic"]["agent_metrics"],
                "delta_vs_legacy": metric_delta(
                    result["agentic"]["communication_metrics"],
                    communication_metrics(reference),
                ),
                "physical_equal_legacy": physical_signature(result) == physical_signature(reference),
                "replay_audit": replay,
                "trace": str(trace.relative_to(ROOT)),
                "trace_sha256": _sha(trace),
            }
            _dump(run_dir / "summary.json", row)
            rows.append(row)
    summary = {
        "stage": "R3",
        "generated_at": datetime.now(UTC).isoformat(),
        "model": args.model,
        "variant": args.variant,
        "contexts": contexts,
        "seeds": seeds,
        "max_model_calls": args.max_model_calls,
        "runs": rows,
        "claim_ceiling": (
            "Model-specific full-simulator results on the frozen Operational Task/context protocol; "
            "interpret communication metrics jointly with model/tool/runtime diagnostics."
        ),
    }
    _dump(out / "r3" / "summary.json", summary)
    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=None)
    ap.add_argument("--stage", choices=("freeze", "r1", "r3", "both"), default="freeze")
    ap.add_argument("--variant", choices=("global", "localized"), default="global")
    ap.add_argument("--freeze-seed", type=int, default=0)
    ap.add_argument("--seeds", default="0")
    ap.add_argument("--contexts", default=",".join(DEFAULT_CONTEXTS))
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--api-key-env", default="OPENAI_API_KEY")
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--r1-limit", type=int, default=None)
    ap.add_argument("--max-model-calls", type=int, default=128)
    ap.add_argument("--input-root", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    contexts = [x.strip() for x in args.contexts.split(",") if x.strip()]
    bad = sorted(set(contexts) - set(SUPPORTED_CONTEXTS))
    if bad:
        raise SystemExit(f"unsupported contexts: {bad}")
    seeds = [int(x) for x in args.seeds.split(",") if x.strip()]
    if args.stage != "freeze" and not args.model:
        raise SystemExit("--model is required for r1/r3/both stages")
    input_root = (
        Path(args.input_root)
        if args.input_root
        else ROOT
        / "results"
        / "agentic"
        / "model-context-inputs-v1"
        / args.variant
        / f"seed-{args.freeze_seed:03d}"
    )
    out = (
        Path(args.out)
        if args.out
        else (
            ROOT
            / "results"
            / "agentic"
            / "model-context-matrix"
            / _safe(args.model or "freeze")
            / args.variant
        )
    )
    config = {
        "model": args.model,
        "stage": args.stage,
        "variant": args.variant,
        "freeze_seed": args.freeze_seed,
        "r3_seeds": seeds,
        "contexts": contexts,
        "protocol_revision": PROTOCOL_REVISION,
        "input_root": str(input_root),
        "base_url": args.base_url or os.environ.get("OPENAI_BASE_URL"),
        "api_key_env": args.api_key_env,
        "api_key_present": bool(os.environ.get(args.api_key_env)),
        "r1_limit": args.r1_limit,
        "max_model_calls": args.max_model_calls,
        "out": str(out),
    }
    if args.dry_run:
        print(json.dumps(config, ensure_ascii=False, indent=2))
        return 0


    if args.stage in {"r1", "r3", "both"}:
        # Fail before any expensive simulator/input-freeze work when credentials
        # are absent. There is deliberately no scripted model fallback.
        if not (args.base_url or os.environ.get("OPENAI_BASE_URL")):
            raise SystemExit("OPENAI_BASE_URL/--base-url is required; no implicit provider endpoint")
        if not os.environ.get(args.api_key_env):
            raise SystemExit(f"{args.api_key_env} is not set; no scripted fallback is allowed")

    if args.stage == "freeze":
        input_root.mkdir(parents=True, exist_ok=True)
        result = freeze_inputs(
            out=input_root, variant=args.variant, seed=args.freeze_seed, contexts=contexts
        )
        print(json.dumps({"input_root": str(input_root), "result": result}, ensure_ascii=False, indent=2))
        return 0

    out.mkdir(parents=True, exist_ok=True)
    _dump(out / "experiment_config.json", config)
    if args.stage == "r1":
        if not (input_root / "frozen_input_manifest.json").is_file():
            freeze_inputs(
                out=input_root, variant=args.variant, seed=args.freeze_seed, contexts=contexts
            )
        result = run_r1(out=out, input_root=input_root, args=args, contexts=contexts)
    elif args.stage == "r3":
        result = run_r3(out=out, args=args, contexts=contexts, seeds=seeds)
    else:
        if not (input_root / "frozen_input_manifest.json").is_file():
            freeze_inputs(
                out=input_root, variant=args.variant, seed=args.freeze_seed, contexts=contexts
            )
        r1 = run_r1(out=out, input_root=input_root, args=args, contexts=contexts)
        r3 = run_r3(out=out, args=args, contexts=contexts, seeds=seeds)
        result = {"r1": r1, "r3": r3}
    print(json.dumps({"out": str(out), "result": result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
