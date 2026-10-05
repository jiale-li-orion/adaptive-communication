#!/usr/bin/env python3
"""V8 ordinary-baseline shortcut audit on exact paid-evidence structural cells."""
from __future__ import annotations

from collections import Counter
import argparse
import json

from audit_exact_reference_oracle_v0_1 import _headroom_from_bundle, _stable_rank
from causal_evidence_process_v0_1 import attach_causal_evidence
from dynamic_world_materializer_v0_1 import iter_world_bundles
from exact_reference_oracle_v0_1 import hindsight_bundle_reference, solve_observation_matched
from ordinary_baselines_compositional_v0_1 import audit_bundle


def _representatives():
    chosen = {}
    for bundle in iter_world_bundles():
        if bundle["pre_oracle_disposition"] != "VALIDITY_PENDING":
            continue
        cell = (
            str(bundle["public_environment"]["terrestrial_process_class"]),
            str(bundle["observation_projection"]["evidence_regime"]),
            str(len(bundle["obligations"])),
            _headroom_from_bundle(bundle),
            str(bundle["recovery"]["regime"]),
        )
        rank = _stable_rank(bundle)
        if cell not in chosen or rank < chosen[cell][0]:
            chosen[cell] = (rank, bundle)
    return chosen


def audit(*, max_memo_nodes: int = 200_000) -> dict:
    selected = []
    for cell, (_rank, bundle) in sorted(_representatives().items()):
        physical = hindsight_bundle_reference(bundle)
        if not physical["all_worlds_solvable"]:
            continue
        process = attach_causal_evidence(bundle)
        exact = solve_observation_matched(bundle, process, max_memo_nodes=max_memo_nodes)
        no_query = solve_observation_matched(
            bundle, process, disable_paid_query=True, max_memo_nodes=max_memo_nodes
        )
        if exact["status"] != "EXACT" or no_query["status"] != "EXACT":
            continue
        if exact["solvable"] and not no_query["solvable"]:
            selected.append((cell, bundle, exact, no_query))

    disposition = Counter()
    same_information_success = Counter()
    deployment_success = Counter()
    rows = []
    for cell, bundle, exact, no_query in selected:
        baselines = audit_bundle(bundle)
        same_information_winners = sorted(
            name for name, row in baselines.items()
            if row.get("legal")
            and row.get("robust_success") is True
            and row.get("comparison_role") == "SAME_INFORMATION_SHORTCUT"
        )
        deployment_winners = sorted(
            name for name, row in baselines.items()
            if row.get("legal")
            and row.get("robust_success") is True
            and row.get("comparison_role") == "DEPLOYMENT_ALTERNATIVE"
        )
        cls = (
            "SHORTCUT_SOLVED_SAME_INFORMATION"
            if same_information_winners
            else "SURVIVES_SAME_INFORMATION_ORDINARY_BASELINES"
        )
        disposition[cls] += 1
        for name in same_information_winners:
            same_information_success[name] += 1
        for name in deployment_winners:
            deployment_success[name] += 1
        rows.append({
            "cell": list(cell),
            "recipe_id": bundle["recipe_id"],
            "task_case_id": bundle["task_case_id"],
            "geometry_signature_id": bundle["public_environment"]["geometry_signature_id"],
            "exact_memo_nodes": exact["memo_nodes"],
            "no_query_memo_nodes": no_query["memo_nodes"],
            "v8_disposition": cls,
            "same_information_shortcut_baselines": same_information_winners,
            "deployment_alternatives": deployment_winners,
            "baselines": {
                name: {
                    "legal": row.get("legal"),
                    "placement": row.get("placement"),
                    "comparison_role": row.get("comparison_role"),
                    "robust_success": row.get("robust_success"),
                    "world_success_count": row.get("world_success_count"),
                    "world_count": row.get("world_count"),
                }
                for name, row in baselines.items()
            },
        })
    return {
        "schema_version": "0.1",
        "status": "V8_ORDINARY_BASELINE_AUDIT",
        "selection": {
            "source": "one stable representative per VALIDITY_PENDING structural cell",
            "paid_evidence_required_cells": len(selected),
        },
        "disposition": dict(sorted(disposition.items())),
        "same_information_shortcut_coverage": dict(sorted(same_information_success.items())),
        "deployment_alternative_coverage": dict(sorted(deployment_success.items())),
        "rows": rows,
        "limitations": [
            "Gateway-local EDF/reserve changes planner placement and is reported as a deployment alternative, not a same-information V8 shortcut.",
            "Same-information shortcut baselines in this layer are blind satellite EDF, legal send-probe ACK fallback, and legal fixed owner-read EDF.",
            "Survivors still require shallow/depth-k/receding-horizon/generic exact computation baselines before final V8 PASS."
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-memo-nodes", type=int, default=200_000)
    args = ap.parse_args()
    print(json.dumps(audit(max_memo_nodes=args.max_memo_nodes), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
