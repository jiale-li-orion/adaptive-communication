#!/usr/bin/env python3
"""Deterministic pre-admission audit for the v0.1 exact references.

The default audit samples the frozen recipe order with a fixed stride.  It is a
construction diagnostic, not a benchmark split and not a model-selected filter.
Use ``--physical-full`` to scan all 58,752 bundles with the cheap hindsight
matching reference before running the more expensive causal AND/OR pilot.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from typing import Any

from causal_evidence_process_v0_1 import attach_causal_evidence
from dynamic_world_materializer_v0_1 import iter_world_bundles
from exact_reference_oracle_v0_1 import (
    hindsight_bundle_reference,
    solve_observation_matched,
)


def physical_full_scan() -> dict[str, Any]:
    bundles = Counter()
    worlds = Counter()
    by_disposition = Counter()
    by_service = Counter()
    total = 0
    for bundle in iter_world_bundles():
        total += 1
        ref = hindsight_bundle_reference(bundle)
        key = (
            "ALL_WORLD_SOLVABLE"
            if ref["all_worlds_solvable"]
            else "MIXED_WORLD_SOLVABILITY"
            if ref["any_world_solvable"]
            else "NO_WORLD_SOLVABLE"
        )
        bundles[key] += 1
        by_disposition[(str(bundle["pre_oracle_disposition"]), key)] += 1
        by_service[(str(bundle["public_environment"]["terrestrial_process_class"]), key)] += 1
        for row in ref["worlds"]:
            worlds["SOLVABLE" if row["solvable"] else "INFEASIBLE"] += 1
    return {
        "bundle_count": total,
        "bundle_physical_class": dict(sorted(bundles.items())),
        "world_physical_class": dict(sorted(worlds.items())),
        "by_pre_oracle_disposition": {
            f"{a}|{b}": v for (a, b), v in sorted(by_disposition.items())
        },
        "by_service_process": {
            f"{a}|{b}": v for (a, b), v in sorted(by_service.items())
        },
    }


def _headroom_from_bundle(bundle: dict[str, Any]) -> str:
    overlap = len(bundle["obligations"])
    budget = int(bundle["public_environment"]["satellite_budget_units"])
    if budget == max(1, overlap - 1):
        return "TIGHT"
    if budget == overlap:
        return "BALANCED"
    if budget == overlap + 1:
        return "SLACK"
    return f"OTHER:{budget}"


def _stable_rank(bundle: dict[str, Any]) -> str:
    payload = "|".join([
        str(bundle["recipe_id"]),
        str(bundle["task_case_id"]),
        str(bundle["public_environment"]["geometry_signature_id"]),
    ])
    return sha256(payload.encode("utf-8")).hexdigest()


def stratified_validity_pilot(*, max_memo_nodes: int) -> dict[str, Any]:
    """One deterministic representative per frozen hard-structure cell."""
    chosen: dict[tuple[str, ...], tuple[str, dict[str, Any]]] = {}
    for bundle in iter_world_bundles():
        if str(bundle["pre_oracle_disposition"]) != "VALIDITY_PENDING":
            continue
        cell = (
            str(bundle["public_environment"]["terrestrial_process_class"]),
            str(bundle["observation_projection"]["evidence_regime"]),
            str(len(bundle["obligations"])),
            _headroom_from_bundle(bundle),
            str(bundle["recovery"]["regime"]),
        )
        rank = _stable_rank(bundle)
        old = chosen.get(cell)
        if old is None or rank < old[0]:
            chosen[cell] = (rank, bundle)

    outcome = Counter()
    reference = Counter()
    by_service_evidence = Counter()
    by_cell: dict[str, str] = {}
    examples: dict[str, dict[str, Any]] = {}
    search_limits: list[str] = []
    memo_nodes: list[int] = []

    for cell, (_rank, bundle) in sorted(chosen.items()):
        physical = hindsight_bundle_reference(bundle)
        if not physical["all_worlds_solvable"]:
            cls = "PHYSICAL_NOT_ALL_WORLD_SOLVABLE"
            outcome[cls] += 1
            by_cell["|".join(cell)] = cls
            continue
        reference["P_ALL_WORLD_PHYSICAL"] += 1
        process = attach_causal_evidence(bundle)
        full_current = solve_observation_matched(
            bundle, process, disable_paid_query=True,
            force_full_current_state=True, max_memo_nodes=max_memo_nodes,
        )
        exact = solve_observation_matched(
            bundle, process, disable_paid_query=False, max_memo_nodes=max_memo_nodes,
        )
        no_query = solve_observation_matched(
            bundle, process, disable_paid_query=True, max_memo_nodes=max_memo_nodes,
        )
        refs = {"full_current": full_current, "exact": exact, "no_query": no_query}
        memo_nodes.append(max(int(x["memo_nodes"]) for x in refs.values()))
        limited = [name for name, row in refs.items() if row["status"] == "SEARCH_LIMIT"]
        if limited:
            cls = "SEARCH_LIMIT"
            search_limits.append("|".join(cell) + ":" + ",".join(limited))
        elif not full_current["solvable"]:
            cls = "FULL_CURRENT_STATE_INFEASIBLE"
        elif not exact["solvable"]:
            cls = "INFORMATION_INFEASIBLE"
            reference["FULL_CURRENT_STATE"] += 1
        elif no_query["solvable"]:
            cls = "NO_PAID_QUERY_REQUIRED"
            reference["FULL_CURRENT_STATE"] += 1
            reference["F_OBSERVATION_MATCHED"] += 1
            reference["N_NO_PAID_QUERY"] += 1
        else:
            cls = "PAID_EVIDENCE_REQUIRED"
            reference["FULL_CURRENT_STATE"] += 1
            reference["F_OBSERVATION_MATCHED"] += 1

        if exact["status"] == "EXACT" and exact["solvable"]:
            assert full_current["status"] == "EXACT" and full_current["solvable"]
        if no_query["status"] == "EXACT" and no_query["solvable"]:
            assert exact["status"] == "EXACT" and exact["solvable"]
        outcome[cls] += 1
        by_service_evidence[(cell[0], cell[1], cls)] += 1
        by_cell["|".join(cell)] = cls
        examples.setdefault(cls, {
            "recipe_id": bundle["recipe_id"],
            "task_case_id": bundle["task_case_id"],
            "geometry_signature_id": bundle["public_environment"]["geometry_signature_id"],
            "cell": list(cell),
            "full_current_memo_nodes": full_current["memo_nodes"],
            "exact_memo_nodes": exact["memo_nodes"],
            "no_query_memo_nodes": no_query["memo_nodes"],
        })

    f = int(reference["F_OBSERVATION_MATCHED"])
    n = int(reference["N_NO_PAID_QUERY"])
    return {
        "selection": {
            "rule": "VALIDITY_PENDING only; one minimum-stable-hash representative per service×evidence×overlap×headroom×recovery cell",
            "cell_count": len(chosen),
            "use": "construction diagnostic only; not a benchmark split or admission filter",
        },
        "outcome": dict(sorted(outcome.items())),
        "reference_counts": dict(sorted(reference.items())),
        "information_value_gap": ((f - n) / f) if f else None,
        "by_service_evidence": {
            f"{a}|{b}|{c}": v for (a, b, c), v in sorted(by_service_evidence.items())
        },
        "by_cell": by_cell,
        "examples": examples,
        "search": {
            "max_memo_nodes_limit": max_memo_nodes,
            "search_limit_count": len(search_limits),
            "search_limit_cells": search_limits,
            "observed_max_memo_nodes": max(memo_nodes) if memo_nodes else 0,
            "mean_max_memo_nodes": (sum(memo_nodes) / len(memo_nodes)) if memo_nodes else 0.0,
        },
    }


def observation_pilot(*, stride: int, limit: int, max_memo_nodes: int) -> dict[str, Any]:
    if stride <= 0 or limit <= 0:
        raise ValueError("stride and limit must be positive")
    outcome = Counter()
    by_structure = Counter()
    examples: dict[str, dict[str, Any]] = {}
    max_nodes = 0
    total_nodes = 0
    reference_solvable = Counter()
    selected = 0
    visited = 0
    for index, bundle in enumerate(iter_world_bundles()):
        if index % stride:
            continue
        visited += 1
        physical = hindsight_bundle_reference(bundle)
        if not physical["all_worlds_solvable"]:
            continue
        process = attach_causal_evidence(bundle)
        full_current = solve_observation_matched(
            bundle,
            process,
            disable_paid_query=True,
            force_full_current_state=True,
            max_memo_nodes=max_memo_nodes,
        )
        exact = solve_observation_matched(
            bundle, process, disable_paid_query=False, max_memo_nodes=max_memo_nodes
        )
        no_query = solve_observation_matched(
            bundle, process, disable_paid_query=True, max_memo_nodes=max_memo_nodes
        )
        for name, ref in (
            ("FULL_CURRENT_STATE", full_current),
            ("OBSERVATION_MATCHED_EXACT", exact),
            ("OBSERVATION_MATCHED_NO_PAID_QUERY", no_query),
        ):
            if ref["status"] == "EXACT" and ref["solvable"]:
                reference_solvable[name] += 1
        if (
            full_current["status"] == "SEARCH_LIMIT"
            or exact["status"] == "SEARCH_LIMIT"
            or no_query["status"] == "SEARCH_LIMIT"
        ):
            cls = "SEARCH_LIMIT"
        elif not full_current["solvable"]:
            cls = "FULL_CURRENT_STATE_INFEASIBLE"
        elif exact["solvable"] and not no_query["solvable"]:
            cls = "PAID_EVIDENCE_REQUIRED"
        elif exact["solvable"] and no_query["solvable"]:
            cls = "NO_PAID_QUERY_REQUIRED"
        elif not exact["solvable"]:
            cls = "INFORMATION_INFEASIBLE"
        else:
            raise AssertionError((exact, no_query))
        if exact["status"] == "EXACT" and exact["solvable"]:
            assert full_current["status"] == "EXACT" and full_current["solvable"], (
                "more current information cannot reduce causal feasibility",
                bundle["recipe_id"],
            )
        if no_query["status"] == "EXACT" and no_query["solvable"]:
            assert exact["status"] == "EXACT" and exact["solvable"], (
                "enabling paid query cannot remove a no-query success policy",
                bundle["recipe_id"],
            )
        outcome[cls] += 1
        structural = (
            str(bundle["public_environment"]["terrestrial_process_class"]),
            str(bundle["observation_projection"]["evidence_regime"]),
            cls,
        )
        by_structure[structural] += 1
        node_cost = max(
            int(full_current["memo_nodes"]),
            int(exact["memo_nodes"]),
            int(no_query["memo_nodes"]),
        )
        max_nodes = max(max_nodes, node_cost)
        total_nodes += node_cost
        examples.setdefault(
            cls,
            {
                "recipe_id": bundle["recipe_id"],
                "task_case_id": bundle["task_case_id"],
                "geometry_signature_id": bundle["public_environment"]["geometry_signature_id"],
                "service_process": structural[0],
                "evidence_regime": structural[1],
                "pre_oracle_disposition": bundle["pre_oracle_disposition"],
                "alias_world_count": len(bundle["worlds"]),
                "full_current_memo_nodes": full_current["memo_nodes"],
                "exact_memo_nodes": exact["memo_nodes"],
                "no_query_memo_nodes": no_query["memo_nodes"],
            },
        )
        selected += 1
        if selected >= limit:
            break
    return {
        "selection": {
            "rule": "frozen generator order, index % stride == 0, retain only ALL_WORLD_SOLVABLE before causal search",
            "stride": stride,
            "requested_limit": limit,
            "visited_stride_rows": visited,
            "selected_all_world_solvable": selected,
            "use": "construction diagnostic only; not a benchmark split or admission filter",
        },
        "outcome": dict(sorted(outcome.items())),
        "reference_solvable": dict(sorted(reference_solvable.items())),
        "by_structure": {
            f"{a}|{b}|{c}": v for (a, b, c), v in sorted(by_structure.items())
        },
        "examples": examples,
        "search": {
            "max_memo_nodes_limit": max_memo_nodes,
            "observed_max_memo_nodes": max_nodes,
            "mean_max_memo_nodes": (total_nodes / selected) if selected else 0.0,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stride", type=int, default=53)
    ap.add_argument("--limit", type=int, default=256)
    ap.add_argument("--max-memo-nodes", type=int, default=50_000)
    ap.add_argument("--physical-full", action="store_true")
    ap.add_argument("--stratified-validity", action="store_true")
    args = ap.parse_args()
    out: dict[str, Any] = {
        "schema_version": "0.1",
        "status": "PRE_ADMISSION_ORACLE_AUDIT",
        "observation_pilot": observation_pilot(
            stride=args.stride,
            limit=args.limit,
            max_memo_nodes=args.max_memo_nodes,
        ),
    }
    if args.physical_full:
        out["physical_full_scan"] = physical_full_scan()
    if args.stratified_validity:
        out["stratified_validity_pilot"] = stratified_validity_pilot(
            max_memo_nodes=args.max_memo_nodes
        )
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
