#!/usr/bin/env python3
"""Small staged exact pilot for the frozen v0.7 gateway-local placement.

The pilot selects one lexicographically-smallest case per placement-relevant
axis cell:

  composition × candidate process × terrestrial capacity
  × feedback profile × fallback mode

Remote-query timing is excluded because the placement contract makes
receipt-summary owner-local at the gateway. Selection never uses solver or
baseline outcomes.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
import argparse
import gzip
import json
from pathlib import Path
import time
from typing import Any

from layer1_v07_gateway_oracle_adapter import (
    gateway_structure_id,
    solve_gateway_reference,
)


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RUN = ROOT / "local_research/current/benchmark/generated/layer1-v0.7-preoracle-r1"


def _sha(path: Path) -> str:
    h = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _rows(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def _base_meta(run: Path) -> dict[str, dict[str, Any]]:
    """Load only selection metadata, never the full 100k-base universe.

    The first implementation retained every complete base row here.  v0.7 base
    rows contain service worlds and satellite opportunity lists, so even a
    one-cell pilot inherited full-universe object memory.  Selection only needs
    six scalar fields; complete base rows are streamed again after selection
    and retained only for the selected case ids.
    """
    out = {}
    for row in _rows(run / "base-scenarios.jsonl.gz"):
        composition = row["composition"]
        out[str(row["base_id"])] = {
            "base_structure_id": str(row["base_structure_id"]),
            "obligations_per_stream": int(composition["obligations_per_stream"]),
            "phase_mode": str(composition["phase_mode"]),
            "service_process": str(row["service_process"]["family"]),
            "service_role": str(row["service_process"]["role"]),
            "terr_capacity": int(row["terrestrial"]["capacity_units_per_opportunity"]),
        }
    return out


def _load_selected_bases(run: Path, base_ids: set[str]) -> dict[str, dict[str, Any]]:
    """Stream the base artifact and retain only bases used by selected cells."""

    remaining = set(base_ids)
    out: dict[str, dict[str, Any]] = {}
    if not remaining:
        return out
    for row in _rows(run / "base-scenarios.jsonl.gz"):
        base_id = str(row["base_id"])
        if base_id not in remaining:
            continue
        out[base_id] = row
        remaining.remove(base_id)
        if not remaining:
            break
    if remaining:
        missing = ", ".join(sorted(remaining)[:5])
        raise KeyError(f"selected cases reference missing base ids: {missing}")
    return out


def _cell_key(meta: dict[str, Any], case: dict[str, Any]) -> tuple[Any, ...]:
    return (
        meta["obligations_per_stream"],
        meta["phase_mode"],
        meta["service_process"],
        meta["terr_capacity"],
        str(case["feedback_profile"]),
        str(case["fallback_budget_mode"]),
    )


def _select(
    run: Path,
    meta: dict[str, dict[str, Any]],
    *,
    service_roles: set[str],
    fallback_modes: set[str],
    obligations_per_stream: set[int] | None = None,
    phase_modes: set[str] | None = None,
    service_processes: set[str] | None = None,
    terr_capacities: set[int] | None = None,
    feedback_profiles: set[str] | None = None,
) -> dict[tuple[Any, ...], dict[str, Any]]:
    selected: dict[tuple[Any, ...], dict[str, Any]] = {}
    for case in _rows(run / "cases.jsonl.gz"):
        m = meta[str(case["base_id"])]
        if m["service_role"] not in service_roles:
            continue
        if str(case["fallback_budget_mode"]) not in fallback_modes:
            continue
        if obligations_per_stream and m["obligations_per_stream"] not in obligations_per_stream:
            continue
        if phase_modes and m["phase_mode"] not in phase_modes:
            continue
        if service_processes and m["service_process"] not in service_processes:
            continue
        if terr_capacities and m["terr_capacity"] not in terr_capacities:
            continue
        if feedback_profiles and str(case["feedback_profile"]) not in feedback_profiles:
            continue
        key = _cell_key(m, case)
        old = selected.get(key)
        if old is None or str(case["case_id"]) < str(old["case_id"]):
            selected[key] = case
    return selected


def _compact(reference: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": reference["status"],
        "solvable": reference["solvable"],
        "memo_nodes": reference["memo_nodes"],
        "attempt_lattice_size": reference["attempt_lattice_size"],
    }


def staged_disposition(
    base: dict[str, Any],
    case: dict[str, Any],
    *,
    max_memo_nodes: int,
) -> tuple[str, dict[str, dict[str, Any]], str]:
    references: dict[str, dict[str, Any]] = {}

    blind = solve_gateway_reference(
        base,
        case,
        "blind_open_loop",
        max_memo_nodes=max_memo_nodes,
    )
    references["blind_open_loop"] = _compact(blind)
    if blind["status"] == "SEARCH_LIMIT":
        return "UNRESOLVED_COMPUTATION", references, "blind_open_loop"
    if blind["solvable"] is True:
        return "BLIND_OPEN_LOOP_SOLVED", references, "blind_open_loop"

    full = solve_gateway_reference(
        base,
        case,
        "full_current",
        max_memo_nodes=max_memo_nodes,
    )
    references["full_current"] = _compact(full)
    if full["status"] == "SEARCH_LIMIT":
        return "UNRESOLVED_COMPUTATION", references, "full_current"
    if full["solvable"] is False:
        return "FULL_CURRENT_CAUSAL_INFEASIBLE", references, "full_current"

    natural = solve_gateway_reference(
        base,
        case,
        "natural_feedback",
        max_memo_nodes=max_memo_nodes,
    )
    references["natural_feedback"] = _compact(natural)
    if natural["status"] == "SEARCH_LIMIT":
        return "UNRESOLVED_COMPUTATION", references, "natural_feedback"
    if natural["solvable"] is True:
        return "GATEWAY_NATURAL_FEEDBACK_REQUIRED_CANDIDATE", references, "natural_feedback"
    return "INFORMATION_INFEASIBLE_UNDER_GATEWAY_HISTORY", references, "natural_feedback"


def audit(
    run: Path,
    *,
    max_memo_nodes: int,
    service_roles: set[str],
    fallback_modes: set[str],
    obligations_per_stream: set[int] | None = None,
    phase_modes: set[str] | None = None,
    service_processes: set[str] | None = None,
    terr_capacities: set[int] | None = None,
    feedback_profiles: set[str] | None = None,
) -> dict[str, Any]:
    meta = _base_meta(run)
    selected = _select(
        run,
        meta,
        service_roles=service_roles,
        fallback_modes=fallback_modes,
        obligations_per_stream=obligations_per_stream,
        phase_modes=phase_modes,
        service_processes=service_processes,
        terr_capacities=terr_capacities,
        feedback_profiles=feedback_profiles,
    )
    selected_bases = _load_selected_bases(
        run,
        {str(case["base_id"]) for case in selected.values()},
    )

    disposition_counts = Counter()
    by_process: dict[str, Counter[str]] = defaultdict(Counter)
    by_composition: dict[str, Counter[str]] = defaultdict(Counter)
    by_feedback: dict[str, Counter[str]] = defaultdict(Counter)
    decisive_reference_counts = Counter()
    rows = []
    started_all = time.time()

    for ordinal, (key, case) in enumerate(sorted(selected.items()), start=1):
        m = meta[str(case["base_id"])]
        base = selected_bases[str(case["base_id"])]
        started = time.time()
        disposition, references, decisive = staged_disposition(
            base,
            case,
            max_memo_nodes=max_memo_nodes,
        )
        elapsed = time.time() - started
        disposition_counts[disposition] += 1
        by_process[m["service_process"]][disposition] += 1
        composition = f"{m['obligations_per_stream']}x2::{m['phase_mode']}"
        by_composition[composition][disposition] += 1
        by_feedback[str(case["feedback_profile"])][disposition] += 1
        decisive_reference_counts[decisive] += 1
        rows.append(
            {
                "ordinal": ordinal,
                "axis_cell": {
                    "obligations_per_stream": key[0],
                    "phase_mode": key[1],
                    "service_process": key[2],
                    "terr_capacity": key[3],
                    "feedback_profile": key[4],
                    "fallback_mode": key[5],
                    "placement": "GATEWAY_LOCAL_PRIMARY",
                },
                "case_id": case["case_id"],
                "base_id": case["base_id"],
                "source_structure_id": case["structure_id"],
                "gateway_structure_id": gateway_structure_id(base, case),
                "source_task_case_id": base["task"]["task_case_id"],
                "geometry_signature_id": base["satellite"]["geometry_signature_id"],
                "selected_query_delay_ratio": case["remote_query"]["response_delay_ratio"],
                "query_delay_is_inactive_at_placement": True,
                "disposition": disposition,
                "decisive_reference": decisive,
                "elapsed_s": round(elapsed, 6),
                "references": references,
            }
        )

    return {
        "schema_version": "0.1",
        "stage": "V07_GATEWAY_LOCAL_MECHANISM_PILOT",
        "placement": "GATEWAY_LOCAL_PRIMARY",
        "official_generation_run": run.name,
        "official_generation_manifest_sha256": _sha(run / "MANIFEST.json"),
        "selection_rule": "one lexicographically-smallest case_id per composition×candidate-process×capacity×feedback×fallback cell after placement-specific query-delay dedupe",
        "selection_depends_on_method_or_baseline": False,
        "service_roles": sorted(service_roles),
        "fallback_modes": sorted(fallback_modes),
        "selection_filters": {
            "obligations_per_stream": sorted(obligations_per_stream or []),
            "phase_modes": sorted(phase_modes or []),
            "service_processes": sorted(service_processes or []),
            "terr_capacities": sorted(terr_capacities or []),
            "feedback_profiles": sorted(feedback_profiles or []),
        },
        "max_memo_nodes_per_reference": max_memo_nodes,
        "axis_cell_count": len(selected),
        "elapsed_s": round(time.time() - started_all, 3),
        "disposition_counts": dict(sorted(disposition_counts.items())),
        "decisive_reference_counts": dict(sorted(decisive_reference_counts.items())),
        "by_service_process": {
            key: dict(sorted(value.items())) for key, value in sorted(by_process.items())
        },
        "by_composition": {
            key: dict(sorted(value.items())) for key, value in sorted(by_composition.items())
        },
        "by_feedback_profile": {
            key: dict(sorted(value.items())) for key, value in sorted(by_feedback.items())
        },
        "rows": rows,
        "claim_boundary": [
            "This is a method-independent mechanism pilot, not a benchmark distribution estimate.",
            "Remote-query timing variants are exact duplicates under gateway-local placement and are collapsed before selection.",
            "UNRESOLVED_COMPUTATION is not counted as hardness, infeasibility or method failure.",
            "A natural-feedback candidate still requires intervention and ordinary-baseline gates before hard admission.",
            "No center-placement or paid-remote-evidence claim is made."
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--max-memo-nodes", type=int, default=50_000)
    parser.add_argument("--service-role", action="append", default=["CANDIDATE"])
    parser.add_argument("--fallback-mode", action="append", default=["TIGHT"])
    parser.add_argument("--obligations-per-stream", type=int, action="append")
    parser.add_argument("--phase-mode", action="append")
    parser.add_argument("--service-process", action="append")
    parser.add_argument("--terr-capacity", type=int, action="append")
    parser.add_argument("--feedback-profile", action="append")
    parser.add_argument(
        "--selection-only",
        action="store_true",
        help="select placement-specific axis cells without invoking any exact reference",
    )
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.selection_only:
        meta = _base_meta(args.run.resolve())
        selected = _select(
            args.run.resolve(),
            meta,
            service_roles=set(args.service_role),
            fallback_modes=set(args.fallback_mode),
            obligations_per_stream=set(args.obligations_per_stream or []),
            phase_modes=set(args.phase_mode or []),
            service_processes=set(args.service_process or []),
            terr_capacities=set(args.terr_capacity or []),
            feedback_profiles=set(args.feedback_profile or []),
        )
        payload = {
            "stage": "V07_GATEWAY_LOCAL_SELECTION_ONLY",
            "axis_cell_count": len(selected),
            "selected": [
                {
                    "axis_cell": list(key),
                    "case_id": case["case_id"],
                    "base_id": case["base_id"],
                }
                for key, case in sorted(selected.items())
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    payload = audit(
        args.run.resolve(),
        max_memo_nodes=args.max_memo_nodes,
        service_roles=set(args.service_role),
        fallback_modes=set(args.fallback_mode),
        obligations_per_stream=set(args.obligations_per_stream or []),
        phase_modes=set(args.phase_mode or []),
        service_processes=set(args.service_process or []),
        terr_capacities=set(args.terr_capacity or []),
        feedback_profiles=set(args.feedback_profile or []),
    )
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
