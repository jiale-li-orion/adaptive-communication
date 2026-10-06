#!/usr/bin/env python3
"""Audit incremental conflict-frontier equivalence on real causal prefixes."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from causal_evidence_process_v0_1 import attach_causal_evidence
from compositional_recipe_generator_v0_1 import core_recipes
from dynamic_world_materializer_v0_1 import materialize_recipe
from exact_reference_oracle_v0_1 import LocalState, _attempt_lattice, _normalize
from layer2_v2_conflict_frontier import (
    IncrementalConflictFrontier,
    canonical_snapshot,
)
from layer2_v2_future_choice import solve_minimal_resource_v2
from v8_policy_baselines_v0_1 import _step


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
    all_rows = [row for case in cases for row in case["result"]["rows"]]
    for event in sorted({row["event_from_parent"] for row in all_rows}):
        subset = [row for row in all_rows if row["event_from_parent"] == event]
        denom = sum(row["component_count"] for row in subset)
        artifact["summary"]["event_recompute"][event] = {
            "prefix_count": len(subset),
            "component_recomputes": sum(row["component_recomputes"] for row in subset),
            "full_rebuild_components": denom,
            "ratio": (
                sum(row["component_recomputes"] for row in subset) / denom
                if denom else None
            ),
        }
    for width in sorted({row["max_component_width"] for row in all_rows}):
        subset = [row for row in all_rows if row["max_component_width"] == width]
        denom = sum(row["component_count"] for row in subset)
        artifact["summary"]["width_recompute"][str(width)] = {
            "prefix_count": len(subset),
            "component_recomputes": sum(row["component_recomputes"] for row in subset),
            "full_rebuild_components": denom,
            "ratio": (
                sum(row["component_recomputes"] for row in subset) / denom
                if denom else None
            ),
            "mean_dependency_edges": (
                sum(row["dependency_edge_count"] for row in subset) / len(subset)
                if subset else None
            ),
        }


def _event_kind(before, after, before_t: int, after_t: int) -> str:
    if set(after) != set(before):
        return "OBSERVATION_SUPPORT_CHANGE"
    if after_t != before_t:
        return "TIME_OR_ASYNC_EVENT"
    for wid in before:
        a, b = before[wid], after[wid]
        if a.delivered != b.delivered:
            return "DELIVERY_COMPLETION"
        if a.terrestrial_used != b.terrestrial_used:
            return "TERRESTRIAL_COMMIT"
        if a.satellite_used != b.satellite_used or a.satellite_budget != b.satellite_budget:
            return "SATELLITE_COMMIT"
        if a.pending_query != b.pending_query or a.last_query_signature != b.last_query_signature:
            return "QUERY_EVENT"
        if a.pending_deliveries != b.pending_deliveries:
            return "DELIVERY_ASYNC_EVENT"
    return "NO_STRUCTURAL_CHANGE"


def _walk(bundle, *, runtime, at_s, states, policy, rows, event_from_parent="ROOT"):
    process = attach_causal_evidence(bundle)
    branches = _normalize(bundle, process, at_s, states)
    if len(branches) != 1 or next(iter(branches)) != "same":
        assert policy.get("event") == "OBSERVATION"
        children = {str(row["observation"]): row for row in policy["children"]}
        assert set(children) == set(branches)
        for observation, child in sorted(branches.items()):
            _walk(
                bundle,
                # Sibling observations are mutually exclusive executions.
                # Each branch inherits the common-prefix frontier but must not
                # reuse certificates learned while auditing another sibling.
                runtime=deepcopy(runtime),
                at_s=at_s,
                states=child,
                policy=children[observation]["subpolicy"],
                rows=rows,
                event_from_parent=f"OBSERVATION:{observation}",
            )
        return

    support = next(iter(branches.values()))
    snapshot, delta = runtime.update(at_s=at_s, states=support)
    fresh = runtime.full_rebuild(at_s=at_s, states=support)
    component_widths = [
        len(component.obligations)
        for world in snapshot.world_certificates
        for component in world.components
    ]
    dependency_edge_count = sum(
        len(component.dependency_nodes)
        for world in snapshot.world_certificates
        for component in world.components
    )
    rows.append(
        {
            "time_s": at_s,
            "event_from_parent": event_from_parent,
            "world_count": len(support),
            "component_count": snapshot.component_count,
            "max_component_width": max(component_widths, default=0),
            "dependency_edge_count": dependency_edge_count,
            "frontier_match": canonical_snapshot(snapshot) == canonical_snapshot(fresh),
            "component_reuses": delta["component_reuses"],
            "component_recomputes": delta["component_recomputes"],
            "world_removals": delta["world_removals"],
            "partition_fallbacks": delta.get("partition_fallbacks", 0),
            "context": runtime.materialized_context(snapshot),
        }
    )
    if policy.get("terminal"):
        return
    action = (str(policy["action"]), policy.get("arg"))
    stepped = _step(bundle, process, support, at_s, action)
    assert stepped is not None
    child, next_t = stepped
    _walk(
        bundle,
        runtime=runtime,
        at_s=next_t,
        states=child,
        policy=policy["subpolicy"],
        rows=rows,
        event_from_parent=_event_kind(support, child, at_s, next_t),
    )


def run_case(bundle):
    solved = solve_minimal_resource_v2(bundle, upper_mode="all_recursive")
    assert solved["solvable"] is True
    q, sat = map(int, solved["minimal_resource_point"])
    runtime = IncrementalConflictFrontier(bundle)
    rows: list[dict[str, Any]] = []
    _walk(
        bundle,
        runtime=runtime,
        at_s=min(_attempt_lattice(bundle)),
        states=_initial(bundle, sat),
        policy=solved["policy"],
        rows=rows,
    )
    return {
        "minimal_resource_point": [q, sat],
        "prefix_count": len(rows),
        "frontier_match_count": sum(row["frontier_match"] for row in rows),
        "component_reuses": sum(row["component_reuses"] for row in rows),
        "component_recomputes": sum(row["component_recomputes"] for row in rows),
        "partition_fallbacks": sum(row["partition_fallbacks"] for row in rows),
        "full_rebuild_component_count": sum(row["component_count"] for row in rows),
        "event_counts": dict(sorted(Counter(row["event_from_parent"] for row in rows).items())),
        "width_counts": dict(sorted(Counter(str(row["max_component_width"]) for row in rows).items())),
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
        print(
            index,
            str(rep["signature"])[:12],
            result["frontier_match_count"],
            "/",
            result["prefix_count"],
            "reuse",
            result["component_reuses"],
            "recompute",
            result["component_recomputes"],
            "full-components",
            result["full_rebuild_component_count"],
            flush=True,
        )
    prefix_count = sum(row["result"]["prefix_count"] for row in cases)
    match_count = sum(row["result"]["frontier_match_count"] for row in cases)
    reuse = sum(row["result"]["component_reuses"] for row in cases)
    recompute = sum(row["result"]["component_recomputes"] for row in cases)
    partition_fallbacks = sum(row["result"]["partition_fallbacks"] for row in cases)
    full = sum(row["result"]["full_rebuild_component_count"] for row in cases)
    artifact = {
        "schema_version": "0.1",
        "status": "PASS" if cases and prefix_count == match_count else "FAIL",
        "experiment": "layer2-v2-conflict-frontier-incremental-equivalence",
        "split": args.split,
        "summary": {
            "signature_count": len(cases),
            "prefix_count": prefix_count,
            "frontier_match_count": match_count,
            "component_reuses": reuse,
            "component_recomputes": recompute,
            "partition_fallbacks": partition_fallbacks,
            "full_rebuild_component_count": full,
            "recompute_ratio_incremental_over_full": recompute / full if full else None,
            "event_recompute": {},
            "width_recompute": {},
        },
        "cases": cases,
        "rules": [
            "Component reuse is allowed only inside an explicit validity domain and with unchanged dependent execution/resource projection.",
            "World-support removal from lawful observations does not invalidate surviving per-world physical conflict certificates by itself.",
            "Incremental and fresh full-rebuild snapshots must match on every reachable causal prefix.",
            "No future hidden window identity is exposed by the materialized Layer-2 context.",
        ],
    }
    all_rows = [row for case in cases for row in case["result"]["rows"]]
    for event in sorted({row["event_from_parent"] for row in all_rows}):
        subset = [row for row in all_rows if row["event_from_parent"] == event]
        denom = sum(row["component_count"] for row in subset)
        recomputes = sum(row["component_recomputes"] for row in subset)
        artifact["summary"]["event_recompute"][event] = {
            "prefix_count": len(subset),
            "component_recomputes": recomputes,
            "full_rebuild_components": denom,
            "ratio": recomputes / denom if denom else None,
        }
    for width in sorted({row["max_component_width"] for row in all_rows}):
        subset = [row for row in all_rows if row["max_component_width"] == width]
        denom = sum(row["component_count"] for row in subset)
        recomputes = sum(row["component_recomputes"] for row in subset)
        artifact["summary"]["width_recompute"][str(width)] = {
            "prefix_count": len(subset),
            "component_recomputes": recomputes,
            "full_rebuild_components": denom,
            "ratio": recomputes / denom if denom else None,
            "mean_dependency_edges": (
                sum(row["dependency_edge_count"] for row in subset) / len(subset)
                if subset else None
            ),
        }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": artifact["status"], "summary": artifact["summary"]}, indent=2))
    return 0 if artifact["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
