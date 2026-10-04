#!/usr/bin/env python3
"""Deterministic computation-gap audit for evidence subset selection."""
from __future__ import annotations

from collections import defaultdict
from typing import Any
import json

from multi_evidence_conflict_planner import (
    conflict_guided_query_search,
    exhaustive_query_search,
)
from scenario_generator_v0_3 import build_bundle, _phase_groups


def run_scaling(
    *,
    phase_limit: int = 6,
    catalog_sizes: tuple[int, ...] = (3, 5, 7, 9),
) -> dict[str, Any]:
    rows = []
    phases = _phase_groups(phase_limit)
    for catalog_size in catalog_sizes:
        for phase_index, (start, sat_slots) in enumerate(phases):
            bundle = build_bundle(
                phase_index=phase_index,
                start_s=start,
                satellite_slots=sat_slots,
                alias_modes=(0, 1, 2),
                evidence_profile="BOTH",
                catalog_size=catalog_size,
            )
            exhaustive, exd = exhaustive_query_search(bundle)
            guided, gd = conflict_guided_query_search(bundle)
            if exhaustive.mode != guided.mode:
                raise AssertionError((exhaustive, guided))
            if set(exhaustive.selected_query_ids) != set(guided.selected_query_ids):
                raise AssertionError((exhaustive, guided))
            rows.append(
                {
                    "catalog_size": catalog_size,
                    "phase_index": phase_index,
                    "selected": list(guided.selected_query_ids),
                    "exhaustive_subset_solves": exd.subset_solves,
                    "guided_subset_solves": gd.subset_solves,
                    "guided_preprocessing_solves": gd.preprocessing_solves,
                    "guided_structural_flow_solves": gd.structural_flow_solves,
                    "exhaustive_total_memo_nodes": exd.total_memo_nodes,
                    "guided_total_memo_nodes": gd.total_memo_nodes,
                    "constant_pruned": len(gd.constant_pruned),
                    "dominated_pruned": len(gd.dominated_pruned),
                }
            )

    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[int(row["catalog_size"])].append(row)

    summary = {}
    for size, group in sorted(grouped.items()):
        def avg(key: str) -> float:
            return sum(float(x[key]) for x in group) / len(group)

        summary[str(size)] = {
            "cases": len(group),
            "mean_exhaustive_subset_solves": avg("exhaustive_subset_solves"),
            "mean_guided_subset_solves": avg("guided_subset_solves"),
            "mean_guided_preprocessing_solves": avg("guided_preprocessing_solves"),
            "mean_guided_structural_flow_solves": avg("guided_structural_flow_solves"),
            "mean_exhaustive_total_memo_nodes": avg("exhaustive_total_memo_nodes"),
            "mean_guided_total_memo_nodes": avg("guided_total_memo_nodes"),
            "mean_constant_pruned": avg("constant_pruned"),
            "memo_node_ratio_guided_over_exhaustive": (
                avg("guided_total_memo_nodes") / avg("exhaustive_total_memo_nodes")
            ),
        }
    return {"rows": rows, "summary": summary}


if __name__ == "__main__":
    print(json.dumps(run_scaling()["summary"], indent=2, sort_keys=True))
