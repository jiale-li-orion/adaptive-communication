#!/usr/bin/env python3
"""Exact-state MiMo probe for residual unresolved audit details in a closed decision.

The frozen input is the first MiMo planner request at t=60 from the held-out
Qili/2024/w1 seed0 episode.  The semantic decision is already closed:

* install_required_profile is the unique supported plan;
* decision_sufficiency == sufficient_for_primary_action;
* blocking_need_ids == [];
* model-visible EvidenceNeed == [].

Arms:

M  protocol-v6 model-facing input unchanged.
P  only clear unresolved_conditions on rejected/dominated candidate plans.
D  decision-closed projection: P plus remove residual unresolved_dependencies and
   set open_dependency_count=0 when the sufficiency certificate has no blocking
   need.  Candidate feasibility, invocations, EvidenceNeed and sufficiency are
   unchanged.

This is an R1 interface diagnosis.  It does not mutate v6 or rerun the simulator.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import UTC, datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import time


HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
ROOT = HERE.parents[2]
for path in (CODE, CODE / "monitoring", CODE / "runtime"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from agentic_communication.model_protocol import render_planner_protocol  # noqa: E402
from agentic_communication.planner import (  # noqa: E402
    BackendPlannerConsumer,
    _expand_selected_candidate_plan,
    _parse_backend_json,
)
from agentic_communication.replay import frozen_r1_inputs, load_trace  # noqa: E402
from agentic_communication.runtime_contracts import (  # noqa: E402
    MaterializedFragment,
    ModelRequest,
    PlannerDecision,
    PlannerDecisionProposal,
    PromptAssembly,
)


TRACE = (
    ROOT
    / "results"
    / "agentic"
    / "heldout-qili-2024-w1"
    / "model-transfer-v1"
    / "mimo-v2.6-flash"
    / "seed-000"
    / "runtime_trace.jsonl"
)
OUT = ROOT / "results" / "agentic" / "mimo-decision-closed-projection-probe-v1"
TARGET_T_S = 60
TARGET_ASSEMBLY_HASH = "d9991fb2702cd3d507ebdd12960d55e2cbda2c30d73ff2edef931e646830bc0d"
MODEL = "mimo-v2.6-flash"
EXPECTED_PLAN = "install_required_profile"


def _canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(value) -> str:
    return sha256(_canonical(value)).hexdigest()


def _fragment(assembly: PromptAssembly, kind: str) -> MaterializedFragment:
    rows = [row for row in assembly.fragments if row.kind == kind]
    if len(rows) != 1:
        raise RuntimeError(f"expected exactly one {kind}, got {len(rows)}")
    return rows[0]


def _replace_candidate(assembly: PromptAssembly, content: dict, reason: str) -> PromptAssembly:
    base = _fragment(assembly, "candidate_action_context")
    replacement = MaterializedFragment.build(
        kind=base.kind,
        source_ref=base.source_ref,
        source_revision=base.source_revision,
        trust_class=base.trust_class,
        cache_class=base.cache_class,
        content=content,
        selection_reason=reason,
    )
    fragments = [replacement if row.kind == base.kind else row for row in assembly.fragments]
    return PromptAssembly.build(
        task_contract_id=assembly.task_contract_id,
        task_run_id=assembly.task_run_id,
        context_manifest_revision=assembly.context_manifest_revision,
        fragments=fragments,
        percept_refs=list(assembly.percept_refs),
    )


def _frozen_assembly() -> PromptAssembly:
    records = frozen_r1_inputs(load_trace(TRACE))
    rows = [
        row.assembly
        for row in records
        if int(row.t_s) == TARGET_T_S and row.assembly.assembly_hash == TARGET_ASSEMBLY_HASH
    ]
    if len(rows) != 1:
        raise RuntimeError(f"expected one frozen target assembly, got {len(rows)}")
    return rows[0]


def _arms(base: PromptAssembly) -> dict[str, PromptAssembly]:
    candidate = deepcopy(_fragment(base, "candidate_action_context").content)
    if not isinstance(candidate, dict):
        raise RuntimeError("candidate context is not an object")
    suff = candidate.get("decision_sufficiency") or {}
    if suff.get("status") != "sufficient_for_primary_action":
        raise RuntimeError(f"unexpected sufficiency: {suff}")
    if suff.get("primary_plan_id") != EXPECTED_PLAN or suff.get("blocking_need_ids"):
        raise RuntimeError(f"target state is not decision-closed: {suff}")

    p = deepcopy(candidate)
    for plan in p.get("candidate_plans", []):
        if isinstance(plan, dict) and plan.get("feasibility") in {"rejected", "dominated"}:
            plan["unresolved_conditions"] = []

    d = deepcopy(p)
    d["unresolved_dependencies"] = []
    d["open_dependency_count"] = 0

    return {
        "M": base,
        "P": _replace_candidate(base, p, "probe_clear_retired_plan_unresolved_conditions"),
        "D": _replace_candidate(base, d, "probe_decision_closed_projection"),
    }


def _candidate_content(assembly: PromptAssembly) -> dict:
    value = _fragment(assembly, "candidate_action_context").content
    return deepcopy(value) if isinstance(value, dict) else {}


def _semantic_core(candidate: dict) -> dict:
    row = deepcopy(candidate)
    for plan in row.get("candidate_plans", []):
        if isinstance(plan, dict) and plan.get("feasibility") in {"rejected", "dominated"}:
            plan.pop("unresolved_conditions", None)
    row.pop("unresolved_dependencies", None)
    row.pop("open_dependency_count", None)
    return row


def _input_audit(arms: dict[str, PromptAssembly]) -> dict:
    payloads = {arm: render_planner_protocol(assembly) for arm, assembly in arms.items()}
    candidates = {arm: _candidate_content(assembly) for arm, assembly in arms.items()}
    semantic_equal = len({_digest(_semantic_core(row)) for row in candidates.values()}) == 1
    protocol_non_candidate_equal = []
    base = deepcopy(payloads["M"])
    base.pop("candidate_action_context", None)
    base.pop("assembly", None)
    for arm in ("P", "D"):
        other = deepcopy(payloads[arm])
        other.pop("candidate_action_context", None)
        other.pop("assembly", None)
        protocol_non_candidate_equal.append(base == other)

    plans = {
        arm: [
            {
                "plan_id": row.get("plan_id"),
                "feasibility": row.get("feasibility"),
                "invocations": row.get("invocations"),
            }
            for row in candidate.get("candidate_plans", [])
            if isinstance(row, dict)
        ]
        for arm, candidate in candidates.items()
    }
    plan_semantics_equal = len({_digest(value) for value in plans.values()}) == 1
    sufficiency_equal = len(
        {_digest(candidate.get("decision_sufficiency")) for candidate in candidates.values()}
    ) == 1

    evidence_needs = {
        arm: _fragment(assembly, "evidence_needs").content
        for arm, assembly in arms.items()
    }
    needs_equal = len({_digest(value) for value in evidence_needs.values()}) == 1

    audit = {
        "target_trace": str(TRACE.relative_to(ROOT)),
        "target_t_s": TARGET_T_S,
        "target_assembly_hash": TARGET_ASSEMBLY_HASH,
        "semantic_core_equal": semantic_equal,
        "plan_id_feasibility_invocations_equal": plan_semantics_equal,
        "decision_sufficiency_equal": sufficiency_equal,
        "evidence_needs_equal": needs_equal,
        "protocol_outside_candidate_equal": all(protocol_non_candidate_equal),
        "arms": {
            arm: {
                "assembly_hash": assembly.assembly_hash,
                "protocol_sha256": _digest(payloads[arm]),
                "protocol_bytes": len(_canonical(payloads[arm])),
                "retired_unresolved_conditions": {
                    str(row.get("plan_id")): list(row.get("unresolved_conditions") or [])
                    for row in candidates[arm].get("candidate_plans", [])
                    if isinstance(row, dict) and row.get("feasibility") in {"rejected", "dominated"}
                },
                "unresolved_dependency_count": len(
                    candidates[arm].get("unresolved_dependencies") or []
                ),
                "open_dependency_count": candidates[arm].get("open_dependency_count"),
            }
            for arm, assembly in arms.items()
        },
    }
    if not all(
        (
            semantic_equal,
            plan_semantics_equal,
            sufficiency_equal,
            needs_equal,
            audit["protocol_outside_candidate_equal"],
        )
    ):
        raise RuntimeError(f"single-variable projection gate failed: {audit}")
    return audit


class _MiMoBackend:
    name = "xiaomi-mimo-openai-compatible"

    def __init__(self, *, api_key: str, base_url: str, timeout: float = 60.0) -> None:
        from openai import OpenAI

        self.model = MODEL
        self.client = OpenAI(base_url=base_url, api_key=api_key, timeout=timeout)
        self.client.models.list()
        self.usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def complete(self, messages):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.0,
            max_tokens=8192,
            response_format={"type": "json_object"},
            extra_body={"thinking": {"type": "disabled"}},
        )
        usage = getattr(response, "usage", None)
        for attr, key in (
            ("prompt_tokens", "prompt_tokens"),
            ("completion_tokens", "completion_tokens"),
            ("total_tokens", "total_tokens"),
        ):
            value = getattr(usage, attr, None)
            if value is not None:
                self.usage[key] += int(value)
        return response.choices[0].message.content or "{}"


def _invocation_key(row: dict) -> tuple[str, str, str]:
    cid = str(row.get("capability_id") or "")
    resource = str(row.get("resource") or "")
    args = dict(row.get("canonical_arguments") or {})
    if cid.startswith("communication.config.") and args.get("node_id") == resource:
        args.pop("node_id", None)
    return cid, resource, json.dumps(args, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _gold(assembly: PromptAssembly) -> tuple[set[tuple[str, str, str]], bool]:
    candidate = _candidate_content(assembly)
    rows = [
        row
        for row in candidate.get("candidate_plans", [])
        if isinstance(row, dict) and row.get("plan_id") == EXPECTED_PLAN
    ]
    if len(rows) != 1:
        raise RuntimeError("gold plan missing")
    effects = {
        _invocation_key(row)
        for row in rows[0].get("invocations", [])
        if str(row.get("capability_id") or "").startswith(
            ("communication.config.", "communication.fallback.")
        )
    }
    return effects, False


def _score(decision: PlannerDecision, assembly: PromptAssembly) -> dict:
    expanded = _expand_selected_candidate_plan(decision, assembly)
    actual_effects = {
        _invocation_key(row.model_dump(mode="json"))
        for row in expanded.invocations
        if row.capability_id.startswith(("communication.config.", "communication.fallback."))
    }
    observations = [
        row.model_dump(mode="json")
        for row in expanded.invocations
        if row.capability_id.startswith(("communication.center.", "communication.gateway."))
    ]
    expected_effects, expected_stop = _gold(assembly)
    return {
        "selected_plan_id": expanded.selected_plan_id,
        "selected_plan_exact": expanded.selected_plan_id == EXPECTED_PLAN,
        "effect_scope_exact": actual_effects == expected_effects,
        "missing_effects": [list(row) for row in sorted(expected_effects - actual_effects)],
        "unexpected_effects": [list(row) for row in sorted(actual_effects - expected_effects)],
        "stop": bool(expanded.stop),
        "stop_exact": bool(expanded.stop) == expected_stop,
        "observation_invocations": observations,
    }


def _historical_failure() -> dict:
    events = list(load_trace(TRACE))
    rows = [
        event.payload
        for event in events
        if event.event_type == "planner_decision"
        and int(event.t_s) == TARGET_T_S
    ]
    if not rows:
        raise RuntimeError("historical t=60 decision missing")
    # First t=60 turn is the inexact query; second is the post-tool correction.
    return deepcopy(rows[0])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.repeats <= 0:
        raise SystemExit("--repeats must be positive")

    base = _frozen_assembly()
    arms = _arms(base)
    audit = _input_audit(arms)
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {
        "experiment": "mimo-decision-closed-projection-probe-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "model": MODEL,
        "generation": {
            "temperature": 0.0,
            "thinking": "disabled",
            "response_format": "json_object",
            "max_tokens": 8192,
        },
        "repeats_per_arm": args.repeats,
        "arm_order_per_repeat": ["M", "P", "D"],
        "arms": {
            "M": "frozen protocol-v6 input unchanged",
            "P": "clear unresolved_conditions only on rejected/dominated plans",
            "D": (
                "P plus remove residual unresolved_dependencies/open_dependency_count from the "
                "model-facing candidate context when sufficiency is already closed and blocking_need_ids is empty"
            ),
        },
        "input_audit": audit,
        "historical_failure": _historical_failure(),
        "claim_boundary": (
            "Exact-state R1 projection diagnosis only. No simulator continuation and no v6 Method mutation."
        ),
    }
    (OUT / "input_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    if args.dry_run:
        return 0

    api_key = os.environ.get("MIMO_API_KEY")
    base_url = os.environ.get("MIMO_BASE_URL")
    if not api_key or not base_url:
        raise SystemExit("MIMO_API_KEY / MIMO_BASE_URL missing")
    backend = _MiMoBackend(api_key=api_key, base_url=base_url)
    consumer = BackendPlannerConsumer(
        backend,
        consumer_id="mimo-decision-closed-projection-probe",
        provider="xiaomi_mimo_official",
        model=MODEL,
    )

    rows = []
    for repeat in range(args.repeats):
        for arm in ("M", "P", "D"):
            assembly = arms[arm]
            request = ModelRequest(
                request_id=f"mimo-projection:{repeat}:{arm}",
                task_run_id=assembly.task_run_id,
                assembly_id=assembly.assembly_id,
                assembly_hash=assembly.assembly_hash,
                consumer_id=consumer.consumer_id,
                response_schema="PlannerDecision",
            )
            started = time.perf_counter()
            decision, usage = consumer.decide(request, assembly)
            rows.append(
                {
                    "repeat": repeat,
                    "arm": arm,
                    "decision": decision.model_dump(mode="json"),
                    "score": _score(decision, assembly),
                    "usage": usage.model_dump(mode="json"),
                    "wall_ms": (time.perf_counter() - started) * 1000.0,
                }
            )

    summary = {}
    for arm in ("M", "P", "D"):
        subset = [row for row in rows if row["arm"] == arm]
        summary[arm] = {
            "n": len(subset),
            "selected_plan_exact": sum(row["score"]["selected_plan_exact"] for row in subset),
            "effect_scope_exact": sum(row["score"]["effect_scope_exact"] for row in subset),
            "stop_exact": sum(row["score"]["stop_exact"] for row in subset),
            "turns_with_observation": sum(
                bool(row["score"]["observation_invocations"]) for row in subset
            ),
            "observation_invocations": sum(
                len(row["score"]["observation_invocations"]) for row in subset
            ),
        }
    result = {
        "experiment": "mimo-decision-closed-projection-probe-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "input_manifest": str((OUT / "input_manifest.json").relative_to(ROOT)),
        "summary": summary,
        "rows": rows,
    }
    (OUT / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

