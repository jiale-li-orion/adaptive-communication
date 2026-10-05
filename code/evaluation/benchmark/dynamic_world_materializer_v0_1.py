#!/usr/bin/env python3
"""Materialize T1 candidate recipes into dynamic world / alias bundles.

This is the stage immediately after ``compositional_recipe_generator_v0_1``.
It deliberately stops before causal evidence responses, exact oracle labels and
V0-V9 admission.  A materialized bundle is therefore an executable *world IR*,
not a benchmark case.

The materializer keeps three boundaries explicit:

* DB44 owns reporting cadence and the warning-state workload contract.
* Connecta geometry is public MODEL_DERIVED_TRACE opportunity; it is never a
  hidden answer bit.
* Terrestrial service variation / workload density / resource headroom are
  declared CONTROLLED_STRESS coordinates.  Alias worlds may differ there, but
  all worlds in a partial-observation bundle share the same initial public
  observation.  The next stage will define causal ACK/query/probe processes.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Mapping
import argparse
import json

from compositional_recipe_generator_v0_1 import (
    CandidateRecipe,
    _db44_resolved_cases,
    core_recipes,
    geometry_signatures,
)


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TRACE = ROOT / "research/benchmark/traces/v0.1/CONNECTA_20260922_SIHUI_GEOMETRY_48H.json"
TRACE_ID = "CONNECTA_20260922_SIHUI_GEOMETRY_48H"
MASK_DEG = 20
TRACE_HORIZON_S = 48 * 3600

WARNING_ORDER = ("none_stable", "blue", "yellow", "orange", "red")


class WorldMaterializationError(ValueError):
    """Raised when a recipe cannot be compiled without crossing its authority boundary."""


@dataclass(frozen=True)
class MaterializedObligation:
    obligation_id: str
    stream_index: int
    protected_subject: str
    release_s: int
    deadline_s: int
    source_interval_s: int
    authority_owner: str
    source_ref_ids: tuple[str, ...]
    workload_provenance: str


@dataclass(frozen=True)
class ServiceWindow:
    window_id: str
    path_class: str
    start_s: int
    end_s: int
    capacity_units: int
    provenance_class: str


def _digest(payload: Any, n: int = 16) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(raw.encode("utf-8")).hexdigest()[:n]


@lru_cache(maxsize=1)
def _case_index() -> dict[str, dict[str, Any]]:
    return {str(x["case_id"]): x for x in _db44_resolved_cases()}


@lru_cache(maxsize=1)
def _geometry_index() -> dict[str, Any]:
    return {g.signature_id: g for g in geometry_signatures()}


def _trace_windows_absolute() -> tuple[tuple[int, int], ...]:
    raw = json.loads(TRACE.read_text(encoding="utf-8"))
    t0 = datetime.fromisoformat(raw["start_utc"])
    rows: list[tuple[int, int]] = []
    for w in raw["thresholds"][str(MASK_DEG)]["windows_utc"]:
        start = int((datetime.fromisoformat(w["start"]) - t0).total_seconds())
        end = int((datetime.fromisoformat(w["end"]) - t0).total_seconds())
        if end > start:
            rows.append((start, end))
    if not rows:
        raise WorldMaterializationError("geometry trace contains no 20-degree windows")
    return tuple(rows)


TRACE_WINDOWS_ABSOLUTE = _trace_windows_absolute()


@lru_cache(maxsize=None)
def _warning_predecessor(grade: int, state: str) -> dict[str, Any] | None:
    """Return a canonical source-valid predecessor for transition metadata.

    The predecessor state is fixed by warning ordering.  When the source cell
    contains a cadence range, the compiler chooses the *minimum interval* as a
    deterministic source-range boundary rule.  This value is metadata for the
    transition contract; current obligations still use the recipe's exact
    source-resolved interval.
    """

    try:
        i = WARNING_ORDER.index(state)
    except ValueError as exc:
        raise WorldMaterializationError(f"unknown DB44 warning state {state!r}") from exc
    if i == 0:
        return None
    prev = WARNING_ORDER[i - 1]
    matches = [
        x
        for x in _case_index().values()
        if int(x["world"].get("monitoring_grade", -1)) == grade
        and str(x["world"].get("warning_state")) == prev
    ]
    if not matches:
        return None
    chosen = min(matches, key=lambda x: int(x["world"]["report_interval_s"]))
    return {
        "warning_state": prev,
        "report_interval_s": int(chosen["world"]["report_interval_s"]),
        "selection_rule": "minimum source-valid predecessor interval; deterministic SOURCE_RANGE boundary",
        "source_ref_ids": ["DB44T2457_2024"],
    }


def _satellite_windows(recipe: CandidateRecipe, horizon_s: int) -> tuple[ServiceWindow, ...]:
    abs_start = int(recipe.geometry_start_s)
    abs_end = min(TRACE_HORIZON_S, abs_start + horizon_s)
    out: list[ServiceWindow] = []
    for j, (start, end) in enumerate(TRACE_WINDOWS_ABSOLUTE):
        if end <= abs_start or start >= abs_end:
            continue
        rel_start = max(start, abs_start) - abs_start
        rel_end = min(end, abs_end) - abs_start
        if rel_end <= rel_start:
            continue
        out.append(
            ServiceWindow(
                window_id=f"sat-{j:03d}",
                path_class="SATELLITE_FALLBACK",
                start_s=rel_start,
                end_s=rel_end,
                capacity_units=1,
                provenance_class="MODEL_DERIVED_TRACE",
            )
        )
    return tuple(out)


def _obligation_timeline(
    recipe: CandidateRecipe,
    base_case: Mapping[str, Any],
    first_satellite_start_s: int | None,
) -> tuple[tuple[MaterializedObligation, ...], int, dict[str, Any]]:
    interval = int(recipe.report_interval_s)
    if interval <= 0:
        raise WorldMaterializationError("report interval must be positive")

    # Workload density is a declared stress coordinate.  Releases are spaced by
    # half a source interval, so k=2/3/4 really creates overlapping obligations
    # without changing any obligation's source-owned deadline.
    release_gap = max(1, interval // 2)
    # Geometry is public.  A deterministic phase rule places the first release
    # close enough to the first visible satellite opportunity for the fallback
    # resource to be testable, without hiding or modifying that opportunity.
    if first_satellite_start_s is None:
        base_release = 0
    else:
        lead = max(1, min(interval // 3, 1800))
        base_release = max(0, first_satellite_start_s - lead)

    templates = base_case.get("obligations", [])
    if not templates:
        raise WorldMaterializationError(f"{recipe.task_case_id} has no obligation template")
    template = templates[0]
    refs = tuple(map(str, template.get("source_ref_ids", [])))
    obligations: list[MaterializedObligation] = []
    for i in range(int(recipe.overlap_count)):
        release = base_release + i * release_gap
        deadline = release + interval
        obligations.append(
            MaterializedObligation(
                obligation_id=f"{recipe.recipe_id}::report::{i:02d}",
                stream_index=i,
                protected_subject=str(template["protected_subject"]),
                release_s=release,
                deadline_s=deadline,
                source_interval_s=interval,
                authority_owner=str(template["authority_owner"]),
                source_ref_ids=refs,
                workload_provenance="CONTROLLED_STRESS_OVERLAP_COUNT_WITH_SOURCE_FIXED_DEADLINE",
            )
        )
    horizon_s = obligations[-1].deadline_s
    max_available = TRACE_HORIZON_S - int(recipe.geometry_start_s)
    if horizon_s > max_available:
        # This should not occur for the frozen 17 core contracts / k<=4, but it
        # is a hard compiler error rather than silent trace wrapping.
        raise WorldMaterializationError(
            f"recipe {recipe.recipe_id} needs {horizon_s}s after geometry start, "
            f"trace only has {max_available}s"
        )
    transition = {
        "at_s": base_release,
        "from": _warning_predecessor(int(recipe.monitoring_grade), str(recipe.warning_state)),
        "to": {
            "warning_state": str(recipe.warning_state),
            "report_interval_s": interval,
            "source_ref_ids": ["DB44T2457_2024"],
        },
        "timing_provenance": "CONTROLLED_STRESS",
        "semantic_rule": "warning-state value and reporting interval are source-resolved; transition placement is controlled stress",
    }
    return tuple(obligations), horizon_s, transition


def _physical_world_count(recipe: CandidateRecipe) -> int:
    """Number of declared future service realizations.

    Physical support must not depend on what the policy is allowed to observe.
    Otherwise evidence regimes would change the task distribution itself and a
    full-current-state reference would collapse into clairvoyance.  The steady
    control has one realization; dynamic service processes use the frozen
    overlap coordinate as a bounded support-size stress axis.
    """

    if recipe.service_process_class == "STEADY_AVAILABLE_CONTROL":
        return 1
    return int(recipe.overlap_count)


def _window_width(interval_s: int) -> int:
    return max(30, min(600, interval_s // 4))


def _bounded_window(
    *,
    oid: str,
    suffix: str,
    center_s: int,
    width_s: int,
    release_s: int,
    deadline_s: int,
) -> ServiceWindow:
    half = max(1, width_s // 2)
    start = max(release_s, center_s - half)
    end = min(deadline_s, center_s + half)
    if end <= start:
        end = min(deadline_s, start + 1)
    if end <= start:
        raise WorldMaterializationError(f"cannot place service window inside {oid}")
    return ServiceWindow(
        window_id=f"terr-{oid.rsplit('::', 1)[-1]}-{suffix}",
        path_class="TERRESTRIAL_HIGHER_PRIORITY_AGGREGATE",
        start_s=start,
        end_s=end,
        capacity_units=1,
        provenance_class="CONTROLLED_STRESS",
    )


def _finite_windows(obligations: tuple[MaterializedObligation, ...], mode: int, n_worlds: int) -> tuple[ServiceWindow, ...]:
    rows: list[ServiceWindow] = []
    for i, o in enumerate(obligations):
        # One finite rescue opportunity per obligation; one mode-dependent
        # opportunity is absent, forcing the oracle to consider fallback.
        if i % n_worlds == mode:
            continue
        center = o.release_s + (2 * o.source_interval_s) // 3
        rows.append(
            _bounded_window(
                oid=o.obligation_id,
                suffix="finite",
                center_s=center,
                width_s=_window_width(o.source_interval_s),
                release_s=o.release_s,
                deadline_s=o.deadline_s,
            )
        )
    return tuple(rows)


def _multi_windows(obligations: tuple[MaterializedObligation, ...], mode: int, n_worlds: int) -> tuple[ServiceWindow, ...]:
    rows: list[ServiceWindow] = []
    for i, o in enumerate(obligations):
        width = _window_width(o.source_interval_s)
        early = _bounded_window(
            oid=o.obligation_id,
            suffix="early",
            center_s=o.release_s + o.source_interval_s // 3,
            width_s=width,
            release_s=o.release_s,
            deadline_s=o.deadline_s,
        )
        late = _bounded_window(
            oid=o.obligation_id,
            suffix="late",
            center_s=o.release_s + (2 * o.source_interval_s) // 3,
            width_s=width,
            release_s=o.release_s,
            deadline_s=o.deadline_s,
        )
        # Non-nested mode differences: one stream loses late service, the next
        # loses early service.  Other streams keep both opportunities.
        if i % n_worlds == mode:
            rows.append(early)
        elif i % n_worlds == (mode + 1) % n_worlds:
            rows.append(late)
        else:
            rows.extend((early, late))
    return tuple(rows)


def _terrestrial_windows(
    recipe: CandidateRecipe,
    obligations: tuple[MaterializedObligation, ...],
    horizon_s: int,
    *,
    mode: int,
    n_worlds: int,
) -> tuple[ServiceWindow, ...]:
    service = recipe.service_process_class
    if service == "STEADY_AVAILABLE_CONTROL":
        return (
            ServiceWindow(
                window_id="terr-steady",
                path_class="TERRESTRIAL_HIGHER_PRIORITY_AGGREGATE",
                start_s=0,
                end_s=max(1, horizon_s),
                capacity_units=max(1, len(obligations)),
                provenance_class="CONTROLLED_STRESS",
            ),
        )
    if service == "MONOTONE_RECOVERY_NEGATIVE":
        recovery = max(0, ((mode + 1) * horizon_s) // (n_worlds + 1))
        return (
            ServiceWindow(
                window_id=f"terr-recovery-m{mode}",
                path_class="TERRESTRIAL_HIGHER_PRIORITY_AGGREGATE",
                start_s=recovery,
                end_s=max(recovery + 1, horizon_s),
                capacity_units=max(1, len(obligations)),
                provenance_class="CONTROLLED_STRESS",
            ),
        )
    if service == "FINITE_CROSSING_WINDOWS":
        return _finite_windows(obligations, mode, n_worlds)
    if service == "MULTI_WINDOW_DYNAMIC":
        return _multi_windows(obligations, mode, n_worlds)
    raise WorldMaterializationError(f"unknown service process {service!r}")


def _recovery_contract(recipe: CandidateRecipe) -> dict[str, Any]:
    regime = recipe.recovery_regime
    if regime == "NO_RECOVERY_STATE":
        return {"regime": regime, "enabled": False}
    base = {
        "regime": regime,
        "enabled": True,
        "local_cache_min_days": 7,
        "cache_provenance": "FIXED_BY_SOURCE",
        "source_ref_ids": ["DZT0450_2023"],
    }
    if regime == "OUTAGE_CACHE_RETAIN":
        return {**base, "reconnect_objective_status": "NOT_REQUIRED_FOR_RETENTION_ONLY"}
    if regime == "RECONNECT_RECONCILE_OBJECTIVE_CHECK":
        return {
            **base,
            "reconnect_objective_status": "UNRESOLVED_IF_SACRIFICE_REQUIRED",
            "unresolved_field": "reconnect_backlog_priority",
            "rule": "preserve blocker; V7 must reject any world that needs invented backlog-vs-fresh sacrifice priority",
        }
    raise WorldMaterializationError(f"unknown recovery regime {regime!r}")


def _evidence_surface_skeleton(recipe: CandidateRecipe) -> list[dict[str, Any]]:
    regime = recipe.evidence_regime
    if regime == "FULL_OBSERVATION_CONTROL":
        return []
    passive = {
        "evidence_id": "delivery_ack",
        "kind": "PASSIVE_ACK",
        "owner": "communication_subsystem",
        "causal_response": "PENDING_NEXT_STAGE",
    }
    query = {
        "evidence_id": "gateway_state_summary",
        "kind": "OWNER_QUERY",
        "owner": "monitoring_center",
        "source_capability": "remote_state_read",
        "causal_response": "PENDING_NEXT_STAGE",
    }
    probe = {
        "evidence_id": "normal_send_probe",
        "kind": "NORMAL_SEND_AS_PROBE",
        "owner": "communication_subsystem",
        "causal_response": "PENDING_NEXT_STAGE",
    }
    if regime == "PASSIVE_ACK_ONLY":
        return [passive]
    if regime == "GATEWAY_SUMMARY_QUERY":
        return [query]
    if regime == "MIXED_PASSIVE_QUERY_PROBE":
        return [passive, query, probe]
    raise WorldMaterializationError(f"unknown evidence regime {regime!r}")


def materialize_recipe(recipe: CandidateRecipe) -> dict[str, Any]:
    cases = _case_index()
    geoms = _geometry_index()
    if recipe.task_case_id not in cases:
        raise WorldMaterializationError(f"unknown task case {recipe.task_case_id}")
    if recipe.geometry_signature_id not in geoms:
        raise WorldMaterializationError(f"unknown geometry signature {recipe.geometry_signature_id}")
    base_case = cases[recipe.task_case_id]
    geometry = geoms[recipe.geometry_signature_id]

    # First determine a conservative horizon/phase from the public geometry.
    first_signature_slot = min(geometry.relative_slots_s) if geometry.relative_slots_s else None
    obligations, horizon_s, warning_transition = _obligation_timeline(
        recipe, base_case, first_signature_slot
    )
    satellites = _satellite_windows(recipe, horizon_s)
    n_worlds = _physical_world_count(recipe)
    satellite_budget = int(recipe.variable_provenance["satellite_budget"]["value"])
    recovery = _recovery_contract(recipe)

    worlds: list[dict[str, Any]] = []
    for mode in range(n_worlds):
        terrestrial = _terrestrial_windows(
            recipe,
            obligations,
            horizon_s,
            mode=mode,
            n_worlds=n_worlds,
        )
        latent = {
            "terrestrial_mode": f"M{mode}",
            "delivery_receipt_state": "UNMATERIALIZED_CAUSAL_PROCESS",
            "recovery_backlog_state": (
                "UNRESOLVED_IF_RECONNECT_CONFLICT"
                if recipe.recovery_regime == "RECONNECT_RECONCILE_OBJECTIVE_CHECK"
                else "NO_UNRESOLVED_PRIORITY"
            ),
        }
        world_payload = {
            "recipe_id": recipe.recipe_id,
            "mode": mode,
            "terrestrial_windows": [asdict(x) for x in terrestrial],
            "latent_state": latent,
        }
        worlds.append(
            {
                "world_id": f"{recipe.recipe_id}::W{mode}-{_digest(world_payload, 10)}",
                "latent_state": latent,
                "terrestrial_windows": [asdict(x) for x in terrestrial],
                # Satellite geometry is repeated here only as a reference.  The
                # canonical public copy lives at bundle level and is identical
                # for every alias world.
                "public_satellite_window_ref": "bundle.public_environment.satellite_windows",
            }
        )

    public_environment = {
        "geometry_signature_id": recipe.geometry_signature_id,
        "geometry_trace_id": TRACE_ID,
        "geometry_mask_deg": MASK_DEG,
        "geometry_start_s": int(recipe.geometry_start_s),
        "horizon_s": horizon_s,
        "warning_transition": warning_transition,
        "satellite_windows": [asdict(x) for x in satellites],
        "satellite_budget_units": satellite_budget,
        "satellite_budget_provenance": dict(recipe.variable_provenance["satellite_budget"]),
        "terrestrial_process_class": recipe.service_process_class,
        "terrestrial_process_provenance": dict(recipe.variable_provenance["service_process_class"]),
        "path_priority_rule": {
            "ordering": ["NB", "4G/5G", "BeiDou"],
            "source_ref_ids": ["JIAOZUO_2024"],
            "note": "world IR aggregates the higher-priority terrestrial paths; this does not grant center per-slot override authority",
        },
    }

    hidden_fields: list[str] = []
    projection = "FULL_CURRENT_STATE"
    if recipe.evidence_regime != "FULL_OBSERVATION_CONTROL":
        hidden_fields = [
            "world.terrestrial_windows",
            "world.latent_state.delivery_receipt_state",
        ]
        if recipe.recovery_regime == "RECONNECT_RECONCILE_OBJECTIVE_CHECK":
            hidden_fields.append("world.latent_state.recovery_backlog_state")
        projection = "CAPABILITY_DEPENDENT"

    bundle_payload = {
        "recipe_id": recipe.recipe_id,
        "world_ids": [w["world_id"] for w in worlds],
        "horizon_s": horizon_s,
        "warning_state": recipe.warning_state,
        "evidence_regime": recipe.evidence_regime,
    }
    bundle = {
        "schema_version": "0.1",
        "bundle_id": f"T1B-{_digest(bundle_payload, 16)}",
        "materializer": "T1-dynamic-world-alias-bundle-v0.1",
        "stage": "WORLD_BUNDLE_PRE_EVIDENCE_PRE_ORACLE",
        "recipe_id": recipe.recipe_id,
        "family": recipe.family,
        "task_case_id": recipe.task_case_id,
        "task_surface_ids": list(recipe.task_surface_ids),
        "source_profiles": list(recipe.source_profiles),
        "hardness_candidates": list(recipe.hardness),
        "pre_oracle_disposition": recipe.pre_oracle_disposition,
        "blockers": list(recipe.blockers),
        "public_environment": public_environment,
        "obligations": [asdict(x) for x in obligations],
        "recovery": recovery,
        "observation_projection": {
            "evidence_regime": recipe.evidence_regime,
            "projection_provenance": projection,
            "initial_public_observation_hash": _digest(
                {
                    "environment": public_environment,
                    "obligations": [asdict(x) for x in obligations],
                    "recovery": recovery,
                }
            ),
            "hidden_fields": hidden_fields,
            "alias_world_ids": [w["world_id"] for w in worlds],
            "evidence_surfaces": _evidence_surface_skeleton(recipe),
            "causal_evidence_status": "PENDING_NEXT_STAGE",
        },
        "worlds": worlds,
        "provenance": {
            "recipe_variable_provenance": recipe.variable_provenance,
            "workload_density": {
                "class": "CONTROLLED_STRESS",
                "value": int(recipe.overlap_count),
                "rule": "parallel recurring-report streams; each stream keeps the source-resolved report deadline",
            },
            "geometry": {
                "class": "MODEL_DERIVED_TRACE",
                "trace_ref": TRACE_ID,
                "public": True,
            },
        },
        "release_status": "NOT_BENCHMARK_ADMIT",
        "next_stage": "CAUSAL_OBSERVATION_EVIDENCE_PROCESS",
    }
    validate_world_bundle(bundle)
    return bundle


def validate_world_bundle(bundle: Mapping[str, Any]) -> None:
    if bundle.get("stage") != "WORLD_BUNDLE_PRE_EVIDENCE_PRE_ORACLE":
        raise WorldMaterializationError("world bundle has wrong stage")
    if bundle.get("release_status") != "NOT_BENCHMARK_ADMIT":
        raise WorldMaterializationError("materialized world must not claim benchmark admission")
    obligations = bundle.get("obligations")
    worlds = bundle.get("worlds")
    if not isinstance(obligations, list) or len(obligations) < 2:
        raise WorldMaterializationError("bundle requires overlapping obligations")
    if not isinstance(worlds, list) or not worlds:
        raise WorldMaterializationError("bundle requires at least one physical world")
    for o in obligations:
        if int(o["deadline_s"]) - int(o["release_s"]) != int(o["source_interval_s"]):
            raise WorldMaterializationError("materializer changed a source-owned reporting deadline")
    env = bundle["public_environment"]
    if env["geometry_trace_id"] != TRACE_ID:
        raise WorldMaterializationError("bundle geometry trace drift")
    obs = bundle["observation_projection"]
    world_ids = [str(w["world_id"]) for w in worlds]
    if list(obs["alias_world_ids"]) != world_ids:
        raise WorldMaterializationError("alias world ids disagree with physical worlds")
    if env.get("satellite_windows") is None:
        raise WorldMaterializationError("public satellite geometry missing")
    if any("satellite" in str(x).lower() for x in obs.get("hidden_fields", [])):
        raise WorldMaterializationError("public satellite geometry must never be hidden")
    if obs["evidence_regime"] == "FULL_OBSERVATION_CONTROL":
        if obs["hidden_fields"]:
            raise WorldMaterializationError("full-current-state control may not hide current fields")
    elif not obs["hidden_fields"]:
        raise WorldMaterializationError("partial-observation bundle must declare hidden current fields")


def iter_world_bundles(recipes: Iterable[CandidateRecipe] | None = None) -> Iterable[dict[str, Any]]:
    source = core_recipes() if recipes is None else recipes
    for recipe in source:
        yield materialize_recipe(recipe)


def materialization_manifest() -> dict[str, Any]:
    by_world_count: Counter[int] = Counter()
    by_evidence: Counter[str] = Counter()
    by_service: Counter[str] = Counter()
    by_recovery: Counter[str] = Counter()
    blocker_count = 0
    count = 0
    digest = sha256()
    for bundle in iter_world_bundles():
        count += 1
        n_worlds = len(bundle["worlds"])
        by_world_count[n_worlds] += 1
        by_evidence[str(bundle["observation_projection"]["evidence_regime"])] += 1
        by_service[str(bundle["public_environment"]["terrestrial_process_class"])] += 1
        by_recovery[str(bundle["recovery"]["regime"])] += 1
        blocker_count += int(bool(bundle["blockers"]))
        digest.update(str(bundle["bundle_id"]).encode("ascii"))
        digest.update(b"\n")
    return {
        "schema_version": "0.1",
        "materializer": "T1-dynamic-world-alias-bundle-v0.1",
        "stage": "WORLD_BUNDLE_PRE_EVIDENCE_PRE_ORACLE",
        "input_recipe_count": count,
        "bundle_count": count,
        "bundle_id_stream_sha256": digest.hexdigest(),
        "by_alias_world_count": {str(k): v for k, v in sorted(by_world_count.items())},
        "by_evidence_regime": dict(sorted(by_evidence.items())),
        "by_service_process": dict(sorted(by_service.items())),
        "by_recovery_regime": dict(sorted(by_recovery.items())),
        "bundles_with_preserved_source_blocker": blocker_count,
        "rules": [
            "One frozen candidate recipe materializes to one world/alias bundle.",
            "Materialized bundles are still NOT_BENCHMARK_ADMIT and have no oracle/V0-V9 labels.",
            "MODEL_DERIVED satellite geometry is public and identical across alias worlds.",
            "Alias differences live in declared dynamic terrestrial/recovery state, never in hidden public geometry.",
            "Workload overlap and service-process variation remain explicit CONTROLLED_STRESS coordinates.",
            "Reconnect backlog-vs-fresh priority remains unresolved; materialization preserves the V7 blocker.",
            "ACK/query/probe response values and arrival timing are deferred to the causal evidence stage.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit-jsonl", type=Path)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    if args.emit_jsonl is None:
        print(json.dumps(materialization_manifest(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    args.emit_jsonl.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with args.emit_jsonl.open("w", encoding="utf-8") as f:
        for bundle in iter_world_bundles():
            if args.limit is not None and n >= args.limit:
                break
            f.write(json.dumps(bundle, ensure_ascii=False, sort_keys=True) + "\n")
            n += 1
    print(f"materialized {n} world bundles -> {args.emit_jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
