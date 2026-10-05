#!/usr/bin/env python3
"""Machine-readable Q0-Q12 release-gate audit for Layer-1 v0.1.

The auditor is intentionally conservative.  Human/source review and policy
evaluation requirements are never auto-promoted to PASS from document presence.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
R = ROOT / "results/benchmark"
B = ROOT / "research/benchmark"


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _gate(qid: str, status: str, reason: str, *, evidence=None, blockers=None) -> dict[str, Any]:
    return {
        "gate_id": qid,
        "status": status,
        "reason": reason,
        "evidence": evidence or [],
        "blockers": blockers or [],
    }


def audit() -> dict[str, Any]:
    v0v7 = _json(R / "layer1-v0-v7-full-v0.1.json")
    v8 = _json(R / "layer1-v8-all-pass-v0.1.json")
    v9 = _json(R / "layer1-v9-evaluator-soundness-v0.1.json")
    split = _json(R / "layer1-structure-aware-split-v0.1.json")
    coverage = _json(R / "layer1-split-coverage-v0.1.json")

    hard = coverage["hard_survivor"]
    hard_axes_complete = all(
        not info["missing_from_global_hard_axes"]
        for split_info in hard["axis_coverage"].values()
        for info in split_info.values()
    )
    near_zero = all(
        x["cross_split_neighbor_fingerprint_count"] == 0
        for x in coverage["near_duplicate_one_axis"].values()
    )
    trace_cluster_owner: dict[str, set[str]] = {}
    for row in split["rows"]:
        trace_cluster_owner.setdefault(str(row["geometry_shape_cluster"]), set()).add(str(row["split"]))
    trace_exclusive = all(len(v) == 1 for v in trace_cluster_owner.values())

    gates = []
    gates.append(_gate(
        "Q0", "PASS",
        "Target construct is frozen as T1 monitoring-information continuity; ordinary saturation is reported as boundary evidence instead of being rebranded as agentic hardness.",
        evidence=[
            "research/benchmark/LAYER1-AUTHORITY.md",
            "research/benchmark/V8-BASELINE-CONTRACT.v0.1.md",
            "results/benchmark/layer1-v8-all-pass-v0.1.json",
        ],
    ))
    gates.append(_gate(
        "Q1", "PASS" if v0v7["status"] == "COMPLETE" else "BLOCKED",
        "Full universe is source/task classified; physically invalid and information-infeasible objects retain explicit dispositions instead of being scored as policy failures.",
        evidence=["results/benchmark/layer1-v0-v7-full-v0.1.json", "research/benchmark/TASK-COVERAGE-CLOSURE.v0.1.md"],
    ))
    gates.append(_gate(
        "Q2", "PASS" if v9.get("passed") else "BLOCKED",
        "Independent execution evaluator accepts legal witnesses and rejects no-op, authority, physics, protected-state and missing-execution mutations.",
        evidence=["results/benchmark/layer1-v9-evaluator-soundness-v0.1.json"],
    ))
    taxonomy_files = [
        B / "TASK-SURFACE-REGISTRY.v0.1.json",
        B / "TASK-COVERAGE-CLOSURE.v0.1.md",
        B / "profiles/v0.1/SOURCE-PROFILE-REGISTRY.v0.1.json",
    ]
    gates.append(_gate(
        "Q3", "PASS" if all(p.exists() for p in taxonomy_files) else "BLOCKED",
        "T1 taxonomy and source profiles are versioned and direct task authority is separated from adjacent mechanism evidence.",
        evidence=[str(p.relative_to(ROOT)) for p in taxonomy_files if p.exists()],
    ))
    q4_pass = bool(split["leakage_audit"]["passed"]) and hard_axes_complete and near_zero
    gates.append(_gate(
        "Q4", "PASS" if q4_pass else "BLOCKED",
        "Pre-admission pool covers easy, negative, information-infeasible and hard survivor roles; held-out split is structural and near-duplicate audits are clean.",
        evidence=["results/benchmark/layer1-structure-aware-split-v0.1.json", "results/benchmark/layer1-split-coverage-v0.1.json"],
        blockers=[] if q4_pass else ["coverage/leakage invariant failed"],
    ))
    q5_pass = v8["status"] == "COMPLETE" and v8["survivor_signature_count"] > 0 and hard["recipe_count"] == v8["projected_survivor_recipe_count"]
    gates.append(_gate(
        "Q5", "PASS" if q5_pass else "BLOCKED",
        "Hard subset passed V0-V7 and the placement-preserving V8 ladder; controls remain separately labeled instead of inheriting hardness claims.",
        evidence=["results/benchmark/layer1-v0-v7-full-v0.1.json", "results/benchmark/layer1-v8-all-pass-v0.1.json"],
    ))

    llm_ref = R / "layer1-llm-baseline-v0.1.json"
    llm_pass = False
    if llm_ref.exists():
        try:
            llm = _json(llm_ref)
            llm_pass = (
                llm.get("status") == "COMPLETE"
                and int(llm.get("completed_signature_count", -1)) == int(llm.get("test_hard_signature_count", -2))
            )
        except Exception:
            llm_pass = False
    gates.append(_gate(
        "Q6", "PASS" if llm_pass else "BLOCKED",
        "Rule/local/EDF/search/oracle ladder exists; release gate still requires an LLM/reasoning-agent baseline on the frozen split.",
        evidence=[
            "results/benchmark/layer1-v8-all-pass-v0.1.json",
            "results/benchmark/layer1-v8-current-v0.1.json",
            "research/benchmark/V8-BASELINE-CONTRACT.v0.1.md",
        ],
        blockers=[] if llm_pass else ["frozen-split LLM/reasoning-agent baseline is missing or incomplete"],
    ))

    q7_pass = bool(split["leakage_audit"]["passed"]) and trace_exclusive and hard_axes_complete and near_zero
    gates.append(_gate(
        "Q7", "PASS" if q7_pass else "BLOCKED",
        "Translation-invariant empirical trace clusters are split-exclusive; exact signatures and one-axis source/template neighbors do not cross splits.",
        evidence=["results/benchmark/layer1-structure-aware-split-v0.1.json", "results/benchmark/layer1-split-coverage-v0.1.json"],
        blockers=[] if q7_pass else ["trace/generalization leakage remains"],
    ))

    public_test = R / "layer1-public-test-freeze-v0.1.json"
    gates.append(_gate(
        "Q8", "PASS" if public_test.exists() else "BLOCKED",
        "Development generator and frozen public test identity must be separated before release.",
        evidence=[str(public_test.relative_to(ROOT))] if public_test.exists() else [],
        blockers=[] if public_test.exists() else ["public test freeze/checksum artifact not materialized"],
    ))

    stats = B / "STATISTICAL-REPORTING.v0.1.md"
    gates.append(_gate(
        "Q9", "PASS" if stats.exists() else "BLOCKED",
        "Statistical protocol must define repeated stochastic runs, intervals, paired comparisons, stratification and invalid-run handling before leaderboard reporting.",
        evidence=[str(stats.relative_to(ROOT))] if stats.exists() else [],
        blockers=[] if stats.exists() else ["statistical reporting protocol missing"],
    ))

    repro = ROOT / "code/evaluation/benchmark/reproduce_layer1_v0_1.py"
    frozen_manifest = R / "layer1-release-manifest-v0.1.json"
    q10_pass = repro.exists() and frozen_manifest.exists()
    gates.append(_gate(
        "Q10", "PASS" if q10_pass else "BLOCKED",
        "Release needs immutable artifact bindings and a one-command validation/reproduction entry.",
        evidence=[str(p.relative_to(ROOT)) for p in (repro, frozen_manifest) if p.exists()],
        blockers=[] if q10_pass else ["reproduction entry and/or frozen release manifest missing"],
    ))

    human = R / "layer1-human-source-audit-v0.1.json"
    human_pass = False
    if human.exists():
        try:
            human_pass = _json(human).get("status") == "PASS"
        except Exception:
            human_pass = False
    gates.append(_gate(
        "Q11", "PASS" if human_pass else "BLOCKED",
        "Human/source review cannot be auto-passed; a stratified audit sample and reviewer disposition are required.",
        evidence=[str(human.relative_to(ROOT))] if human.exists() else [],
        blockers=[] if human_pass else ["human/source audit pending reviewer completion"],
    ))

    maintenance = B / "BENCHMARK-MAINTENANCE.v0.1.md"
    gates.append(_gate(
        "Q12", "PASS" if maintenance.exists() else "BLOCKED",
        "Schema/source/generator/case versions and flaw migration policy must be frozen for lifecycle maintenance.",
        evidence=[str(maintenance.relative_to(ROOT))] if maintenance.exists() else [],
        blockers=[] if maintenance.exists() else ["maintenance/version-migration policy missing"],
    ))

    counts: dict[str, int] = {}
    for g in gates:
        counts[g["status"]] = counts.get(g["status"], 0) + 1
    return {
        "schema_version": "0.1",
        "status": "QUALITY_GATE_AUDIT",
        "gate_counts": counts,
        "all_pass": all(g["status"] == "PASS" for g in gates),
        "gates": gates,
        "release_status": "BENCHMARK_ADMIT" if all(g["status"] == "PASS" for g in gates) else "NOT_BENCHMARK_ADMIT",
    }


if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False, indent=2, sort_keys=True))
