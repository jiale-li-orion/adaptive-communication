#!/usr/bin/env python3
"""Minimal causal probe for Full-Evidence (CF) and no-Sufficiency (CS) variants.

The probe freezes two already-observed v6 decision states:

* O5 seed0 t=14400: task-revision configuration action;
* O6 seed0 t=10860: closed zero-effect hold decision.

The formal v6 Method (M) output is reused from the audited trace.  CR is the
deterministic compiled-checklist consumer.  Only CF and CS issue new model calls.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import UTC, datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
import time


HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
ROOT = HERE.parents[2]
for path in (CODE, CODE / "monitoring", CODE / "runtime"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from agentic_communication.episodes import benchmark_episode_catalog  # noqa: E402
from agentic_communication.metrics import physical_signature  # noqa: E402
from agentic_communication.model_protocol import render_planner_protocol  # noqa: E402
from agentic_communication.planner import (  # noqa: E402
    BackendPlannerConsumer,
    CompiledChecklistPlannerConsumer,
    DeterministicComplyPlannerConsumer,
    _expand_selected_candidate_plan,
    _parse_backend_json,
)
from agentic_communication.replay import frozen_r1_inputs, load_trace  # noqa: E402
from agentic_communication.run import run_agentic_episode, run_reference_comply  # noqa: E402
from agentic_communication.runtime_contracts import (  # noqa: E402
    MaterializedFragment,
    ModelRequest,
    PlannerDecision,
    PlannerDecisionProposal,
    PromptAssembly,
)


FORMAL_ROOT = ROOT / "results" / "agentic" / "main-table-v6-confirmatory" / "deepseek-flash"
DEFAULT_OUT = ROOT / "results" / "agentic" / "causal-interface-probe-v1"
TARGETS = (
    {"task": "o5", "episode": "O5", "seed": 0, "t_s": 14400, "label": "o5-task-revision-action"},
    {"task": "o6", "episode": "O6", "seed": 0, "t_s": 10860, "label": "o6-closed-hold"},
)


def _canonical_bytes(value) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _digest(value) -> str:
    return sha256(_canonical_bytes(value)).hexdigest()


def _load_shell_export(name: str) -> str | None:
    path = Path.home() / ".bashrc"
    if not path.exists():
        return None
    matches = re.findall(
        rf"export\s+{re.escape(name)}=([^\s#]+)",
        path.read_text(encoding="utf-8", errors="ignore"),
    )
    return matches[-1].strip().strip('"').strip("'") if matches else None


def _fragment(assembly: PromptAssembly, kind: str) -> MaterializedFragment:
    rows = [row for row in assembly.fragments if row.kind == kind]
    if len(rows) != 1:
        raise RuntimeError(f"expected exactly one {kind} fragment, got {len(rows)}")
    return rows[0]


def _rebuild_fragment(base: MaterializedFragment, *, content, selection_reason: str) -> MaterializedFragment:
    return MaterializedFragment.build(
        kind=base.kind,
        source_ref=base.source_ref,
        source_revision=base.source_revision,
        trust_class=base.trust_class,
        cache_class=base.cache_class,
        content=content,
        selection_reason=selection_reason,
    )


def _replace_fragment(
    assembly: PromptAssembly,
    *,
    kind: str,
    content,
    selection_reason: str,
) -> PromptAssembly:
    base = _fragment(assembly, kind)
    replacement = _rebuild_fragment(base, content=content, selection_reason=selection_reason)
    fragments = [replacement if row.kind == kind else row for row in assembly.fragments]
    return PromptAssembly.build(
        task_contract_id=assembly.task_contract_id,
        task_run_id=assembly.task_run_id,
        context_manifest_revision=assembly.context_manifest_revision,
        fragments=fragments,
        percept_refs=list(assembly.percept_refs),
    )


def _record_at(policy, t_s: int):
    rows = [row for row in frozen_r1_inputs(policy.trace.events) if int(row.t_s) == int(t_s)]
    if not rows:
        raise RuntimeError(f"no PromptAssembly at t={t_s}")
    return rows[0]


def _saved_method_trace(task: str) -> Path:
    return FORMAL_ROOT / task / "seed-000" / "action_conditioned_compact" / "runtime_trace.jsonl"


def _saved_method_assembly(task: str, t_s: int) -> PromptAssembly:
    rows = [row for row in frozen_r1_inputs(load_trace(_saved_method_trace(task))) if int(row.t_s) == int(t_s)]
    if not rows:
        raise RuntimeError(f"formal v6 trace missing {task} t={t_s}")
    return rows[0].assembly


def _saved_method_decision(task: str, t_s: int) -> dict:
    events = list(load_trace(_saved_method_trace(task)))
    rows = [event.payload for event in events if event.event_type == "planner_decision" and int(event.t_s) == int(t_s)]
    if len(rows) != 1:
        raise RuntimeError(f"formal v6 trace expected one decision at {task} t={t_s}, got {len(rows)}")
    return dict(rows[0])


def _build_cases(target: dict) -> dict:
    episode = benchmark_episode_catalog()[target["episode"]]
    legacy, _, _ = run_reference_comply(
        seed=target["seed"],
        operational_task=episode.task,
        simulator_kwargs=episode.simulator_overrides,
    )
    compact_result, compact_policy, _, _ = run_agentic_episode(
        seed=target["seed"],
        operational_task=episode.task,
        context_mode="action_conditioned_compact",
        planner_consumer=CompiledChecklistPlannerConsumer(),
        planner_replan_mode="decision_state",
        simulator_kwargs=episode.simulator_overrides,
    )
    full_result, full_policy, _, _ = run_agentic_episode(
        seed=target["seed"],
        operational_task=episode.task,
        context_mode="full_dump",
        planner_consumer=DeterministicComplyPlannerConsumer(),
        planner_replan_mode="decision_state",
        simulator_kwargs=episode.simulator_overrides,
    )
    if physical_signature(compact_result) != physical_signature(legacy):
        raise RuntimeError(f"compact checklist trajectory diverged for {target['label']}")
    if physical_signature(full_result) != physical_signature(legacy):
        raise RuntimeError(f"full-dump deterministic trajectory diverged for {target['label']}")

    compact = _record_at(compact_policy, target["t_s"]).assembly
    full = _record_at(full_policy, target["t_s"]).assembly
    saved = _saved_method_assembly(target["task"], target["t_s"])
    if compact.assembly_hash != saved.assembly_hash:
        raise RuntimeError(
            f"current compact assembly differs from frozen v6 at {target['label']}: "
            f"{compact.assembly_hash} != {saved.assembly_hash}"
        )

    full_evidence = deepcopy(_fragment(full, "evidence_slice").content)
    cf = _replace_fragment(
        compact,
        kind="evidence_slice",
        content=full_evidence,
        selection_reason="causal_probe_cf_full_evidence",
    )

    candidate = deepcopy(_fragment(compact, "candidate_action_context").content)
    if not isinstance(candidate, dict) or "decision_sufficiency" not in candidate:
        raise RuntimeError(f"missing decision_sufficiency at {target['label']}")
    gold_sufficiency = deepcopy(candidate["decision_sufficiency"])
    candidate.pop("decision_sufficiency", None)
    cs = _replace_fragment(
        compact,
        kind="candidate_action_context",
        content=candidate,
        selection_reason="causal_probe_cs_no_sufficiency",
    )

    m_payload = render_planner_protocol(compact)
    cf_payload = render_planner_protocol(cf)
    cs_payload = render_planner_protocol(cs)
    cs_payload["planner_rules"] = [
        row
        for row in cs_payload["planner_rules"]
        if "decision_sufficiency.status" not in row
    ]

    m_without_evidence = deepcopy(m_payload)
    cf_without_evidence = deepcopy(cf_payload)
    for payload in (m_without_evidence, cf_without_evidence):
        payload.pop("evidence", None)
        payload.pop("assembly", None)
    cf_single_variable = m_without_evidence == cf_without_evidence

    m_core = deepcopy(m_payload)
    cs_core = deepcopy(cs_payload)
    m_candidate = deepcopy(m_core["candidate_action_context"])
    cs_candidate = deepcopy(cs_core["candidate_action_context"])
    removed_sufficiency = m_candidate.pop("decision_sufficiency", None)
    m_core["candidate_action_context"] = m_candidate
    for payload in (m_core, cs_core):
        payload.pop("assembly", None)
    m_rules_without_suff = [
        row for row in m_core["planner_rules"] if "decision_sufficiency.status" not in row
    ]
    m_core["planner_rules"] = m_rules_without_suff
    cs_single_variable = (
        removed_sufficiency == gold_sufficiency
        and m_candidate == cs_candidate
        and m_core == cs_core
    )
    if not cf_single_variable or not cs_single_variable:
        raise RuntimeError(
            f"causal-input single-variable gate failed for {target['label']}: "
            f"CF={cf_single_variable} CS={cs_single_variable}"
        )

    plan_id = str(gold_sufficiency.get("primary_plan_id") or "")
    plans = list(_fragment(compact, "candidate_action_context").content.get("candidate_plans", []))
    plan = next((row for row in plans if row.get("plan_id") == plan_id), None)
    if plan is None:
        raise RuntimeError(f"gold primary plan missing at {target['label']}: {plan_id}")
    return {
        "target": target,
        "m_assembly": compact,
        "cf_assembly": cf,
        "cs_assembly": cs,
        "payloads": {"M": m_payload, "CF": cf_payload, "CS": cs_payload},
        "gold_plan_id": plan_id,
        "gold_invocations": list(plan.get("invocations") or []),
        "gold_stop": not bool(plan.get("invocations")),
        "saved_method_decision": _saved_method_decision(target["task"], target["t_s"]),
        "input_audit": {
            "frozen_method_assembly_hash": saved.assembly_hash,
            "current_method_assembly_hash": compact.assembly_hash,
            "cf_assembly_hash": cf.assembly_hash,
            "cs_assembly_hash": cs.assembly_hash,
            "method_evidence_count": len(m_payload.get("evidence") or []),
            "cf_evidence_count": len(cf_payload.get("evidence") or []),
            "cs_evidence_count": len(cs_payload.get("evidence") or []),
            "cf_only_changes_evidence_slice": cf_single_variable,
            "cs_only_removes_sufficiency_and_rules": cs_single_variable,
            "method_protocol_sha256": _digest(m_payload),
            "cf_protocol_sha256": _digest(cf_payload),
            "cs_protocol_sha256": _digest(cs_payload),
            "method_protocol_bytes": len(_canonical_bytes(m_payload)),
            "cf_protocol_bytes": len(_canonical_bytes(cf_payload)),
            "cs_protocol_bytes": len(_canonical_bytes(cs_payload)),
        },
    }


def _invocation_key(row: dict) -> tuple[str, str, str]:
    args = dict(row.get("canonical_arguments") or {})
    cid = str(row.get("capability_id") or "")
    resource = str(row.get("resource") or "")
    if cid.startswith("communication.config.") and args.get("node_id") == resource:
        args.pop("node_id", None)
    return cid, resource, json.dumps(args, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _score_decision(case: dict, decision: PlannerDecision) -> dict:
    expanded = _expand_selected_candidate_plan(decision, case["m_assembly"])
    effects = [
        row.model_dump(mode="json")
        for row in expanded.invocations
        if row.capability_id.startswith(("communication.config.", "communication.fallback."))
    ]
    observations = [
        row.model_dump(mode="json")
        for row in expanded.invocations
        if row.capability_id.startswith(("communication.center.", "communication.gateway."))
    ]
    expected = {_invocation_key(row) for row in case["gold_invocations"]}
    actual = {_invocation_key(row) for row in effects}
    return {
        "selected_plan_id": expanded.selected_plan_id,
        "selected_plan_exact": expanded.selected_plan_id == case["gold_plan_id"],
        "stop": bool(expanded.stop),
        "stop_exact": bool(expanded.stop) == bool(case["gold_stop"]),
        "effect_scope_exact": actual == expected,
        "missing_effects": [list(row) for row in sorted(expected - actual)],
        "unexpected_effects": [list(row) for row in sorted(actual - expected)],
        "observation_invocations": len(observations),
    }


def _decision_from_payload(payload: dict, request_id: str) -> PlannerDecision:
    proposal = PlannerDecisionProposal.model_validate(payload)
    return PlannerDecision(
        decision_id=f"decision:{request_id}",
        request_id=request_id,
        **proposal.model_dump(mode="python"),
    )


def _call_backend(backend, envelope: dict, request_id: str) -> tuple[PlannerDecision, dict]:
    messages = [
        {
            "role": "system",
            "content": (
                "You are a communication-operations planner. Follow the supplied typed "
                "protocol exactly and return one JSON object matching output_schema."
            ),
        },
        {"role": "user", "content": json.dumps(envelope, ensure_ascii=False, sort_keys=True)},
    ]
    before = BackendPlannerConsumer._usage_snapshot(backend)
    t0 = time.perf_counter()
    raw_text = backend.complete(messages)
    latency_ms = (time.perf_counter() - t0) * 1000.0
    after = BackendPlannerConsumer._usage_snapshot(backend)
    usage = BackendPlannerConsumer._usage_delta(before, after, latency_ms)
    decision = _decision_from_payload(_parse_backend_json(raw_text), request_id)
    return decision, usage.model_dump(mode="json")


def _saved_method_row(case: dict) -> dict:
    decision = PlannerDecision.model_validate(case["saved_method_decision"])
    return {
        "arm": "M",
        "source": "formal_v6_saved_trace",
        "decision": decision.model_dump(mode="json"),
        "score": _score_decision(case, decision),
    }


def _compiled_rule_row(case: dict) -> dict:
    request = ModelRequest(
        request_id=f"causal:{case['target']['label']}:CR",
        task_run_id=case["m_assembly"].task_run_id,
        assembly_id=case["m_assembly"].assembly_id,
        assembly_hash=case["m_assembly"].assembly_hash,
        consumer_id="compiled-checklist-v1",
        response_schema="PlannerDecision",
    )
    decision, _ = CompiledChecklistPlannerConsumer().decide(request, case["m_assembly"])
    return {
        "arm": "CR",
        "source": "deterministic_compiled_checklist",
        "decision": decision.model_dump(mode="json"),
        "score": _score_decision(case, decision),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="deepseek-flash")
    ap.add_argument("--credential-profile", choices=("deepseek_official",), default="deepseek_official")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max-tokens", type=int, default=8192)
    ap.add_argument("--reasoning-effort", default="low")
    ap.add_argument("--json-object", action="store_true", default=True)
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cases = [_build_cases(dict(target)) for target in TARGETS]
    manifest = {
        "experiment": "causal-interface-probe-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "model": args.model,
        "settings": {
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "reasoning_effort": args.reasoning_effort,
            "json_object": args.json_object,
        },
        "arms": {
            "M": "formal protocol-v6 compact Method output reused from audited trace",
            "CF": "same candidate/needs/sufficiency; only evidence slice replaced by FullDump from the same deterministic physical trajectory",
            "CS": "same compact input; only decision_sufficiency certificate and its two dedicated protocol rules removed",
            "CR": "ordinary unique-supported-plan checklist; no LLM and no decision_sufficiency read",
        },
        "cases": [
            {
                "target": case["target"],
                "gold_plan_id": case["gold_plan_id"],
                "gold_effect_count": len(case["gold_invocations"]),
                "gold_stop": case["gold_stop"],
                "input_audit": case["input_audit"],
            }
            for case in cases
        ],
    }
    (out / "input_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    if args.dry_run:
        return 0

    base_url = "https://api.deepseek.com"
    api_key = os.environ.get("DEEPSEEK_API_KEY") or _load_shell_export("DEEPSEEK_API_KEY")
    if not api_key:
        raise SystemExit("DEEPSEEK_API_KEY is not set")
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

    rows = []
    for case in cases:
        rows.append({"target": case["target"], **_saved_method_row(case)})
        rows.append({"target": case["target"], **_compiled_rule_row(case)})
        for arm, key in (("CF", "cf_assembly"), ("CS", "cs_assembly")):
            request_id = f"causal:{case['target']['label']}:{arm}"
            decision, usage = _call_backend(backend, case["payloads"][arm], request_id)
            rows.append(
                {
                    "target": case["target"],
                    "arm": arm,
                    "source": "live_deepseek_flash",
                    "decision": decision.model_dump(mode="json"),
                    "usage": usage,
                    "score": _score_decision(case, decision),
                }
            )

    payload = {
        "experiment": "causal-interface-probe-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "model": args.model,
        "input_manifest": str(out / "input_manifest.json"),
        "rows": rows,
    }
    (out / "result.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"WROTE {out / 'result.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

