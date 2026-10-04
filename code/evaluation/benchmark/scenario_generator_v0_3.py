#!/usr/bin/env python3
"""Process-generated multi-evidence Layer-1 bundles.

Unlike v0.2, this generator does not emit QUERY_REQUIRED/HARMFUL labels.
It samples a latent current service mode, source-shaped periodic obligations,
actual Connecta opportunity phases, and owner-evidence projections. Exact
solvers label information structure after generation.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable
import json

from multi_evidence_conflict_planner import exhaustive_query_search
from multi_evidence_scenario_tree import Bundle, EvidenceQuery, Obligation, World, solve

ROOT = Path(__file__).resolve().parents[3]
TRACE = ROOT / "research/benchmark/traces/v0.1/CONNECTA_20260922_SIHUI_GEOMETRY_48H.json"

CADENCE_S = 2 * 3600  # DB44 grade-3 orange lower source boundary.
MASK_DEG = 20

ALIAS_MODE_SETS: tuple[tuple[int, ...], ...] = (
    (0, 0),      # physically equivalent aliases: no paid evidence required
    (0, 1),      # primary_health can distinguish
    (1, 2),      # receipt_summary can distinguish
    (0, 1, 2),   # complementary evidence required when both projections live
)
EVIDENCE_PROFILES = ("BOTH", "PRIMARY_ONLY", "RECEIPT_ONLY", "NONE")


@dataclass(frozen=True)
class GeneratedBundle:
    bundle: Bundle
    coordinates: dict[str, Any]
    outcome_class: str
    selected_query_ids: tuple[str, ...]
    no_query_solvable: bool
    exact_solvable: bool


def _hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return sha256(raw).hexdigest()[:16]


def _satellite_starts(mask: int = MASK_DEG) -> list[int]:
    trace = json.loads(TRACE.read_text())
    t0 = datetime.fromisoformat(trace["start_utc"])
    return [
        int((datetime.fromisoformat(w["start"]) - t0).total_seconds())
        for w in trace["thresholds"][str(mask)]["windows_utc"]
    ]


def _phase_groups(limit: int = 8) -> list[tuple[int, tuple[int, int, int]]]:
    slots = _satellite_starts()
    groups: list[tuple[int, tuple[int, int, int]]] = []
    horizon = 48 * 3600
    for start in range(0, horizon - 3 * CADENCE_S + 1, 1800):
        selected: list[int] = []
        for i in range(3):
            lo = start + i * CADENCE_S
            hi = lo + CADENCE_S
            candidates = [s for s in slots if lo + 120 <= s < hi - 120]
            if not candidates:
                selected = []
                break
            selected.append(candidates[0])
        if len(selected) == 3:
            groups.append((start, (selected[0], selected[1], selected[2])))
            if len(groups) >= limit:
                break
    return groups


def _queries(catalog_size: int) -> tuple[EvidenceQuery, ...]:
    if catalog_size < 3:
        raise ValueError("catalog_size must be >= 3")
    rows = [
        EvidenceQuery(
            "primary_health",
            "communication.gateway.primary_health",
            "gateway",
            40,
        ),
        EvidenceQuery(
            "receipt_summary",
            "communication.gateway.receipt_summary",
            "gateway",
            20,
        ),
        EvidenceQuery(
            "node_report:n0",
            "communication.gateway.node_report",
            "gateway",
            60,
        ),
    ]
    # Extra entries are legitimate resource-specific node_report requests but
    # intentionally irrelevant for this generated conflict. They stress catalog
    # scaling without inventing new capability types.
    for i in range(1, catalog_size - 2):
        rows.append(
            EvidenceQuery(
                f"node_report:n{i}",
                "communication.gateway.node_report",
                "gateway",
                60 + 10 * i,
            )
        )
    return tuple(rows[:catalog_size])


def _mode_evidence(
    mode: int,
    *,
    profile: str,
    queries: tuple[EvidenceQuery, ...],
) -> tuple[tuple[str, str], ...]:
    primary_live = profile in {"BOTH", "PRIMARY_ONLY"}
    receipt_live = profile in {"BOTH", "RECEIPT_ONLY"}
    values: dict[str, str] = {
        "primary_health": (
            ("early-path-unavailable" if mode == 0 else "early-path-available")
            if primary_live
            else "same"
        ),
        "receipt_summary": (
            ("r2-needs-sat" if mode == 2 else "r2-not-indicated")
            if receipt_live
            else "same"
        ),
    }
    for q in queries:
        if q.query_id.startswith("node_report:"):
            values[q.query_id] = "same"
    return tuple((q.query_id, values[q.query_id]) for q in queries)


def build_bundle(
    *,
    phase_index: int,
    start_s: int,
    satellite_slots: tuple[int, int, int],
    alias_modes: tuple[int, ...],
    evidence_profile: str,
    catalog_size: int,
) -> Bundle:
    queries = _queries(catalog_size)
    obligations = tuple(
        Obligation(
            oid=f"report_{i}",
            release_s=start_s + i * CADENCE_S,
            deadline_s=start_s + (i + 1) * CADENCE_S,
        )
        for i in range(3)
    )

    rescue_slots: list[int] = []
    for i, sat in enumerate(satellite_slots):
        deadline = obligations[i].deadline_s
        rescue = min(sat + 600, deadline - 60)
        if rescue <= sat:
            raise ValueError("satellite opportunity leaves no later terrestrial rescue slot")
        rescue_slots.append(rescue)

    worlds: list[World] = []
    seen_mode_count: Counter[int] = Counter()
    for mode in alias_modes:
        suffix = seen_mode_count[mode]
        seen_mode_count[mode] += 1
        terrestrial = tuple(
            rescue_slots[i] for i in range(3) if i != mode
        )
        worlds.append(
            World(
                world_id=f"mode{mode}-v{suffix}",
                terrestrial_slots=terrestrial,
                evidence_values=_mode_evidence(
                    mode,
                    profile=evidence_profile,
                    queries=queries,
                ),
            )
        )

    fixed = {
        start_s,
        *(o.release_s for o in obligations),
        *(o.deadline_s for o in obligations),
        *satellite_slots,
        *rescue_slots,
    }
    coords = {
        "phase_index": phase_index,
        "start_s": start_s,
        "satellite_slots": satellite_slots,
        "alias_modes": alias_modes,
        "evidence_profile": evidence_profile,
        "catalog_size": catalog_size,
    }
    return Bundle(
        bundle_id="v03-" + _hash(coords),
        fixed_event_times=tuple(sorted(fixed)),
        obligations=obligations,
        satellite_slots=satellite_slots,
        worlds=tuple(worlds),
        satellite_budget=1,
        queries=queries,
        initial_public_observation=(
            ("warning", "orange"),
            ("report_period_s", str(CADENCE_S)),
            ("gateway_health", "stale"),
            ("receipt_state", "stale"),
            ("satellite_budget", "1"),
        ),
    )


def label_bundle(bundle: Bundle) -> tuple[str, tuple[str, ...], bool, bool]:
    all_query_ids = frozenset(q.query_id for q in bundle.queries)
    no_query = solve(bundle, disabled_queries=all_query_ids)
    exact = solve(bundle)
    if no_query["solvable"]:
        return "NO_PAID_QUERY", (), True, True
    if not exact["solvable"]:
        return "INFORMATION_INFEASIBLE", (), False, False
    plan, _ = exhaustive_query_search(bundle)
    return plan.mode, plan.selected_query_ids, False, True


def generate(
    *,
    catalog_size: int = 5,
    phase_limit: int = 8,
) -> list[GeneratedBundle]:
    rows: list[GeneratedBundle] = []
    for phase_index, (start, sat_slots) in enumerate(_phase_groups(phase_limit)):
        for alias_modes in ALIAS_MODE_SETS:
            for profile in EVIDENCE_PROFILES:
                bundle = build_bundle(
                    phase_index=phase_index,
                    start_s=start,
                    satellite_slots=sat_slots,
                    alias_modes=alias_modes,
                    evidence_profile=profile,
                    catalog_size=catalog_size,
                )
                outcome, selected, no_query, exact = label_bundle(bundle)
                rows.append(
                    GeneratedBundle(
                        bundle=bundle,
                        coordinates={
                            "phase_index": phase_index,
                            "start_s": start,
                            "alias_modes": list(alias_modes),
                            "evidence_profile": profile,
                            "catalog_size": catalog_size,
                            "cadence_s": CADENCE_S,
                            "elevation_mask_deg": MASK_DEG,
                        },
                        outcome_class=outcome,
                        selected_query_ids=selected,
                        no_query_solvable=no_query,
                        exact_solvable=exact,
                    )
                )
    return rows


def summarize(rows: Iterable[GeneratedBundle]) -> dict[str, Any]:
    rows = list(rows)
    return {
        "bundle_count": len(rows),
        "outcome_counts": dict(sorted(Counter(r.outcome_class for r in rows).items())),
        "phase_count": len({r.coordinates["phase_index"] for r in rows}),
        "alias_patterns": len({tuple(r.coordinates["alias_modes"]) for r in rows}),
        "evidence_profiles": len({r.coordinates["evidence_profile"] for r in rows}),
        "catalog_sizes": sorted({r.coordinates["catalog_size"] for r in rows}),
    }


if __name__ == "__main__":
    print(json.dumps(summarize(generate()), indent=2, sort_keys=True))
