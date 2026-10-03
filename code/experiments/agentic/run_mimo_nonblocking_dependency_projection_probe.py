#!/usr/bin/env python3
"""Exact-state MiMo probe for nonblocking unresolved dependency audit residue.

Target: held-out Qili/2024/w1, MiMo, seed3, v7, first t=3660 request.
The envelope already says the install plan is decision-sufficient and has no
blocking EvidenceNeed, while one top-level unresolved dependency for n10 remains.

P = frozen v7 input unchanged.
D = hide only top-level unresolved_dependencies/open_dependency_count because the
    sufficiency certificate is already closed and blocking_need_ids is empty.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
ROOT = HERE.parents[2]
for path in (CODE, CODE / "monitoring", CODE / "runtime", HERE):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from agentic_communication.planner import (  # noqa: E402
    BackendPlannerConsumer,
    _expand_selected_candidate_plan,
)
from agentic_communication.replay import frozen_r1_inputs, load_trace  # noqa: E402
from agentic_communication.runtime_contracts import (  # noqa: E402
    MaterializedFragment,
    ModelRequest,
    PlannerDecision,
    PromptAssembly,
)
from run_heldout_qili2024_seed0 import _backend, MODELS  # noqa: E402


TRACE = (
    ROOT
    / "results"
    / "agentic"
    / "heldout-qili-2024-w1"
    / "model-transfer-v7"
    / "mimo-v2.6-flash"
    / "seed-003"
    / "runtime_trace.jsonl"
)
TARGET_T_S = 3660
TARGET_HASH = "f8cd75c0614c28c9d739aca943a75b7b9ca6e94e38e37b454695662b9e235533"
EXPECTED_PLAN = "install_required_profile"
OUT = ROOT / "results" / "agentic" / "mimo-nonblocking-dependency-projection-probe-v1"


def _fragment(assembly: PromptAssembly, kind: str) -> MaterializedFragment:
    rows = [row for row in assembly.fragments if row.kind == kind]
    if len(rows) != 1:
        raise RuntimeError(f"expected one {kind}, got {len(rows)}")
    return rows[0]


def _frozen() -> PromptAssembly:
    rows = [
        row.assembly
        for row in frozen_r1_inputs(load_trace(TRACE))
        if int(row.t_s) == TARGET_T_S and row.assembly.assembly_hash == TARGET_HASH
    ]
    if len(rows) != 1:
        raise RuntimeError(f"expected one frozen assembly, got {len(rows)}")
    return rows[0]


def _replace_candidate(assembly: PromptAssembly, candidate: dict) -> PromptAssembly:
    base = _fragment(assembly, "candidate_action_context")
    replacement = MaterializedFragment.build(
        kind=base.kind,
        source_ref=base.source_ref,
        source_revision=base.source_revision,
        trust_class=base.trust_class,
        cache_class=base.cache_class,
        content=candidate,
        selection_reason="probe_hide_nonblocking_dependency_audit_after_closed_sufficiency",
    )
    return PromptAssembly.build(
        task_contract_id=assembly.task_contract_id,
        task_run_id=assembly.task_run_id,
        context_manifest_revision=assembly.context_manifest_revision,
        fragments=[replacement if row.kind == base.kind else row for row in assembly.fragments],
        percept_refs=list(assembly.percept_refs),
    )


def _arms() -> dict[str, PromptAssembly]:
    p = _frozen()
    candidate = deepcopy(_fragment(p, "candidate_action_context").content)
    if not isinstance(candidate, dict):
        raise RuntimeError("candidate context is not a dict")
    suff = candidate.get("decision_sufficiency") or {}
    if (
        suff.get("status") != "sufficient_for_primary_action"
        or suff.get("primary_plan_id") != EXPECTED_PLAN
        or suff.get("blocking_need_ids")
    ):
        raise RuntimeError(f"target is not closed primary-action state: {suff}")
    needs = _fragment(p, "evidence_needs").content
    if needs:
        raise RuntimeError(f"target unexpectedly exposes EvidenceNeed: {needs}")
    unresolved = list(candidate.get("unresolved_dependencies") or [])
    if len(unresolved) != 1 or int(candidate.get("open_dependency_count") or 0) != 1:
        raise RuntimeError(f"expected one residual unresolved dependency, got {unresolved}")
    d = deepcopy(candidate)
    d["unresolved_dependencies"] = []
    d["open_dependency_count"] = 0
    return {"P": p, "D": _replace_candidate(p, d)}


def _candidate(assembly: PromptAssembly) -> dict:
    value = _fragment(assembly, "candidate_action_context").content
    return deepcopy(value) if isinstance(value, dict) else {}


def _audit(arms: dict[str, PromptAssembly]) -> dict:
    p = _candidate(arms["P"])
    d = _candidate(arms["D"])
    p_residual = {
        "unresolved_dependencies": p.pop("unresolved_dependencies", None),
        "open_dependency_count": p.pop("open_dependency_count", None),
    }
    d_residual = {
        "unresolved_dependencies": d.pop("unresolved_dependencies", None),
        "open_dependency_count": d.pop("open_dependency_count", None),
    }
    if p != d:
        raise RuntimeError("P/D differ outside residual dependency audit fields")
    if len(p_residual["unresolved_dependencies"] or []) != 1 or p_residual["open_dependency_count"] != 1:
        raise RuntimeError(f"unexpected P residual: {p_residual}")
    if d_residual != {"unresolved_dependencies": [], "open_dependency_count": 0}:
        raise RuntimeError(f"unexpected D residual: {d_residual}")
    return {
        "target_trace": str(TRACE.relative_to(ROOT)),
        "target_t_s": TARGET_T_S,
        "target_assembly_hash": TARGET_HASH,
        "same_candidate_semantics_outside_residual_audit": True,
        "P_residual": p_residual,
        "D_residual": d_residual,
        "evidence_needs": _fragment(arms["P"], "evidence_needs").content,
        "sufficiency": _candidate(arms["P"])["decision_sufficiency"],
    }


def _key(row: dict) -> tuple[str, str, str]:
    cid = str(row.get("capability_id") or "")
    resource = str(row.get("resource") or "")
    args = dict(row.get("canonical_arguments") or {})
    if cid.startswith("communication.config.") and args.get("node_id") == resource:
        args.pop("node_id", None)
    return cid, resource, json.dumps(args, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _score(decision: PlannerDecision, assembly: PromptAssembly) -> dict:
    candidate = _candidate(assembly)
    plan = next(
        row
        for row in candidate.get("candidate_plans", [])
        if isinstance(row, dict) and row.get("plan_id") == EXPECTED_PLAN
    )
    expected = {
        _key(row)
        for row in plan.get("invocations", [])
        if str(row.get("capability_id") or "").startswith(
            ("communication.config.", "communication.fallback.")
        )
    }
    expanded = _expand_selected_candidate_plan(decision, assembly)
    actual = {
        _key(row.model_dump(mode="json"))
        for row in expanded.invocations
        if row.capability_id.startswith(("communication.config.", "communication.fallback."))
    }
    observations = [
        row.model_dump(mode="json")
        for row in expanded.invocations
        if row.capability_id.startswith(("communication.center.", "communication.gateway."))
    ]
    return {
        "selected_plan_id": expanded.selected_plan_id,
        "selected_plan_exact": expanded.selected_plan_id == EXPECTED_PLAN,
        "effect_scope_exact": actual == expected,
        "stop_exact": expanded.stop is False,
        "observation_invocations": observations,
        "missing_effects": [list(row) for row in sorted(expected - actual)],
        "unexpected_effects": [list(row) for row in sorted(actual - expected)],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.repeats <= 0:
        raise SystemExit("--repeats must be positive")

    arms = _arms()
    audit = _audit(arms)
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {
        "experiment": "mimo-nonblocking-dependency-projection-probe-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "model": "mimo-v2.6-flash",
        "generation": {
            "temperature": 0.0,
            "thinking": "disabled",
            "response_format": "json_object",
            "max_tokens": 8192,
        },
        "repeats_per_arm": args.repeats,
        "arm_order_per_repeat": ["P", "D"],
        "arms": {
            "P": "frozen v7 input unchanged",
            "D": "hide only residual nonblocking unresolved_dependencies/open_dependency_count after closed sufficiency",
        },
        "input_audit": audit,
        "historical_failure": {
            "reason_codes": ["sufficient_for_primary_action", "primary_plan_supported", "nonblocking_open_need_present"],
            "observation": "communication.center.node_report(n10)",
        },
        "claim_boundary": "Exact-state R1 diagnosis only; no simulator continuation or selective retries.",
    }
    (OUT / "input_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    if args.dry_run:
        return 0

    mimo_config = next(row for row in MODELS if row["id"] == "mimo-v2.6-flash")
    backend = _backend(mimo_config)
    consumer = BackendPlannerConsumer(
        backend,
        consumer_id="mimo-nonblocking-dependency-projection-probe",
        provider="xiaomi_mimo_official",
        model="mimo-v2.6-flash",
    )
    rows = []
    for repeat in range(args.repeats):
        for arm in ("P", "D"):
            assembly = arms[arm]
            request = ModelRequest(
                request_id=f"mimo-nonblocking:{repeat}:{arm}",
                task_run_id=assembly.task_run_id,
                assembly_id=assembly.assembly_id,
                assembly_hash=assembly.assembly_hash,
                consumer_id=consumer.consumer_id,
                response_schema="PlannerDecision",
            )
            try:
                decision, usage = consumer.decide(request, assembly)
            except Exception as exc:  # noqa: BLE001
                rows.append(
                    {
                        "repeat": repeat,
                        "arm": arm,
                        "status": "failed",
                        "error_type": type(exc).__name__,
                        "error": str(exc)[:500],
                    }
                )
                continue
            rows.append(
                {
                    "repeat": repeat,
                    "arm": arm,
                    "status": "succeeded",
                    "decision": decision.model_dump(mode="json"),
                    "score": _score(decision, assembly),
                    "usage": usage.model_dump(mode="json"),
                }
            )

    summary = {}
    for arm in ("P", "D"):
        subset = [row for row in rows if row["arm"] == arm]
        success = [row for row in subset if row["status"] == "succeeded"]
        summary[arm] = {
            "n": len(subset),
            "successful_calls": len(success),
            "failed_calls": len(subset) - len(success),
            "selected_plan_exact": sum(row["score"]["selected_plan_exact"] for row in success),
            "effect_scope_exact": sum(row["score"]["effect_scope_exact"] for row in success),
            "stop_exact": sum(row["score"]["stop_exact"] for row in success),
            "turns_with_observation": sum(
                bool(row["score"]["observation_invocations"]) for row in success
            ),
            "observation_invocations": sum(
                len(row["score"]["observation_invocations"]) for row in success
            ),
        }
    result = {
        "experiment": "mimo-nonblocking-dependency-projection-probe-v1",
        "generated_at": datetime.now(UTC).isoformat(),
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

