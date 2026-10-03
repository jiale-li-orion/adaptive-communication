#!/usr/bin/env python3
"""O5 task-transition Context ablation: structural validation and live-model R1.

Inputs are frozen protocol envelopes, including deliberately stale/full-history
counterfactuals.  They are therefore not round-tripped through PromptAssembly.
"""
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
    CODE / "v3joint",
    CODE / "instance",
    CODE / "monitoring",
    CODE / "physics",
    CODE / "runtime",
    CODE / "experiments",
    CODE / "analysis",
):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from agentic_communication.model_protocol import assert_no_evaluator_leakage  # noqa: E402
from agentic_communication.runtime_contracts import PlannerDecisionProposal  # noqa: E402


DEFAULT_INPUT = (
    ROOT
    / "results"
    / "agentic"
    / "o5-context-update-ablation-v1"
)
DEFAULT_OUT = ROOT / "results" / "agentic" / "o5-context-update-model-probe-v1"
VARIANTS = (
    "fresh_rebuild",
    "full_history",
    "naive_incremental_cache",
    "revision_aware_update",
)


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def transition_dirs(root: Path) -> list[Path]:
    return sorted(p for p in root.iterdir() if p.is_dir() and "__to__" in p.name)


def current_period(env: dict) -> int:
    return int(env["task_contract"]["desired_state"]["required_period_s"])


def task_targets(env: dict) -> list[str]:
    candidate_scope = list(
        (env.get("candidate_action_context") or {}).get("action_scope") or []
    )
    if candidate_scope:
        return sorted({str(x) for x in candidate_scope})
    inventory = list(env.get("resource_inventory") or [])
    if inventory:
        return sorted({str(x) for x in inventory})
    # TaskContract target_resources may contain a logical aggregate such as
    # ``monitoring-network``.  Only concrete resources can receive config calls.
    return sorted(
        {
            str(x)
            for x in env["task_contract"].get("target_resources", [])
            if str(x) != "monitoring-network"
        }
    )


def legal_caps(env: dict) -> set[str]:
    return {
        str(x.get("capability_id"))
        for x in env.get("capabilities", [])
        if x.get("capability_id")
    }


def fresh_gold(env: dict) -> list[dict]:
    plans = (env.get("candidate_action_context") or {}).get("candidate_plans", [])
    plan = next(
        (
            p
            for p in plans
            if p.get("plan_id") == "install_required_profile"
            and p.get("feasibility") == "supported"
        ),
        None,
    )
    return [] if plan is None else list(plan.get("invocations") or [])


def inv_key(row: dict) -> tuple[str, str, str]:
    cid = str(row.get("capability_id"))
    resource = str(row.get("resource"))
    args = dict(row.get("canonical_arguments") or {})
    if cid in {
        "communication.config.set_sampling_interval",
        "communication.config.set_report_period",
    }:
        # ``resource`` already binds the target node.  Some model backends repeat
        # that binding as canonical_arguments.node_id while the runtime compiler
        # emits only target_s.  Treat those forms as the same device effect.
        return (cid, resource, f"target_s={args.get('target_s')}")
    return (
        cid,
        resource,
        json.dumps(args, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
    )


def config_target(row: dict) -> int | None:
    cid = str(row.get("capability_id", ""))
    if cid not in {
        "communication.config.set_sampling_interval",
        "communication.config.set_report_period",
    }:
        return None
    value = (row.get("canonical_arguments") or {}).get("target_s")
    return None if value is None else int(value)


def invocation_kind(row: dict) -> str:
    cid = str(row.get("capability_id", ""))
    if cid.startswith("communication.config."):
        return "config"
    if cid.startswith("communication.fallback."):
        return "fallback"
    if cid in {
        "communication.center.full_dump",
        "communication.center.node_report",
        "communication.gateway.node_report",
        "communication.gateway.primary_health",
        "communication.gateway.receipt_summary",
    }:
        return "observe"
    return "other"


def expected_primary_class(env: dict) -> str:
    plans = (env.get("candidate_action_context") or {}).get("candidate_plans", [])
    supported = [p for p in plans if p.get("feasibility") == "supported"]
    if any(
        p.get("kind") == "configuration_update" and list(p.get("invocations") or [])
        for p in supported
    ):
        return "act_config"
    if any(p.get("kind") in {"wait_or_keep", "hold"} for p in supported):
        return "wait"
    if any(str(need.get("status")) == "open" for need in env.get("evidence_needs", [])):
        return "query"
    return "stop"


def decision_class(invocations: list[dict], *, stop: bool) -> str:
    kinds = [invocation_kind(row) for row in invocations]
    if "config" in kinds:
        return "act_config"
    if "fallback" in kinds:
        return "act_fallback"
    if "observe" in kinds:
        return "query"
    if stop:
        return "stop"
    return "empty"


def evaluate_decision(
    raw: dict,
    env: dict,
    gold: list[dict],
    *,
    gold_env: dict | None = None,
) -> dict:
    proposal = PlannerDecisionProposal.model_validate(raw)
    obj = proposal.model_dump(mode="json")
    inv = list(obj.get("invocations") or [])
    expected_class = expected_primary_class(gold_env or env)
    actual_class = decision_class(inv, stop=bool(obj.get("stop")))
    period = current_period(env)
    caps = legal_caps(env)
    targets = set(task_targets(env))
    stale, illegal, out_scope = [], [], []
    for row in inv:
        cid = str(row.get("capability_id"))
        if cid not in caps:
            illegal.append(cid)
        resource = str(row.get("resource"))
        if cid.startswith("communication.config.") and resource not in targets:
            out_scope.append(resource)
        target = config_target(row)
        if target is not None and target != period:
            stale.append(
                {
                    "capability_id": cid,
                    "resource": resource,
                    "target_s": target,
                }
            )

    pred = {
        inv_key(x)
        for x in inv
        if str(x.get("capability_id", "")).startswith("communication.config.")
    }
    truth = {
        inv_key(x)
        for x in gold
        if str(x.get("capability_id", "")).startswith("communication.config.")
    }
    tp = len(pred & truth)
    precision = tp / len(pred) if pred else (1.0 if not truth else 0.0)
    recall = tp / len(truth) if truth else 1.0
    counts = {kind: 0 for kind in ("config", "fallback", "observe", "other")}
    for row in inv:
        counts[invocation_kind(row)] += 1
    conditional_fallback_open = any(
        p.get("kind") == "fallback"
        and p.get("feasibility") == "conditional"
        and bool(p.get("unresolved_conditions"))
        for p in (env.get("candidate_action_context") or {}).get("candidate_plans", [])
    )
    return {
        "valid_schema": True,
        "stop": bool(obj.get("stop")),
        "expected_primary_class": expected_class,
        "expected_class_source": "shared_gold_context" if gold_env is not None else "input_context",
        "decision_class": actual_class,
        "primary_class_correct": actual_class == expected_class,
        "invocation_count": len(inv),
        "config_invocation_count": counts["config"],
        "observation_invocation_count": counts["observe"],
        "fallback_invocation_count": counts["fallback"],
        "illegal_capabilities": sorted(set(illegal)),
        "out_of_scope_resources": sorted(set(out_scope)),
        "stale_config_targets": stale,
        "revision_authority_correct": not stale and not illegal and not out_scope,
        "observation_only_delay": expected_class == "act_config" and actual_class == "query",
        "orthogonal_observation_count_while_config_supported": (
            counts["observe"] if expected_class == "act_config" else 0
        ),
        "conditional_fallback_without_resolved_guard": (
            conditional_fallback_open and counts["fallback"] > 0
        ),
        "gold_config_invocations": len(truth),
        "pred_config_invocations": len(pred),
        "config_precision_vs_fresh_gold": precision,
        "config_recall_vs_fresh_gold": recall,
        "reason_codes": obj.get("reason_codes") or [],
    }


def authority_precedence_baseline(env: dict) -> dict:
    """Strong deterministic revision baseline: current Task authority always wins.

    It deliberately over-applies the idempotent profile to all Task targets when
    compact context has no raw evidence.  That makes it a semantic upper/reference
    baseline for stale-context resistance, not an efficient communication policy.
    """
    period = current_period(env)
    invocations = []
    for nid in task_targets(env):
        invocations.append(
            {
                "capability_id": "communication.config.set_sampling_interval",
                "resource": nid,
                "canonical_arguments": {"target_s": period},
            }
        )
        invocations.append(
            {
                "capability_id": "communication.config.set_report_period",
                "resource": nid,
                "canonical_arguments": {"target_s": period},
            }
        )
    return {
        "stop": False,
        "invocations": invocations,
        "reason_codes": ["current-task-authority-precedence"],
    }


def structural_row(env: dict, gold: list[dict]) -> dict:
    assert_no_evaluator_leakage(env)
    baseline = authority_precedence_baseline(env)
    return {
        "current_required_period_s": current_period(env),
        "candidate_required_period_s": (
            env.get("candidate_action_context") or {}
        ).get("required_period_s"),
        "gold_supported_config_invocations": len(gold),
        "protocol_json_bytes": len(
            json.dumps(
                env,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ),
        "authority_precedence_baseline": evaluate_decision(baseline, env, gold, gold_env=env),
    }


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


def validate_inputs(root: Path, out: Path) -> dict:
    rows = []
    for transition in transition_dirs(root):
        fresh = json.loads((transition / "fresh_rebuild.json").read_text())
        gold = fresh_gold(fresh)
        for variant in VARIANTS:
            env = json.loads((transition / f"{variant}.json").read_text())
            rows.append(
                {
                    "transition": transition.name,
                    "variant": variant,
                    **structural_row(env, gold),
                }
            )
    result = {
        "stage": "validate",
        "generated_at": datetime.now(UTC).isoformat(),
        "input_root": str(root),
        "rows": rows,
        "claim_ceiling": (
            "Pre-model structural/schema validation only; no model or physical consequence claim."
        ),
    }
    dump(out / "validate.json", result)
    return result


def run_r1(root: Path, out: Path, args) -> dict:
    backend, base_url = real_backend(args)
    rows = []
    for transition in transition_dirs(root):
        fresh = json.loads((transition / "fresh_rebuild.json").read_text())
        gold = fresh_gold(fresh)
        for variant in VARIANTS:
            env = json.loads((transition / f"{variant}.json").read_text())
            assert_no_evaluator_leakage(env)
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a communication-operations planner. Follow the supplied typed "
                        "protocol exactly. The current task_contract is authoritative over cached "
                        "or historical state. Return one JSON object matching output_schema and do "
                        "not add prose."
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
                evaluation = evaluate_decision(raw, env, gold, gold_env=fresh)
                error = None
            except Exception as exc:
                evaluation = {"valid_schema": False}
                error = f"{type(exc).__name__}: {exc}"
            row = {
                "transition": transition.name,
                "variant": variant,
                "model": args.model,
                "base_url": base_url,
                "latency_ms": latency_ms,
                "provider_metadata": getattr(backend, "last_metadata", None),
                "evaluation": evaluation,
                "error": error,
                "raw_output": output_text,
            }
            rows.append(row)
            dump(out / "r1" / transition.name / f"{variant}.json", row)
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
        "rows": rows,
        "claim_ceiling": (
            "Frozen transition-input model diagnosis only; R3 physical consequence remains separate."
        ),
    }
    dump(out / "r1" / "summary.json", result)
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=("validate", "r1"), default="validate")
    ap.add_argument("--model", default=None)
    ap.add_argument("--input-root", default=str(DEFAULT_INPUT))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--api-key-env", default="OPENAI_API_KEY")
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--reasoning-effort", choices=("low", "high", "max"), default="low")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = Path(args.input_root)
    out = Path(args.out)
    config = {
        "stage": args.stage,
        "model": args.model,
        "input_root": str(root),
        "out": str(out),
        "base_url": args.base_url or os.environ.get("OPENAI_BASE_URL"),
        "api_key_present": bool(os.environ.get(args.api_key_env)),
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
    result = validate_inputs(root, out) if args.stage == "validate" else run_r1(root, out, args)
    print(json.dumps({"out": str(out), "result": result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
