#!/usr/bin/env python3
"""Audit Evidence-node lifecycle on real Layer-1 v0.2 causal policy prefixes."""
from __future__ import annotations

import argparse
from collections import defaultdict
from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from causal_evidence_process_v0_1 import attach_causal_evidence
from compositional_recipe_generator_v0_1 import core_recipes
from dynamic_world_materializer_v0_1 import materialize_recipe
from exact_reference_oracle_v0_1 import LocalState, _attempt_lattice, _normalize
from layer2_v2_conflict_frontier import IncrementalConflictFrontier
from layer2_v2_evidence_context import EvidenceLedger, materialize_context_graph
from layer2_v2_future_choice import solve_minimal_resource_v2
from v8_policy_baselines_v0_1 import _legal_actions, _step


ROOT = Path(__file__).resolve().parents[3]
SPLIT = ROOT / "results/benchmark/layer1-structure-aware-split-v0.2-retry-legality.json"


def _representatives(split_name: str) -> list[dict[str, Any]]:
    frozen = json.loads(SPLIT.read_text(encoding="utf-8"))
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in frozen["rows"]:
        if row.get("candidate_role") == "HARD_PRE_ADMISSION_SURVIVOR" and row.get("split") == split_name:
            grouped[str(row["signature"])].append(row)
    return [min(rows, key=lambda row: str(row["recipe_id"])) for _, rows in sorted(grouped.items())]


def _initial(bundle, sat_budget: int):
    return {
        str(world["world_id"]): LocalState(satellite_budget=sat_budget)
        for world in bundle["worlds"]
    }


def _walk(bundle, *, at_s, states, query_budget, policy, ledger, conflict, rows):
    process = attach_causal_evidence(bundle)
    branches = _normalize(bundle, process, at_s, states)
    if len(branches) != 1 or next(iter(branches)) != "same":
        assert policy.get("event") == "OBSERVATION"
        children = {str(row["observation"]): row for row in policy["children"]}
        assert set(children) == set(branches)
        for observation, child in sorted(branches.items()):
            branch_ledger = ledger.clone()
            added = branch_ledger.apply_observation_key(observation, arrived_at_s=at_s)
            _walk(
                bundle,
                at_s=at_s,
                states=child,
                query_budget=query_budget,
                policy=children[observation]["subpolicy"],
                ledger=branch_ledger,
                conflict=deepcopy(conflict),
                rows=rows,
            )
        return

    support = next(iter(branches.values()))
    snapshot, _delta = conflict.update(at_s=at_s, states=support)
    graph = materialize_context_graph(
        bundle,
        at_s=at_s,
        conflict_snapshot=snapshot,
        evidence_ledger=ledger,
        legal_actions=_legal_actions(bundle, process, support, at_s),
    )
    evidence_nodes = [row for row in graph["nodes"] if row["kind"] == "Evidence"]
    rows.append(
        {
            "time_s": at_s,
            "evidence_count": len(evidence_nodes),
            "history_retained": all(row["historical_fact_retained"] for row in evidence_nodes),
            "timeout_payload_violation": any(
                row["outcome"] == "TIMEOUT" and row["value"] is not None
                for row in evidence_nodes
            ),
            "future_hidden_exposed": bool(graph["hidden_future_window_identity_exposed"]),
            "oracle_witness_exposed": bool(graph["oracle_witness_exposed"]),
            "gateway_versions": [
                row["version"]
                for row in evidence_nodes
                if row["proposition"] == "communication.gateway.state_summary"
            ],
            "gateway_inference_statuses": [
                row["current_inference_status"]
                for row in evidence_nodes
                if row["proposition"] == "communication.gateway.state_summary"
            ],
            "graph": graph,
        }
    )
    if policy.get("terminal"):
        return
    action = (str(policy["action"]), policy.get("arg"))
    dq = int(action[0] == "ISSUE_QUERY")
    if action[0] == "ISSUE_QUERY":
        ledger.issue_gateway_query(issue_at_s=at_s)
    stepped = _step(bundle, process, support, at_s, action)
    assert stepped is not None
    child, next_t = stepped
    _walk(
        bundle,
        at_s=next_t,
        states=child,
        query_budget=query_budget - dq,
        policy=policy["subpolicy"],
        ledger=ledger,
        conflict=conflict,
        rows=rows,
    )


def run_case(bundle):
    solved = solve_minimal_resource_v2(bundle, upper_mode="all_recursive")
    assert solved["solvable"] is True
    q, sat = map(int, solved["minimal_resource_point"])
    rows: list[dict[str, Any]] = []
    _walk(
        bundle,
        at_s=min(_attempt_lattice(bundle)),
        states=_initial(bundle, sat),
        query_budget=q,
        policy=solved["policy"],
        ledger=EvidenceLedger(),
        conflict=IncrementalConflictFrontier(bundle),
        rows=rows,
    )
    gateway_records = [
        (row["time_s"], version, status)
        for row in rows
        for version, status in zip(row["gateway_versions"], row["gateway_inference_statuses"])
    ]
    return {
        "prefix_count": len(rows),
        "history_retention_pass": all(row["history_retained"] for row in rows),
        "timeout_unresolved_pass": not any(row["timeout_payload_violation"] for row in rows),
        "no_hidden_future_pass": not any(row["future_hidden_exposed"] for row in rows),
        "no_oracle_witness_pass": not any(row["oracle_witness_exposed"] for row in rows),
        "gateway_version_monotone": all(
            versions == sorted(versions)
            for versions in (row["gateway_versions"] for row in rows)
        ),
        "stale_gateway_history_observed": any(status == "STALE_FOR_CURRENT_STATE" for _t, _v, status in gateway_records),
        "current_gateway_sample_observed": any(status == "CURRENT_AT_SAMPLE" for _t, _v, status in gateway_records),
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["train", "dev", "test"], default="dev")
    ap.add_argument("--limit", type=int, default=1)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    reps = _representatives(args.split)[: args.limit]
    recipes = {row.recipe_id: row for row in core_recipes()}
    cases = []
    for index, rep in enumerate(reps, 1):
        result = run_case(materialize_recipe(recipes[str(rep["recipe_id"])]))
        cases.append({"signature": rep["signature"], "recipe_id": rep["recipe_id"], "result": result})
        print(index, str(rep["signature"])[:12], result["prefix_count"], "prefixes", flush=True)
    checks = [
        "history_retention_pass",
        "timeout_unresolved_pass",
        "no_hidden_future_pass",
        "no_oracle_witness_pass",
        "gateway_version_monotone",
    ]
    summary = {
        "signature_count": len(cases),
        "prefix_count": sum(row["result"]["prefix_count"] for row in cases),
        **{
            key: all(row["result"][key] for row in cases)
            for key in checks
        },
        "signatures_with_stale_gateway_history": sum(
            row["result"]["stale_gateway_history_observed"] for row in cases
        ),
        "signatures_with_current_gateway_sample": sum(
            row["result"]["current_gateway_sample_observed"] for row in cases
        ),
    }
    passed = bool(cases) and all(summary[key] for key in checks)
    artifact = {
        "schema_version": "0.1",
        "status": "PASS" if passed else "FAIL",
        "experiment": "layer2-v2-versioned-evidence-context",
        "split": args.split,
        "summary": summary,
        "cases": cases,
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": artifact["status"], "summary": summary}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
