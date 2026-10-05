#!/usr/bin/env python3
"""Regression guards for the Layer-1 recipe -> dynamic-world stage."""
from __future__ import annotations

from itertools import islice

from compositional_recipe_generator_v0_1 import core_recipes
from dynamic_world_materializer_v0_1 import (
    materialize_recipe,
)


def main() -> int:
    samples = {}
    recovery_sample = None
    for recipe in core_recipes():
        samples.setdefault((recipe.service_process_class, recipe.evidence_regime), recipe)
        if (
            recipe.recovery_regime == "RECONNECT_RECONCILE_OBJECTIVE_CHECK"
            and recipe.blockers
            and recovery_sample is None
        ):
            recovery_sample = recipe
        if len(samples) == 16 and recovery_sample is not None:
            break

    assert len(samples) == 16
    assert recovery_sample is not None
    for (service, evidence), recipe in samples.items():
        bundle = materialize_recipe(recipe)
        assert bundle["recipe_id"] == recipe.recipe_id
        assert bundle["release_status"] == "NOT_BENCHMARK_ADMIT"
        assert bundle["next_stage"] == "CAUSAL_OBSERVATION_EVIDENCE_PROCESS"
        assert bundle["public_environment"]["geometry_trace_id"] == "CONNECTA_20260922_SIHUI_GEOMETRY_48H"
        assert all(
            o["deadline_s"] - o["release_s"] == recipe.report_interval_s
            for o in bundle["obligations"]
        )
        assert len(bundle["obligations"]) == recipe.overlap_count
        assert not any(
            "satellite" in field.lower()
            for field in bundle["observation_projection"]["hidden_fields"]
        )
        if evidence == "FULL_OBSERVATION_CONTROL":
            assert bundle["observation_projection"]["hidden_fields"] == []
        else:
            assert bundle["observation_projection"]["causal_evidence_status"] == "PENDING_NEXT_STAGE"
        if service in {"FINITE_CROSSING_WINDOWS", "MULTI_WINDOW_DYNAMIC", "MONOTONE_RECOVERY_NEGATIVE"} and len(bundle["worlds"]) > 1:
            signatures = {
                tuple((w["start_s"], w["end_s"], w["window_id"]) for w in world["terrestrial_windows"])
                for world in bundle["worlds"]
            }
            assert len(signatures) > 1, (service, evidence)

    rb = materialize_recipe(recovery_sample)
    assert rb["recovery"]["unresolved_field"] == "reconnect_backlog_priority"
    assert rb["recovery"]["reconnect_objective_status"] == "UNRESOLVED_IF_SACRIFICE_REQUIRED"
    assert rb["blockers"], "materializer must preserve the recipe's V7 source blocker"

    # A deterministic prefix check catches accidental IDs/seeds in world construction.
    prefix = list(islice(core_recipes(), 8))
    first = [materialize_recipe(x)["bundle_id"] for x in prefix]
    second = [materialize_recipe(x)["bundle_id"] for x in prefix]
    assert first == second and len(set(first)) == len(first)

    # Evidence regime changes observation capability, never physical future
    # support.  Compare one complete 4-regime cell with all other coordinates
    # fixed and require identical terrestrial schedules.
    grouped = {}
    for recipe in core_recipes():
        key = (
            recipe.task_case_id,
            recipe.geometry_signature_id,
            recipe.service_process_class,
            recipe.overlap_count,
            recipe.resource_headroom,
            recipe.recovery_regime,
        )
        grouped.setdefault(key, {})[recipe.evidence_regime] = recipe
        if len(grouped[key]) == 4:
            rows = [materialize_recipe(r) for r in grouped[key].values()]
            signatures = [
                [
                    [(w["start_s"], w["end_s"], w["capacity_units"]) for w in world["terrestrial_windows"]]
                    for world in b["worlds"]
                ]
                for b in rows
            ]
            assert all(x == signatures[0] for x in signatures[1:])
            break
    else:
        raise AssertionError("no complete evidence-regime comparison cell")

    print(
        "PASS dynamic world materialization semantics: public geometry, alias state, "
        "source deadlines and V7 blockers remain separated; evidence regime does not change physics"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
