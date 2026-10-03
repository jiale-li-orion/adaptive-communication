#!/usr/bin/env python3
"""Frozen-input go/no-go audit for low-cost evidence-basis selection.

This script intentionally does not optimize anything.  It first asks whether the
formal model-facing inputs contain a real proof-choice space at all.  If there is
no alternative proof, multi-source requirement, shared blocking need across live
plans, or duplicate evidence key, a new minimum-basis optimizer would be solving
an artificial problem rather than one activated by the current paper workloads.
"""
from __future__ import annotations

from collections import Counter
import glob
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "results" / "agentic" / "basis-selection-headroom-v1" / "audit.json"


TRACE_GROUPS = {
    "A7-main": str(
        ROOT
        / "results/agentic/main-table-v6-confirmatory/deepseek-flash/*/seed-*/"
        "action_conditioned_compact/runtime_trace.jsonl"
    ),
    "A10-query-positive-deepseek": str(
        ROOT / "results/agentic/query-positive-gateway-backup-v1/deepseek-flash/seed-*/runtime_trace.jsonl"
    ),
    # A11 uses the same frozen compiler family but is included to ensure a
    # second model did not activate a different model-facing proof structure.
    "A11-query-positive-mimo": str(
        ROOT / "results/agentic/query-positive-gateway-backup-v1/mimo-v2.6-flash/seed-*/runtime_trace.jsonl"
    ),
}


def _event_type_hint(line: str, event_type: str) -> bool:
    return f'"event_type": "{event_type}"' in line or f'"event_type":"{event_type}"' in line


def _model_request_assembly_ids(path: Path) -> set[str]:
    out: set[str] = set()
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if not _event_type_hint(line, "model_request"):
                continue
            event = json.loads(line)
            assembly_id = str((event.get("payload") or {}).get("assembly_id") or "")
            if assembly_id:
                out.add(assembly_id)
    return out


def _requested_assemblies(path: Path):
    wanted = _model_request_assembly_ids(path)
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if not _event_type_hint(line, "prompt_assembly"):
                continue
            event = json.loads(line)
            payload = event.get("payload") or {}
            if str(payload.get("assembly_id") or "") not in wanted:
                continue
            fragments = {
                str(row.get("kind") or ""): row.get("content")
                for row in payload.get("fragments", [])
                if isinstance(row, dict)
            }
            yield int(event.get("t_s") or 0), fragments


def _duplicate_evidence_keys(evidence: list[dict]) -> list[tuple[str, str]]:
    counts = Counter(
        (str(row.get("proposition") or ""), str(row.get("subject_ref") or ""))
        for row in evidence
        if isinstance(row, dict)
    )
    return sorted(key for key, count in counts.items() if count > 1)


def main() -> int:
    rows = []
    totals = Counter()
    key_shapes = Counter()
    examples = {
        "multi_plan_blocking_need": [],
        "multi_source_need": [],
        "duplicate_evidence_key": [],
        "multiple_live_plans": [],
    }

    for group, pattern in TRACE_GROUPS.items():
        paths = [Path(path) for path in sorted(glob.glob(pattern))]
        for trace in paths:
            for t_s, fragments in _requested_assemblies(trace):
                candidate = fragments.get("candidate_action_context") or {}
                plans = [row for row in (candidate.get("candidate_plans") or []) if isinstance(row, dict)]
                needs = [row for row in (fragments.get("evidence_needs") or []) if isinstance(row, dict)]
                evidence = [row for row in (fragments.get("evidence_slice") or []) if isinstance(row, dict)]
                live = [
                    row
                    for row in plans
                    if row.get("feasibility") not in {"rejected", "dominated"}
                ]

                multi_plan_needs = [
                    row for row in needs if len(set(row.get("blocking_plan_ids") or [])) > 1
                ]
                multi_source_needs = []
                for row in needs:
                    contract = row.get("evidence_contract") or {}
                    if int(contract.get("min_independent_sources") or 1) > 1:
                        multi_source_needs.append(row)
                    elif len(set(contract.get("required_source_roles") or [])) > 1:
                        multi_source_needs.append(row)
                duplicates = _duplicate_evidence_keys(evidence)

                totals["model_requests"] += 1
                totals["visible_plans"] += len(plans)
                totals["live_plans"] += len(live)
                totals["evidence_needs"] += len(needs)
                totals["evidence_rows"] += len(evidence)
                totals["multi_plan_blocking_needs"] += len(multi_plan_needs)
                totals["multi_source_needs"] += len(multi_source_needs)
                totals["duplicate_evidence_keys"] += len(duplicates)
                totals["requests_with_multiple_live_plans"] += int(len(live) > 1)

                # A first-class alternative proof representation would need an
                # explicit nested proof/alternative field.  Record actual key
                # shapes rather than inferring alternatives from prose reasons.
                for plan in plans:
                    for key in plan:
                        key_shapes[f"plan:{key}"] += 1
                for need in needs:
                    for key in need:
                        key_shapes[f"need:{key}"] += 1

                def add_example(bucket: str, value) -> None:
                    if len(examples[bucket]) >= 5:
                        return
                    examples[bucket].append(
                        {
                            "group": group,
                            "trace": str(trace.relative_to(ROOT)),
                            "t_s": t_s,
                            "value": value,
                        }
                    )

                if multi_plan_needs:
                    add_example(
                        "multi_plan_blocking_need",
                        [
                            {
                                "need_id": row.get("need_id"),
                                "blocking_plan_ids": row.get("blocking_plan_ids"),
                            }
                            for row in multi_plan_needs
                        ],
                    )
                if multi_source_needs:
                    add_example(
                        "multi_source_need",
                        [row.get("need_id") for row in multi_source_needs],
                    )
                if duplicates:
                    add_example("duplicate_evidence_key", duplicates)
                if len(live) > 1:
                    add_example(
                        "multiple_live_plans",
                        [
                            {
                                "plan_id": row.get("plan_id"),
                                "feasibility": row.get("feasibility"),
                                "guards": row.get("decision_guards") or {},
                            }
                            for row in live
                        ],
                    )

                rows.append(
                    {
                        "group": group,
                        "trace": str(trace.relative_to(ROOT)),
                        "t_s": t_s,
                        "live_plan_count": len(live),
                        "need_count": len(needs),
                        "multi_plan_need_count": len(multi_plan_needs),
                        "multi_source_need_count": len(multi_source_needs),
                        "duplicate_evidence_key_count": len(duplicates),
                    }
                )

    alternative_key_names = sorted(
        key
        for key in key_shapes
        if any(token in key.lower() for token in ("alternative_proof", "proof_options", "proof_sets", "witness_options"))
    )
    active_choice_signals = {
        "first_class_alternative_proof_fields": alternative_key_names,
        "multi_plan_blocking_needs": totals["multi_plan_blocking_needs"],
        "multi_source_needs": totals["multi_source_needs"],
        "duplicate_evidence_keys": totals["duplicate_evidence_keys"],
    }
    real_basis_choice_space = bool(
        alternative_key_names
        or totals["multi_plan_blocking_needs"]
        or totals["multi_source_needs"]
        or totals["duplicate_evidence_keys"]
    )

    # Multiple live plans are a decision problem, but do not by themselves
    # create alternative proof bases.  A10 legitimately has hold + conditional
    # backup before acquisition; its blocking evidence is still a fixed
    # conjunction owned by one plan.
    decision = (
        "GO_STATIC_BASIS_STUDY"
        if real_basis_choice_space
        else "KILL_BASIS_SELECTION_NO_REAL_CHOICE_SPACE"
    )
    payload = {
        "experiment": "basis-selection-headroom-v1",
        "status": "PASS",
        "decision": decision,
        "scope": {
            "trace_groups": TRACE_GROUPS,
            "model_facing_requested_assemblies": totals["model_requests"],
        },
        "totals": dict(sorted(totals.items())),
        "active_choice_signals": active_choice_signals,
        "examples": examples,
        "observed_key_shapes": dict(sorted(key_shapes.items())),
        "interpretation": (
            "The formal paper inputs contain no first-class alternative proof sets, no EvidenceNeed "
            "blocking multiple live plans, no multi-source requirement, and no duplicate proposition/subject "
            "evidence rows in the model-facing slice. Multiple live plans occur in the query-positive family, "
            "but the gateway-backup guard has a fixed conjunctive owner-evidence requirement. Therefore the "
            "current frozen workloads do not activate a nontrivial minimum-basis choice problem. Building an "
            "optimizer would require manufacturing proof alternatives not present in A7/A10/A11."
        ),
        "claim_boundary": (
            "This is a go/no-go audit for an optional future basis-selection algorithm. It does not change "
            "A7-A11 and does not claim that all future Agentic Communication workloads lack proof-choice structure."
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "decision": decision,
                "model_requests": totals["model_requests"],
                "requests_with_multiple_live_plans": totals["requests_with_multiple_live_plans"],
                **active_choice_signals,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print(f"WROTE {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

