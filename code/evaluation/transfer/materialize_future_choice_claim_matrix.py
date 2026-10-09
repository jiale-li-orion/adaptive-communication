#!/usr/bin/env python3
"""Materialize the paper-facing A/B/C claim matrix from tracked artifacts.

The file is deliberately conservative: every quantitative statement is read
from an existing result artifact and every claim carries a boundary/forbidden
overclaim.  A's LLM subset is left OPEN until the frozen 60-row run completes.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "results/transfer/future-choice-claim-matrix.json"

FILES = {
    "A_inventory": ROOT / "results/benchmark/layer1-paper-track-inventory.json",
    "A_deterministic": ROOT / "results/benchmark/layer1-paper-deterministic-test/statistical-analysis.json",
    "A_release": ROOT / "results/benchmark/layer1-paper-release-candidate.json",
    "B_conditional": ROOT / "results/transfer/asc-pull-query-conditional-family.json",
    "B_shared": ROOT / "results/transfer/asc-pull-query-shared-opportunity-frontier.json",
    "B_dynamic": ROOT / "results/transfer/asc-pull-query-dynamic-frontier-reuse.json",
    "B_components": ROOT / "results/transfer/asc-pull-query-component-strong-baselines.json",
    "BC_engine": ROOT / "results/transfer/generic-future-choice-engine-cross-domain.json",
    "C_generic_parity": ROOT / "results/transfer/uav-attention-generic-engine-n10-parity.json",
    "C_scale": ROOT / "results/transfer/uav-attention-n10-scale-statistics.json",
    "C_n10": ROOT / "results/transfer/uav-attention-n10-future-choice-summary.json",
    "C_set_mst": ROOT / "results/transfer/uav-attention-set-mst-attribution.json",
    "C_pareto": ROOT / "results/transfer/uav-attention-correctness-compute-frontier.json",
    "C_robust": ROOT / "results/transfer/uav-attention-future-choice-robustness-summary.json",
}


def load(name: str):
    return json.loads(FILES[name].read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main() -> int:
    a_inv = load("A_inventory")
    a_det = load("A_deterministic")
    a_rel = load("A_release")
    b_cond = load("B_conditional")
    b_shared = load("B_shared")
    b_dyn = load("B_dynamic")
    b_comp = load("B_components")
    bc = load("BC_engine")
    cgeneric = load("C_generic_parity")
    cscale = load("C_scale")
    c10 = load("C_n10")
    cset = load("C_set_mst")
    cpareto = load("C_pareto")
    crob = load("C_robust")

    n10_rows = c10["rows"]
    claims = [
        {
            "id": "A1_source_grounded_executable_benchmark",
            "status": "SUPPORTED_DETERMINISTIC_LLM_SUBSET_OPEN",
            "claim": (
                "Layer 1 provides a source-grounded executable pre-disaster emergency-communication benchmark "
                "with explicit conformance/interactive/stress roles rather than presuming all realistic tasks are Agentic-hard."
            ),
            "evidence": {
                "canonical_surfaces": a_inv["counts"]["canonical_surface_count"],
                "release_candidate_surfaces": a_inv["counts"]["paper_release_candidate_surface_count"],
                "blocked_surfaces": a_inv["counts"]["blocked_surface_count"],
                "deterministic_checks": a_det["checks"],
                "pre_release_status": a_rel["status"],
            },
            "boundary": "The frozen 30-coordinate × 2-mode LLM spectrum is still running; do not claim the final benchmark release until it is complete and the final manifest is frozen."
        },
        {
            "id": "B1_static_union_fails_conditional_obligations",
            "status": "SUPPORTED",
            "claim": "Static worst-case union of mutually exclusive future obligations can reject a valid causal query policy; future obligations must be observation-conditioned.",
            "evidence": {
                "conditional_family_cells": b_cond["summary"]["cell_count"],
                "conditional_multibranch_cells": b_cond["summary"]["nontrivial_multibranch_cells"],
                "static_union_false_negative_cells": b_cond["summary"]["static_union_false_negative_cells"],
                "shared_opportunity_nontrivial_cells": b_shared["summary"]["nontrivial_cells"],
                "shared_opportunity_false_negative_cells": b_shared["summary"]["static_union_false_negative_cells"],
                "max_union_min_backup": b_shared["summary"]["max_union_min_backup"],
            },
            "boundary": "This proves representation necessity against static union/reservation, not superiority over a strong exact belief-space solver."
        },
        {
            "id": "B2_persistent_conditional_domains_reduce_rebuilds",
            "status": "SUPPORTED_STRUCTURAL_WORK",
            "claim": "Persistent conditional validity domains avoid rebuilding inactive branch frontiers across observation-only support narrowing.",
            "evidence": b_dyn["summary"],
            "boundary": "Frontier-build counts are structural work, not a wall-time theorem."
        },
        {
            "id": "B3_dependency_local_invalidation",
            "status": "SUPPORTED_STRUCTURAL_WORK",
            "claim": "Future-feasibility certificates should be invalidated by dependency changes, not by every new history event.",
            "evidence": {
                "C16_fresh_exact_expanded": b_comp["summary"]["fresh_exact_expanded"]["16"],
                "C16_persistent_exact_expanded": b_comp["summary"]["ordinary_persistent_exact_expanded"]["16"],
                "C16_dependency_exact_expanded": b_comp["summary"]["dependency_cache_exact_expanded"]["16"],
                "C16_dependency_separator_replay": b_comp["summary"]["dependency_separator_replay_success"]["16"],
                "C16_component_recomputes": b_comp["summary"]["incremental_component_recomputes"]["16"],
                "C16_component_reuses": b_comp["summary"]["incremental_component_reuses"]["16"],
            },
            "boundary": "Exact expansions and component recomputes are different work units; do not ratio them as CPU-equivalent operations."
        },
        {
            "id": "C1_local_legality_not_full_feasibility",
            "status": "SUPPORTED_EXTERNAL_DOMAIN",
            "claim": "In an independent public deadline/battery routing environment, a native-mask-legal action can destroy an otherwise feasible zero-tardiness full continuation.",
            "evidence": {
                "robust_seed_count": next(iter(crob["exact_shield_1000"].values()))["hard_feasible_seed_count"],
            },
            "boundary": "Zero-tardiness treats the environment's native deadline fields as hard operational obligations; the released environment itself permits tardy completion."
        },
        {
            "id": "C2_exact_correct_future_choice_improves_mission_quality",
            "status": "SUPPORTED_EXTERNAL_DOMAIN",
            "claim": "Continuation-aware L/U shielding eliminates residual short-horizon failures on the frozen N=10 constructive cohort while preserving exact action feasibility.",
            "evidence": {
                policy: {
                    "depth4_zero_tardiness": row["depth4_receding"]["zero_tardiness"],
                    "depth4_completed": row["depth4_receding"]["completed"],
                    "depth4_infeasible": row["depth4_receding"]["infeasible"],
                    "future_choice_zero_tardiness": row["future_choice_lu"]["zero_tardiness"],
                    "future_choice_completed": row["future_choice_lu"]["completed"],
                    "future_choice_infeasible": row["future_choice_lu"]["infeasible"],
                }
                for policy, row in n10_rows.items()
            },
            "pareto_checks": cpareto["checks"],
            "scale_checks": cscale["checks"],
            "constructive100": {
                policy: {
                    method: {
                        "zero_tardiness": stats["zero_tardiness"],
                        "completion": stats["completion"],
                        "infeasible_free": stats["infeasible_free"],
                    }
                    for method, stats in row["methods"].items()
                }
                for policy, row in cscale["constructive100"].items()
            },
            "boundary": "Depth-4 is cheaper and nearly saturates some policies; future-choice is a selective exact-correct safety layer, not a universal replacement for MPC."
        },
        {
            "id": "BC1_set_level_conflict_transfers_across_domains",
            "status": "SUPPORTED_CROSS_DOMAIN_ATTRIBUTION",
            "claim": "The set-level obligation-conflict principle isolated in ASC directly strengthens the external UAV domain's sound U-bound without changing task outcomes or the exact correctness authority.",
            "evidence": {
                policy: row["n10_compute"]
                for policy, row in cset["n10"]["rows"].items()
            },
            "checks": cset["checks"],
            "pareto_checks": cpareto["checks"],
            "boundary": "The C-domain deadline-set MST is a domain-specific certificate; the cross-domain claim is about the shared set-level future-conflict abstraction, not identical physical constraints."
        },
        {
            "id": "BC2_shared_orchestration_core",
            "status": "SUPPORTED",
            "claim": "ASC and UAV adapters share the same carried-certificate → sound U=0 → constructive L=1 → exact-fallback orchestration protocol.",
            "evidence": {
                "cross_domain_smoke": bc.get("checks", bc),
                "uav_n10_full_cohort_parity": cgeneric["checks"],
                "uav_n10_frontier_checks": cgeneric["frontier_checks"],
            },
            "boundary": "Domain-specific certificate construction is still separate; shared orchestration alone is not proof of one universal physical model."
        },
    ]

    payload = {
        "stage": "FUTURE_CHOICE_PAPER_CLAIM_MATRIX",
        "claims": claims,
        "files": {
            name: {
                "path": str(path.relative_to(ROOT)),
                "sha256": digest(path),
            }
            for name, path in FILES.items()
        },
        "global_forbidden_overclaims": [
            "Do not claim wall-time superiority over ordinary persistent exact or depth-k receding planning.",
            "Do not claim every source-grounded emergency-communication task requires future-choice reasoning.",
            "Do not claim C itself is an emergency-communication benchmark.",
            "Do not call the internal assistant-led source audit independent expert validation.",
            "Do not use the N=15 seed1 probe as a distribution-level result."
        ],
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(OUT), "claim_count": len(claims)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
