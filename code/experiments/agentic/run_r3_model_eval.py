#!/usr/bin/env python3
"""Run a real model consumer through R3 full physics for O2 benchmark episodes."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import re
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
    benchmark_episode_catalog,
    o2_localized_risk_escalation_task,
    o2_risk_escalation_task,
)
from agentic_communication.metrics import metric_delta, physical_signature  # noqa: E402
from agentic_communication.model_protocol import PROTOCOL_REVISION  # noqa: E402
from agentic_communication.planner import (  # noqa: E402
    ActionConditionedReferencePlannerConsumer,
    BackendPlannerConsumer,
    BudgetedPlannerConsumer,
)
from agentic_communication.replay import audit_trace  # noqa: E402
from agentic_communication.run import run_agentic_episode, run_reference_comply  # noqa: E402


def _safe_model_name(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in name)


def _load_shell_export(name: str) -> str | None:
    path = Path.home() / ".bashrc"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="ignore")
    matches = re.findall(rf"export\s+{re.escape(name)}=([^\s#]+)", text)
    if not matches:
        return None
    return matches[-1].strip().strip('"').strip("'")


def _invocation_key(row: dict) -> tuple[str, str, str]:
    capability_id = str(row.get("capability_id", ""))
    resource = str(row.get("resource", ""))
    arguments = dict(row.get("canonical_arguments") or {})
    # Config capability schemas accept node_id, but the planner contract also
    # carries the target as ``resource``.  Treat the redundant, matching node_id
    # as the same invocation semantics as Runtime candidate plans that omit it.
    if capability_id.startswith("communication.config.") and arguments.get("node_id") == resource:
        arguments.pop("node_id", None)
    return (
        capability_id,
        resource,
        json.dumps(
            arguments,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
    )


def _planner_behavior_audit(policy) -> dict:
    """Separate effect-scope fidelity from optional observation overhead."""
    current_candidate: dict = {}
    current_semantic_reference: dict = {}
    turns: list[dict] = []
    failed_attempts = 0
    successful_attempts = 0

    for event in policy.trace.events:
        if event.event_type == "model_attempt":
            if event.payload.get("status") == "failed":
                failed_attempts += 1
            elif event.payload.get("status") == "succeeded":
                successful_attempts += 1
            continue
        if event.event_type == "prompt_assembly":
            fragments = {
                str(row.get("kind", "")): row.get("content")
                for row in event.payload.get("fragments", [])
                if isinstance(row, dict)
            }
            candidate = fragments.get("candidate_action_context")
            current_candidate = candidate if isinstance(candidate, dict) else {}
            continue
        if event.event_type == "planner_semantic_reference":
            current_semantic_reference = dict(event.payload or {})
            continue
        if event.event_type != "planner_decision":
            continue

        actual = list(event.payload.get("invocations") or [])
        actual_effect = [
            row
            for row in actual
            if str(row.get("capability_id", "")).startswith(
                ("communication.config.", "communication.fallback.")
            )
        ]
        local_obs = [
            row for row in actual
            if str(row.get("capability_id", "")).startswith("communication.center.")
        ]
        remote_obs = [
            row for row in actual
            if str(row.get("capability_id", "")).startswith("communication.gateway.")
        ]

        primary_plan_id = current_semantic_reference.get("primary_plan_id")
        expected_effect = list(
            current_semantic_reference.get("expected_effect_invocations") or []
        )
        reference_source = current_semantic_reference.get("source")
        if not reference_source:
            # Backward-compatible fallback for older action-conditioned traces.
            plans = list(current_candidate.get("candidate_plans") or [])
            sufficiency = current_candidate.get("decision_sufficiency") or {}
            primary_plan_id = sufficiency.get("primary_plan_id")
            expected_plan = next(
                (row for row in plans if row.get("plan_id") == primary_plan_id),
                None,
            )
            if expected_plan is None:
                supported_effect = [
                    row
                    for row in plans
                    if row.get("feasibility") == "supported" and row.get("invocations")
                ]
                expected_plan = supported_effect[0] if len(supported_effect) == 1 else None
            expected_effect = list((expected_plan or {}).get("invocations") or [])
            reference_source = "model_visible_candidate_context" if current_candidate else "none"

        expected_set = {_invocation_key(row) for row in expected_effect}
        actual_set = {_invocation_key(row) for row in actual_effect}
        turns.append(
            {
                "t_s": int(event.t_s),
                "primary_plan_id": primary_plan_id,
                "semantic_reference_source": reference_source,
                "effect_scope_exact": actual_set == expected_set,
                "expected_effect_invocations": len(expected_set),
                "actual_effect_invocations": len(actual_set),
                "missing_effect_invocations": [list(row) for row in sorted(expected_set - actual_set)],
                "unexpected_effect_invocations": [list(row) for row in sorted(actual_set - expected_set)],
                "local_observation_invocations": len(local_obs),
                "remote_observation_invocations": len(remote_obs),
                "stop": bool(event.payload.get("stop")),
            }
        )

    return {
        "planner_decision_turns": len(turns),
        "successful_model_attempts": successful_attempts,
        "failed_model_attempts": failed_attempts,
        "effect_scope_exact_turns": sum(row["effect_scope_exact"] for row in turns),
        "effect_scope_inexact_turns": sum(not row["effect_scope_exact"] for row in turns),
        "local_observation_invocations": sum(row["local_observation_invocations"] for row in turns),
        "remote_observation_invocations": sum(row["remote_observation_invocations"] for row in turns),
        "turns": turns,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--variant", choices=("global", "localized"), default="global")
    ap.add_argument("--episode", choices=sorted(benchmark_episode_catalog()), default=None)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument(
        "--context-mode",
        choices=("task_conditioned", "full_dump", "generic_react", "action_conditioned_compact"),
        default="task_conditioned",
    )
    ap.add_argument(
        "--planner-replan-mode",
        choices=("every_context", "decision_state"),
        default="every_context",
    )
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--api-key-env", default="OPENAI_API_KEY")
    ap.add_argument(
        "--credential-profile",
        choices=("env", "deepseek_official"),
        default="env",
    )
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--max-model-calls", type=int, default=128)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max-tokens", type=int, default=None)
    ap.add_argument("--reasoning-effort", default=None)
    ap.add_argument("--json-object", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    episode = benchmark_episode_catalog().get(args.episode) if args.episode else None
    task = (
        episode.task
        if episode is not None
        else (
            o2_risk_escalation_task()
            if args.variant == "global"
            else o2_localized_risk_escalation_task()
        )
    )
    simulator_kwargs = dict(episode.simulator_overrides) if episode is not None else None
    if args.credential_profile == "deepseek_official":
        base_url = args.base_url or "https://api.deepseek.com"
        api_key_env = "DEEPSEEK_API_KEY"
        api_key = os.environ.get(api_key_env) or _load_shell_export(api_key_env)
    else:
        base_url = args.base_url or os.environ.get("OPENAI_BASE_URL")
        api_key_env = args.api_key_env
        api_key = os.environ.get(api_key_env)
    key_present = bool(api_key)
    config = {
        "mode": "R3_full_simulator",
        "protocol_revision": PROTOCOL_REVISION,
        "model": args.model,
        "variant": args.variant,
        "episode": args.episode,
        "seed": args.seed,
        "context_mode": args.context_mode,
        "planner_replan_mode": args.planner_replan_mode,
        "max_model_calls": args.max_model_calls,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "reasoning_effort": args.reasoning_effort,
        "json_object": args.json_object,
        "credential_profile": args.credential_profile,
        "base_url": base_url,
        "api_key_env": api_key_env,
        "api_key_present": key_present,
        "operational_task": task.model_dump(mode="json"),
        "dry_run": args.dry_run,
    }
    if args.dry_run:
        print(json.dumps(config, ensure_ascii=False, indent=2))
        return 0
    if not base_url:
        raise SystemExit("OPENAI_BASE_URL/--base-url is required; no implicit provider endpoint")
    if not api_key:
        raise SystemExit(f"{api_key_env} is not set; no scripted fallback is allowed")

    from llm_planner import make_real_backend  # noqa: E402

    backend, reason = make_real_backend(
        model=args.model,
        base_url=base_url,
        api_key=api_key,
        timeout=args.timeout,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        reasoning_effort=args.reasoning_effort,
        json_object=args.json_object,
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

    reference, _, _ = run_reference_comply(
        seed=args.seed,
        operational_task=task,
        simulator_kwargs=simulator_kwargs,
    )
    # Evaluator-only candidate reference.  All Context arms are compared with
    # the same declared candidate surface; the reference representation is never
    # exposed to the tested model.
    candidate_reference, _, _, _ = run_agentic_episode(
        seed=args.seed,
        operational_task=task,
        context_mode="action_conditioned_compact",
        planner_consumer=ActionConditionedReferencePlannerConsumer(),
        planner_replan_mode=args.planner_replan_mode,
        simulator_kwargs=simulator_kwargs,
    )
    result, policy, _, _ = run_agentic_episode(
        seed=args.seed,
        operational_task=task,
        context_mode=args.context_mode,
        planner_consumer=consumer,
        planner_replan_mode=args.planner_replan_mode,
        simulator_kwargs=simulator_kwargs,
    )
    safe_model = _safe_model_name(args.model)
    out = (
        Path(args.out)
        if args.out
        else ROOT
        / "results"
        / "agentic"
        / "r3-model"
        / safe_model
        / (args.episode.lower() if args.episode else args.variant)
        / f"seed-{args.seed:03d}"
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
        "physical_equal_candidate_reference": (
            physical_signature(result) == physical_signature(candidate_reference)
        ),
        "model_calls_consumed": consumer.calls,
        "planner_behavior_audit": _planner_behavior_audit(policy),
        "replay_audit": replay,
        "trace": str(trace_path),
    }
    # Reference runs do not carry agentic wrappers; compute communication delta directly.
    from agentic_communication.metrics import communication_metrics  # noqa: E402
    payload["delta_vs_legacy"] = metric_delta(
        result["agentic"]["communication_metrics"], communication_metrics(reference)
    )
    payload["delta_vs_candidate_reference"] = metric_delta(
        result["agentic"]["communication_metrics"],
        communication_metrics(candidate_reference),
    )
    payload["candidate_reference"] = {
        "context_mode": "action_conditioned_compact",
        "planner": "ActionConditionedReferencePlannerConsumer",
        "model_visible_to_test_arm": False,
    }
    (out / "summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"out": str(out), **payload}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
